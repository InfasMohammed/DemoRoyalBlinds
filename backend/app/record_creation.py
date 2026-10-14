"""Add records to Supabase without overwriting existing knowledge or stock."""
import os
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator
from postgrest.exceptions import APIError
from supabase import create_client

from .business_data import data_source, load_operations, load_database_knowledge, Identifier
from .catalog import today

Amount = Annotated[float, Field(ge=0, allow_inf_nan=False)]


class CreationUnavailable(RuntimeError):
    pass


class RecordConflict(ValueError):
    pass


class NewRecord(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    request_id: UUID = Field(default_factory=uuid4)


class MaterialCreate(NewRecord):
    name: str = Field(min_length=2, max_length=120)
    sku: str = Field(min_length=2, max_length=80)
    roll_width_m: float = Field(gt=0, allow_inf_nan=False)
    stock_lm: Amount
    cost_per_lm: Amount
    lead_days: int = Field(ge=0, le=3650)
    transmission: str = Field(min_length=2, max_length=120)
    color: str = Field(min_length=2, max_length=80)
    compatible: list[Identifier] = Field(min_length=1, max_length=100)
    source: str = Field(min_length=3, max_length=500)

    @model_validator(mode='after')
    def unique_profiles(self):
        if len(set(self.compatible)) != len(self.compatible):
            raise ValueError('Compatible profiles must be unique.')
        return self


class KnowledgeCreate(NewRecord):
    title: str = Field(min_length=2, max_length=200)
    heading: str = Field(min_length=2, max_length=200)
    category: Literal['internal', 'external', 'smart', 'company']
    product_ids: list[Identifier] = Field(default_factory=list, max_length=100)
    content: str = Field(min_length=10, max_length=30000)
    source_url: HttpUrl
    reviewed: Literal[True]

    @model_validator(mode='after')
    def source_valid(self):
        if self.source_url.username or self.source_url.password:
            raise ValueError('Source URLs must not contain login credentials.')
        if len(set(self.product_ids)) != len(self.product_ids):
            raise ValueError('Related products must be unique.')
        return self


def require_database():
    if data_source() != 'supabase':
        raise CreationUnavailable('Adding records requires Supabase business data. Connect Supabase before saving; offline fixtures are not changed.')


def insert_record(table, row):
    """Stable request IDs make a lost-response retry safe; never use upsert."""
    try:
        client = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])
        try:
            result = client.table(table).insert(row).execute().data
        except APIError as exc:
            if exc.code != '23505':
                raise
            existing = client.table(table).select(','.join(row)).eq('id', row['id']).execute().data
            if existing and all(existing[0].get(key) == value for key, value in row.items() if key != 'captured_on'):
                return {'record': existing[0], 'created': False, 'data_source': 'supabase'}
            raise RecordConflict('This record or material SKU already exists. Existing data was not overwritten; refresh the page or use a different SKU.') from None
        if not result:
            raise CreationUnavailable('The save could not be confirmed. Retry with the same form to check whether it was saved.')
        # Return only the fields written, never vectors or unrelated columns.
        return {'record': {key: result[0][key] for key in row}, 'created': True, 'data_source': 'supabase'}
    except (RecordConflict, CreationUnavailable):
        raise
    except Exception as exc:
        raise CreationUnavailable('Could not save the Supabase record. Check database access and the backend connection; retrying the same form is safe.') from exc


def create_material(request: MaterialCreate):
    require_database()
    business = load_operations()
    if not set(request.compatible) <= business['products'].keys():
        raise ValueError('Select compatible manufacturing profiles from the current catalog.')
    row = request.model_dump(mode='json', exclude={'request_id'})
    row['id'] = 'mat_' + request.request_id.hex
    return insert_record('inventory_materials', row)


def create_knowledge(request: KnowledgeCreate):
    require_database()
    corpus = load_database_knowledge()
    products = {product['id']: product for product in corpus['products']}
    if not set(request.product_ids) <= products.keys():
        raise ValueError('Select related products from the current portfolio.')
    if request.category in ('internal', 'external') and any(products[id]['category'] != request.category for id in request.product_ids):
        raise ValueError('Related products must match the knowledge category.')
    row = request.model_dump(mode='json', exclude={'request_id', 'reviewed'})
    row.update(id='RB-USER-' + request.request_id.hex, document_id='RB-USER-' + request.request_id.hex,
               source_kind='user_added_content', captured_on=today().isoformat())
    return {**insert_record('company_knowledge_chunks', row), 'indexing_status': 'pending'}
