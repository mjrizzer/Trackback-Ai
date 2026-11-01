import json
from types import SimpleNamespace
import pytest
import openai
from backend.agents.orchestrator import live_stage
from backend.config import settings


class FakeTools:
    def __init__(self):
        self.calls = []
        self.incident = SimpleNamespace(id=7)
        self.db = None
        self.observed_references = set()

    def call(self, name, arguments):
        self.calls.append((name, arguments))
        if name != 'get_incident_details':
            raise ValueError('Tool not authorized')
        self.observed_references.add('incidents:7')
        return {'incident': {'id': 7}}


def test_live_response_executes_selected_tool_and_validates_output(monkeypatch):
    from backend.agents import orchestrator

    monkeypatch.setattr(settings, 'openai_api_key', 'test-only-no-network')
    outputs = iter(
        [
            SimpleNamespace(
                output=[
                    SimpleNamespace(
                        type='function_call',
                        name='get_incident_details',
                        arguments='{"query":""}',
                        call_id='call-1',
                    )
                ]
            ),
            SimpleNamespace(
                output=[],
                output_text=json.dumps(
                    {
                        'summary': 'Incident reviewed using the tool.',
                        'evidence_references': ['incidents:7'],
                        'uncertainties': ['Supplier verification pending.'],
                    }
                ),
            ),
        ]
    )
    monkeypatch.setattr(
        openai,
        'OpenAI',
        lambda **_: SimpleNamespace(responses=SimpleNamespace(create=lambda **_: next(outputs))),
    )
    monkeypatch.setattr(
        orchestrator,
        'trace',
        lambda *_: {'lots': [], 'batches': [], 'shipments': [], 'customers': [], 'edges': []},
    )
    monkeypatch.setattr(orchestrator, 'evidence', lambda *_: {'inspections': [], 'documents': []})
    tools = FakeTools()
    result = live_stage(tools, 'Incident Triage', 'Use evidence tools', [])
    assert tools.calls == [('get_incident_details', {'query': ''})]
    assert result.evidence_references == ['incidents:7']


def test_live_cannot_conclude_without_tools(monkeypatch):
    monkeypatch.setattr(settings, 'openai_api_key', 'test-only-no-network')
    monkeypatch.setattr(
        openai,
        'OpenAI',
        lambda **_: SimpleNamespace(
            responses=SimpleNamespace(
                create=lambda **_: SimpleNamespace(output=[], output_text='{}')
            )
        ),
    )
    with pytest.raises(ValueError, match='without using evidence tools'):
        live_stage(FakeTools(), 'Triage', '', [])


def test_live_provider_failure_stops_safely(monkeypatch):
    monkeypatch.setattr(settings, 'openai_api_key', 'test-only-no-network')

    def fail(**_):
        raise TimeoutError('Simulated provider timeout')

    monkeypatch.setattr(
        openai, 'OpenAI', lambda **_: SimpleNamespace(responses=SimpleNamespace(create=fail))
    )
    with pytest.raises(TimeoutError):
        live_stage(FakeTools(), 'Triage', '', [])


def test_live_rejects_unobserved_source_reference(monkeypatch):
    monkeypatch.setattr(settings, 'openai_api_key', 'test-only-no-network')
    outputs = iter(
        [
            SimpleNamespace(
                output=[
                    SimpleNamespace(
                        type='function_call',
                        name='get_incident_details',
                        arguments='{"query":""}',
                        call_id='call-1',
                    )
                ]
            ),
            SimpleNamespace(
                output=[],
                output_text=json.dumps(
                    {
                        'summary': 'Claim with a source the agent never retrieved.',
                        'evidence_references': ['production_batches:1'],
                        'uncertainties': ['Unverified'],
                    }
                ),
            ),
        ]
    )
    monkeypatch.setattr(
        openai,
        'OpenAI',
        lambda **_: SimpleNamespace(responses=SimpleNamespace(create=lambda **_: next(outputs))),
    )
    with pytest.raises(ValueError, match='unverifiable source'):
        live_stage(FakeTools(), 'Triage', '', [])
