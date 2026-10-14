"""Company questions must use current company facts, never a product draft."""

from copy import deepcopy

import pytest

from app import knowledge


@pytest.fixture
def corpus(monkeypatch):
    data = {
        **deepcopy(knowledge.DATA),
        "chunks": deepcopy(knowledge.CHUNKS),
        "data_source": "supabase",
    }
    data["chunks"].append(
        {
            "id": "RB-USER-WOOD",
            "document_id": "WOOD",
            "title": "Indoor wood decoration",
            "heading": "Customer enquiry",
            "category": "company",
            "product_ids": [],
            "source_url": "https://example.com/wood",
            "source_kind": "user_added_content",
            "content": "Indoor wood decoration is a proposed customer enquiry requiring company confirmation. During consultation, collect the room type, installation location, measurements, preferred wood appearance, colour, finish, budget and requested completion date. Separate wood-decoration or wall-panelling services have not been confirmed in the supplied company information.",
        }
    )
    monkeypatch.setattr(knowledge, "load_corpus", lambda: data)
    # Direct company answers must remain grounded even when generation/indexing
    # are configured and an LLM would omit its required source citations.
    monkeypatch.setenv("LLM_API_KEY", "fake-provider-key")
    monkeypatch.setenv("KNOWLEDGE_RETRIEVAL_MODE", "supabase_vector")
    monkeypatch.setattr(
        knowledge,
        "grounded_chat",
        lambda *_args, **_kwargs: pytest.fail("Basic facts must not depend on generation."),
    )
    monkeypatch.setattr(
        knowledge,
        "embedding_client",
        lambda: pytest.fail("Basic facts use current records directly."),
    )
    return data


@pytest.mark.parametrize(
    "question,expected,source",
    [
        ("who is the owner of the company", "Al Jallaf Family", "RB-COMPANY-01"),
        ("Who owns Royal Blinds?", "Al Jallaf Family", "RB-COMPANY-01"),
        ("Company ownership", "Al Jallaf Family", "RB-COMPANY-01"),
        ("give me the contact of company", "info@royalblinds.com", "RB-COMPANY-04"),
        ("What are your contacts?", "+971 4 347 4760", "RB-COMPANY-04"),
        ("What is the company phone number?", "+971 2 555 7393", "RB-COMPANY-04"),
        ("What is your email address?", "info@royalblinds.com", "RB-COMPANY-04"),
        ("give me the location of company", "Al Quoz", "RB-COMPANY-02"),
        ("Where is Royal Blinds located?", "Abu Dhabi", "RB-COMPANY-04"),
        ("Where are you located?", "Dubai", "RB-COMPANY-04"),
        ("When was the company established?", "1989", "RB-COMPANY-01"),
        ("Tell me the company history", "1989", "RB-COMPANY-01"),
    ],
)
def test_company_fact_questions_exclude_the_misclassified_wood_enquiry(
    corpus, question, expected, source
):
    result = knowledge.answer_question(question)
    assert result["generation_mode"] == "company_profile"
    assert result["retrieval_mode"] == "company_profile"
    assert result["knowledge_source"] == "supabase"
    assert expected in result["answer"]
    assert f"[{source}]" in result["answer"]
    assert "wood" not in result["answer"].lower()
    assert "RB-USER-WOOD" not in {c["id"] for c in result["citations"]}
    assert not result["needs_review"]


def test_profile_lookup_uses_changed_database_values_and_arbitrary_ids(corpus):
    corpus["chunks"] = [
        corpus["chunks"][-1],
        {
            "id": "CURRENT-OWNERSHIP",
            "document_id": "CURRENT",
            "title": "Company update",
            "heading": "Ownership",
            "category": "company",
            "product_ids": [],
            "source_url": "https://example.com/profile",
            "source_kind": "user_added_content",
            "content": "Owner: Example Holdings Group.",
        },
    ]
    result = knowledge.answer_question("Who owns the company?")
    assert result["answer"] == '"Owner: Example Holdings Group." [CURRENT-OWNERSHIP]'
    assert "Al Jallaf" not in result["answer"]


def test_missing_ownership_does_not_fall_back_to_seed_or_enquiry(corpus):
    corpus["chunks"] = [c for c in corpus["chunks"] if c["id"] != "RB-COMPANY-01"]
    result = knowledge.answer_question("Who owns the company?")
    assert result["generation_mode"] == "no_evidence"
    assert result["needs_review"]
    assert result["citations"] == []
    assert "do not confirm" in result["answer"]
    assert "wood" not in result["answer"].lower()


def test_explicit_category_is_respected_and_can_be_cleared(corpus):
    result = knowledge.answer_question("Who owns the company?", "internal")
    assert result["generation_mode"] == "no_evidence"
    assert result["citations"] == []
    assert "Select All categories or Company profile" in result["answer"]
    assert "Al Jallaf" in knowledge.answer_question("Who owns the company?", "company")["answer"]


def test_owner_is_not_assumed_to_be_the_founder(corpus):
    result = knowledge.answer_question("Who founded Royal Blinds?")
    assert result["generation_mode"] == "no_evidence"
    assert "founder" in result["answer"]
    assert "Al Jallaf" not in result["answer"]


def test_combined_questions_cover_both_requested_topics(corpus):
    result = knowledge.answer_question("Who owns the company and where are its offices?")
    assert (
        "Al Jallaf" in result["answer"]
        and "Abu Dhabi" in result["answer"]
        and "Al Quoz" in result["answer"]
    )


def test_product_enquiries_are_not_company_location_or_contact_questions(corpus, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("KNOWLEDGE_RETRIEVAL_MODE", "local")
    for question in [
        "What information should we collect for an indoor wood decoration enquiry?",
        "Where can Royal Blinds products be used?",
        "Can motorized blinds use phone control?",
        "ultramarine showroom panel protocol",
    ]:
        result = knowledge.answer_question(question)
        assert result["retrieval_mode"] != "company_profile"
    assert (
        "installation location"
        in knowledge.answer_question(
            "What information should we collect for an indoor wood decoration enquiry?"
        )["answer"]
    )


def test_location_lookup_does_not_append_the_company_timeline(corpus):
    result = knowledge.answer_question("Give me the company location")
    assert "timeline" not in result["answer"]
    assert "premise expansion" not in result["answer"]
    assert {c["id"] for c in result["citations"]} == {"RB-COMPANY-02", "RB-COMPANY-04"}


def test_confirmed_certifications_still_need_certificate_evidence(corpus, monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_RETRIEVAL_MODE", "local")
    result = knowledge.answer_question("Are the company certifications currently valid?", "company")
    assert result["generation_mode"] == "evidence_gap" and result["needs_review"]
