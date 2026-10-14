"""One synthetic provider request, without database reads or RAG retrieval."""
import argparse
import math
import sys
from pathlib import Path
from time import monotonic

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / '.env')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import llm


def run_check(timeout=None, stream=None):
    try:
        config = llm.chat_config()
        wait = timeout if timeout is not None else llm.qa_chat_timeout_seconds()
        if not math.isfinite(wait) or not 5 <= wait <= 120:
            raise ValueError('Timeout must be between 5 and 120 seconds.')
    except ValueError:
        print('FAIL: Invalid chat configuration. Check endpoint, model and timeout settings; no secrets were printed.')
        return 2
    if not config.api_key:
        print('BLOCKED: No chat key configured. Set it privately in backend/.env or your environment.')
        return 2
    use_stream = config.provider == 'nvidia' if stream is None else stream
    print(f'Provider: {config.provider}; model: {config.model}; streaming: {use_stream}; I/O timeout: {wait:g}s; automatic retries: 0.', flush=True)
    print('Sending one tiny synthetic request. No Supabase reads or RAG retrieval.', flush=True)
    started = monotonic()
    try:
        llm.request_chat_text(config, [{'role': 'user', 'content': 'Reply with exactly READY.'}],
                              timeout_seconds=wait, max_retries=0, stream=use_stream)
        elapsed = monotonic() - started
        print(f'PASS: Provider returned complete answer text in {elapsed:.1f}s. Response and reasoning text are not printed.')
        print('This verifies a minimal chat request only; it does not verify a full grounded Q&A answer.')
        return 0
    except Exception as exc:
        elapsed = monotonic() - started
        print(f'FAIL after {elapsed:.1f}s: {llm.failure_reason(exc)}')
        print('This request did not involve Supabase or RAG. Check provider availability and your network connection.')
        return 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeout', type=float, help='Provider I/O timeout, 5–120 seconds; defaults to the active Q&A setting.')
    parser.add_argument('--no-stream', action='store_true', help='Compare with the older non-streaming request mode.')
    args = parser.parse_args()
    raise SystemExit(run_check(args.timeout, stream=False if args.no_stream else None))
