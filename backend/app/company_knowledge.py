"""Answer basic company questions from relevant, current source sentences.

Topic patterns describe the question and evidence type, never company values
or fixed source IDs. Even a product enquiry filed under company must contain
an actual company fact to be selected.
"""

import re


def matches(pattern, text):
    return bool(re.search(pattern, text, re.I))


def company_topics(question, category=None):
    text = question.lower().strip()
    without_brand = re.sub(r"\broyal\s+blinds?\b", "", text)
    product_question = matches(
        r"\b(products?|rollers?|blinds?|curtains?|awnings?|pergolas?|shades?|motors?|motorized|battery|fabrics?)\b",
        without_brand,
    )
    if product_question and not matches(
        r"\b(owners?|ownership|offices?|headquarters|factory|history|founded|established)\b",
        without_brand,
    ):
        return []
    subject = category == "company" or matches(
        r"\b(company|royal\s+blinds?|your|you|head\s*office|headquarters|offices?|showrooms?|branches|factory)\b",
        text,
    )
    bare = re.fullmatch(
        r"(?:who (?:is|are) (?:the )?)?(?:owners?|ownership|contact(?: details)?|address|locations?)\??",
        text,
    )
    if not subject and not bare:
        return []
    # These ask about a customer's enquiry/site, not corporate profile facts.
    if matches(r"\b(enquir\w*|collect|decoration|panelling|measurements)\b", text):
        return []
    topics = []
    if matches(r"\b(owners?|ownership|owns?|owned|belongs)\b", text):
        topics.append("ownership")
    founder = matches(r"\bfounders?\b|who.*\b(founded|started|established)\b|\bfounded by\b", text)
    if founder:
        topics.append("founder")
    if not founder and matches(r"\b(founded|established|inception|began|started)\b|how old", text):
        topics.append("founding")
    contact = matches(r"\b(contacts?|reach|contacting)\b", text)
    phone = matches(r"\b(telephone|phones?|mobile|call)\b", text) and not matches(
        r"\b(control|operate|motorized|battery)\b", text
    )
    email = matches(r"\b(e-?mails?)\b", text)
    if contact:
        topics.append("contact")
    else:
        if phone:
            topics.append("phone")
        if email:
            topics.append("email")
    if (
        matches(r"\b(locations?|located|where)\b", text)
        or (matches(r"\baddress\b", text) and not email)
        or re.fullmatch(
            r"(?:(?:give me|show me|list|what are|where are) (?:the |your |company )?)?(?:head offices?|headquarters|offices?|showrooms?|branches)\??",
            text,
        )
    ):
        topics.append("location")
    if matches(r"\b(history|milestones?|timeline|anniversary)\b", text):
        topics.append("history")
    if not topics and matches(
        r"\b(profile|background|about|describe)\b|who is royal\s+blinds", text
    ):
        topics.append("background")
    return topics


def topic_sentence(topic, sentence):
    if "?" in sentence or matches(
        r"\b(proposed|unconfirmed|unknown|might|whether|collect)\b|"
        r"\bnot (?:confirmed|provided|supplied|owned|founded|located)\b|"
        r"\brequires? (?:company )?confirmation\b",
        sentence,
    ):
        return False
    email = matches(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", sentence)
    phone = matches(r"\b(telephone|phone|tel|call|mobile)\b", sentence) and matches(
        r"\+?\d[\d ()-]{6,}\d", sentence
    )
    if topic == "contact":
        return email or phone
    if topic == "phone":
        return phone
    if topic == "email":
        return email
    if topic == "ownership":
        return matches(
            r"\bowned\s+by\b|\bowners?\s*(?::|is\b|are\b)|\bownership\s*(?::|is\b|belongs\b|rests\b)",
            sentence,
        )
    if topic == "founder":
        return matches(r"\bfounded\s+by\b|\bfounders?\s*(?::|is\b|are\b)", sentence)
    if topic == "location":
        if matches(r"\b(timeline|milestones?)\b", sentence):
            return False
        facility = matches(
            r"\b(offices?|showrooms?|factory|factories|headquarters|branches|branch|production (?:unit|plant)|premises)\b",
            sentence,
        )
        place = matches(r"\b(located|based|in|at)\b|:", sentence)
        return facility and place
    if topic == "founding":
        return matches(r"\b(established|founded|inception|began|started)\b", sentence) and matches(
            r"\b(?:18|19|20)\d{2}\b", sentence
        )
    if topic == "history":
        return matches(r"\b(?:18|19|20)\d{2}\b", sentence) and matches(
            r"\b(timeline|milestone|established|inception|expansion|anniversary|commenced|expanded)\b",
            sentence,
        )
    return matches(r"\b(established|owned by|manufacturer|supplies|production unit)\b", sentence)


def company_answer(question, category, product_id, corpus):
    if product_id:
        return None
    topics = company_topics(question, category)
    if not topics:
        return None
    result = {
        "citations": [],
        "retrieval_mode": "company_profile",
        "warning": None,
        "knowledge_source": corpus["data_source"],
        "company_topics": topics,
        "generation_warning": None,
        "needs_review": False,
    }
    if category not in (None, "company"):
        return {
            **result,
            "answer": "This is a company-profile question. Select All categories or Company profile to search those sources.",
            "generation_mode": "no_evidence",
            "needs_review": True,
        }
    selected = []
    seen = set()
    missing = []
    for topic in topics:
        found = []
        for chunk in corpus["chunks"]:
            if chunk["category"] != "company" or chunk["product_ids"]:
                continue
            context = f"{chunk['title']} {chunk['heading']}"
            if matches(r"\b(draft|proposed|enquir(?:y|ies)|intake)\b", context):
                continue
            if not matches(
                r"\b(company|corporate|profile|background|contacts?|locations?|offices?|ownership|owners?|history|milestones?|founders?|founding|headquarters)\b|about us",
                context,
            ):
                continue
            for sentence in re.split(r"(?<=[.!?])\s+|\n+", chunk["content"]):
                sentence = sentence.strip()
                if (
                    not sentence
                    or len(sentence.split()) > 100
                    or not topic_sentence(topic, sentence)
                ):
                    continue
                # Prefer compact declarations over a timeline listing many dates.
                found.append((len(sentence.split()), chunk["id"], sentence, chunk))
        if not found:
            missing.append(topic)
        for _, _, sentence, chunk in sorted(found, key=lambda item: item[:3])[:4]:
            normalized = " ".join(sentence.casefold().split())
            if normalized not in seen:
                seen.add(normalized)
                selected.append((sentence, chunk))
    citations = {chunk["id"]: chunk for _, chunk in selected}
    lines = [f'"{sentence}" [{chunk["id"]}]' for sentence, chunk in selected]
    if missing:
        labels = {"founding": "founding date", "background": "company background"}
        details = ", ".join(labels.get(topic, topic) for topic in missing)
        lines.append(
            f"The current company sources do not confirm the requested {details}. Add a confirmed company-profile passage before answering this detail."
        )
    return {
        **result,
        "citations": list(citations.values()),
        "answer": "\n\n".join(lines),
        "generation_mode": "company_profile" if citations else "no_evidence",
        "needs_review": bool(missing),
    }
