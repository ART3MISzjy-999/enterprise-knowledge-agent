TOOLS = {"search_documents", "read_document"}
STATUSES = {"answered", "conflict", "insufficient", "incomplete", "needs_clarification"}


def decision_node(model, view: dict) -> dict:
    decision = model.decide(view)
    if not isinstance(decision, dict):
        raise ValueError("decision must be an object")
    action = decision.get("action")
    if not isinstance(action, str) or action not in TOOLS | {"finish", "clarify"}:
        raise ValueError("unknown action")
    reason = decision.get("reason")
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 160:
        raise ValueError("reason must be a short public action summary")
    if action in TOOLS:
        if set(decision) != {"action", "arguments", "reason"}:
            raise ValueError("tool decision fields must be action, arguments, reason")
        args = decision["arguments"]
        if not isinstance(args, dict):
            raise ValueError("arguments must be an object")
        if action == "search_documents":
            if set(args) != {"query", "top_k"}:
                raise ValueError("search requires query and top_k")
            if not isinstance(args["query"], str) or not 1 <= len(args["query"].strip()) <= 500:
                raise ValueError("query must be 1..500 characters")
            if type(args["top_k"]) is not int or not 1 <= args["top_k"] <= 8:
                raise ValueError("top_k must be 1..8")
        elif set(args) != {"doc_id"} or not isinstance(args["doc_id"], str) or not args["doc_id"]:
            raise ValueError("read requires doc_id")
    else:
        if set(decision) != {"action", "reason", "result"}:
            raise ValueError("terminal decision requires action, reason, result")
        result = decision["result"]
        if not isinstance(result, dict) or set(result) != {"status", "citations", "missing_info", "question"}:
            raise ValueError("invalid result fields")
        if not isinstance(result["status"], str) or result["status"] not in STATUSES:
            raise ValueError("unknown status")
        if not isinstance(result["citations"], list) or len(result["citations"]) > 10:
            raise ValueError("citations must be a list of at most 10")
        for citation in result["citations"]:
            if not isinstance(citation, dict) or set(citation) != {"doc_id", "quote"}:
                raise ValueError("citation requires doc_id and quote")
            if not all(isinstance(v, str) and v for v in citation.values()):
                raise ValueError("citation values must be non-empty strings")
        if not isinstance(result["missing_info"], list) or not all(
                isinstance(v, str) and 0 < len(v) <= 400 for v in result["missing_info"]):
            raise ValueError("missing_info must contain short strings")
        if not isinstance(result["question"], str) or len(result["question"]) > 400:
            raise ValueError("question must be a short string")
        if (action == "clarify") != (result["status"] == "needs_clarification"):
            raise ValueError("clarify requires needs_clarification and vice versa")
    return decision
