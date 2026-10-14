from fastapi import APIRouter, HTTPException

from ..knowledge import answer_question, portfolio
from ..models import KnowledgeQuery
from ..record_creation import KnowledgeCreate, RecordConflict, create_knowledge

router = APIRouter(tags=["knowledge"])


@router.post("/knowledge/entries", status_code=201)
def add_knowledge(request: KnowledgeCreate):
    try:
        return create_knowledge(request)
    except RecordConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/knowledge/portfolio")
def product_portfolio():
    return portfolio()


@router.post("/knowledge/ask")
def knowledge_answer(request: KnowledgeQuery):
    try:
        return answer_question(request.question, request.category, request.product_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
