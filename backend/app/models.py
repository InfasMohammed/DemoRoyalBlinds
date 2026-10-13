from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class ProjectRequest(BaseModel):
    customer: str = Field(min_length=2, max_length=100)
    project_name: str = Field(min_length=2, max_length=120)
    brief: str = Field(min_length=10, max_length=4000)
    product: str = Field(default='motorized_roller', min_length=1, max_length=100, pattern=r'^[A-Za-z0-9_-]+$')
    fabric_id: str = Field(default='linen_blackout', min_length=1, max_length=100, pattern=r'^[A-Za-z0-9_-]+$')
    quantity: int = Field(default=24, ge=1, le=500)
    width_m: float = Field(default=1.8, ge=0.3, le=4)
    height_m: float = Field(default=2.4, ge=0.5, le=5)
    due_date: date
    site: str = Field(default='Business Bay, Dubai', min_length=2, max_length=160)


class ApprovalRequest(BaseModel):
    reviewer: str = Field(min_length=2, max_length=100)
    measurements_confirmed: bool
    specification_confirmed: bool
    commercial_terms_confirmed: bool


class AgentNarrative(BaseModel):
    summary: str = Field(max_length=700)
    recommendation: str = Field(max_length=700)


class KnowledgeQuery(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    category: Literal['internal', 'external', 'smart', 'company'] | None = None
    product_id: str | None = Field(default=None, max_length=60)
