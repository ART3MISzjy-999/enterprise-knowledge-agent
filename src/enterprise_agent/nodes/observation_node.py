def observation_node(state, step: int, decision: dict, result: dict) -> None:
    state.observations.append({"step": step, "tool": decision["action"],
                               "arguments": decision["arguments"], "result": result})
    if not result["ok"]:
        return
    data = result["data"]
    docs = data["results"] if decision["action"] == "search_documents" else [data]
    for doc in docs:
        previous = state.evidence.get(doc["doc_id"], {})
        if "content" in doc:
            state.evidence[doc["doc_id"]] = {**doc, "read": True, "observed_text": doc["content"]}
        elif not previous.get("read"):
            state.evidence[doc["doc_id"]] = {**doc, "read": False, "observed_text": doc["snippet"]}
    # No automatic completion here: every observation returns to the model.
