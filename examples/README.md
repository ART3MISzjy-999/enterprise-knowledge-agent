> 当前评估与历史统一见 [复测报告](retest-report.md)。

# 实际执行样例

下列内容从本次执行生成的JSON提取。全部是 **offline_mock**：真实工具运行，但模型动作是预设脚本，不能证明模型决策。修复后真实记录及结果以[评估入口](../docs/03-evaluation.md)为准。本页以下离线输出是历史生成摘录，可能与当前正文格式不同，不能作为当前真实模型结果。

## normal

**输入**：正式员工每年有多少天带薪年假？

**实际离线输出**：
```text
依据已获取的适用资料：
[LEAVE-FT] 正式员工每个完整服务年度享有12天带薪年假。
状态：answered
资料缺口：[]
```

| step | 动作及参数 | 返回摘要 | 实际下一动作 | 公开行动依据 |
|---|---|---|---|---|
| 1 | search_documents {"query": "正式员工 年假", "top_k": 5} | {"ok": true, "doc_ids": ["LEAVE-FT", "LEAVE-IN", "TRAVEL-HOTEL"], "total_hits": 3} | finish | 离线脚本：检索资料 |
| 2 | finish {} | null | end:answered | 离线脚本：提交预设结果供流程验证 |

完整记录：[offline/normal.json](offline/normal.json)。

## insufficient

**输入**：公司火星殖民补贴每人多少元？

**实际离线输出**：
```text
现有资料不足以回答，未找到可确认的依据。
状态：insufficient
资料缺口：["没有火星殖民补贴资料"]
```

| step | 动作及参数 | 返回摘要 | 实际下一动作 | 公开行动依据 |
|---|---|---|---|---|
| 1 | search_documents {"query": "火星殖民补贴", "top_k": 5} | {"ok": true, "doc_ids": [], "total_hits": 0} | search_documents | 离线脚本：检索资料 |
| 2 | search_documents {"query": "火星 津贴 标准", "top_k": 5} | {"ok": true, "doc_ids": ["PRODUCT-EXPORT", "TRAVEL-HOTEL"], "total_hits": 2} | finish | 离线脚本：检索资料 |
| 3 | finish {} | null | end:insufficient | 离线脚本：提交预设结果供流程验证 |

完整记录：[offline/insufficient.json](offline/insufficient.json)。

## tool_failure

**输入**：正式员工每年有多少天带薪年假？

**实际离线输出**：
```text
本次查询未完成，不能确认结论。
状态：incomplete
资料缺口：["检索工具持续不可用，无法确认原文"]
```

| step | 动作及参数 | 返回摘要 | 实际下一动作 | 公开行动依据 |
|---|---|---|---|---|
| 1 | search_documents {"query": "正式员工 年假", "top_k": 5} | {"ok": false, "error": "injected_search_unavailable", "retryable": true} | search_documents | 离线脚本：检索资料 |
| 2 | search_documents {"query": "正式员工 年假", "top_k": 5} | {"ok": false, "error": "injected_search_unavailable", "retryable": true} | finish | 离线脚本：检索资料 |
| 3 | finish {} | null | end:incomplete | 离线脚本：提交预设结果供流程验证 |

完整记录：[offline/tool_failure.json](offline/tool_failure.json)。

## conflict

**输入**：员工报销应在费用发生后多少天内提交？

**实际离线输出**：
```text
资料存在冲突，尚不能确定适用结论；版本日期本身不足以确定优先级。
[EXP-A] 员工应在费用发生后30天内提交报销申请。
[EXP-B] 员工应在费用发生后15天内提交报销申请。
请确认适用部门及哪份报销制度具有优先级？
状态：conflict
资料缺口：["缺少明确适用制度优先级"]
```

| step | 动作及参数 | 返回摘要 | 实际下一动作 | 公开行动依据 |
|---|---|---|---|---|
| 1 | search_documents {"query": "报销期限", "top_k": 5} | {"ok": true, "doc_ids": ["EXP-B", "EXP-A"], "total_hits": 2} | read_document | 离线脚本：检索资料 |
| 2 | read_document {"doc_id": "EXP-A"} | {"ok": true, "doc_id": "EXP-A", "characters": 38} | read_document | 离线脚本：交叉核对原文 |
| 3 | read_document {"doc_id": "EXP-B"} | {"ok": true, "doc_id": "EXP-B", "characters": 38} | finish | 离线脚本：交叉核对原文 |
| 4 | finish {} | null | end:conflict | 离线脚本：提交预设结果供流程验证 |

完整记录：[offline/conflict.json](offline/conflict.json)。

## 其余场景

改写相似问题、历史追问、故障恢复、单份证据与冲突证据对照均见 [离线汇总](offline/summary.json)。实际状态检查通过9/9；仍不代表真实模型通过。

## 真实记录入口

- 正常、资料不足、工具失败至少3组真实模型执行：已记录。
- 至少2条不同工具反馈引起不同后续动作：已记录。
- 最新修复后记录位于`release-regression/`，见[评估入口](../docs/03-evaluation.md)。较早记录保留失败与修复历史。
