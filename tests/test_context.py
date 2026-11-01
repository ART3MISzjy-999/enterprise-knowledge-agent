import unittest
from enterprise_agent.context import user_facts, hotel_comparison
from enterprise_agent.state import AgentState
from enterprise_agent.nodes.generate_node import generate_node

HOTEL = {'doc_id':'H','scope':'正式员工','quote':'正式员工在中国大陆出差的住宿费用上限为每晚500元。'}
class ContextTests(unittest.TestCase):
    def test_only_user_corrections_update_role(self):
        s=AgentState('对的，这是一晚住的', history=[{'role':'user','content':'我是实习生，宾馆费用409元'}, {'role':'assistant','content':'我是正式员工'}, {'role':'user','content':'说错了，我是正式员工'}])
        self.assertEqual(user_facts(s)['role']['value'],'正式员工')
        note=hotel_comparison(s,[HOTEL])
        self.assertIn('409元',note);self.assertIn('未超过',note);self.assertIn('若本次是在中国大陆',note)
        self.assertNotIn('一定可以报销',note)
    def test_role_correction_variants_and_negation(self):
        for phrase, expected in [('我已是正式员工','正式员工'),('我已经转正了','正式员工'),
                                 ('我不是正式员工，是实习生','实习生'),('刚才说错了，我现在是实习生','实习生')]:
            with self.subTest(phrase=phrase):
                s=AgentState(phrase, history=[{'role':'user','content':'我是实习生'}])
                self.assertEqual(user_facts(s)['role']['value'],expected)
        s=AgentState('我不是实习生',history=[{'role':'user','content':'我是实习生'}])
        self.assertNotIn('role',user_facts(s))
    def test_hypothetical_role_does_not_replace_user_identity(self):
        s=AgentState('如果我是正式员工会怎样？',history=[{'role':'user','content':'我是实习生'}])
        self.assertEqual(user_facts(s)['role']['value'],'实习生')

    def test_yesterday_is_not_confirmation_of_one_night(self):
        s=AgentState('我是正式员工，昨天出差宾馆费用409元')
        self.assertFalse(user_facts(s).get('one_night'))
        self.assertEqual(hotel_comparison(s,[HOTEL]),'')
    def test_intern_cannot_get_formal_employee_comparison(self):
        s=AgentState('我是实习生，住了一晚，宾馆费用409元')
        self.assertEqual(hotel_comparison(s,[HOTEL]),'')
    def test_no_arithmetic_without_verified_evidence(self):
        s=AgentState('我是正式员工，住了一晚，宾馆费用409元')
        self.assertEqual(hotel_comparison(s,[]),'')
    def test_conflict_cannot_be_bypassed_by_partial_status(self):
        s=AgentState('报销')
        s.evidence={i:{'doc_id':i,'version_date':'2026-01-01','scope':'全体员工','policy_key':'expense','read':True,'observed_text':quote} for i,quote in [('A','员工应在费用发生后30天内提交报销申请。'),('B','员工应在费用发生后15天内提交报销申请。')]}
        d={'result':{'status':'insufficient','citations':[{'doc_id':'B','quote':s.evidence['B']['observed_text']}],'missing_info':['流程未知'],'question':''}}
        _,errors=generate_node(s,d)
        self.assertTrue(any('unresolved_conflict' in e for e in errors))

    def test_conflict_pair_read_does_not_require_unrelated_snippet_read(self):
        from pathlib import Path
        from enterprise_agent.retrieval import DocumentStore
        from enterprise_agent.graph import Agent
        from enterprise_agent.model import ScriptedModel
        from enterprise_agent.scenarios import search,read,finish,EXP_A,EXP_B
        from enterprise_agent.evaluation import audit_record
        store=DocumentStore.from_path(Path(__file__).resolve().parents[1]/'data/documents.json')
        hotel={'doc_id':'TRAVEL-HOTEL','quote':store.documents['TRAVEL-HOTEL']['content']}
        model=ScriptedModel([search('报销期限'),read('EXP-A'),read('EXP-B'),search('住宿'),
                             finish('conflict',[EXP_A,EXP_B,hotel],['制度优先级未说明'],'哪份制度优先？')])
        record=Agent(model,store).run('住宿标准及报销期限？')
        self.assertEqual(record['result']['status'],'conflict')
        self.assertFalse(audit_record(record))
        self.assertFalse(any(t['action']=='read_document' and t['tool_arguments']['doc_id']=='TRAVEL-HOTEL' for t in record['trace']))
