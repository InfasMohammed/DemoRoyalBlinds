"""Post-approval LangGraph: propose handoffs, then commit through atomic tools.

The approval job and every effect live in persistent storage. A crash before
commit leaves a queued job; retries never duplicate reservations/work orders.
No external supplier messages or machine commands are sent.
"""
import logging
from threading import Event, Thread
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from .workflow import calculate_production

logger = logging.getLogger(__name__)


class ExecutionState(TypedDict, total=False):
    report: dict
    store: object
    plan: dict | None
    findings: list[dict]
    result: dict


def approval_handoff(state):
    report = state['report']
    if report['status'] != 'demo_approved' or not report.get('approval', {}).get('execution_confirmed'):
        raise ValueError('A human must approve and authorize execution before actions can run.')
    return {'findings': [{'agent': 'Approval coordinator', 'summary': 'Human approval and execution authorization verified.', 'mode': 'validated_tools'}]}


def inventory_handoff(state):
    report = state['report']
    findings = [*state['findings'], {'agent': 'Inventory handoff', 'mode': 'validated_tools',
                'summary': f"Request an atomic reservation of {report['materials']['required_lm']} lm; recheck current available stock at commit."}]
    return {'findings': findings}


def production_handoff(state):
    report = state['report']
    snapshot = report.get('data_snapshot')
    plan = None
    if snapshot:
        product = snapshot['products'][report['request']['product']]
        plan = calculate_production(report['request'], product, snapshot['policy'])
    return {'plan': plan, 'findings': [*state['findings'], {'agent': 'Production handoff', 'mode': 'validated_tools',
            'summary': 'Prepare a current production plan. The database allocates capacity without overlapping existing bookings.'}]}


def quality_installation_handoff(state):
    return {'findings': [*state['findings'], {'agent': 'Quality & installation handoff', 'mode': 'validated_tools',
            'summary': 'Prepare required quality checks and installation handover. Quality confirmation gates installation.'}]}


def commit_handoffs(state):
    result = state['store'].execute(state['report']['id'], state.get('plan'), state['findings'])
    return {'result': result}


def build_execution_graph():
    graph = StateGraph(ExecutionState)
    for name, node in [('approval', approval_handoff), ('inventory', inventory_handoff),
                       ('production', production_handoff), ('quality_installation', quality_installation_handoff),
                       ('commit', commit_handoffs)]:
        graph.add_node(name, node)
    graph.add_edge(START, 'approval')
    graph.add_edge('approval', 'inventory')
    graph.add_edge('inventory', 'production')
    graph.add_edge('production', 'quality_installation')
    graph.add_edge('quality_installation', 'commit')
    graph.add_edge('commit', END)
    return graph.compile()


EXECUTION_GRAPH = build_execution_graph()


def run_post_approval(store, report_id):
    report = store.get(report_id)
    if not report:
        return None
    if (report.get('execution') or {}).get('status') in ('completed', 'cancelled'):
        return report
    if 'execution' not in report:
        raise ValueError('This report predates the execution workflow. Analyze and approve a new report.')
    return EXECUTION_GRAPH.invoke({'report': report, 'store': store})['result']


class ApprovalWorker:
    """Recover queued approvals across backend restarts; terminal tools are atomic."""
    def __init__(self, store, interval=10):
        self.store = store
        self.interval = interval
        self.stop_event = Event()
        self.thread = Thread(target=self.run, name='approval-worker', daemon=True)
        self.failed_ids = set()

    def process_once(self):
        processed = 0
        for report_id in self.store.pending_execution_ids():
            try:
                run_post_approval(self.store, report_id)
                processed += 1
                self.failed_ids.discard(report_id)
            except Exception:
                if report_id not in self.failed_ids:
                    logger.warning('A queued approval could not complete; it remains recoverable. Other approvals will continue.')
                self.failed_ids.add(report_id)
        return processed

    def run(self):
        unavailable = False
        while not self.stop_event.is_set():
            try:
                self.process_once()
                unavailable = False
            except Exception:
                if not unavailable:
                    logger.warning('Post-approval queue unavailable. Check database access and apply supabase/post_approval.sql; queued approvals remain recoverable.')
                unavailable = True
            self.stop_event.wait(self.interval)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=2)
