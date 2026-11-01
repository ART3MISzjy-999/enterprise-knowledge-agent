# 统一复测报告

最新修复回归：自动化54/54，原9场景真实9/9；混合完整轮19/20（M19连接失败），M19单独双轮重跑通过。旧M18身份错误已修复。详见[评估入口](../docs/03-evaluation.md)。

所有轮次在本报告追加；每轮原始JSON单独保存，不以成功结果覆盖失败历史。

## 历史：充值前

真实API返回403/AccountOverdueError，0/9通过。原始文件在后一次复测前已被覆盖，只有此前文字记录；不能重新伪造历史Trace。

## 第01轮：充值后、修复前

2/9通过：tool_failure、tool_recovery。其余失败。问题包括把输入问题填入澄清字段、JSON解析失败、响应截断。已归档实际记录到[第01轮](runs/round-01-before-fix/summary.json)。

## 第02轮：结构化输出修复

修复：明确澄清字段语义；温度设0；输出上限1400→3000；只剥离完整JSON围栏，不拼造内容；格式错误或截断反馈模型重试，仍受max_steps限制。引用与冲突校验不放宽。本轮最终6/9，详见下方20261101T014456074440Z记录。

### 独立诊断（不计验收通过）

对已取得的冲突工具反馈单独请求模型，得到有效JSON，但missing_info为字符串而非数组。未将此诊断冒充完整运行。下一轮改用服务端严格JSON Schema约束（封装decision对象），保留全部动作选择；不再仅依赖提示词。参考[官方结构化输出文档](https://docs.volcengine.com/docs/ark/structured-output-beta?lang=en)。此前设置temperature=0不作为确定性保证，已撤去。

## 第02轮实际结果 · 2026-11-01 09:44（北京时间）

结果：6/9。原始记录：[本轮汇总](live/runs/20261101T014456074440Z/summary.json)。

- normal: answered；通过=True；错误=[]
- conflict: incomplete；通过=False；错误=['unexpected_status', 'missing_expected_citations']
- insufficient: insufficient；通过=True；错误=[]
- paraphrase: answered；通过=True；错误=[]
- followup: answered；通过=True；错误=[]
- tool_failure: incomplete；通过=True；错误=[]
- tool_recovery: incomplete；通过=False；错误=['unexpected_status', 'missing_expected_citations']
- evidence_single: incomplete；通过=False；错误=['unexpected_status', 'missing_expected_citations']
- evidence_conflict: conflict；通过=True；错误=[]

## 第03轮：严格Schema · 2026-11-01 09:51（北京时间）

结果：9/9。原始记录：[本轮汇总](live/runs/20261101T015114709328Z/summary.json)。

- normal: answered；通过=True；错误=[]
- conflict: conflict；通过=True；错误=[]
- insufficient: insufficient；通过=True；错误=[]
- paraphrase: answered；通过=True；错误=[]
- followup: answered；通过=True；错误=[]
- tool_failure: incomplete；通过=True；错误=[]
- tool_recovery: answered；通过=True；错误=[]
- evidence_single: answered；通过=True；错误=[]
- evidence_conflict: conflict；通过=True；错误=[]

## 第03轮行为证据与剩余局限

### normal

输入：正式员工每年有多少天带薪年假？

实际输出：

```text
依据已获取的适用资料：
[LEAVE-FT] 正式员工每个完整服务年度享有12天带薪年假。
```

动作：search_documents → invalid_decision → finish。状态：answered。

[完整Trace](live/runs/20261101T015114709328Z/normal.json)

### insufficient

输入：公司火星殖民补贴每人多少元？

实际输出：

```text
现有资料不足以回答，未找到可确认的依据。
```

动作：search_documents → finish。状态：insufficient。

[完整Trace](live/runs/20261101T015114709328Z/insufficient.json)

### tool_failure

输入：正式员工每年有多少天带薪年假？

实际输出：

```text
本次查询未完成，不能确认结论。
```

动作：search_documents → search_documents → invalid_decision → invalid_decision → search_documents → finish。状态：incomplete。

[完整Trace](live/runs/20261101T015114709328Z/tool_failure.json)

### tool_recovery

输入：正式员工每年有多少天带薪年假？

实际输出：

```text
依据已获取的适用资料：
[LEAVE-FT] 正式员工每个完整服务年度享有12天带薪年假。年假申请应提前3个工作日提交直属主管。
```

动作：search_documents → search_documents → finish。状态：answered。

[完整Trace](live/runs/20261101T015114709328Z/tool_recovery.json)

### evidence_single

输入：员工报销应在费用发生后多少天内提交？

实际输出：

```text
依据已获取的适用资料：
[EXP-A] 员工应在费用发生后30天内提交报销申请。
```

动作：search_documents → finish。状态：answered。

[完整Trace](live/runs/20261101T015114709328Z/evidence_single.json)

### evidence_conflict

输入：员工报销应在费用发生后多少天内提交？

实际输出：

```text
资料存在冲突，尚不能确定适用结论；版本日期本身不足以确定优先级。
[EXP-A] 员工应在费用发生后30天内提交报销申请。本文件未说明与其他报销文件的优先级。
[EXP-B] 员工应在费用发生后15天内提交报销申请。本文件未声明废止或替代其他报销制度。
请问《费用报销提交规则》和《费用报销操作 FAQ》的适用优先级是什么？
```

动作：invalid_decision → search_documents → finish → read_document → model_error → read_document → finish。状态：conflict。

[完整Trace](live/runs/20261101T015114709328Z/evidence_conflict.json)

不同反馈下的实际动作：tool_failure 中失败反馈后选择再次 search_documents；insufficient 中空检索结果后选择 finish/insufficient；tool_recovery 中失败后重新检索、成功后 finish/answered。均来自本轮真实模型响应。

相同报销问题在单份文档下回答30天，在加入冲突文档后最终报告冲突。后者曾在未交叉读取时尝试finish，被引用门禁拒绝后才完成双方读取；这同时展示了模型判断和程序保护的作用，不能把它描述为模型全程无误。

严格Schema请求并未消除全部协议异常：本轮仍有unknown action、一次JSON解析错误及引用门禁纠正，均在预算内恢复。不得宣称一次输出成功率100%，尚未开展大规模、多轮重复稳定性评估。

## 后续记录方式

从仓库根目录执行 `python -m enterprise_agent evaluate --mode live`，每轮自动在本报告追加，原始记录写入 `examples/live/runs/<UTC时间>/`。顶层JSON仅为最近一次快照，历史目录保留。外部临时输出目录不自动写入本仓库报告；正常项目内输出会追加。

## 接入点切换：Doubao-Seed-2.1-pro

用户提供新2.1接入点后，仅修改本项目忽略提交的本地配置，旧语音项目配置未改动。先运行normal场景验证可用性，不将2.0的9/9结果等同为2.1完整验收。免费额度及实际扣费尚未通过账单核实。

## 实际复测 20261101T015753332540Z

结果：1/1。原始记录：[本轮汇总](live-2.1/runs/20261101T015753332540Z/summary.json)。

- normal: answered；通过=True；错误=[]

2.1验证补充：服务端实际返回模型 doubao-seed-2-1-pro-260915；normal通过，2次模型决策、1次工具调用。API报告总token为3596，该数字不等于已核实的资源包扣减量。旧2.0完整9/9记录保留。

## 实际复测 20261101T020057431535Z

结果：9/9。原始记录：[本轮汇总](live-2.1/runs/20261101T020057431535Z/summary.json)。

- normal: answered；通过=True；错误=[]
- conflict: conflict；通过=True；错误=[]
- insufficient: insufficient；通过=True；错误=[]
- paraphrase: answered；通过=True；错误=[]
- followup: answered；通过=True；错误=[]
- tool_failure: incomplete；通过=True；错误=[]
- tool_recovery: answered；通过=True；错误=[]
- evidence_single: answered；通过=True；错误=[]
- evidence_conflict: conflict；通过=True；错误=[]

### 2.1完整复测核对

真实模型：doubao-seed-2-1-pro-260915。本轮9/9通过，9份Trace审计通过。API报告累计59970 tokens；这不是实际扣费或免费资源包抵扣确认。

协议/校验恢复事件（如有，不能省略）：[["conflict", 4, "invalid_decision", ["missing_info must contain short strings"]], ["evidence_single", 1, "model_error", []], ["evidence_conflict", 1, "model_error", []], ["evidence_conflict", 2, "model_error", []]]。

- normal：search_documents → finish；最终 answered。
- conflict：search_documents → read_document → read_document → invalid_decision → finish；最终 conflict。
- insufficient：search_documents → search_documents → finish；最终 insufficient。
- paraphrase：search_documents → finish；最终 answered。
- followup：search_documents → finish；最终 answered。
- tool_failure：search_documents → search_documents → search_documents → search_documents → search_documents → finish；最终 incomplete。
- tool_recovery：search_documents → search_documents → finish；最终 answered。
- evidence_single：model_error → search_documents → finish；最终 answered。
- evidence_conflict：model_error → model_error → search_documents → read_document → read_document → finish；最终 conflict。

结论：2.1完成一次完整9场景真实验收，旧2.0与2.1单场验证记录均保留。不据此推断长期成功率。

## 多轮费用子问题漏答修复 · 20261101T031614951405Z

输入为用户提供的四条历史消息及末轮“半个月的那份”，历史助手消息仅作为上下文，不作为制度证据。修改提示保留原始未完成子问题，渲染回答显示资料缺口；自动化44/44通过。以下为单个针对性复测，不代表重跑原9场景。

[原始Trace](context-retests/20261101T031614951405Z/expense-followup.json)

检查：{"not_falsely_complete": true, "hotel_evidence_retained": true, "remaining_gaps_visible": true}；Trace审计错误：[]。

实际输出：

```text
已找到部分依据，但现有资料不足以完整回答：
[EXP-B] 员工应在费用发生后15天内提交报销申请。本文件未声明废止或替代其他报销制度。
[TRAVEL-HOTEL] 正式员工在中国大陆出差的住宿费用上限为每晚500元。超出上限的部分须在预订前获得部门负责人书面确认。
尚待确认：
- 高铁费350元是否可报销及其标准或凭证要求
- 报销申请入口、审批流程及需上传的发票或车票等凭证要求
- 宾馆费用409元是否为一晚、出差地点是否在中国大陆，以及是否已取得合规住宿凭证
- 住宿是否需要出差审批或其他事前审批证明
```

## 本人手测审查与能力边界修复 · 20261101T033413761732Z

审查用户手测目录：normal覆盖VPN明确答案；context-first覆盖冲突；tool-failure及tool-recovery覆盖故障；clarification-first/second及session覆盖主动澄清续答。缺少独立paraphrase记录；followup保留的是已确认的旧版漏答；航班问题误追问出发地；本人记录表仍待填写。未代填本人判定，未修改原手测文件。

本次只修改能力边界提示，由真实模型判断并选动作，未按航班关键词硬编码路由。下面复测不代表重新全量验收。

### flight_ambiguous

输入：我想知道明天最早一班去北京的飞机是几点钟？？

检查通过：True；[完整Trace](scope-retests/20261101T033413761732Z/flight_ambiguous.json)。

```text
现有资料不足以回答，未找到可确认的依据。
尚待确认：
- 需要实时航班查询工具或外部航班时刻表数据
- 需要出发地机场、目的地北京的具体机场及出行日期才能查询最早航班
```

### flight_with_origin

输入：明天从上海去北京最早一班飞机几点钟？

检查通过：True；[完整Trace](scope-retests/20261101T033413761732Z/flight_with_origin.json)。

```text
现有资料不足以回答，未找到可确认的依据。
尚待确认：
- 缺少明天上海至北京的实时航班时刻表数据
- 缺少可查询民航航班实时信息的外部工具；当前仅有本地企业制度或产品资料检索能力
```

## 混合问题判断尺度调整 · 20261101T035105228113Z

按子命题判断支持/未知，保留原文校验；有引用且存在缺口时增加coverage=partial，正文先显示“以下部分可以确认”，再显示未知部分；status仍保留insufficient表示整体未完整解决。44项自动化测试通过。以下仅针对性复测。

输入：客户的相关信息是不是只能保存在公司已经确认的系统里面，不能保存在个人设备里面？

[原始Trace](mixed-retests/20261101T035105228113Z/customer-data.json)

{"partial_coverage": false, "security_cited": true, "missing_scope_visible": false, "audit_errors": []}

```text
依据已获取的适用资料：
[SECURITY] 客户资料只能保存在企业批准的系统内。未经授权不得将客户资料上传至个人网盘。
```

## 混合问题判断尺度调整 · 20261101T035140518881Z

按子命题判断支持/未知，保留原文校验；有引用且存在缺口时增加coverage=partial，正文先显示“以下部分可以确认”，再显示未知部分；status仍保留insufficient表示整体未完整解决。44项自动化测试通过。以下仅针对性复测。

输入：客户的相关信息是不是只能保存在公司已经确认的系统里面，不能保存在个人设备里面？

[原始Trace](mixed-retests/20261101T035140518881Z/customer-data.json)

{"partial_coverage": true, "security_cited": true, "missing_scope_visible": true, "audit_errors": []}

```text
以下部分可以确认：
[SECURITY] 客户资料只能保存在企业批准的系统内。未经授权不得将客户资料上传至个人网盘。
现有资料尚不能确认的部分：
- 现有资料明确客户资料只能保存在企业批准的系统内，且未经授权不得上传至个人网盘；但没有明确说明是否一律禁止保存在个人手机、个人电脑、U盘等个人设备本地，也未说明经授权情形或系统与设备访问终端的区别。
```

## 联合回归：用户事实、适用范围和部分回答冲突保护 · 20261101T043744668596Z

定位：旧条件提示过于笼统、原文展示混淆适用结论、冲突门禁仅拦answered。增加仅从用户消息提取的有限事实账本、基于实际原文的条件金额比较、跨状态版本核对。航班及混合扩展范围规则保留。自动化49项通过。先跑原9场景，再验证以下4项；不同阶段结果分别记录。

## 实际复测 20261101T043744668925Z

结果：9/9。原始记录：[本轮汇总](integrated-retests/20261101T043744668596Z/baseline/runs/20261101T043744668925Z/summary.json)。

- normal: answered；通过=True；错误=[]
- conflict: conflict；通过=True；错误=[]
- insufficient: insufficient；通过=True；错误=[]
- paraphrase: answered；通过=True；错误=[]
- followup: answered；通过=True；错误=[]
- tool_failure: incomplete；通过=True；错误=[]
- tool_recovery: answered；通过=True；错误=[]
- evidence_single: answered；通过=True；错误=[]
- evidence_conflict: conflict；通过=True；错误=[]

### intern

[原始Trace](integrated-retests/20261101T043744668596Z/intern.json)

{"audit_errors": []}

```text
资料存在冲突，尚不能确定适用结论；版本日期本身不足以确定优先级。
[EXP-B] 【优先级待确认】员工应在费用发生后15天内提交报销申请。本文件未声明废止或替代其他报销制度。
[EXP-A] 【优先级待确认】员工应在费用发生后30天内提交报销申请。本文件未说明与其他报销文件的优先级。
尚待确认：
- 实习生出差高铁费用350元是否可报销、适用标准及具体报销流程，现有资料没有明确说明。
- 实习生住宿费用409元是否可报销、适用住宿限额及具体报销流程，现有资料没有明确说明；现有住宿标准仅明确适用于正式员工，不能据此直接判断实习生。
- 费用报销申请应适用15天还是30天期限，两份全体员工制度规定不一致，且均未说明优先级或替代关系，需要权威确认。
请确认实习生差旅费用应优先适用哪份报销制度，以及15天和30天提交期限以哪一个为准？
```

### formal_one_night

[原始Trace](integrated-retests/20261101T043744668596Z/formal_one_night.json)

{"audit_errors": [], "conditional_comparison": true}

```text
需要补充适用信息后再确认。
[TRAVEL-HOTEL] 正式员工在中国大陆出差的住宿费用上限为每晚500元。超出上限的部分须在预订前获得部门负责人书面确认。
[EXP-B] 【优先级待确认】员工应在费用发生后15天内提交报销申请。本文件未声明废止或替代其他报销制度。
[EXP-A] 【优先级待确认】员工应在费用发生后30天内提交报销申请。本文件未说明与其他报销文件的优先级。
根据你提供的信息，正式员工一晚住宿费为409元，未超过资料规定的每晚500元上限。若本次是在中国大陆出差，该比较适用；这是金额标准比较，不代表已确认全部报销条件。[TRAVEL-HOTEL]
尚待确认：
- 出差地点是否在中国大陆，以判断409元一晚住宿是否适用每晚500元上限。
- 350元高铁费用的具体报销规则，现有检索结果未提供交通费标准。
- 15天与30天两个报销申请期限均适用全体员工且无替代关系，需确认以哪项制度为准。
本次出差是否在中国大陆？另外，报销提交期限应适用15天还是30天的制度？
```

### flight

[原始Trace](integrated-retests/20261101T043744668596Z/flight.json)

{"audit_errors": [], "correct_boundary": true}

```text
现有资料不足以回答，未找到可确认的依据。
尚待确认：
- 明天飞往北京的最早航班起飞时间
- 可用的实时航班查询工具或外部航班数据
- 具体出发地机场
```

### mixed

[原始Trace](integrated-retests/20261101T043744668596Z/mixed.json)

{"audit_errors": [], "partial": true}

```text
以下是已核对的资料（具体适用范围见各条）：
[SECURITY] 客户资料只能保存在企业批准的系统内。未经授权不得将客户资料上传至个人网盘。
现有资料尚不能确认的部分：
- 现有资料未明确是否所有个人设备都不能保存客户资料；仅明确不得未经授权上传至个人网盘。
```

联合回归结论：原9场景9/9通过；4项新增检查均达到本轮预期。修复后的正式员工一晚409元输出明确金额比较、只追问大陆地区等未确认条件；实习生不套用正式员工上限；航班仍insufficient；混合设备问题仍partial。有限用户事实识别和scope规则仍有覆盖边界。

## 用户手测模型切换审查：manual-20261101-124441

本轮只读审查已有记录，没有发起新模型调用，没有改写用户原始结果。7份运行JSON：6份返回doubao-seed-2-1-pro-260915，1份paraphrase.json返回doubao-seed-2-1-turbo-260628。不能据此宣称Turbo完整验收通过。

|文件|实际模型|状态|步数|记录内部审计|
|---|---|---|---|---|
|clarification-first.json|doubao-seed-2-1-pro-260915|needs_clarification|2|[]|
|clarification-second.json|doubao-seed-2-1-pro-260915|answered|3|[]|
|context-first.json|doubao-seed-2-1-pro-260915|incomplete|10|[]|
|followup.json|doubao-seed-2-1-pro-260915|insufficient|8|[]|
|insufficient.json|doubao-seed-2-1-pro-260915|insufficient|3|[]|
|normal.json|doubao-seed-2-1-pro-260915|answered|2|[]|
|paraphrase.json|doubao-seed-2-1-turbo-260628|insufficient|3|[]|

审查结论：

- Turbo的混合改写样例：检索→读SECURITY→finish/insufficient，coverage=partial，无协议重试；已确认与未知范围区分合理。一个样例不构成同条件的Pro/Turbo比较。
- Pro的年假明确答案、上市计划资料外、主动澄清及身份补充续答表现符合预期。
- context-first为真实失败：max_steps_reached。模型已读EXP-A与EXP-B，但finish还引用了未完整读取的其他文档；现有conflict校验要求所有被引文档都已read，统一错误conflict_requires_two_read_documents无法清楚指出是哪份额外引用未读。模型反复提交未修复，耗尽预算。应改善校验反馈精度或明确只核对冲突集合，不能称本轮全部通过。
- followup识别了北京、一晚409元与正式员工，但把已确认事实放进missing_info，表达仍不够直接；有限确定性用户事实抽取未识别“昨天一天的409的住宿费”这一表达，因此未触发独立金额比较。记录中曾有校验修正，不能说全程无错误。
- 这组paraphrase是混合语义边界样例，不是纯同义对照；本目录没有Turbo的正常/资料外/工具失败三组完整覆盖。

建议先确认新终端实际LLM_MODEL，再用Turbo只补正常、资料外、工具失败及冲突场景。保留本轮Pro失败历史；不要把现有文件更名或改写成Turbo结果。工作目录不自动进入提交材料，审阅后的代表性记录需整理至examples。本人记录表是可选辅助材料，不是新增必交项。

## 新20组混合测试 · 20261101T051921397765Z（UTC）

先冻结预期再测试。16组单轮+4组双轮，共24条用户输入。双轮助手历史由本轮真实生成。数据集SHA256：71292ba8d58873163906efa4f18feadf13e4c1b3090119915304b636e002d019。规则初筛并非完整语义正确性证明，失败不重跑覆盖。

### M01 年假与年终奖金

输入：我已转正，在这儿干满一个服务年了，带工资的假能有多少天？休完以后年底奖金会被扣吗？

预期：确认12天；不推断奖金政策。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](mixed20-runs/20261101T051921397765Z/M01-turn-1.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[LEAVE-FT] 正式员工每个完整服务年度享有12天带薪年假。年假申请应提前3个工作日提交直属主管。
现有资料尚不能确认的部分：
- 休完带薪年假是否会导致年底奖金被扣，现有企业制度资料中没有明确说明。
```


### M02 休假提前量与审批入口

输入：我是正式员工，准备请年休，最晚得提前几个上班日找主管？顺便把内部请假网页地址发给我。

预期：保留提前3工作日，入口未知。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](mixed20-runs/20261101T051921397765Z/M02-turn-1.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[LEAVE-FT] 年假申请应提前3个工作日提交直属主管。
现有资料尚不能确认的部分：
- 现有资料中未提及内部请假网页地址的相关信息
```


### M03 实习请假与月度次数

输入：我是实习同学，下周有私事要请假，提前多久跟导师打招呼？每个月可以这么请多少回而不影响考核？

预期：提前1工作日有依据；次数/考核无依据。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](mixed20-runs/20261101T051921397765Z/M03-turn-1.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[LEAVE-IN] 实习生因个人事务请假须提前1个工作日向导师申请，是否带薪以实习协议为准。
现有资料尚不能确认的部分：
- 现有资料未明确实习生每月因私事请假的次数上限，以及该类请假是否会影响考核的相关规定。
```


### M04 实习带薪与保险

输入：我还在实习期，能和转正同事拿一样的年度带薪假么？请假这几天的意外保险是不是也一定照常保？

预期：不得套正式员工12天；不承诺保险。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](mixed20-runs/20261101T051921397765Z/M04-turn-1.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[LEAVE-IN] 实习生不适用正式员工的12天带薪年假制度。实习生因个人事务请假须提前1个工作日向导师申请，是否带薪以实习协议为准。
[LEAVE-FT] 正式员工每个完整服务年度享有12天带薪年假。年假申请应提前3个工作日提交直属主管。
现有资料尚不能确认的部分：
- 现有资料没有明确说明实习生请假期间的意外保险是否照常投保。
```


### M05 报账期限与退款到账

输入：员工垫出去的钱应该隔多久把报账申请递上去？交完以后财务最迟几天必须把钱打回来？

预期：交叉核对15/30；到账时限未知。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](mixed20-runs/20261101T051921397765Z/M05-turn-1.json)

