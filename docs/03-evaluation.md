# 评估

## 测试预期

| 场景 | 预期 |
|---|---|
| 正常问答 | 回答正式员工12天带薪年假，引用LEAVE-FT |
| 制度冲突 | 读取EXP-A、EXP-B，报告30/15天冲突并请求确认 |
| 资料不足 | 不编造火星补贴，不冒充已有制度 |
| 同义改写 | 换说法仍找到LEAVE-FT |
| 上下文追问 | 根据上一轮年假话题回答实习生制度 |
| 工具持续失败/短暂恢复 | 前者明确未完成，后者根据成功工具结果继续回答 |
| 单份/冲突证据对照 | 同一问题因实际证据不同而改变结果 |
| 20组混合问题 | 同时保留相关证据与具体缺口；多轮更正不能丢失任务或沿用旧身份 |
| 自动化边界 | 拦截未观察引用、数字或片段篡改；限制预算，验证身份纠正与冲突校验 |

混合集包含16组单轮及4组双轮，共24条用户输入；预期在模型调用前冻结，双轮历史使用本轮模型实际生成的回答。题目及预期见[混合测试集](../examples/mixed20-testset.md)。

## 实际结果

| 验证 | 实际结果 | 记录 |
|---|---|---|
| 自动化测试 | 54/54通过 | [测试日志](../examples/test-results.txt) |
| 修复后原9场景真实回归 | 9/9通过 | [汇总](../examples/release-regression/baseline/runs/20261101T062515498683Z/summary.json) |
| 修复后混合20组完整轮 | 19/20通过；M19第二轮连接失败 | [汇总](../examples/release-regression/mixed20/20261101T062819231194Z/summary.json)、[内容审读](../examples/release-regression/mixed20/20261101T062819231194Z/review.json) |
| M19独立双轮重跑 | 通过，原完整轮统计仍为19/20 | [重跑结果](../examples/release-regression/m19-retry/20261101T063653762702Z/summary.json) |

| 原验收用例 | 实际状态 | 输入、实际输出与Trace |
|---|---|---|
| normal | answered，通过=True | [记录](../examples/release-regression/baseline/runs/20261101T062515498683Z/normal.json) |
| conflict | conflict，通过=True | [记录](../examples/release-regression/baseline/runs/20261101T062515498683Z/conflict.json) |
| insufficient | insufficient，通过=True | [记录](../examples/release-regression/baseline/runs/20261101T062515498683Z/insufficient.json) |
| paraphrase | answered，通过=True | [记录](../examples/release-regression/baseline/runs/20261101T062515498683Z/paraphrase.json) |
| followup | answered，通过=True | [记录](../examples/release-regression/baseline/runs/20261101T062515498683Z/followup.json) |
| tool_failure | incomplete，通过=True | [记录](../examples/release-regression/baseline/runs/20261101T062515498683Z/tool_failure.json) |
| tool_recovery | answered，通过=True | [记录](../examples/release-regression/baseline/runs/20261101T062515498683Z/tool_recovery.json) |
| evidence_single | answered，通过=True | [记录](../examples/release-regression/baseline/runs/20261101T062515498683Z/evidence_single.json) |
| evidence_conflict | conflict，通过=True | [记录](../examples/release-regression/baseline/runs/20261101T062515498683Z/evidence_conflict.json) |

不同反馈后的实际动作示例：
- normal：search_documents反馈{"ok": true, "doc_ids": ["LEAVE-FT", "LEAVE-IN", "TRAVEL-HOTEL"], "total_hits": 3}→read_document；read_document反馈{"ok": true, "doc_id": "LEAVE-FT", "characters": 41}→finish。[完整记录](../examples/release-regression/baseline/runs/20261101T062515498683Z/normal.json)
- insufficient：search_documents反馈{"ok": true, "doc_ids": [], "total_hits": 0}→search_documents；search_documents反馈{"ok": true, "doc_ids": [], "total_hits": 0}→finish。[完整记录](../examples/release-regression/baseline/runs/20261101T062515498683Z/insufficient.json)
- tool_recovery：search_documents反馈{"ok": false, "error": "injected_search_unavailable", "retryable": true}→search_documents；search_documents反馈{"ok": true, "doc_ids": ["LEAVE-FT", "LEAVE-IN", "TRAVEL-HOTEL"], "total_hits": 3}→read_document；read_document反馈{"ok": true, "doc_id": "LEAVE-FT", "characters": 41}→finish。[完整记录](../examples/release-regression/baseline/runs/20261101T062515498683Z/tool_recovery.json)
- evidence_conflict：search_documents反馈{"ok": true, "doc_ids": ["EXP-A", "EXP-B", "LEAVE-FT", "TRAVEL-HOTEL"], "total_hits": 4}→finish；read_document反馈{"ok": true, "doc_id": "EXP-A", "characters": 38}→read_document；read_document反馈{"ok": true, "doc_id": "EXP-B", "characters": 38}→finish。[完整记录](../examples/release-regression/baseline/runs/20261101T062515498683Z/evidence_conflict.json)

## 失败和限制

首次20组混合规则初筛为20/20，但逐条审读只有19组符合预期：M18的模型已理解“我已是正式员工”，程序有限身份提取却沿用实习生标签。现已修复该表达、转正和否定纠正，并增加自动化回归；修复后M18不再出现错误标签。

另一个已修复问题是冲突双方已经读取，额外引用的非冲突摘要仍触发模糊错误，导致模型重复提交直到步数耗尽。现在只对冲突集合要求原文读取；相同历史工具结果的离线校验重放可以通过。该重放不计作新模型响应。

修复后的混合完整轮M19仍发生model_connection_failed，正确返回incomplete。独立重跑成功不能改写原完整轮结果。最早欠费API尝试的原始文件曾被覆盖，仅保留文字说明；后续均采用独立归档，未伪造还原。各轮历史与对应Trace见[统一复测报告](../examples/retest-report.md)。

规则初筛只检查状态、证据编号、缺口关键词、模型响应和Trace内部关系，不是语义蕴含证明；Codex逐条审读也不是独立人工或第二模型裁判。词法召回、有限身份模式与范围元数据不能覆盖全部问法；完整引用不能保证必然相关。回答仍偏抽取式，没有长期成功率、生产可用率或完整对抗注入评测结论。离线Mock只证明流程，不能证明真实模型决策。
