import json
from datetime import date

import httpx
import pytest
from openai import OpenAI as RealOpenAI
from pydantic import ValidationError

from app import knowledge, llm, workflow
from app.models import AgentNarrative, ProjectRequest


@pytest.fixture(autouse=True)
def nvidia_settings(monkeypatch):
    monkeypatch.setenv('LLM_BASE_URL', llm.NVIDIA_URL)
    monkeypatch.setenv('LLM_MODEL', 'openai/gpt-oss-20b')
    monkeypatch.setenv('LLM_API_KEY', 'fake-nvidia-key-for-tests')
    monkeypatch.delenv('NVIDIA_API_KEY', raising=False)
    monkeypatch.delenv('EMBEDDING_API_KEY', raising=False)
    monkeypatch.setenv('KNOWLEDGE_RETRIEVAL_MODE', 'local')
    monkeypatch.delenv('QA_CHAT_TIMEOUT_SECONDS', raising=False)


def mock_nvidia(monkeypatch, content, status=200, finish_reason='stop'):
    requests = []

    def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        assert request.url.host == 'integrate.api.nvidia.com'
        assert request.url.path == '/v1/chat/completions'
        assert request.headers['authorization'] == 'Bearer fake-nvidia-key-for-tests'
        assert body['model'] == 'openai/gpt-oss-20b'
        assert body['stream'] is False
        assert body['max_tokens'] == 4096
        assert 'response_format' not in body
        assert 'JSON object' in body['messages'][0]['content']
        if status != 200:
            return httpx.Response(status, json={'error': {'message': 'Provider quota exceeded'}})
        return httpx.Response(200, json={
            'id': 'chatcmpl-demo', 'object': 'chat.completion', 'created': 0,
            'model': 'openai/gpt-oss-20b',
            'choices': [{'index': 0, 'finish_reason': finish_reason,
                         'message': {'role': 'assistant', 'content': content,
                                     'reasoning_content': 'INTERNAL_REASONING_NOT_FOR_OUTPUT'}}],
            'usage': {'prompt_tokens': 30, 'completion_tokens': 20, 'total_tokens': 50},
        })

    def client(**kwargs):
        return RealOpenAI(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    monkeypatch.setattr(llm, 'OpenAI', client)
    return requests


@pytest.mark.parametrize('fenced', [False, True])
def test_nvidia_payload_validates_answer_and_ignores_reasoning(monkeypatch, fenced):
    content = json.dumps({'summary': '24 motorized rollers.', 'recommendation': 'Confirm measurements.'})
    if fenced:
        content = '```json\n' + content + '\n```'
    calls = mock_nvidia(monkeypatch, content)
    result = llm.structured_chat(AgentNarrative, [('system', 'Use computed facts.'), ('human', 'Project facts')])
    assert result.summary == '24 motorized rollers.'
    assert len(calls) == 1
    assert calls[0]['messages'][1]['role'] == 'user'
    assert 'INTERNAL_REASONING' not in result.model_dump_json()


@pytest.mark.parametrize('content', ['not JSON', '{"summary":"missing recommendation"}', '{}'])
def test_invalid_provider_output_does_not_pass_validation(monkeypatch, content):
    mock_nvidia(monkeypatch, content)
    with pytest.raises(ValidationError):
        llm.structured_chat(AgentNarrative, [('human', 'Project')])


def test_truncated_response_is_rejected(monkeypatch):
    mock_nvidia(monkeypatch, '{"summary":"partial"}', finish_reason='length')
    with pytest.raises(ValueError, match='complete answer'):
        llm.structured_chat(AgentNarrative, [('human', 'Project')])


def test_nvidia_runs_all_specialists_and_keeps_tool_prices(monkeypatch):
    calls = mock_nvidia(monkeypatch, json.dumps({'summary': 'Review the tool findings.', 'recommendation': 'Confirm the survey.'}))
    request = ProjectRequest(customer='Demo', project_name='NVIDIA integration demo',
                             brief='24 motorized rollers for office windows.',
                             fabric_id='premium_blackout', due_date=date(2099, 1, 1))
    result = workflow.run_workflow(request)
    assert len(calls) == 6
    assert result['reasoning_mode'] == 'live_ai'
    assert all(t['mode'] == 'llm' for t in result['traces'])
    assert result['costing']['total'] == 20404.27
    assert 'INTERNAL_REASONING' not in json.dumps(result)


def test_nvidia_rag_keeps_citations(monkeypatch):
    mock_nvidia(monkeypatch, json.dumps({
        'answer': 'The supplied copy describes rechargeable battery or mains power [RB-SMART-03].',
        'cited_chunk_ids': ['RB-SMART-03'],
    }))
    result = knowledge.answer_question('battery or mains power', 'smart')
    assert result['generation_mode'] == 'llm'
    assert result['retrieval_mode'] == 'local_keyword'
    assert '[RB-SMART-03]' in result['answer']


def test_nvidia_rate_limit_falls_back_without_exposing_raw_errors(monkeypatch):
    mock_nvidia(monkeypatch, '', status=429)
    result = knowledge.answer_question('battery power', 'smart')
    assert result['generation_mode'] == 'extractive_fallback'
    assert result['generation_warning'].startswith('Chat provider quota or rate limit was reached.')
    assert 'Showing retrieved source excerpts instead' in result['generation_warning']
    assert 'Provider quota exceeded' not in json.dumps(result)


@pytest.mark.parametrize('configured_timeout', [None, '12.5'])
def test_qa_transport_timeout_is_one_attempt_and_keeps_sources(monkeypatch, configured_timeout):
    if configured_timeout is not None:
        monkeypatch.setenv('QA_CHAT_TIMEOUT_SECONDS', configured_timeout)
    calls = []
    observed = {}

    def handler(request):
        calls.append(request)
        expected_timeout = float(configured_timeout or '30')
        assert request.extensions['timeout']['read'] == expected_timeout
        payload = json.loads(request.content)
        context = json.loads(payload['messages'][1]['content'])
        assert all(set(p) == {'id', 'title', 'heading', 'content'} for p in context['passages'])
        raise httpx.ReadTimeout('Sensitive transport error fake-nvidia-key-for-tests', request=request)

    def client(**kwargs):
        observed.update(kwargs)
        return RealOpenAI(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    monkeypatch.setattr(llm, 'OpenAI', client)
    result = knowledge.answer_question('Can roller blinds use rechargeable battery power?', 'smart')
    assert len(calls) == 1
    assert observed['max_retries'] == 0
    assert result['generation_mode'] == 'extractive_fallback'
    assert result['generation_warning'].startswith('Chat provider timed out.')
    assert 'Showing retrieved source excerpts instead' in result['generation_warning']
    assert 'rechargeable battery' in result['answer']
    assert any(c['id'] == 'RB-SMART-03' for c in result['citations'])
    assert 'Sensitive transport error' not in json.dumps(result)
    assert 'fake-nvidia-key' not in json.dumps(result)


@pytest.mark.parametrize('value', ['0', '121', 'nan', 'inf', 'bad-value'])
def test_invalid_qa_timeout_is_rejected_by_health_configuration(monkeypatch, value):
    monkeypatch.setenv('QA_CHAT_TIMEOUT_SECONDS', value)
    with pytest.raises(ValueError, match='between 5 and 120'):
        llm.chat_info()


def test_nvidia_key_cannot_be_reused_for_openai_embeddings(monkeypatch):
    with pytest.raises(ValueError, match='EMBEDDING_API_KEY'):
        knowledge.embedding_client()
    monkeypatch.setenv('EMBEDDING_API_KEY', 'fake-separate-openai-key')
    assert llm.embedding_key() == 'fake-separate-openai-key'


def test_openai_embeddings_keep_backwards_compatible_key(monkeypatch):
    monkeypatch.setenv('LLM_BASE_URL', llm.OPENAI_URL)
    monkeypatch.setenv('LLM_API_KEY', 'fake-openai-key')
    assert llm.embedding_key() == 'fake-openai-key'


def test_existing_nvidia_variable_binding_can_be_reused(monkeypatch):
    monkeypatch.delenv('LLM_API_KEY')
    monkeypatch.setenv('NVIDIA_API_KEY', 'fake-existing-binding')
    assert llm.chat_enabled()
    assert llm.chat_config().api_key == 'fake-existing-binding'


@pytest.mark.parametrize('url', ['http://example.com/v1', 'https://user:password@example.com/v1', 'https://example.com/v1?token=secret'])
def test_invalid_endpoint_config_is_rejected_without_printing_credentials(monkeypatch, url):
    monkeypatch.setenv('LLM_BASE_URL', url)
    with pytest.raises(ValueError) as caught:
        llm.chat_config()
    assert url not in str(caught.value)


def test_sample_placeholder_is_not_a_real_key(monkeypatch):
    monkeypatch.setenv('LLM_API_KEY', '$NVIDIA_API_KEY')
    with pytest.raises(ValueError, match='placeholder'):
        llm.chat_config()


def test_openai_still_uses_native_structured_responses(monkeypatch):
    monkeypatch.setenv('LLM_BASE_URL', llm.OPENAI_URL)
    monkeypatch.setenv('LLM_MODEL', 'gpt-4.1-mini')
    observed = {}

    class Model:
        def __init__(self, **kwargs):
            observed.update(kwargs)

        def with_structured_output(self, schema):
            observed['schema'] = schema
            return self

        def invoke(self, messages):
            return AgentNarrative(summary='Grounded summary', recommendation='Review')

    monkeypatch.setattr(llm, 'ChatOpenAI', Model)
    result = llm.structured_chat(AgentNarrative, [('human', 'Project')], timeout_seconds=30, max_retries=0)
    assert observed['base_url'] == llm.OPENAI_URL
    assert observed['schema'] is AgentNarrative
    assert observed['timeout'] == 30
    assert observed['max_retries'] == 0
    assert result.summary == 'Grounded summary'
