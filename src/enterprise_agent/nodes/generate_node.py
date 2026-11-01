"""Evidence gate and extractive rendering; never chooses a tool for the model."""
import re
from itertools import combinations
from ..context import user_facts, hotel_comparison


def unresolved_pairs(evidence: dict) -> list[tuple[str, str]]:
    """Conservative metadata guard, not a general semantic contradiction detector."""
    pairs = []
    for a, b in combinations(evidence.values(), 2):
        broad_or_unknown = {"全体员工", "未说明", "未知", "不详"}
        overlap = a["scope"] == b["scope"] or bool(broad_or_unknown & {a["scope"], b["scope"]})
        if a["policy_key"] != b["policy_key"] or not overlap:
            continue
        if a["observed_text"] == b["observed_text"]:
            continue
        replaced = (a.get("read") and b["doc_id"] in a.get("supersedes", [])) or (
            b.get("read") and a["doc_id"] in b.get("supersedes", []))
        if not replaced:
            pairs.append((a["doc_id"], b["doc_id"]))
    return pairs


def is_whole_sentence_quote(quote: str, source: str) -> bool:
    # Match contiguous complete sentences, preserving scope, negation and conditions.
    sentences = re.findall(r"[^。！？!?]+[。！？!?]", source)
    return len(quote) >= 8 and any(
        quote == "".join(sentences[i:j]).strip()
        for i in range(len(sentences)) for j in range(i + 1, len(sentences) + 1))


def generate_node(state, decision: dict) -> tuple[dict | None, list[str]]:
    result = decision["result"]
    status = result["status"]
    errors, verified = [], []
    for citation in result["citations"]:
        doc = state.evidence.get(citation["doc_id"])
        if doc is None:
            errors.append("citation_not_observed:" + citation["doc_id"])
            continue
        if not is_whole_sentence_quote(citation["quote"], doc["observed_text"]):
            errors.append("quote_not_exact_complete_sentence:" + citation["doc_id"])
            continue
        verified.append({**citation, "version_date": doc["version_date"], "scope": doc["scope"],
                         "source": "read_document" if doc["read"] else "search_documents"})
    if status == "answered" and not verified:
        errors.append("answered_requires_evidence")
    if status == "answered" and result["missing_info"]:
        errors.append("answered_cannot_have_unresolved_gaps")
    if status not in {"conflict", "needs_clarification"} and result["question"]:
        errors.append("question_allowed_only_for_conflict_or_clarification")
    if status != "answered" and not result["missing_info"]:
        errors.append("non_answer_requires_missing_info")
    if status in {"conflict", "needs_clarification"} and not result["question"].strip():
        errors.append("clarification_question_required")
    elif status in {"conflict", "needs_clarification"} and not result["question"].rstrip().endswith(("?", "？")):
        errors.append("clarification_must_be_a_question")
    if status == "insufficient" and not state.observations:
        errors.append("insufficient_requires_search_attempt")
    if status == "insufficient" and state.observations and not any(
            o["result"]["ok"] for o in state.observations):
        errors.append("tool_failure_is_incomplete_not_insufficient")
    pairs = unresolved_pairs(state.evidence)
    cited_ids = {c["doc_id"] for c in verified}
    for c in verified:
        for peer_id in state.evidence[c["doc_id"]].get("version_peer_ids", []):
            if not state.evidence.get(peer_id, {}).get("read"):
                errors.append("read_related_version_before_concluding:" + peer_id)
    for a, b in pairs:
        if cited_ids & {a, b}:
            if not {a, b}.issubset(cited_ids) or not all(state.evidence[i].get("read") for i in (a, b)):
                errors.append("unresolved_conflict_requires_both_originals_and_citations:" + a + "," + b)
    facts = user_facts(state)
    if facts.get("one_night") and any(re.search(r"(?:未知|未确认|尚未确认|缺少).{0,5}(?:住宿晚数|住宿晚数)|(?:住宿晚数|住了几晚).{0,5}(?:未知|未确认|尚未确认)", item) for item in result["missing_info"]):
        errors.append("night_count_already_confirmed_by_user")
    if pairs and status == "answered":
        errors.append("potential_conflict_requires_cross_read_and_confirmation:" + str(pairs))
    if status == "conflict":
        ids = {c["doc_id"] for c in verified}
        if len(ids) < 2:
            errors.append("conflict_requires_two_cited_documents")
        # Non-conflicting supporting citations may use verified complete snippets.
        # When metadata cannot identify the conflicting pair, require two originals.
        if not pairs and len([i for i in ids if state.evidence[i].get("read")]) < 2:
            unread = sorted(i for i in ids if not state.evidence[i].get("read"))
            errors.append("conflict_requires_two_read_documents; read_originals:" + ",".join(unread))
        for a, b in pairs:
            if not {a, b}.issubset(ids):
                errors.append("conflict_requires_both_citations:" + a + "," + b)
    if errors:
        return None, errors
    prefixes = {
        "answered": "依据已获取的适用资料：",
        "conflict": "资料存在冲突，尚不能确定适用结论；版本日期本身不足以确定优先级。",
        "insufficient": "现有资料不足以回答，未找到可确认的依据。",
        "incomplete": "本次查询未完成，不能确认结论。",
        "needs_clarification": "需要补充适用信息后再确认。",
    }
    answer = prefixes[status]
    if status == "insufficient" and verified:
        answer = "以下是已核对的资料（具体适用范围见各条）："
    if verified:
        conflict_ids = {i for pair in pairs for i in pair}
        lines = []
        role = facts.get("role", {}).get("value")
        for c in verified:
            label = "【优先级待确认】" if c["doc_id"] in conflict_ids else ""
            if role == "实习生" and c["scope"] == "正式员工":
                label += "【仅适用正式员工，不能直接套用于你当前的实习生身份】"
            lines.append(f'[{c["doc_id"]}] {label}{c["quote"]}')
        answer += "\n" + "\n".join(lines)
        comparison = hotel_comparison(state, verified)
        if comparison:
            answer += "\n" + comparison
    if result["missing_info"]:
        label = "现有资料尚不能确认的部分：" if status == "insufficient" and verified else "尚待确认："
        answer += "\n" + label + "\n" + "\n".join("- " + item for item in result["missing_info"])
    if result["question"]:
        answer += "\n" + result["question"]
    coverage = "partial" if verified and result["missing_info"] else "supported" if verified else "none"
    return {**result, "answer": answer, "citations": verified, "coverage": coverage}, []
