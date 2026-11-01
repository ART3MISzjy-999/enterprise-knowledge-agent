import argparse
import json
import sys
from pathlib import Path

from .evaluation import audit_record, evaluate, write_json
from .graph import Agent
from .model import HTTPDecisionModel, ScriptedModel, load_env
from .retrieval import DocumentStore
from .scenarios import scenarios

ROOT = Path(__file__).resolve().parents[2]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Enterprise Q&A agent with auditable evidence")
    sub = parser.add_subparsers(dest="command", required=True)
    ask = sub.add_parser("ask")
    ask.add_argument("question")
    ask.add_argument("--mode", choices=["live", "mock"], default="live")
    ask.add_argument("--mock-case", default="normal", choices=[s.name for s in scenarios()])
    ask.add_argument("--history", type=Path, help="JSON list of role/content messages")
    ask.add_argument("--session", type=Path, help="Read and update a local conversation history")
    ask.add_argument("--output", type=Path)
    ask.add_argument("--max-steps", type=int, default=10)
    ask.add_argument("--max-tool-calls", type=int, default=7)
    ask.add_argument("--fail-search", type=int, default=0)
    ev = sub.add_parser("evaluate")
    ev.add_argument("--mode", choices=["live", "mock"], default="mock")
    ev.add_argument("--output-dir", type=Path)
    ev.add_argument("--cases", nargs="+")
    verify = sub.add_parser("verify")
    verify.add_argument("records", type=Path, nargs="+")
    for command in (ask, ev):
        command.add_argument("--data", type=Path, default=ROOT / "data/documents.json")
        command.add_argument("--env-file", type=Path, default=ROOT / ".env")
    args = parser.parse_args(argv)
    try:
        if args.command == "verify":
            failures = 0
            for path in args.records:
                record = json.loads(path.read_text(encoding="utf-8"))
                if "trace" not in record:
                    continue
                errors = audit_record(record)
                print(json.dumps({"file": path.name, "errors": errors}, ensure_ascii=False))
                failures += bool(errors)
            return int(failures > 0)
        load_env(args.env_file)
        store = DocumentStore.from_path(args.data)
        if args.command == "evaluate":
            folder = args.output_dir or ROOT / "examples" / ("live" if args.mode == "live" else "offline")
            report = evaluate(store, args.mode, folder, HTTPDecisionModel.from_env, args.cases)
            return int(report["passed"] != report["total"])
        if args.history and args.session:
            raise ValueError("Use either --history or --session")
        history_path = args.history or args.session
        history = json.loads(history_path.read_text(encoding="utf-8")) if history_path and history_path.exists() else []
        if args.history and not args.history.exists():
            raise ValueError("History file does not exist")
        if args.mode == "live":
            model = HTTPDecisionModel.from_env()
        else:
            case = next(c for c in scenarios() if c.name == args.mock_case)
            if args.question != case.question:
                raise ValueError("Mock accepts only the exact selected fixture question; it is not an intelligent model")
            model = ScriptedModel(case.decisions)
            history = history or case.history
            store = DocumentStore([d for d in store.documents.values() if d["doc_id"] not in case.exclude_docs])
            args.fail_search = args.fail_search or case.fail_search
        record = Agent(model, store, max_steps=args.max_steps, max_tool_calls=args.max_tool_calls,
                       fail_search=args.fail_search).run(args.question, history)
        print(json.dumps(record, ensure_ascii=False, indent=2))
        if args.output:
            write_json(args.output, record)
        if args.session:
            updated = history + [{"role": "user", "content": args.question},
                                 {"role": "assistant", "content": record["result"]["answer"]}]
            write_json(args.session, updated[-20:])
        return int(record["result"]["status"] == "incomplete") * 2
    except (ValueError, OSError, KeyError, TypeError):
        # Generic message avoids accidentally echoing a secret configuration value.
        print("配置或输入无效。请检查路径、JSON、模型环境变量与参数范围；未自动回退到 mock。", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
