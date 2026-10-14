"""One synthetic provider request, without database reads or RAG retrieval."""

import argparse
import math
import os
import sys
from pathlib import Path
from time import monotonic

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import llm


def run_check(timeout=None, stream=None):
    try:
        config = llm.chat_config()
        wait = timeout if timeout is not None else llm.qa_chat_timeout_seconds()
        if not math.isfinite(wait) or not 5 <= wait <= 120:
            raise ValueError("Timeout must be between 5 and 120 seconds.")
    except ValueError:
        print(
            "FAIL: Invalid chat configuration. Check endpoint, model and timeout settings; no secrets were printed."
        )
        return 2
    if not config.api_key:
        print(
            "BLOCKED: No chat key configured. Set it privately in backend/.env or your environment."
        )
        return 2
    use_stream = config.provider == "nvidia" if stream is None else stream
    print(
        f"Provider: {config.provider}; model: {config.model}; streaming: {use_stream}; I/O timeout: {wait:g}s; automatic retries: 0.",
        flush=True,
    )
    print("Sending one tiny synthetic request. No Supabase reads or RAG retrieval.", flush=True)
    started = monotonic()
    try:
        llm.request_chat_text(
            config,
            [{"role": "user", "content": "Reply with exactly READY."}],
            timeout_seconds=wait,
            max_retries=0,
            stream=use_stream,
        )
        elapsed = monotonic() - started
        print(
            f"PASS: Provider returned complete answer text in {elapsed:.1f}s. Response and reasoning text are not printed."
        )
        print(
            "This verifies a minimal chat request only; it does not verify a full grounded Q&A answer."
        )
        return 0
    except Exception as exc:
        elapsed = monotonic() - started
        print(f"FAIL after {elapsed:.1f}s: {llm.failure_reason(exc)}")
        print(
            "This request did not involve Supabase or RAG. Check provider availability and your network connection."
        )
        return 1


def run_rag_check(timeout=None):
    """Use the actual Q&A route logic without printing answer or provider text."""
    previous = os.getenv("QA_CHAT_TIMEOUT_SECONDS")
    try:
        if timeout is not None:
            os.environ["QA_CHAT_TIMEOUT_SECONDS"] = str(timeout)
        wait = llm.qa_chat_timeout_seconds()
        if not llm.chat_enabled():
            print(
                "BLOCKED: No chat key configured. Set it privately in backend/.env or your environment."
            )
            return 2
        print(
            f"Testing grounded Q&A with current knowledge records; chat timeout: {wait:g}s.",
            flush=True,
        )
        print(
            "This is read-only. It makes one chat request and may use provider credits.", flush=True
        )
        from app.business_data import BusinessDataUnavailable
        from app.knowledge import answer_question

        started = monotonic()
        try:
            result = answer_question(
                "Can motorized roller blinds use smartphone control and a rechargeable battery?"
            )
        except BusinessDataUnavailable:
            print(
                "FAIL: Current knowledge records could not be read. Check business-data configuration and database access."
            )
            return 1
        print(
            f"Result after {monotonic() - started:.1f}s: generation={result['generation_mode']}; "
            f"retrieval={result['retrieval_mode']}; knowledge={result['knowledge_source']}; citations={len(result['citations'])}."
        )
        if result["generation_mode"] == "llm":
            print(
                "PASS: Generated answer passed format and source-ID checks. Answer and reasoning text are not printed."
            )
            return 0
        print(
            "FAIL: "
            + (
                result.get("generation_warning")
                or "A generated answer was not returned. Check the current evidence and chat configuration."
            )
        )
        return 1
    except Exception as exc:
        print("FAIL: " + llm.failure_reason(exc))
        return 1
    finally:
        if previous is None:
            os.environ.pop("QA_CHAT_TIMEOUT_SECONDS", None)
        else:
            os.environ["QA_CHAT_TIMEOUT_SECONDS"] = previous


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--timeout",
        type=float,
        help="Provider I/O timeout, 5–120 seconds; defaults to the active Q&A setting.",
    )
    parser.add_argument(
        "--no-stream",
        action="store_true",
        help="Compare with the older non-streaming request mode.",
    )
    parser.add_argument(
        "--rag",
        action="store_true",
        help="Test actual grounded Q&A using current knowledge records, without printing answer text.",
    )
    args = parser.parse_args()
    if args.rag and args.no_stream:
        parser.error("--no-stream is only available for the minimal provider check.")
    raise SystemExit(
        run_rag_check(args.timeout)
        if args.rag
        else run_check(args.timeout, stream=False if args.no_stream else None)
    )
