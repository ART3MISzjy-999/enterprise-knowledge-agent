import contextlib
import io
import json
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

from enterprise_agent.evaluation import evaluate
from enterprise_agent.model import HTTPDecisionModel, ModelError, NoRedirect, load_env
from enterprise_agent.retrieval import DocumentStore
from enterprise_agent.scenarios import finish


class AdapterTests(unittest.TestCase):
    def make_model(self):
        return HTTPDecisionModel("test-secret", "https://example.invalid/v1", "test-model")

    def test_parses_real_protocol_and_discards_private_reasoning(self):
        decision = finish("needs_clarification", missing=["任职类型"], question="您的任职类型？")
        payload = {"id": "test-response", "model": "test-model", "usage": {"total_tokens": 123},
                   "choices": [{"finish_reason": "stop", "message": {
                       "content": json.dumps(decision), "reasoning_content": "PRIVATE_REASONING"}}]}
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value.read.return_value = json.dumps(payload).encode()
        with patch("urllib.request.build_opener", return_value=opener):
            model = self.make_model()
            self.assertEqual(model.decide({"question": "问题"}), decision)
        self.assertNotIn("PRIVATE_REASONING", json.dumps(model.last_meta))
        self.assertNotIn("test-secret", json.dumps(model.last_meta))
        request = opener.open.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer test-secret")
        self.assertEqual(json.loads(request.data)["response_format"]["type"], "json_schema")

    def test_strict_schema_wrapper_is_unwrapped_without_changing_decision(self):
        decision = finish("needs_clarification", missing=["任职类型"], question="您的任职类型？")
        payload = {"id": "response", "choices": [{"finish_reason": "stop", "message": {
            "content": json.dumps({"decision": decision})}}]}
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value.read.return_value = json.dumps(payload).encode()
        with patch("urllib.request.build_opener", return_value=opener):
            self.assertEqual(self.make_model().decide({}), decision)
        schema = json.loads(opener.open.call_args.args[0].data)["response_format"]["json_schema"]
        self.assertTrue(schema["strict"])
        self.assertEqual(len(schema["schema"]["properties"]["decision"]["anyOf"]), 4)

    def test_http_error_does_not_leak_body_or_credentials(self):
        error = urllib.error.HTTPError("https://example.invalid", 429, "test-secret", {}, None)
        opener = MagicMock()
        opener.open.side_effect = error
        with patch("urllib.request.build_opener", return_value=opener), self.assertRaisesRegex(ModelError, "^http_429$"):
            self.make_model().decide({})

    def test_provider_error_code_preserved_without_sensitive_message(self):
        error_body = io.BytesIO(json.dumps({"error": {"code": "AccountOverdueError", "message": "test-secret"}}).encode())
        error = urllib.error.HTTPError("https://example.invalid", 403, "Forbidden", {}, error_body)
        opener = MagicMock()
        opener.open.side_effect = error
        model = self.make_model()
        with patch("urllib.request.build_opener", return_value=opener), self.assertRaisesRegex(ModelError, "^http_403$"):
            model.decide({})
        self.assertEqual(model.last_meta, {"provider_error_code": "AccountOverdueError"})
        self.assertNotIn("test-secret", json.dumps(model.last_meta))

    def test_invalid_json_is_explicit_failure(self):
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value.read.return_value = b'{"choices": []}'
        with patch("urllib.request.build_opener", return_value=opener), self.assertRaisesRegex(ModelError, "invalid_model_json"):
            self.make_model().decide({})

    def test_truncated_model_output_is_not_accepted(self):
        payload = {"id": "test-response", "choices": [{"finish_reason": "length", "message": {"content": "{}"}}]}
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value.read.return_value = json.dumps(payload).encode()
        with patch("urllib.request.build_opener", return_value=opener), self.assertRaisesRegex(ModelError, "model_response_incomplete"):
            self.make_model().decide({})

    def test_connection_error_does_not_become_a_mock_answer(self):
        opener = MagicMock()
        opener.open.side_effect = urllib.error.URLError("private-local-path")
        with patch("urllib.request.build_opener", return_value=opener), self.assertRaisesRegex(ModelError, "^model_connection_failed$"):
            self.make_model().decide({})

    def test_redirects_cannot_forward_authorization_header(self):
        with self.assertRaisesRegex(ModelError, "http_redirect_refused"):
            NoRedirect().redirect_request(None, None, 302, "", {}, "https://elsewhere.invalid")

    def test_config_rejects_unsafe_url_and_payload_overrides(self):
        for base in ("http://example.invalid", "https://user:secret@example.invalid", "https://example.invalid?api_key=x"):
            with self.subTest(base=base), self.assertRaises(ValueError):
                HTTPDecisionModel("x", base, "model")
        with self.assertRaises(ValueError):
            HTTPDecisionModel("x", "https://example.invalid", "model", extra_body={"messages": []})

    def test_env_file_is_not_executed_and_does_not_override_environment(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"EXISTING": "keep"}, clear=True):
            path = Path(folder) / ".env"
            path.write_text('EXISTING=replace\nTASK_VALUE="$(echo never-executed)"\n')
            load_env(path)
            self.assertEqual(os.environ["EXISTING"], "keep")
            self.assertEqual(os.environ["TASK_VALUE"], "$(echo never-executed)")

    def test_api_outage_does_not_count_as_tool_failure_acceptance(self):
        root = Path(__file__).resolve().parents[1]
        opener = MagicMock()
        opener.open.side_effect = urllib.error.URLError("offline")
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()), patch(
                "urllib.request.build_opener", return_value=opener):
            report = evaluate(DocumentStore.from_path(root / "data/documents.json"), "live", Path(folder),
                              self.make_model, ["tool_failure"])
        self.assertEqual(report["passed"], 0)
        self.assertIn("failure_injection_not_exercised", report["cases"][0]["errors"])
        self.assertIn("no_real_model_response", report["cases"][0]["errors"])


if __name__ == "__main__":
    unittest.main()
