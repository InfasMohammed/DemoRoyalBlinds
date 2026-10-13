"""Persist demo reports locally or in Supabase, without changing real stock."""
import json
import os
import threading
from pathlib import Path
from typing import Any

from supabase import create_client


class StorageUnavailable(RuntimeError):
    pass


class ReportStore:
    def __init__(self):
        url, key = os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        if bool(url) != bool(key):
            raise RuntimeError('Configure both SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY, or leave both unset.')
        self.client = create_client(url, key) if url and key else None
        self.mode = 'supabase' if self.client else 'local_demo'
        self.path = Path(os.getenv('DEMO_STORE_PATH', str(Path(__file__).resolve().parents[2] / '.runtime' / 'reports.json')))
        self.lock = threading.RLock()

    def _read(self):
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text())

    def _write(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(data, indent=2))
        temporary.replace(self.path)

    def save(self, report: dict[str, Any]):
        try:
            if self.client:
                self.client.table('demo_reports').insert({
                    'id': report['id'], 'project_name': report['request']['project_name'],
                    'status': report['status'], 'payload': report,
                }).execute()
            else:
                with self.lock:
                    data = self._read()
                    data[report['id']] = report
                    self._write(data)
        except Exception as exc:
            raise StorageUnavailable('Could not save the report. Check database setup and connection.') from exc

    def list(self):
        try:
            if self.client:
                return [row['payload'] for row in self.client.table('demo_reports').select('payload').order('created_at', desc=True).limit(50).execute().data]
            with self.lock:
                return sorted(self._read().values(), key=lambda item: item['created_at'], reverse=True)[:50]
        except Exception as exc:
            raise StorageUnavailable('Could not load reports. Check database setup and connection.') from exc

    def get(self, report_id):
        try:
            if self.client:
                rows = self.client.table('demo_reports').select('payload').eq('id', report_id).execute().data
                return rows[0]['payload'] if rows else None
            with self.lock:
                return self._read().get(report_id)
        except Exception as exc:
            raise StorageUnavailable('Could not load the report. Check database setup and connection.') from exc

    def approve(self, report_id, approval):
        """Atomically accept one approval. Supabase enforces the status predicate."""
        with self.lock:
            report = self.get(report_id)
            if not report:
                return None
            if report['status'] != 'awaiting_review':
                raise ValueError('This report is already reviewed or has unresolved blockers.')
            report['status'] = 'demo_approved'
            report['approval'] = approval
            try:
                if self.client:
                    rows = self.client.table('demo_reports').update({'status': 'demo_approved', 'payload': report}).eq('id', report_id).eq('status', 'awaiting_review').execute().data
                    if not rows:
                        raise ValueError('This report was reviewed by another request. Reload it.')
                else:
                    data = self._read()
                    data[report_id] = report
                    self._write(data)
            except ValueError:
                raise
            except Exception as exc:
                raise StorageUnavailable('Could not record approval. Check database connection.') from exc
            return report
