"""Public synthetic evaluation inputs; scripts below are explicitly NOT model runs."""
from dataclasses import dataclass, field


def search(query, top_k=5):
    return {"action": "search_documents", "arguments": {"query": query, "top_k": top_k},
            "reason": "离线脚本：检索资料"}


def read(doc_id):
    return {"action": "read_document", "arguments": {"doc_id": doc_id},
            "reason": "离线脚本：交叉核对原文"}


def finish(status, citations=None, missing=None, question=""):
    return {"action": "clarify" if status == "needs_clarification" else "finish",
            "reason": "离线脚本：提交预设结果供流程验证",
            "result": {"status": status, "citations": citations or [],
                       "missing_info": missing or [], "question": question}}


LEAVE = {"doc_id": "LEAVE-FT", "quote": "正式员工每个完整服务年度享有12天带薪年假。"}
INTERN = {"doc_id": "LEAVE-IN", "quote": "实习生不适用正式员工的12天带薪年假制度。"}
EXP_A = {"doc_id": "EXP-A", "quote": "员工应在费用发生后30天内提交报销申请。"}
EXP_B = {"doc_id": "EXP-B", "quote": "员工应在费用发生后15天内提交报销申请。"}


@dataclass
class Scenario:
    name: str
    question: str
    expected_status: str
    decisions: list[dict]
    required_citations: set[str] = field(default_factory=set)
    history: list[dict] = field(default_factory=list)
    fail_search: int = 0
    exclude_docs: set[str] = field(default_factory=set)


def scenarios():
    conflict = [search("报销期限"), read("EXP-A"), read("EXP-B"),
                finish("conflict", [EXP_A, EXP_B], ["缺少明确适用制度优先级"],
                       "请确认适用部门及哪份报销制度具有优先级？")]
    return [
        Scenario("normal", "正式员工每年有多少天带薪年假？", "answered",
                 [search("正式员工 年假"), finish("answered", [LEAVE])], {"LEAVE-FT"}),
        Scenario("conflict", "员工报销应在费用发生后多少天内提交？", "conflict",
                 conflict, {"EXP-A", "EXP-B"}),
        Scenario("insufficient", "公司火星殖民补贴每人多少元？", "insufficient",
                 [search("火星殖民补贴"), search("火星 津贴 标准"),
                  finish("insufficient", missing=["没有火星殖民补贴资料"]) ]),
        Scenario("paraphrase", "全职同事一年有几天带薪休假额度？", "answered",
                 [search("全职 带薪休假额度"), finish("answered", [LEAVE])], {"LEAVE-FT"}),
        Scenario("followup", "那实习生呢？", "answered",
                 [search("实习生 年假"), finish("answered", [INTERN])], {"LEAVE-IN"},
                 [{"role": "user", "content": "正式员工每年有多少天带薪年假？"},
                  {"role": "assistant", "content": "正式员工每个完整服务年度享有12天带薪年假。"}]),
        Scenario("tool_failure", "正式员工每年有多少天带薪年假？", "incomplete",
                 [search("正式员工 年假"), search("正式员工 年假"),
                  finish("incomplete", missing=["检索工具持续不可用，无法确认原文"])], fail_search=99),
        Scenario("tool_recovery", "正式员工每年有多少天带薪年假？", "answered",
                 [search("正式员工 年假"), search("正式员工 年假"), finish("answered", [LEAVE])],
                 {"LEAVE-FT"}, fail_search=1),
        Scenario("evidence_single", "员工报销应在费用发生后多少天内提交？", "answered",
                 [search("报销期限"), finish("answered", [EXP_A])], {"EXP-A"}, exclude_docs={"EXP-B"}),
        Scenario("evidence_conflict", "员工报销应在费用发生后多少天内提交？", "conflict",
                 conflict, {"EXP-A", "EXP-B"}),
    ]