```text
资料存在冲突，尚不能确定适用结论；版本日期本身不足以确定优先级。
[EXP-A] 【优先级待确认】员工应在费用发生后30天内提交报销申请。本文件未说明与其他报销文件的优先级。
[EXP-B] 【优先级待确认】员工应在费用发生后15天内提交报销申请。本文件未声明废止或替代其他报销制度。
尚待确认：
- 员工垫付费用后财务付款的最迟到账时限，现有资料中没有相关规定
关于费用报销提交期限，EXP-A（2026-01-01）规定30天、EXP-B（2026-03-01）规定15天，两份文件均未说明优先级或替代关系，请问应以哪份制度为准？
```


### M06 较新版报销与短信服务

输入：报账FAQ看起来更新些，我是不是只按较短期限交就行？你还能到期前一天给我自动发短信提醒吗？

预期：日期不定权威；无短信工具。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](mixed20-runs/20261101T051921397765Z/M06-turn-1.json)

```text
资料存在冲突，尚不能确定适用结论；版本日期本身不足以确定优先级。
[EXP-B] 【优先级待确认】员工应在费用发生后15天内提交报销申请。本文件未声明废止或替代其他报销制度。
[EXP-A] 【优先级待确认】员工应在费用发生后30天内提交报销申请。本文件未说明与其他报销文件的优先级。
尚待确认：
- 现有资料未提及报销到期前一天自动发短信提醒的相关服务或机制
- 两份同为全体员工适用的报销期限文件未明确替代或优先级，无法确定是否按较短期限执行
请问费用报销期限以《费用报销提交规则》还是《费用报销操作 FAQ》为准？
```


