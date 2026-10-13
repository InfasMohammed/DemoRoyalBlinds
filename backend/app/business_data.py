"""Read fresh business snapshots from Supabase; offline fixtures are explicit."""
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator
from supabase import create_client
from .models import ProjectRequest

DATA_DIR = Path(__file__).parent / 'data'
Number = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]
Identifier = Annotated[str, Field(pattern=r'^[A-Za-z0-9_-]+$', min_length=1, max_length=100)]


class BusinessDataUnavailable(RuntimeError):
    pass


def data_source():
    configured = bool(os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_SERVICE_ROLE_KEY'))
    mode = os.getenv('BUSINESS_DATA_SOURCE', 'auto')
    if mode not in ('auto', 'supabase', 'demo'):
        raise ValueError('BUSINESS_DATA_SOURCE must be auto, supabase or demo.')
    if mode == 'supabase' and not configured:
        raise BusinessDataUnavailable('Supabase business data requires both backend Supabase variables.')
    return 'supabase' if mode == 'supabase' or (mode == 'auto' and configured) else 'demo'


def database_snapshot(function):
    try:
        client = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])
        result = client.rpc(function, {}).execute().data
        if not isinstance(result, dict):
            raise ValueError('Snapshot was not an object.')
        return result
    except Exception as exc:
        raise BusinessDataUnavailable('Could not read Supabase business data. Run supabase/database_setup.sql and check the backend server key and connection. No fixture fallback was used.') from exc


class Record(BaseModel):
    model_config = ConfigDict(extra='ignore')


class Material(Record):
    id: Identifier
    name: str = Field(min_length=1)
    sku: str
    roll_width_m: Positive
    stock_lm: Number
    cost_per_lm: Number
    lead_days: int = Field(ge=0, le=3650)
    transmission: str
    color: str
    compatible: list[Identifier] = Field(min_length=1)
    source: str


class Product(Record):
    name: str = Field(min_length=1)
    estimation_kind: Literal['roller', 'curtain']
    knowledge_product_id: Identifier
    hardware_aed: Number
    motor_aed: Number
    labor_hours: Positive
    install_hours: Positive
    max_width_m: Positive
    max_height_m: Positive
    width_allowance_m: Number
    length_allowance_m: Number
    fullness: Positive
    source: str


class Policy(Record):
    labor_aed_hour: Number
    installation_aed_hour: Number
    margin_fraction: float = Field(ge=0, lt=1, allow_inf_nan=False)
    vat_fraction: Number
    waste_fraction: Number
    factory_hours_day: Positive
    installation_hours_day: Positive
    queue_business_days: int = Field(ge=0, le=365)
    quality_business_days: int = Field(ge=1, le=365)
    working_weekdays: list[int] = Field(min_length=1, max_length=7)
    holidays: list[date]
    currency: Literal['AED']
    quote_exclusions: list[str]
    source: str

    @model_validator(mode='after')
    def calendar_valid(self):
        if len(set(self.working_weekdays)) != len(self.working_weekdays) or any(day not in range(7) for day in self.working_weekdays):
            raise ValueError('Working weekdays must be unique values from 0 to 6.')
        return self


class Scenario(Record):
    id: Identifier
    title: str
    category: str
    description: str
    deadline_days: int = Field(ge=0, le=3650)
    request: dict

    @model_validator(mode='after')
    def request_valid(self):
        self.request = ProjectRequest.model_validate({**self.request, 'due_date': date.max}).model_dump(mode='json', exclude={'due_date'})
        return self


class Operations(Record):
    fabrics: list[Material] = Field(min_length=1)
    products: dict[Identifier, Product] = Field(min_length=1)
    policy: Policy
    checklists: dict[Identifier, list[str]]
    scenarios: list[Scenario]
    provenance: str
    is_sample: bool

    @model_validator(mode='after')
    def references_valid(self):
        ids = [f.id for f in self.fabrics]
        if len(set(ids)) != len(ids):
            raise ValueError('Duplicate material IDs.')
        for fabric in self.fabrics:
            if not set(fabric.compatible) <= self.products.keys():
                raise ValueError('Unknown product in material compatibility.')
        if any(not self.checklists.get(id) for id in self.products):
            raise ValueError('Each product needs an inspection checklist.')
        for scenario in self.scenarios:
            if scenario.request.get('product') not in self.products or scenario.request.get('fabric_id') not in ids:
                raise ValueError('Scenario references an unknown product or material.')
        return self


def load_operations():
    source = data_source()
    raw = database_snapshot('get_operations_snapshot') if source == 'supabase' else json.loads((DATA_DIR / 'demo_operations.json').read_text())
    try:
        result = Operations.model_validate(raw).model_dump(mode='json')
    except Exception as exc:
        raise BusinessDataUnavailable('Business records are missing or invalid. Check product, material, policy, checklist and scenario records before analyzing an order.') from exc
    return {**result, 'data_source': source, 'fetched_at': datetime.now(timezone.utc).isoformat()}


class KnowledgeProduct(Record):
    id: Identifier
    name: str
    category: Literal['internal', 'external']
    source_url: HttpUrl
    quote_products: list[Identifier]


class Passage(Record):
    id: Identifier
    document_id: Identifier
    title: str
    heading: str
    category: Literal['internal', 'external', 'smart', 'company']
    product_ids: list[Identifier]
    content: str = Field(min_length=1, max_length=30000)
    source_url: HttpUrl
    source_kind: str


class KnowledgeCategory(Record):
    id: Literal['internal', 'external', 'smart', 'company']
    name: str = Field(min_length=1)
    description: str
    source_url: HttpUrl


class KnowledgeMetadata(Record):
    categories: list[KnowledgeCategory] = Field(min_length=1)
    limitations: list[str]
    provenance: str = Field(min_length=1)
    source_kind: str
    captured_on: date


def load_database_knowledge():
    raw = database_snapshot('get_company_knowledge_snapshot')
    try:
        metadata = KnowledgeMetadata.model_validate(raw['metadata']).model_dump(mode='json')
        products = [KnowledgeProduct.model_validate(row).model_dump(mode='json') for row in raw['products']]
        passages = [Passage.model_validate(row).model_dump(mode='json') for row in raw['chunks']]
        if not products or not passages or len({row['id'] for row in passages}) != len(passages):
            raise ValueError('Knowledge corpus is empty or has duplicate identifiers.')
        product_ids = {p['id'] for p in products}
        if len(product_ids) != len(products) or any(not set(p['product_ids']) <= product_ids for p in passages):
            raise ValueError('Knowledge product references are invalid.')
        return {**metadata, 'products': products, 'chunks': passages, 'data_source': 'supabase'}
    except Exception as exc:
        raise BusinessDataUnavailable('Supabase knowledge records are missing or invalid. Check company_products, company_knowledge_chunks and company_knowledge_settings.') from exc
