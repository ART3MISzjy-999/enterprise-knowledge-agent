# 企业知识问答 Agent

一个只依赖 Python 标准库的精简 ReAct 原型：模型根据工具结果选择检索、补查、读取原文、追问或结束，回答附可核查的原文证据。数据完全合成，不代表任何真实公司的制度或产品承诺。

**当前交付状态（2026-11-01修复后）**：54项自动化回归通过，原9场景真实回归9/9通过；冻结20组混合完整轮19/20通过（M19连接失败），M19单独重跑通过。M18身份标签及冲突误拦截已修复。[评估入口](docs/03-evaluation.md)集中列出预期、实际结果与Trace；[统一报告](examples/retest-report.md)保留完整历史。不能将单独重跑成功改写为原完整轮20/20。

## 安装和快速运行

在本仓库根目录运行。已验证环境：macOS、CPython 3.14.0、pip 25.3。代码要求 Python 3.11+，其他版本尚未实测。无数据库、无模型 SDK、无第三方测试依赖。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export PYTHONPATH="$PWD/src"

python -m unittest discover -s tests -v
python -m enterprise_agent evaluate --mode mock
python -m enterprise_agent ask '正式员工每年有多少天带薪年假？' --mode mock --mock-case normal
```

Mock 是预设决策列表，只接受所选场景的精确输入；不具备理解任意问题的能力。`evaluate --mode mock` 执行真实检索和引用校验，但模型决策来自脚本。

## 配置真实模型

```bash
test -f .env || cp .env.example .env
```

在 `.env` 填写自己的 `LLM_API_KEY`、`LLM_MODEL` 和兼容 Chat Completions 的 `LLM_BASE_URL`。方舟模型名可以是已授权的推理接入点 ID。`.env` 已被 Git 忽略；不要在命令行参数、截图或提交文件中粘贴密钥。环境变量优先于 `.env`。

默认示例针对方舟，使用严格 JSON Schema 输出和 `thinking=disabled`。换其他服务时先删除不支持的 `LLM_EXTRA_BODY`；若不支持 JSON mode，将 `LLM_JSON_MODE=0`，程序仍严格解析模型返回的 JSON。HTTP 层只通过 HTTPS 连接配置的服务，拒绝重定向，不会悄悄切换成 mock。配置/协议兼容性需要实际验证。

```bash
python -m enterprise_agent ask '正式员工每年有多少天带薪年假？' \
  --mode live --output work/normal.json

