# agent-demo：从零手写一个最小可运行 Agent

> 化工专业转行 AI 的练手项目。不依赖 LangChain，用原生 OpenAI SDK 手写一个 ReAct 循环 Agent，作为 AI Agent 应用层作品集的第一件可演示作品。

## 这是什么

一个命令行 Agent，演示 Agent 的核心三要素：

- **LLM（大脑）**：决定要不要调工具、调哪个、调几次
- **工具（手脚）**：`calculator` / `write_note` / `read_note` / `list_files`
- **循环（引擎）**：`while True` 反复「思考 → 行动 → 观察」，直到任务完成

相对普通的 Function Calling，它多了三样东西：`SYSTEM` 提示词（赋予目标感）、`write_note`（让 Agent 能"记忆"）、`_safe_path` 沙箱（安全护栏）。

## 运行

```bash
pip install -r requirements.txt
cp .env.example .env        # 填入你的 API 配置（base_url / api_key / model）
python agent_v1.py
```

进去问它一个多步任务，看它怎么自己编排步骤：

```
你：帮我算 1234 乘以 5678 等于多少，然后把结果写进 result.txt 文件里
```

预期：Agent 先调 `calculator`、再调 `write_note`，最后给一句话答复。

## 文件说明

| 文件 | 作用 |
|---|---|
| `agent_v1.py` | 真正的 Agent（含 4 个工具 + 沙箱护栏 + ReAct 主循环） |
| `func_call.py` | 前身：只有工具 + 循环、没有目标感/记忆/护栏的"半个 Agent" |
| `Agent学习总结.md` | 学习过程记录 + 自测答案（新手向） |
| `.env.example` | API 配置模板 |
| `requirements.txt` | 依赖 |

## 安全设计（呼应 Claude Code 误删 700GB 事件）

- **`_safe_path` 沙箱**：所有文件操作锁死在 `sandbox/` 内，防 `../` 路径穿越
- **无 delete 函数**：Agent 没有任何删除能力，想删也删不掉
- **calculator 字符白名单 + 空 `__builtins__`**：`eval` 被锁死在 数字+运算符，杜绝执行任意代码

## 下一步（作品集演进路线）

1. 套 Web UI（Flask / Gradio），从本地脚本变可演示网页
2. 接 RAG：把检索函数做成 Agent 的一个 tool
3. 用 LangChain 重写一遍（对照裸写版学框架，不当黑盒）
4. 加步数护栏 + 人工确认（生产必考题）
5. 做一个最小 MCP server（工具标准化）

## 模型配置

默认按 DeepSeek 配（OpenAI 兼容接口）：

```
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_API_KEY=sk-你的密钥
OPENAI_MODEL=deepseek-chat
```

> 注意：用 `deepseek-chat`（V3）跑多轮带工具最稳；`deepseek-reasoner`（R1）是推理模型，工具调度不稳定，不推荐。
> 换成任何 OpenAI 兼容中转站只需改这三个值，代码一行不用动。
