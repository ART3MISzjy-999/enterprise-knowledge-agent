import json


def tool_call_signature(tool_name: str, arguments: dict) -> str:
    return json.dumps(
        {"tool": tool_name, "input": arguments},
        sort_keys=True,
        ensure_ascii=False,
    )


class ToolNode:
    def __init__(self, store, fail_search: int = 0):
        if fail_search < 0:
            raise ValueError("fail_search must be non-negative")
        self.store, self.fail_search = store, fail_search

    def __call__(self, state, decision: dict) -> dict:
        action, args = decision["action"], decision["arguments"]
        signature = tool_call_signature(action, args)
        if signature in state.successful_signatures:
            return {"ok": False, "error": "duplicate_successful_call", "retryable": False}
        try:
            if action == "search_documents":
                if self.fail_search:
                    self.fail_search -= 1
                    return {"ok": False, "error": "injected_search_unavailable", "retryable": True}
                data = self.store.search_documents(**args)
            elif action == "read_document":
                data = self.store.read_document(**args)
            else:
                return {"ok": False, "error": "unknown_tool", "retryable": False}
            state.successful_signatures.add(signature)
            return {"ok": True, "data": data}
        except (ValueError, TypeError, KeyError):
            return {"ok": False, "error": "invalid_tool_arguments", "retryable": False}
        except Exception:
            # Do not expose exception text: it can contain credentials or private paths.
            return {"ok": False, "error": "tool_execution_failed", "retryable": True}
