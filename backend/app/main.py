import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / '.env')

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .catalog import today
from .business_data import BusinessDataUnavailable, load_operations, data_source
from .models import ApprovalRequest, ProjectRequest, KnowledgeQuery
from .knowledge import answer_question, portfolio
from .llm import chat_info
from .store import ReportStore, StorageUnavailable
from .workflow import llm_enabled, run_workflow

if os.getenv('DATA_MODE', 'demo') != 'demo':
    raise RuntimeError('Only DATA_MODE=demo is supported. Connect verified business data in a separate production implementation.')
if os.getenv('KNOWLEDGE_RETRIEVAL_MODE', 'local') not in ('local', 'supabase_vector'):
    raise RuntimeError('KNOWLEDGE_RETRIEVAL_MODE must be local or supabase_vector.')

app = FastAPI(title='Royal Blinds · Operations Studio', version='0.1.0',
              description='Interview demonstration. Synthetic data. Human-reviewed estimates.')
app.add_middleware(CORSMiddleware, allow_origins=os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(','),
                   allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])
store = ReportStore()
data_source()
chat_info()  # Validate endpoint/model settings at startup without making requests.


@app.exception_handler(BusinessDataUnavailable)
@app.exception_handler(StorageUnavailable)
async def storage_error(request, exc):
    return JSONResponse(status_code=503, content={'detail': str(exc)})


@app.get('/api/health')
def health():
    business = load_operations()
    return {'status': 'ok', 'storage_mode': store.mode,
            'reasoning_mode': 'live_ai_configured' if llm_enabled() else 'rule_based_demo',
            'data_mode': 'synthetic_demo' if business['is_sample'] else 'configured_records', 'today': today().isoformat(), 'chat_provider': chat_info(),
            'business_data_source': business['data_source'], 'business_data_fetched_at': business['fetched_at']}


@app.get('/api/catalog')
def catalog():
    return load_operations()


@app.get('/api/knowledge/portfolio')
def product_portfolio():
    return portfolio()


@app.post('/api/knowledge/ask')
def knowledge_answer(request: KnowledgeQuery):
    try:
        return answer_question(request.question, request.category, request.product_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post('/api/projects/analyze', status_code=201)
def analyze(request: ProjectRequest):
    if request.due_date < today():
        raise HTTPException(422, 'Requested completion date must be today or later.')
    try:
        report = run_workflow(request)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    store.save(report)
    return report


@app.get('/api/projects')
def projects():
    return store.list()


@app.get('/api/projects/{report_id}')
def project(report_id: str):
    report = store.get(report_id)
    if not report:
        raise HTTPException(404, 'Project report not found.')
    return report


@app.post('/api/projects/{report_id}/approve')
def approve(report_id: str, request: ApprovalRequest):
    if not all([request.measurements_confirmed, request.specification_confirmed, request.commercial_terms_confirmed]):
        raise HTTPException(422, 'All three review confirmations are required.')
    try:
        report = store.approve(report_id, {**request.model_dump(), 'approved_at': datetime.now(timezone.utc).isoformat(),
                                         'scope': 'Demo estimate approval only; no operational action.'})
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    if not report:
        raise HTTPException(404, 'Project report not found.')
    return report
