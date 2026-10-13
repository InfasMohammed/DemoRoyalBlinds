"""Index reviewed website passages; never print keys or silently accept failures."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

load_dotenv(Path(__file__).resolve().parents[1] / '.env')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.knowledge import CHUNKS, embedding_client


def main():
    url, key = os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    if not url or not key or not os.getenv('LLM_API_KEY'):
        raise SystemExit('Set SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY and LLM_API_KEY securely before indexing.')
    client = create_client(url, key)
    existing = client.table('company_knowledge_chunks').select('id,content,embedding_model,embedding').execute().data
    rows = {row['id']: row for row in existing}
    if any(c['id'] not in rows or rows[c['id']]['content'] != c['content'] for c in CHUNKS):
        raise SystemExit('Apply the current supabase/knowledge_base.sql before indexing; bundled corpus does not match the database.')
    pending = [c for c in CHUNKS if rows[c['id']]['embedding_model'] != 'text-embedding-3-small' or rows[c['id']]['embedding'] is None]
    if not pending:
        print(f'All {len(CHUNKS)} passages already indexed; no embedding requests needed.')
        return
    vectors = embedding_client().embed_documents([c['content'] for c in pending])
    if len(vectors) != len(pending) or any(len(v) != 1536 for v in vectors):
        raise SystemExit('Embedding dimensions/count mismatch; nothing was written.')
    for c, vector in zip(pending, vectors):
        # Predicate prevents attaching stale embeddings to concurrently revised text.
        result = client.table('company_knowledge_chunks').update({
            'embedding': vector, 'embedding_model': 'text-embedding-3-small',
        }).eq('id', c['id']).eq('content', c['content']).execute().data
        if len(result) != 1:
            raise SystemExit('A passage changed during indexing. Reapply the corpus and retry.')
    probe = client.rpc('match_company_knowledge', {
        'query_embedding': vectors[0], 'match_count': 1,
    }).execute().data
    if not probe or probe[0]['id'] != pending[0]['id']:
        raise SystemExit('Embedding writes completed but retrieval verification failed.')
    print(f'Indexed {len(pending)} passages; verified vector retrieval for the current corpus.')


if __name__ == '__main__':
    main()