# 会产生实际模型调用及费用。默认最多10次决策、7次工具调用。
python -m enterprise_agent evaluate --mode live --output-dir examples/live
python -m enterprise_agent verify examples/live/*.json
```

成功补跑后检查 `examples/live/summary.json`：应为 `passed: 9`、`total: 9`；`real_llm_path_divergence: true` 仅是初筛，还须人工核对不同工具反馈与后续动作。`verify` 只核验记录内部的步骤和引用关系，**它通过不代表真实模型验收通过**。失败尝试也可通过格式审计。

## 多轮、历史、故障与上限

```bash
# 两次调用共享历史；第二轮会重新获取证据。
python -m enterprise_agent ask '正式员工每年有多少天带薪年假？' --session work/session.json
python -m enterprise_agent ask '那实习生呢？' --session work/session.json

# 使用准备好的历史文件
python -m enterprise_agent ask '那实习生呢？' --history examples/history.json

# 注入一次检索失败，让真实模型根据反馈决定是否重试。
python -m enterprise_agent ask '正式员工每年有多少天带薪年假？' --fail-search 1

# 持续失败、预算边界
python -m enterprise_agent ask '正式员工每年有多少天带薪年假？' --fail-search 99 --max-steps 4
python -m enterprise_agent ask '正式员工每年有多少天带薪年假？' --max-steps 1 --max-tool-calls 1
```

历史格式是 `[{"role":"user","content":"..."},{"role":"assistant","content":"..."}]`，最多20条。历史用来消解指代，不视为引用证据。`--session` 自动保留最近20条；文件仅保存在本地。可用 `--data PATH` 更换合成文档，`--env-file PATH` 指定配置文件。

退出码：`ask` 的完整答复、资料不足、冲突或追问为0，未完成/配置错误为2；`evaluate` 任一场景失败为1；`verify` 审计失败为1。冲突是有效业务结果，并不等于已确定制度结论。

## 输出与执行记录

- `result`：`answer`、`status`、`citations`（doc_id、原文整句、版本、范围、来源工具）、`missing_info`、`question`。
- `trace`：step、action、工具参数、完整工具返回及摘要、实际下一动作、简短公开行动依据、校验反馈、模型请求/响应摘要哈希与响应 ID（若服务返回）。不记录密钥、模型隐藏推理字段或内部思维链。
- `mode`、`evidence_kind`、`model_response_count`：明确区分离线脚本、真实调用尝试、取得模型响应的运行。
- `corpus_sha256`：本次语料快照摘要。`test_setup` 标明故障注入和移除文档等实验条件。

业务状态为 `answered / conflict / insufficient / needs_clarification / incomplete`。最终事实回答使用模型选取、程序校验的完整原文句子，不提供自由改写摘要。此外，仅对有明确用户输入和原文依据的住宿金额提供条件比较。引用校验能防止原文数字被篡改、引用未观察文档或截掉否定前缀；不能证明模型一定选对相关制度或穷尽全部证据。

## 仓库导航

```text
src/enterprise_agent/
  graph.py             精简状态循环与预算
  state.py             单轮问题、历史、观察和证据
  model.py             真实HTTP适配层、明确标注的离线脚本模型
  retrieval.py         中文双字词 + 同义改写 + BM25
  nodes/               decision / tool / observation / generate
  scenarios.py         合成输入、预期和离线决策脚本
  evaluation.py        场景评估、Trace审计
  __main__.py          CLI
tests/                 自动化回归，不访问真实模型
data/documents.json    8篇合成制度/FAQ
examples/offline/      9组实际离线输入、输出和Trace
examples/release-regression/  修复后原9场景、20组混合与M19重跑
examples/live*/        较早模型运行；保留历史轮次
docs/                  需求、设计、评估、AI使用和复盘
```

详细阅读：[需求概述](docs/01-requirements.md)、[架构与技术取舍](docs/02-solution.md)、[评估与未完成项](docs/03-evaluation.md)、[AI使用说明](docs/04-ai-usage.md)、[复盘](docs/05-retrospective.md)。

## 提交前清单

- [x] 已补齐最新9组真实运行，包括正常、资料不足、工具失败。提交前建议本人复现。
- [x] 已在评估文档列出多条不同工具反馈后的真实动作；提交者应审读并能解释。
- [ ] 审阅全部生成代码，自己完成并记录修改、局限与理解；在 AI 使用文档中确认个人贡献。不要声称全部独立手写。
- [ ] 检查所有待提交文件没有题面、公司内部材料、真实密钥、个人路径或真实会话数据；新生成的 Trace 也要复核。
- [ ] 本地重跑测试、离线场景和 Trace 审计；按目标方保密要求选择仓库可见性。

已经准备独立的本地 Git 仓库，不配置远程、不提交身份、不自动推送。审核后可自行执行：

```bash
git status --short
git add README.md requirements.txt .env.example .gitignore src tests examples data docs
git diff --cached --check
git diff --cached --stat
git commit -m "Add evidence-grounded enterprise QA agent"
```

建议维持约3小时 MVP 范围：框架35分钟、检索与证据65分钟、验证55分钟、文档25分钟。这是规划建议，非实际工时或完成承诺。

## 手动体验

通过前文CLI命令自行提问，连续对话从第一轮起使用同一`--session`文件。查看输出的`input.history`确认历史完整。


多轮费用修复与原9场景、20组混合回归已完成。当前结果及全部原始记录以[评估入口](docs/03-evaluation.md)为准；历史报告保留旧版失败与改进过程。

## 混合问题新测试集

新增[20组混合问题/对话](examples/mixed20-testset.md)，机器可读版本在data/mixed-evaluation-v1.json。16组单轮与4组双轮；每组均包含有依据和缺资料的子问题，预期在真实调用前冻结。

配置有效模型后运行：`PYTHONPATH=src python -m enterprise_agent.mixed_evaluation`。每轮在examples/mixed20-runs中保存原始Trace、冻结问题、汇总，并逐组追加统一复测报告。规则初筛不是完整语义正确性证明，需审读实际回答。
