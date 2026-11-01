import json
from datetime import datetime, timezone
from pathlib import Path

from .graph import Agent
from .model import ScriptedModel
from .nodes.generate_node import is_whole_sentence_quote, unresolved_pairs
from .retrieval import DocumentStore
from .scenarios import scenarios


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def audit_record(record: dict) -> list[str]:
    """Check stored evidence and actual transitions, without trusting the mode label alone."""
    errors, observed, read_ids, evidence = [], {}, set(), {}
    trace = record["trace"]
    for i, row in enumerate(trace):
        if row["step"] != i + 1:
            errors.append("non_sequential_step")
        expected_next = trace[i + 1]["action"] if i + 1 < len(trace) else "end:" + record["result"]["status"]
        if row["next_action"] != expected_next:
            errors.append("incorrect_next_action")
        if record["mode"] == "live" and row["action"] not in {"model_error", "invalid_decision"}:
            if not row.get("model_metadata", {}).get("response_id"):
                errors.append("missing_provider_response_id")
        result = row.get("tool_result", {})
        if result.get("ok"):
            if row["action"] == "search_documents":
                for doc in result["data"]["results"]:
                    observed.setdefault(doc["doc_id"], []).append(doc["snippet"])
                    evidence.setdefault(doc['doc_id'], {**doc, 'observed_text':doc['snippet'], 'read':False})
            elif row["action"] == "read_document":
                doc = result["data"]
                observed.setdefault(doc["doc_id"], []).append(doc["content"])
                read_ids.add(doc["doc_id"])
                evidence[doc['doc_id']] = {**doc, 'observed_text':doc['content'], 'read':True}
    for c in record["result"]["citations"]:
        if not any(is_whole_sentence_quote(c["quote"], text) for text in observed.get(c["doc_id"], [])):
            errors.append("citation_without_observed_support:" + c["doc_id"])
    if record["result"]["status"] == "conflict":
        ids = {c["doc_id"] for c in record["result"]["citations"]}
        pairs = [pair for pair in unresolved_pairs(evidence) if ids.intersection(pair)]
        pair_ids = {i for pair in pairs for i in pair}
        if len(ids) < 2 or (pair_ids and (not pair_ids.issubset(ids) or not pair_ids.issubset(read_ids))) or (not pairs and len(ids & read_ids) < 2):
            errors.append("conflict_without_cross_read")
    if len(trace) > record["config"]["max_steps"] or record["tool_calls"] > record["config"]["max_tool_calls"]:
        errors.append("budget_exceeded")
    return errors


def evaluate(store: DocumentStore, mode: str, output_dir: Path, model_factory=None,
             selected: list[str] | None = None) -> dict:
    cases = scenarios()
    if selected:
        unknown = set(selected) - {c.name for c in cases}
        if unknown:
            raise ValueError("unknown cases: " + ",".join(sorted(unknown)))
        cases = [c for c in cases if c.name in selected]
    run_dir = output_dir / "runs" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_dir.mkdir(parents=True, exist_ok=False)
    rows, paths = [], []
    for case in cases:
        case_store = DocumentStore([d for d in store.documents.values() if d["doc_id"] not in case.exclude_docs])
        model = model_factory() if mode == "live" else ScriptedModel(case.decisions)
        record = Agent(model, case_store, fail_search=case.fail_search).run(case.question, case.history)
        record["scenario"] = case.name
        record["test_setup"] = {"injected_search_failures": case.fail_search,
                                "excluded_doc_ids": sorted(case.exclude_docs),
                                "synthetic_data": True}
        write_json(run_dir / (case.name + ".json"), record)
        write_json(output_dir / (case.name + ".json"), record)
        errors = audit_record(record)
        if mode == "live" and not any(r.get("model_metadata", {}).get("response_id") for r in record["trace"]):
            errors.append("no_real_model_response")
        if case.fail_search and not any(r.get("tool_result", {}).get("error") == "injected_search_unavailable"
                                        for r in record["trace"]):
            errors.append("failure_injection_not_exercised")
        if record["result"]["status"] != case.expected_status:
            errors.append("unexpected_status")
        if not case.required_citations.issubset({c["doc_id"] for c in record["result"]["citations"]}):
            errors.append("missing_expected_citations")
        first_tool = next((r for r in record["trace"] if "tool_result" in r), None)
        path = {"case": case.name, "after_first_tool": first_tool["next_action"] if first_tool else None}
        paths.append(path)
        rows.append({"case": case.name, "passed": not errors, "errors": errors,
                     "expected_status": case.expected_status, "actual_status": record["result"]["status"],
                     "steps": len(record["trace"]), "tool_calls": record["tool_calls"]})
        print(json.dumps(rows[-1], ensure_ascii=False), flush=True)
    report = {"mode": mode if mode == "live" else "offline_mock", "cases": rows,
              "passed": sum(r["passed"] for r in rows), "total": len(rows),
              "observed_paths": paths,
              "real_llm_path_divergence": mode == "live" and len({p["after_first_tool"] for p in paths
                  if p["after_first_tool"] not in {None, "model_error", "invalid_decision"}}) >= 2,
              "note": "仅比较已记录行为，不构成密码学真实性证明；离线脚本不证明模型决策。"}
    report["run_directory"] = "runs/" + run_dir.name
    write_json(run_dir / "summary.json", report)
    write_json(output_dir / "summary.json", report)
    report_path = Path(__file__).resolve().parents[2] / "examples/retest-report.md"
    if mode == "live" and report_path.exists() and output_dir.resolve().is_relative_to(report_path.parent.parent):
        import os
        link = os.path.relpath(run_dir / "summary.json", report_path.parent)
        with report_path.open("a", encoding="utf-8") as log:
            log.write(f"\n## 实际复测 {run_dir.name}\n\n结果：{report['passed']}/{report['total']}。原始记录：[本轮汇总]({link})。\n\n")
            for row in rows:
                log.write(f"- {row['case']}: {row['actual_status']}；通过={row['passed']}；错误={row['errors']}\n")
    return report
