"""A small synchronous graph runtime; business actions come only from the model."""
import hashlib
import json
import uuid
from datetime import datetime, timezone

from .model import ModelError
from .nodes.decision_node import TOOLS, decision_node
from .nodes.generate_node import generate_node
from .nodes.observation_node import observation_node
from .nodes.tool_node import ToolNode
from .state import AgentState


def incomplete(code: str) -> dict:
    return {"status": "incomplete", "answer": "本次查询未完成，不能确认结论。",
            "citations": [], "missing_info": [code], "question": ""}


class Agent:
    def __init__(self, model, store, *, max_steps: int = 10, max_tool_calls: int = 7,
                 fail_search: int = 0):
        if type(max_steps) is not int or type(max_tool_calls) is not int or not 1 <= max_steps <= 30 or not 0 <= max_tool_calls <= 20:
            raise ValueError("max_steps must be 1..30; max_tool_calls must be 0..20")
        self.model, self.store = model, store
        self.max_steps, self.max_tool_calls = max_steps, max_tool_calls
        self.tool_node = ToolNode(store, fail_search)

    def run(self, question: str, history: list[dict] | None = None) -> dict:
        if not isinstance(question, str) or not 1 <= len(question.strip()) <= 2000:
            raise ValueError("question must be 1..2000 characters")
        history = [] if history is None else history
        if not isinstance(history, list) or len(history) > 20:
            raise ValueError("history must be at most 20 user/assistant messages")
        for message in history:
            if not isinstance(message, dict) or set(message) != {"role", "content"} or (
                    not isinstance(message["role"], str) or message["role"] not in {"user", "assistant"} or
                    not isinstance(message["content"], str) or len(message["content"]) > 6000):
                raise ValueError("invalid history message")
        state = AgentState(question=question, history=history)
        output = None
        for step in range(1, self.max_steps + 1):
            row = {"step": step, "source": self.model.mode, "action": None,
                   "tool_arguments": {}, "return_summary": None, "next_action": None,
                   "decision_basis": "", "validation_errors": []}
            try:
                decision = decision_node(self.model, state.model_view(
                    step, self.max_steps, self.max_tool_calls))
            except ModelError as exc:
                row.update(action="model_error", decision_basis=str(exc))
                row["model_metadata"] = dict(self.model.last_meta)
                state.trace.append(row)
                if str(exc) in {"invalid_model_json", "model_response_incomplete"}:
                    state.feedback.append("上次响应无法解析或被截断。请重新输出一个简短合法JSON动作，不要Markdown或解释。")
                    continue
                output = incomplete(str(exc))
                break
            except ValueError as exc:
                row.update(action="invalid_decision", validation_errors=[str(exc)])
                row["model_metadata"] = dict(self.model.last_meta)
                state.feedback.append(str(exc))
                state.trace.append(row)
                continue
            row.update(action=decision["action"], decision_basis=decision["reason"],
                       model_metadata=dict(self.model.last_meta), decision=decision)
            state.trace.append(row)
            if decision["action"] in TOOLS:
                row["tool_arguments"] = decision["arguments"]
                if state.tool_calls >= self.max_tool_calls:
                    row["return_summary"] = {"ok": False, "error": "tool_call_limit", "executed": False}
                    output = incomplete("tool_call_limit")
                    break
                state.tool_calls += 1
                result = self.tool_node(state, decision)
                observation_node(state, step, decision, result)
                row["tool_result"] = result
                if not result["ok"]:
                    row["return_summary"] = result
                elif decision["action"] == "search_documents":
                    row["return_summary"] = {"ok": True,
                        "doc_ids": [d["doc_id"] for d in result["data"]["results"]],
                        "total_hits": result["data"]["total_hits"]}
                else:
                    row["return_summary"] = {"ok": True, "doc_id": result["data"]["doc_id"],
                                             "characters": len(result["data"]["content"])}
            else:
                output, errors = generate_node(state, decision)
                row["validation_errors"] = errors
                if errors:
                    state.feedback.extend(errors)
                else:
                    break
        if output is None:
            output = incomplete("max_steps_reached")
        # Link only to the action actually taken next; no invented future plan.
        for index, row in enumerate(state.trace):
            row["next_action"] = state.trace[index + 1]["action"] if index + 1 < len(state.trace) else "end:" + output["status"]
            row["next_decision_basis"] = state.trace[index + 1]["decision_basis"] if index + 1 < len(state.trace) else ""
        corpus = list(self.store.documents.values())
        responses = sum(bool(r.get("model_metadata", {}).get("response_id")) for r in state.trace)
        return {"schema_version": 1, "run_id": uuid.uuid4().hex,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "mode": self.model.mode, "input": {"question": question, "history": history},
                "model_response_count": responses,
                "evidence_kind": ("offline_script_only" if self.model.mode == "offline_mock" else
                                  "real_llm_execution" if responses else "live_attempt_no_model_response"),
                "config": {"max_steps": self.max_steps, "max_tool_calls": self.max_tool_calls},
                "corpus_sha256": hashlib.sha256(json.dumps(corpus, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
                "result": output, "tool_calls": state.tool_calls, "trace": state.trace}
