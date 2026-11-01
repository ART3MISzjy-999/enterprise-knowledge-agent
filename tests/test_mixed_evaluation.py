import json, unittest
from pathlib import Path
from enterprise_agent.mixed_evaluation import inspect_case
from enterprise_agent.retrieval import DocumentStore
from enterprise_agent.graph import Agent
from enterprise_agent.model import ScriptedModel
from enterprise_agent.scenarios import search,finish
ROOT=Path(__file__).resolve().parents[1]
class MixedEvaluationTests(unittest.TestCase):
    def test_frozen_questions_are_unique_and_reference_real_docs(self):
        data=json.loads((ROOT/'data/mixed-evaluation-v1.json').read_text());docs=json.loads((ROOT/'data/documents.json').read_text())
        self.assertEqual(len(data['cases']),20);self.assertEqual(len({c['id'] for c in data['cases']}),20)
        self.assertEqual(sum(len(c['turns']) for c in data['cases']),24)
        for c in data['cases']:
            self.assertTrue(c['expected']['gap_keyword_groups'])
            self.assertTrue(set(c['expected']['required_doc_ids']).issubset({d['doc_id'] for d in docs}))
            for q in c['turns']:self.assertFalse(any(d['content'] in q for d in docs))
    def test_blanket_rejection_does_not_pass_mixed_evaluation(self):
        store=DocumentStore.from_path(ROOT/'data/documents.json')
        r=Agent(ScriptedModel([search('火星'),finish('insufficient',missing=['奖金未知'])]),store).run('年假和奖金？')
        c={'expected':{'required_doc_ids':['LEAVE-FT'],'allowed_statuses':['insufficient'],'gap_keyword_groups':[['奖金']]}}
        checks=inspect_case(c,[r]);self.assertFalse(checks['known_evidence_retained']);self.assertFalse(checks['real_response_every_turn'])