### M07 住宿限额与餐补

输入：我已经转正，在广州跑业务准备订房，单晚最多能花多少？一天的伙食津贴又能拿多少？

预期：住宿大陆正式每晚500；餐补未知。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](mixed20-runs/20261101T051921397765Z/M07-turn-1.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[TRAVEL-HOTEL] 正式员工在中国大陆出差的住宿费用上限为每晚500元。超出上限的部分须在预订前获得部门负责人书面确认。
现有资料尚不能确认的部分：
- 现有资料中未找到正式员工出差伙食津贴的相关标准，无法确认一天的伙食津贴金额
```


### M08 超额房费与班次

输入：我是正式员工，这次去南京的旅馆一夜要620块，按制度订之前该找谁确认？明早最早一趟去南京的高铁几点开？

预期：超额预订前部门负责人书面确认；无实时班次。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](mixed20-runs/20261101T051921397765Z/M08-turn-1.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[TRAVEL-HOTEL] 正式员工在中国大陆出差的住宿费用上限为每晚500元。超出上限的部分须在预订前获得部门负责人书面确认。
现有资料尚不能确认的部分：
- 明早最早一趟去南京的高铁发车时刻属于外部实时交通数据，现有企业制度资料中没有相关查询能力和数据。
```


### M09 登录验证与重置网址

输入：我在家连公司的远程网络，除了账户口令还得输入什么？要是手机丢了，在哪个网址自助重置那个验证方式？

预期：动态验证码有依据，重置网址未知。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](mixed20-runs/20261101T051921397765Z/M09-turn-1.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[IT-VPN] 远程办公登录VPN需要企业账号密码和动态验证码。连续5次验证失败后账号将锁定15分钟，可联系IT服务台处理。
现有资料尚不能确认的部分：
- 手机丢失后自助重置动态验证码（验证方式）的网址未在现有资料中明确说明
```


### M10 账号锁定与全天值班

输入：远程登录的验证连续输错五回，被锁后通常得等几分钟、能找谁？IT那边是不是凌晨三点也有人接电话？

预期：15分钟及IT服务台；值班时段未知。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](mixed20-runs/20261101T051921397765Z/M10-turn-1.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[IT-VPN] 远程办公登录VPN需要企业账号密码和动态验证码。连续5次验证失败后账号将锁定15分钟，可联系IT服务台处理。
现有资料尚不能确认的部分：
- 现有资料未明确IT服务台的值班时间，无法确认凌晨三点是否有人接电话。
```


### M11 视频规格与字幕

输入：Aurora普通标准套餐输出视频能用哪种封装、画面最高多清楚？它还能自动听语音生成字幕吗？

预期：MP4/1080p有依据，不编字幕能力。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](mixed20-runs/20261101T051921397765Z/M11-turn-1.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[PRODUCT-EXPORT] Aurora标准版支持导出MP4格式视频，最高分辨率为1080p。当前资料未说明4K导出能力。
现有资料尚不能确认的部分：
- Aurora普通标准套餐是否具备自动听语音生成字幕的功能，现有资料中没有明确说明。
```


### M12 更高分辨率与订阅价

输入：我用Aurora标准档，把成片存出来的分辨率上限是多少？想升到能出超高清的套餐，每个月要花多少钱？

预期：1080p有依据，4K/升级套餐价格未说明。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](mixed20-runs/20261101T051921397765Z/M12-turn-1.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[PRODUCT-EXPORT] Aurora标准版支持导出MP4格式视频，最高分辨率为1080p。当前资料未说明4K导出能力。
现有资料尚不能确认的部分：
- 现有资料未说明能导出超高清（如4K）的Aurora套餐类型、是否存在此类套餐以及对应的月费/升级价格。
```


### M13 客户数据与个人终端

输入：客户信息放在公司认可的应用里才合规，对吧？那么所有自用手机、电脑都连打开查看也绝对不允许吗？

预期：认可系统同义；禁止网盘不等于禁止设备访问。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](mixed20-runs/20261101T051921397765Z/M13-turn-1.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[SECURITY] 客户资料只能保存在企业批准的系统内。未经授权不得将客户资料上传至个人网盘。
现有资料尚不能确认的部分：
- 现有资料未明确规定是否允许通过自用手机、电脑等个人设备打开查看客户信息，仅限制了保存位置和上传个人网盘的行为。
```


### M14 个人云盘与处罚

输入：没获许可就把客户文件传进自己的云盘是不行的吧？如果真这么做，公司会罚多少钱或者直接辞退？

预期：保留未经授权条件，不编处罚。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](mixed20-runs/20261101T051921397765Z/M14-turn-1.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[SECURITY] 客户资料只能保存在企业批准的系统内。未经授权不得将客户资料上传至个人网盘。
现有资料尚不能确认的部分：
- 现有资料未明确未经授权将客户资料上传至个人网盘的具体处罚措施，包括罚款金额或是否直接辞退。
```


### M15 两个已有制度加实时天气

输入：我是转正员工，年休额度有几天、远程办公进内网又得用什么验证？另外北京明天会下雨吗？

预期：两个已知事项都引用；不编实时天气。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](mixed20-runs/20261101T051921397765Z/M15-turn-1.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[LEAVE-FT] 正式员工每个完整服务年度享有12天带薪年假。年假申请应提前3个工作日提交直属主管。
[IT-VPN] 远程办公登录VPN需要企业账号密码和动态验证码。连续5次验证失败后账号将锁定15分钟，可联系IT服务台处理。
现有资料尚不能确认的部分：
- 北京明天是否下雨属于外部实时天气信息，现有工具仅能查询本地企业制度，无法提供该天气数据。
```


### M16 房费和导出加企业规划

输入：我转正后在杭州出差住宿一晚的费用标准多少？Aurora标准档能输出什么格式？再问一句公司明年打算上市吗？

预期：两篇证据同时保留；上市计划未知。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](mixed20-runs/20261101T051921397765Z/M16-turn-1.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[TRAVEL-HOTEL] 正式员工在中国大陆出差的住宿费用上限为每晚500元。超出上限的部分须在预订前获得部门负责人书面确认。
[PRODUCT-EXPORT] Aurora标准版支持导出MP4格式视频，最高分辨率为1080p。当前资料未说明4K导出能力。
现有资料尚不能确认的部分：
- 公司明年是否打算上市，现有企业制度与产品资料中无相关依据，无法通过当前工具查询
```


### M17 身份澄清续答与奖金

输入：我在这里干满一年，年休能放几天还领工资？年度绩效奖会不会跟着少？ / 补充一下，我已转成正式员工了；刚才年休和绩效奖金的两个问题都想了解。

预期：后轮使用真实前轮历史，不能只因补身份就漏掉奖金缺口。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](mixed20-runs/20261101T051921397765Z/M17-turn-1.json)

