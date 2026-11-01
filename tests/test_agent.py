import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from enterprise_agent.__main__ import main
from enterprise_agent.evaluation import audit_record, evaluate
from enterprise_agent.graph import Agent
from enterprise_agent.model import ModelError, ScriptedModel
from enterprise_agent.nodes.generate_node import is_whole_sentence_quote, unresolved_pairs
from enterprise_agent.retrieval import DocumentStore
from enterprise_agent.scenarios import EXP_A, EXP_B, INTERN, LEAVE, finish, read, scenarios, search

ROOT = Path(__file__).resolve().parents[1]


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.store = DocumentStore.from_path(ROOT / "data/documents.json")

    def run_script(self, decisions, **kwargs):
        return Agent(ScriptedModel(decisions), self.store, **kwargs).run("正式员工年假有多少天？")

    def test_nine_acceptance_scenarios_offline(self):
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
            report = evaluate(self.store, "mock", Path(folder))
            self.assertEqual((report["passed"], report["total"]), (9, 9))
            self.assertFalse(report["real_llm_path_divergence"])
            for case in scenarios():
                record = json.loads((Path(folder) / (case.name + ".json")).read_text())
                self.assertEqual(record["mode"], "offline_mock")
                self.assertFalse(audit_record(record))

    def test_retest_archives_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
            first = evaluate(self.store, "mock", Path(folder), selected=["normal"])
            saved = (Path(folder) / first["run_directory"] / "normal.json").read_bytes()
            second = evaluate(self.store, "mock", Path(folder), selected=["normal"])
            self.assertNotEqual(first["run_directory"], second["run_directory"])
            self.assertEqual(saved, (Path(folder) / first["run_directory"] / "normal.json").read_bytes())

    def test_partial_answer_keeps_evidence_and_displays_remaining_gaps(self):
        record = self.run_script([search("年假"), finish("insufficient", [LEAVE], missing=["奖金发放规则未提供"])])
        answer = record["result"]["answer"]
        self.assertIn("以下是已核对的资料", answer)
        self.assertEqual(record["result"]["coverage"], "partial")
        self.assertIn(LEAVE["quote"], answer)
        self.assertIn("奖金发放规则未提供", answer)

    def test_synonym_recall_without_vector_database(self):
        for query in ("正式员工年假", "全职同事带薪休假额度", "转正员工一年能休几天"):
            with self.subTest(query=query):
                result = self.store.search_documents(query, 3)
                self.assertIn("LEAVE-FT", [d["doc_id"] for d in result["results"]])

    def test_unknown_question_has_no_matching_evidence(self):
        self.assertEqual(self.store.search_documents("火星殖民补贴")["results"], [])

    def test_tool_feedback_is_delivered_before_next_model_decision(self):
        model = ScriptedModel([search("年假"), finish("answered", [LEAVE])])
        record = Agent(model, self.store).run("年假？")
        self.assertTrue(model.views[1]["observations"][0]["result"]["ok"])
        self.assertEqual(record["trace"][0]["next_action"], "finish")

    def test_retry_after_transient_failure_is_allowed(self):
        record = self.run_script([search("年假"), search("年假"), finish("answered", [LEAVE])], fail_search=1)
        self.assertEqual(record["result"]["status"], "answered")
        self.assertFalse(record["trace"][0]["tool_result"]["ok"])
        self.assertTrue(record["trace"][1]["tool_result"]["ok"])

    def test_unexpected_tool_exception_becomes_observation(self):
        with patch.object(self.store, "search_documents", side_effect=RuntimeError("secret-value")):
            record = self.run_script([search("年假"), finish("incomplete", missing=["工具不可用"])])
        self.assertEqual(record["result"]["status"], "incomplete")
        self.assertNotIn("secret-value", json.dumps(record))
        self.assertEqual(record["trace"][0]["tool_result"]["error"], "tool_execution_failed")

    def test_invalid_model_json_retries_with_feedback_and_budget(self):
        model = ScriptedModel([search("年假"), finish("answered", [LEAVE])])
        original = model.decide
        def decide(view):
            if view["budget"]["step"] == 1:
                raise ModelError("invalid_model_json")
            return original(view)
        model.decide = decide
        result = Agent(model, self.store).run("年假？")
        self.assertEqual(result["result"]["status"], "answered")
        self.assertTrue(model.views[0]["validation_feedback"])
        with patch.object(model, "decide", side_effect=ModelError("model_response_incomplete")):
            bounded = Agent(model, self.store, max_steps=2).run("年假？")
        self.assertEqual(len(bounded["trace"]), 2)
        self.assertEqual(bounded["result"]["missing_info"], ["max_steps_reached"])

    def test_step_limit_is_hard(self):
        record = self.run_script([search("年假"), search("正式员工 年假")], max_steps=2)
        self.assertEqual(len(record["trace"]), 2)
        self.assertEqual(record["result"]["missing_info"], ["max_steps_reached"])

    def test_tool_limit_prevents_execution(self):
        with patch.object(self.store, "search_documents") as execute:
            record = self.run_script([search("年假")], max_tool_calls=0)
        execute.assert_not_called()
        self.assertEqual(record["tool_calls"], 0)
        self.assertEqual(record["result"]["missing_info"], ["tool_call_limit"])

    def test_duplicate_success_does_not_reexecute(self):
        record = self.run_script([search("年假"), search("年假"), finish("answered", [LEAVE])])
        self.assertEqual(record["trace"][1]["tool_result"]["error"], "duplicate_successful_call")

    def test_unobserved_document_cannot_be_cited_even_if_in_corpus(self):
        record = self.run_script([finish("answered", [LEAVE])], max_steps=1)
        self.assertEqual(record["result"]["status"], "incomplete")
        self.assertIn("citation_not_observed:LEAVE-FT", record["trace"][0]["validation_errors"])

    def test_changed_number_cannot_pass_exact_quote_check(self):
        bad = {**LEAVE, "quote": LEAVE["quote"].replace("12", "20")}
        record = self.run_script([search("年假"), finish("answered", [bad])], max_steps=2)
        self.assertEqual(record["result"]["status"], "incomplete")
        self.assertTrue(record["trace"][1]["validation_errors"])

    def test_sentence_fragment_cannot_drop_negation(self):
        self.assertFalse(is_whole_sentence_quote("适用正式员工的12天带薪年假制度。", INTERN["quote"]))
        self.assertTrue(is_whole_sentence_quote(INTERN["quote"], INTERN["quote"]))

    def test_model_repairs_bad_quote_using_validation_feedback(self):
        model = ScriptedModel([search("年假"), finish("answered", [{**LEAVE, "quote": "12天"}]),
                               finish("answered", [LEAVE])])
        record = Agent(model, self.store).run("年假？")
        self.assertEqual(record["result"]["status"], "answered")
        self.assertTrue(model.views[2]["validation_feedback"])

    def test_newer_document_does_not_automatically_override(self):
        record = self.run_script([search("报销期限"), finish("answered", [EXP_B])], max_steps=2)
        self.assertEqual(record["result"]["status"], "incomplete")
        self.assertIn("potential_conflict", " ".join(record["trace"][1]["validation_errors"]))

    def test_conflict_must_read_both_originals(self):
        record = self.run_script([search("报销期限"), finish("conflict", [EXP_A, EXP_B], ["缺少优先级"], "适用哪份？")], max_steps=2)
        self.assertTrue(any("unresolved_conflict_requires_both_originals_and_citations" in e for e in record["trace"][1]["validation_errors"]))

    def test_explicit_replacement_metadata_requires_original_read(self):
        a = {**self.store.documents["EXP-A"], "observed_text": EXP_A["quote"], "read": False}
        b = {**self.store.documents["EXP-B"], "observed_text": EXP_B["quote"], "read": False, "supersedes": ["EXP-A"]}
        self.assertTrue(unresolved_pairs({"EXP-A": a, "EXP-B": b}))
        b["read"] = True
        self.assertFalse(unresolved_pairs({"EXP-A": a, "EXP-B": b}))

    def test_disjoint_scopes_do_not_trigger_conflict_guard(self):
        docs = {i: {**self.store.documents[i], "observed_text": self.store.documents[i]["content"]}
                for i in ["LEAVE-FT", "LEAVE-IN"]}
        self.assertFalse(unresolved_pairs(docs))

    def test_missing_scope_is_unknown_not_assumed_disjoint(self):
        docs = [dict(self.store.documents[i]) for i in ["EXP-A", "EXP-B"]]
        del docs[0]["scope"]
        docs[1]["scope"] = "正式员工"
        store = DocumentStore(docs)
        self.assertEqual(store.documents["EXP-A"]["scope"], "未说明")
        evidence = {i: {**d, "observed_text": d["content"]} for i, d in store.documents.items()}
        self.assertTrue(unresolved_pairs(evidence))

    def test_malformed_decision_is_bounded_and_recoverable(self):
        for invalid in ({"action": []}, {"action": "launch_shell"}, [], None):
            with self.subTest(invalid=invalid):
                record = self.run_script([invalid, search("年假"), finish("answered", [LEAVE])])
                self.assertEqual(record["result"]["status"], "answered")
                self.assertEqual(record["trace"][0]["action"], "invalid_decision")

    def test_unvalidated_freeform_answer_field_is_rejected(self):
        bad = finish("answered", [LEAVE])
        bad["result"]["answer"] = "每年有999天年假"
        record = self.run_script([search("年假"), bad], max_steps=2)
        self.assertEqual(record["result"]["status"], "incomplete")

    def test_question_field_cannot_smuggle_an_unverified_answer(self):
        record = self.run_script([search("年假"), finish("answered", [LEAVE], question="另享有365天额外假期。")], max_steps=2)
        self.assertEqual(record["result"]["status"], "incomplete")
        self.assertNotIn("365", record["result"]["answer"])

    def test_answered_cannot_hide_unresolved_gaps(self):
        record = self.run_script([search("年假"), finish("answered", [LEAVE], missing=["适用范围未知"])], max_steps=2)
        self.assertEqual(record["result"]["status"], "incomplete")

    def test_clarification_can_happen_without_tools(self):
        record = self.run_script([finish("needs_clarification", missing=["缺少任职类型"], question="您是正式员工还是实习生？")])
        self.assertEqual(record["result"]["status"], "needs_clarification")
        self.assertEqual(record["tool_calls"], 0)

    def test_no_evidence_and_tool_outage_are_distinct(self):
        record = self.run_script([search("年假"), finish("insufficient", missing=["无资料"])],
                                 fail_search=1, max_steps=2)
        self.assertEqual(record["result"]["status"], "incomplete")
        self.assertIn("tool_failure_is_incomplete_not_insufficient", record["trace"][1]["validation_errors"])

    def test_history_passed_to_model_but_not_used_as_evidence(self):
        history = [{"role": "assistant", "content": LEAVE["quote"]}]
        model = ScriptedModel([finish("answered", [LEAVE])])
        record = Agent(model, self.store, max_steps=1).run("那实习生呢？", history)
        self.assertEqual(model.views[0]["history"], history)
        self.assertEqual(record["result"]["status"], "incomplete")

    def test_separate_runs_do_not_share_evidence(self):
        model = ScriptedModel([search("年假"), finish("answered", [LEAVE]), finish("answered", [LEAVE])])
        agent = Agent(model, self.store, max_steps=2)
        self.assertEqual(agent.run("年假？")["result"]["status"], "answered")
        self.assertEqual(agent.run("再次询问年假？")["result"]["status"], "incomplete")

    def test_invalid_history_and_limits_are_rejected(self):
        with self.assertRaises(ValueError):
            Agent(ScriptedModel([]), self.store, max_steps=0)
        with self.assertRaises(ValueError):
            Agent(ScriptedModel([]), self.store).run("问题", [{"role": "system", "content": "指令"}])

    def test_model_failure_never_falls_back_to_mock(self):
        model = ScriptedModel([])
        model.mode = "live"
        record = Agent(model, self.store).run("年假？")
        self.assertEqual(record["mode"], "live")
        self.assertEqual(record["trace"][0]["action"], "model_error")
        self.assertEqual(record["result"]["status"], "incomplete")

    def test_audit_detects_evidence_tampering(self):
        record = self.run_script([search("年假"), finish("answered", [LEAVE])])
        record["result"]["citations"][0]["quote"] = "正式员工每年有999天年假。"
        self.assertTrue(audit_record(record))

    def test_cli_mock_is_explicit_and_cannot_answer_arbitrary_questions(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = main(["ask", scenarios()[0].question, "--mode", "mock"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.getvalue())["mode"], "offline_mock")
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["ask", "任何问题", "--mode", "mock"]), 2)


if __name__ == "__main__":
    unittest.main()