```text
需要补充适用信息后再确认。
[LEAVE-FT] 正式员工每个完整服务年度享有12天带薪年假。年假申请应提前3个工作日提交直属主管。
[LEAVE-IN] 实习生不适用正式员工的12天带薪年假制度。实习生因个人事务请假须提前1个工作日向导师申请，是否带薪以实习协议为准。
尚待确认：
- 用户的具体用工身份（正式员工或实习生等）尚未明确，无法确定适用的年假天数与工资规则。
- 现有资料未说明休年假是否会影响年度绩效奖。
请问你目前的用工身份是正式员工还是实习生呢？
```

[第2轮Trace](mixed20-runs/20261101T051921397765Z/M17-turn-2.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[LEAVE-FT] 正式员工每个完整服务年度享有12天带薪年假。年假申请应提前3个工作日提交直属主管。
现有资料尚不能确认的部分：
- 现有资料未说明休年假是否会影响年度绩效奖。
```


### M18 身份纠正住宿和交通

输入：我是实习生，去武汉出差住店花了409元，车票350元，住宿有没有金额标准，交通票又怎么报？ / 前面身份讲错了，我已是正式员工；房费确实是一晚409元，住宿标准和那350元交通票都还请帮我核对。

预期：保留纠正身份、一晚；不把正式住宿标准当交通标准。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](mixed20-runs/20261101T051921397765Z/M18-turn-1.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[TRAVEL-HOTEL] 【仅适用正式员工，不能直接套用于你当前的实习生身份】正式员工在中国大陆出差的住宿费用上限为每晚500元。超出上限的部分须在预订前获得部门负责人书面确认。
[LEAVE-IN] 实习生不适用正式员工的12天带薪年假制度。实习生因个人事务请假须提前1个工作日向导师申请，是否带薪以实习协议为准。
现有资料尚不能确认的部分：
- 实习生出差住宿是否有金额标准、是否适用正式员工标准，现有资料没有明确说明
- 实习生出差交通车票的报销规则，现有资料没有明确说明
```

[第2轮Trace](mixed20-runs/20261101T051921397765Z/M18-turn-2.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[TRAVEL-HOTEL] 【仅适用正式员工，不能直接套用于你当前的实习生身份】正式员工在中国大陆出差的住宿费用上限为每晚500元。超出上限的部分须在预订前获得部门负责人书面确认。
现有资料尚不能确认的部分：
- 正式员工出差交通票（350元车票）的报销标准及规则，现有资料没有明确说明
```


### M19 错误范围追问续答

输入：客户材料只放公司许可系统可以理解为不许放到个人云盘么？这是否也代表用私人的电脑登录看一眼都违规？ / 我说的是自己的电脑仅在线查看，不把文件下载到本机；公司系统存储要求和这种访问方式都帮我分开说明。

预期：新增条件不等于已有访问授权，保留已知存储条款。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](mixed20-runs/20261101T051921397765Z/M19-turn-1.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[SECURITY] 客户资料只能保存在企业批准的系统内。未经授权不得将客户资料上传至个人网盘。
现有资料尚不能确认的部分：
- 现有资料仅明确客户资料只能保存在企业批准的系统内、未经授权不得上传个人网盘，未明确说明是否允许用私人电脑登录公司许可系统查看客户资料，无法判断该行为是否违规。
```

[第2轮Trace](mixed20-runs/20261101T051921397765Z/M19-turn-2.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[SECURITY] 客户资料只能保存在企业批准的系统内。未经授权不得将客户资料上传至个人网盘。
现有资料尚不能确认的部分：
- 现有资料仅明确客户资料的存储要求和上传个人网盘的限制，未对使用私人电脑登录公司许可系统仅在线查看、不下载到本机的访问方式作出明确规定，无法判断该行为是否违规。
```


### M20 版本选择与节日放假

输入：报销申请递交期限到底几天？下个月我们公司哪天放假，也能一并告诉我吗？ / 提交期限我倾向用FAQ里那一版，但没有人给我确认优先级；假期安排那一项也还想知道。

预期：用户倾向不消除15/30冲突；不凭公共节日推公司通知。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](mixed20-runs/20261101T051921397765Z/M20-turn-1.json)

```text
资料存在冲突，尚不能确定适用结论；版本日期本身不足以确定优先级。
[EXP-B] 【优先级待确认】员工应在费用发生后15天内提交报销申请。本文件未声明废止或替代其他报销制度。
[EXP-A] 【优先级待确认】员工应在费用发生后30天内提交报销申请。本文件未说明与其他报销文件的优先级。
尚待确认：
- 现有企业制度中未查询到下个月的公司放假安排，缺少相关外部或内部节假日安排的资料依据
报销申请递交期限存在15天和30天两种规定且均未说明优先级，请问应以哪份制度为准？
```

[第2轮Trace](mixed20-runs/20261101T051921397765Z/M20-turn-2.json)

```text
资料存在冲突，尚不能确定适用结论；版本日期本身不足以确定优先级。
[EXP-B] 【优先级待确认】员工应在费用发生后15天内提交报销申请。本文件未声明废止或替代其他报销制度。
[EXP-A] 【优先级待确认】员工应在费用发生后30天内提交报销申请。本文件未说明与其他报销文件的优先级。
尚待确认：
- 现有企业制度资料中未查询到公司下个月放假安排的相关依据。
- 费用报销提交期限在《费用报销操作 FAQ》（15天）与《费用报销提交规则》（30天）中规定不一致，且两份文件均未明确各自的优先级或替代关系。
请确认报销提交期限应适用《费用报销操作 FAQ》还是《费用报销提交规则》，或由哪个部门/制度确定两者的优先级？
```


完成20/20；规则初筛通过20/20；模型['doubao-seed-2-1-turbo-260628']；API报告token合计284696，不等于已核实扣费。[本轮汇总](mixed20-runs/20261101T051921397765Z/summary.json)。

### 20组混合测试逐条审读结论

规则初筛20/20；Codex对全部24份回答逐条审读后，19组符合本轮预期，M18失败。该审读不是独立人工标注或第二模型裁判。

M18第二轮“我已是正式员工”未被有限身份账本识别，旧实习生标签污染最终展示；模型缺口文字本身已经按正式员工处理。失败原样保留，本轮不修代码后覆盖重跑。

真实模型：['doubao-seed-2-1-turbo-260628']；API报告token合计284696，不等于已核实扣费；观察到3个协议/校验恢复事件。

[审读结论及恢复事件](mixed20-runs/20261101T051921397765Z/review.json)。

其他限制：部分条款引用需要读者自行对应具体问法；规则评分对语义范围的检查有限；20组全部含未知项，因此不能独立证明系统对完全可答问题不保守。不能把20/20初筛写成20/20语义正确。

### 冲突误拦截的旧Trace离线重放

在旧context-first的相同工具结果上重放第6步结束决策；旧校验错误为['conflict_requires_two_read_documents']，修复后错误为[]。这是历史决策的离线校验重放，不是新模型响应，不计入真实模型通过率。

## 实际复测 20261101T062515498683Z

结果：9/9。原始记录：[本轮汇总](release-regression/baseline/runs/20261101T062515498683Z/summary.json)。

- normal: answered；通过=True；错误=[]
- conflict: conflict；通过=True；错误=[]
- insufficient: insufficient；通过=True；错误=[]
- paraphrase: answered；通过=True；错误=[]
- followup: answered；通过=True；错误=[]
- tool_failure: incomplete；通过=True；错误=[]
- tool_recovery: answered；通过=True；错误=[]
- evidence_single: answered；通过=True；错误=[]
- evidence_conflict: conflict；通过=True；错误=[]

## 新20组混合测试 · 20261101T062819231194Z（UTC）

先冻结预期再测试。16组单轮+4组双轮，共24条用户输入。双轮助手历史由本轮真实生成。数据集SHA256：71292ba8d58873163906efa4f18feadf13e4c1b3090119915304b636e002d019。规则初筛并非完整语义正确性证明，失败不重跑覆盖。

### M01 年假与年终奖金

输入：我已转正，在这儿干满一个服务年了，带工资的假能有多少天？休完以后年底奖金会被扣吗？

预期：确认12天；不推断奖金政策。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](release-regression/mixed20/20261101T062819231194Z/M01-turn-1.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[LEAVE-FT] 正式员工每个完整服务年度享有12天带薪年假。年假申请应提前3个工作日提交直属主管。
现有资料尚不能确认的部分：
- 现有资料未明确说明正式员工休完带薪年假后年底奖金是否会被扣除
```


## 交付收尾修复说明

角色账本补充“我已是”“已经转正”、否定式纠正及假设句保护；冲突校验与Trace审计统一为冲突集合必须读取，额外非冲突原文引用可用完整检索片段。保留原文、版本及适用范围门禁。新增回归自动化54/54通过。原9场景真实回归9/9通过；同一冻结20组正在另轮回归，最终结论待本轮结果和内容审读。

### M02 休假提前量与审批入口

输入：我是正式员工，准备请年休，最晚得提前几个上班日找主管？顺便把内部请假网页地址发给我。

预期：保留提前3工作日，入口未知。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](release-regression/mixed20/20261101T062819231194Z/M02-turn-1.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[LEAVE-FT] 年假申请应提前3个工作日提交直属主管。
现有资料尚不能确认的部分：
- 现有资料中未明确内部请假网页地址，无法提供该信息。
```


### M03 实习请假与月度次数

输入：我是实习同学，下周有私事要请假，提前多久跟导师打招呼？每个月可以这么请多少回而不影响考核？

预期：提前1工作日有依据；次数/考核无依据。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](release-regression/mixed20/20261101T062819231194Z/M03-turn-1.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[LEAVE-IN] 实习生因个人事务请假须提前1个工作日向导师申请，是否带薪以实习协议为准。
现有资料尚不能确认的部分：
- 现有资料未明确实习生每月因私事请假的次数上限，也未说明该类请假次数对实习考核的具体影响。
```


### M04 实习带薪与保险

输入：我还在实习期，能和转正同事拿一样的年度带薪假么？请假这几天的意外保险是不是也一定照常保？

预期：不得套正式员工12天；不承诺保险。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](release-regression/mixed20/20261101T062819231194Z/M04-turn-1.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[LEAVE-IN] 实习生不适用正式员工的12天带薪年假制度。实习生因个人事务请假须提前1个工作日向导师申请，是否带薪以实习协议为准。
[LEAVE-FT] 正式员工每个完整服务年度享有12天带薪年假。年假申请应提前3个工作日提交直属主管。
现有资料尚不能确认的部分：
- 现有资料未说明实习生请假期间意外保险是否照常承保的相关规定。
```


### M05 报账期限与退款到账

输入：员工垫出去的钱应该隔多久把报账申请递上去？交完以后财务最迟几天必须把钱打回来？

预期：交叉核对15/30；到账时限未知。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](release-regression/mixed20/20261101T062819231194Z/M05-turn-1.json)

```text
资料存在冲突，尚不能确定适用结论；版本日期本身不足以确定优先级。
[EXP-A] 【优先级待确认】员工应在费用发生后30天内提交报销申请。本文件未说明与其他报销文件的优先级。
[EXP-B] 【优先级待确认】员工应在费用发生后15天内提交报销申请。本文件未声明废止或替代其他报销制度。
尚待确认：
- 现有资料未提及财务收到报销申请后最迟的付款或打款时限。
关于报销申请提交期限，《费用报销提交规则》（EXP-A）规定费用发生后30天内提交，《费用报销操作 FAQ》（EXP-B）规定费用发生后15天内提交，两份文件均未说明优先级或替代关系，请确认以哪份制度为准？
```


### M06 较新版报销与短信服务

输入：报账FAQ看起来更新些，我是不是只按较短期限交就行？你还能到期前一天给我自动发短信提醒吗？

预期：日期不定权威；无短信工具。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](release-regression/mixed20/20261101T062819231194Z/M06-turn-1.json)

```text
资料存在冲突，尚不能确定适用结论；版本日期本身不足以确定优先级。
[EXP-B] 【优先级待确认】员工应在费用发生后15天内提交报销申请。本文件未声明废止或替代其他报销制度。
[EXP-A] 【优先级待确认】员工应在费用发生后30天内提交报销申请。本文件未说明与其他报销文件的优先级。
尚待确认：
- 当前没有提供到期前一天自动发短信提醒的相关工具或制度依据，无法确认是否具备该功能
- 两份制度均适用于全体员工且未明确优先级，无法确定是否可直接按较短期限执行
请问这两份报销制度（EXP-A 30天期限、EXP-B 15天期限）中，应以哪份为准，或由哪个部门确认适用优先级？
```


### M07 住宿限额与餐补

输入：我已经转正，在广州跑业务准备订房，单晚最多能花多少？一天的伙食津贴又能拿多少？

预期：住宿大陆正式每晚500；餐补未知。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](release-regression/mixed20/20261101T062819231194Z/M07-turn-1.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[TRAVEL-HOTEL] 正式员工在中国大陆出差的住宿费用上限为每晚500元。超出上限的部分须在预订前获得部门负责人书面确认。
现有资料尚不能确认的部分：
- 现有资料中未找到正式员工出差伙食津贴（餐补）的标准相关规定，无法回答一天伙食津贴金额。
```


### M08 超额房费与班次

输入：我是正式员工，这次去南京的旅馆一夜要620块，按制度订之前该找谁确认？明早最早一趟去南京的高铁几点开？

预期：超额预订前部门负责人书面确认；无实时班次。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](release-regression/mixed20/20261101T062819231194Z/M08-turn-1.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[TRAVEL-HOTEL] 正式员工在中国大陆出差的住宿费用上限为每晚500元。超出上限的部分须在预订前获得部门负责人书面确认。
现有资料尚不能确认的部分：
- 明早最早一趟去南京的高铁几点开属于实时外部交通数据，现有工具仅支持查询本地企业制度或合成产品资料，无高铁班次时刻查询能力，无法提供相关信息。
```


### M09 登录验证与重置网址

输入：我在家连公司的远程网络，除了账户口令还得输入什么？要是手机丢了，在哪个网址自助重置那个验证方式？

预期：动态验证码有依据，重置网址未知。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](release-regression/mixed20/20261101T062819231194Z/M09-turn-1.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[IT-VPN] 远程办公登录VPN需要企业账号密码和动态验证码。连续5次验证失败后账号将锁定15分钟，可联系IT服务台处理。
现有资料尚不能确认的部分：
- 手机丢失后自助重置验证方式的网址未在现有资料中明确说明
```


### M10 账号锁定与全天值班

输入：远程登录的验证连续输错五回，被锁后通常得等几分钟、能找谁？IT那边是不是凌晨三点也有人接电话？

预期：15分钟及IT服务台；值班时段未知。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](release-regression/mixed20/20261101T062819231194Z/M10-turn-1.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[IT-VPN] 远程办公登录VPN需要企业账号密码和动态验证码。连续5次验证失败后账号将锁定15分钟，可联系IT服务台处理。
现有资料尚不能确认的部分：
- IT服务台的值班时间（包括凌晨三点是否有人接电话）现有资料没有明确说明
```


### M11 视频规格与字幕

输入：Aurora普通标准套餐输出视频能用哪种封装、画面最高多清楚？它还能自动听语音生成字幕吗？

预期：MP4/1080p有依据，不编字幕能力。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](release-regression/mixed20/20261101T062819231194Z/M11-turn-1.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[PRODUCT-EXPORT] Aurora标准版支持导出MP4格式视频，最高分辨率为1080p。当前资料未说明4K导出能力。
现有资料尚不能确认的部分：
- Aurora普通标准套餐是否支持自动听语音生成字幕，现有资料没有明确说明
```


### M12 更高分辨率与订阅价

输入：我用Aurora标准档，把成片存出来的分辨率上限是多少？想升到能出超高清的套餐，每个月要花多少钱？

预期：1080p有依据，4K/升级套餐价格未说明。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](release-regression/mixed20/20261101T062819231194Z/M12-turn-1.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[PRODUCT-EXPORT] Aurora标准版支持导出MP4格式视频，最高分辨率为1080p。当前资料未说明4K导出能力。
现有资料尚不能确认的部分：
- 可导出超高清（4K）的Aurora套餐名称及每月费用，现有资料未提及相关套餐定价信息
```


### M13 客户数据与个人终端

输入：客户信息放在公司认可的应用里才合规，对吧？那么所有自用手机、电脑都连打开查看也绝对不允许吗？

预期：认可系统同义；禁止网盘不等于禁止设备访问。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](release-regression/mixed20/20261101T062819231194Z/M13-turn-1.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[SECURITY] 客户资料只能保存在企业批准的系统内。未经授权不得将客户资料上传至个人网盘。
现有资料尚不能确认的部分：
- 现有资料没有明确说明是否绝对不允许在自用手机、电脑等个人设备上打开查看客户信息。
```


### M14 个人云盘与处罚

输入：没获许可就把客户文件传进自己的云盘是不行的吧？如果真这么做，公司会罚多少钱或者直接辞退？

预期：保留未经授权条件，不编处罚。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](release-regression/mixed20/20261101T062819231194Z/M14-turn-1.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[SECURITY] 客户资料只能保存在企业批准的系统内。未经授权不得将客户资料上传至个人网盘。
现有资料尚不能确认的部分：
- 现有资料未明确未经授权将客户资料上传至个人网盘的具体处罚措施（包括罚款金额或是否直接辞退）。
```


### M15 两个已有制度加实时天气

输入：我是转正员工，年休额度有几天、远程办公进内网又得用什么验证？另外北京明天会下雨吗？

预期：两个已知事项都引用；不编实时天气。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](release-regression/mixed20/20261101T062819231194Z/M15-turn-1.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[LEAVE-FT] 正式员工每个完整服务年度享有12天带薪年假。年假申请应提前3个工作日提交直属主管。
[IT-VPN] 远程办公登录VPN需要企业账号密码和动态验证码。连续5次验证失败后账号将锁定15分钟，可联系IT服务台处理。
现有资料尚不能确认的部分：
- 北京明天是否会下雨属于外部实时天气数据，现有企业制度及产品资料工具均无法查询，缺少外部天气数据来源及相关查询能力。
```


### M16 房费和导出加企业规划

输入：我转正后在杭州出差住宿一晚的费用标准多少？Aurora标准档能输出什么格式？再问一句公司明年打算上市吗？

预期：两篇证据同时保留；上市计划未知。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](release-regression/mixed20/20261101T062819231194Z/M16-turn-1.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[TRAVEL-HOTEL] 正式员工在中国大陆出差的住宿费用上限为每晚500元。超出上限的部分须在预订前获得部门负责人书面确认。
[PRODUCT-EXPORT] Aurora标准版支持导出MP4格式视频，最高分辨率为1080p。当前资料未说明4K导出能力。
现有资料尚不能确认的部分：
- 公司明年是否打算上市：现有企业制度及产品资料中未提及相关上市计划信息，无法核实。
```


### M17 身份澄清续答与奖金

输入：我在这里干满一年，年休能放几天还领工资？年度绩效奖会不会跟着少？ / 补充一下，我已转成正式员工了；刚才年休和绩效奖金的两个问题都想了解。

预期：后轮使用真实前轮历史，不能只因补身份就漏掉奖金缺口。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](release-regression/mixed20/20261101T062819231194Z/M17-turn-1.json)

```text
需要补充适用信息后再确认。
[LEAVE-FT] 正式员工每个完整服务年度享有12天带薪年假。
[LEAVE-IN] 实习生不适用正式员工的12天带薪年假制度。实习生因个人事务请假须提前1个工作日向导师申请，是否带薪以实习协议为准。
尚待确认：
- 用户的用工身份（正式员工或实习生等）尚不明确，无法确定适用的年假天数及是否带薪的具体规则
- 现有资料未提及年度绩效奖是否会因休年假而减少的相关规定
请问你是公司的正式员工还是实习生？
```

[第2轮Trace](release-regression/mixed20/20261101T062819231194Z/M17-turn-2.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[LEAVE-FT] 正式员工每个完整服务年度享有12天带薪年假。年假申请应提前3个工作日提交直属主管。
现有资料尚不能确认的部分：
- 现有资料未提及正式员工年度绩效奖是否会因休年假而减少的相关规定
```


### M18 身份纠正住宿和交通

输入：我是实习生，去武汉出差住店花了409元，车票350元，住宿有没有金额标准，交通票又怎么报？ / 前面身份讲错了，我已是正式员工；房费确实是一晚409元，住宿标准和那350元交通票都还请帮我核对。

预期：保留纠正身份、一晚；不把正式住宿标准当交通标准。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](release-regression/mixed20/20261101T062819231194Z/M18-turn-1.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[TRAVEL-HOTEL] 【仅适用正式员工，不能直接套用于你当前的实习生身份】正式员工在中国大陆出差的住宿费用上限为每晚500元。超出上限的部分须在预订前获得部门负责人书面确认。
现有资料尚不能确认的部分：
- 实习生出差住宿是否有金额标准，现有资料未明确说明。
- 实习生出差交通票的报销规则，现有资料未明确说明。
```

[第2轮Trace](release-regression/mixed20/20261101T062819231194Z/M18-turn-2.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[TRAVEL-HOTEL] 正式员工在中国大陆出差的住宿费用上限为每晚500元。超出上限的部分须在预订前获得部门负责人书面确认。
现有资料尚不能确认的部分：
- 正式员工出差350元交通票（如车票）的具体报销规则（如交通工具等级、金额标准、报销范围等），现有资料未明确说明。
```


### M19 错误范围追问续答

输入：客户材料只放公司许可系统可以理解为不许放到个人云盘么？这是否也代表用私人的电脑登录看一眼都违规？ / 我说的是自己的电脑仅在线查看，不把文件下载到本机；公司系统存储要求和这种访问方式都帮我分开说明。

预期：新增条件不等于已有访问授权，保留已知存储条款。

规则检查：{"non_complete_status": false, "known_evidence_retained": false, "specific_unknowns_identified": false, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](release-regression/mixed20/20261101T062819231194Z/M19-turn-1.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[SECURITY] 客户资料只能保存在企业批准的系统内。未经授权不得将客户资料上传至个人网盘。
现有资料尚不能确认的部分：
- 现有资料未明确说明使用私人电脑登录公司许可系统查看客户资料是否属于违规行为。
```

[第2轮Trace](release-regression/mixed20/20261101T062819231194Z/M19-turn-2.json)

```text
本次查询未完成，不能确认结论。
```


### M20 版本选择与节日放假

输入：报销申请递交期限到底几天？下个月我们公司哪天放假，也能一并告诉我吗？ / 提交期限我倾向用FAQ里那一版，但没有人给我确认优先级；假期安排那一项也还想知道。

预期：用户倾向不消除15/30冲突；不凭公共节日推公司通知。

规则检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}

[第1轮Trace](release-regression/mixed20/20261101T062819231194Z/M20-turn-1.json)

```text
资料存在冲突，尚不能确定适用结论；版本日期本身不足以确定优先级。
[EXP-B] 【优先级待确认】员工应在费用发生后15天内提交报销申请。本文件未声明废止或替代其他报销制度。
[EXP-A] 【优先级待确认】员工应在费用发生后30天内提交报销申请。本文件未说明与其他报销文件的优先级。
尚待确认：
- 公司下个月的具体放假日期，现有企业制度资料中没有相关放假安排的规定。
报销申请递交期限有15天和30天两个版本且均适用于全体员工、无明确替代关系，请确认应以哪份制度为准？
```

[第2轮Trace](release-regression/mixed20/20261101T062819231194Z/M20-turn-2.json)

```text
资料存在冲突，尚不能确定适用结论；版本日期本身不足以确定优先级。
[EXP-B] 【优先级待确认】员工应在费用发生后15天内提交报销申请。本文件未声明废止或替代其他报销制度。
[EXP-A] 【优先级待确认】员工应在费用发生后30天内提交报销申请。本文件未说明与其他报销文件的优先级。
尚待确认：
- 公司下个月的具体放假日期，现有企业制度资料中没有相关放假安排的规定。
报销申请递交期限的15天版本（费用报销操作 FAQ）与30天版本（费用报销提交规则）均适用于全体员工且无明确替代关系，请确认应以哪份制度为准？
```


完成20/20；规则初筛通过19/20；模型['doubao-seed-2-1-turbo-260628']；API报告token合计253458，不等于已核实扣费。[本轮汇总](release-regression/mixed20/20261101T062819231194Z/summary.json)。

## M19连接失败后的单独复测 · 20261101T063653762702Z

原完整20组首轮保持19/20（M19第二轮model_connection_failed），本次独立重跑同一M19双轮，新的第一轮回复生成新的真实历史，不覆盖原失败。

[本轮Trace](release-regression/m19-retry/20261101T063653762702Z/M19-turn-1.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[SECURITY] 客户资料只能保存在企业批准的系统内。未经授权不得将客户资料上传至个人网盘。
现有资料尚不能确认的部分：
- 现有资料没有明确说明使用私人电脑登录查看客户资料是否违规。
```

[本轮Trace](release-regression/m19-retry/20261101T063653762702Z/M19-turn-2.json)

```text
以下是已核对的资料（具体适用范围见各条）：
[SECURITY] 客户资料只能保存在企业批准的系统内。未经授权不得将客户资料上传至个人网盘。
现有资料尚不能确认的部分：
- 现有资料没有明确说明使用私人电脑仅在线查看（不下载到本机）客户资料是否违规。
```

单独复测检查：{"non_complete_status": true, "known_evidence_retained": true, "specific_unknowns_identified": true, "real_response_every_turn": true, "trace_audit": true}。不能将这次通过改写为原完整轮20/20。

## 修复后交付回归结论

M18身份纠正已验证，额外非冲突引用不再导致误拦截；原失败决策离线重放已通过。完整轮19/20，M19网络失败后单独通过，不改写整轮统计。[本轮逐条审读](release-regression/mixed20/20261101T062819231194Z/review.json)。已统一评估入口、更新可核实的用户手测贡献及已知限制。

## 提交材料总检查与说明校对

本轮未追加真实API调用。自动化测试再次54/54通过；按Git待提交清单审查代码、配置、资料、全部JSON和文档。240个文件、177份Trace内部审计通过，未发现已配置密钥、本机隐私路径、保密题目名称或失效文档链接。51份相同内容为快照与分轮归档的重复，保留历史未删除。

已纠正README中未全量回归的旧说明、手测文档中主动澄清待验证的旧说明、可选记录表的表达，以及例子目录的历史/最新结果入口。历史轮次原始结果不改写。所有当前结论以03-evaluation.md为入口；个人贡献说明按实际观察记录，仍由提交者审读确认。

## 提交结构与文字规范整理

当前docs目录仅保留01-requirements.md、02-solution.md、03-evaluation.md、04-ai-usage.md、05-retrospective.md。设计说明直接描述当前四节点、状态、模型和工具职责；辅助操作说明移至本地忽略目录。统一历史报告及测试结果归档在examples，原始JSON不改写。运行日志追加位置及文档链接已同步更新。结构整理后54项自动化测试通过。

## 五份提交文档内容逐项对齐

按规定重写：01为用户/目标/范围/成功标准；02为调用流程/动态决策/技术取舍；03为测试预期/实际结果/失败和限制；04为AI辅助内容/个人修改及验证；05为最难问题/学习收获/下一步。移除额外工时章节和重复主题；最难问题明确说明混合多轮中的事实、适用范围与程序校验一致性。仅修改文档，本轮没有新增模型调用或修改运行代码。
