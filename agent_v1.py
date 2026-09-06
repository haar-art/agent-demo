# agent_v1.py —— 最小可运行 Agent（在 func_call.py 基础上"升级"）
#
# 你已经会的是 Function Calling：模型下订单(tool_calls) -> Python 执行 -> 结果回传。
# 今天加的三件事，让它变成"真正的 Agent"：
#   1) 系统提示词把模型框成"有目标、会自己规划步骤"的 Agent
#   2) 工具从"算钱"升级为"真实动作"：读文件 / 写文件（写文件 = Agent 有了记忆）
#   3) 安全护栏：工具只能在 sandbox/ 目录里操作，禁止越权、禁止删除
#      （呼应 9/1 新闻：Claude Code 误删 700GB —— 护栏不是可选项）
#
# 你接下来要做的（别光看）：
#   A) 跑起来，问一个"需要先算、再写文件"的任务，看它怎么自己编排步骤
#   B) 给本文件加第 4 个工具 list_files（列出 sandbox/ 内容），走"加菜单+加函数+加白名单"三步
#   C) 故意把 write_note 的文件名改成 "../../etc/passwd" 试试，看护栏怎么拦你

import os, json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent / ".env")   # 密钥在仓库根目录 .env（见 .env.example）
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL"))
MODEL = os.getenv("OPENAI_MODEL")

# 沙箱根目录：所有文件操作都被锁在这里，模型/工具出不去这个文件夹
SANDBOX = Path(__file__).parent / "sandbox"
SANDBOX.mkdir(exist_ok=True)

# 安全函数：把用户/模型给的文件名"锁死"在 sandbox 内，防路径穿越（../ 逃跑）
def _safe_path(filename: str) -> Path:
    target = (SANDBOX / filename).resolve()          # 解析成绝对路径
    if not str(target).startswith(str(SANDBOX.resolve())):
        raise ValueError(f"越权访问被拦截：{filename} 不在沙箱内")
    return target

# ② 工具菜单（"说明书"，写给会读它的模型看）
tools = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "做四则运算与取余。用户要算加减乘除、百分比时使用。参数 expression 是数学表达式，如 '1234 * 5678'。",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "数学表达式，如 '100 / 8'"},
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_note",
            "description": "把一段文字写进沙箱里的某个文件（如 'memo.txt'）。用于让 Agent 保存/记住结果。不能写沙箱外的路径，也没有删除能力。",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "文件名，如 'result.txt'，只能在沙箱内"},
                    "content": {"type": "string", "description": "要写入的文字内容"},
                },
                "required": ["filename", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_note",
            "description": "读取沙箱里某个文件的内容。用于 Agent 回头查看自己之前写下的东西（这就是它的'记忆'）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "要读取的文件名，如 'result.txt'"},
                },
                "required": ["filename"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "列出沙箱(sandbox)里的文件。可传 pattern 按后缀/名字过滤，如 '*.txt'；不传则列出全部。用于 Agent 先看清楚有哪些文件再决定下一步。",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "可选过滤，如 '*.txt'，留空则列全部"},
                },
                "required": [],
            },
        },
    },
]

# ③ 真正干活的函数（模型碰不到，全在白名单里）
def calculator(expression: str):
    # 只允许数字和基础运算符，杜绝 eval 执行任意代码
    allowed = set("0123456789+-*/().% ")
    if not set(expression) <= allowed:
        return "错误：表达式含非法字符"
    try:
        return eval(expression, {"__builtins__": {}}, {})
    except Exception as e:
        return f"计算失败：{e}"

def write_note(filename: str, content: str):
    path = _safe_path(filename)
    path.write_text(content, encoding="utf-8")
    return f"已写入 {filename}（{len(content)} 字）"

def read_note(filename: str):
    path = _safe_path(filename)
    if not path.exists():
        return f"文件不存在：{filename}"
    return path.read_text(encoding="utf-8")

def list_files(pattern: str = ""):
    import fnmatch
    files = [p for p in SANDBOX.iterdir() if p.is_file()]
    if pattern:
        files = [p for p in files if fnmatch.fnmatch(p.name, pattern)]
    if not files:
        return "（沙箱为空或无匹配文件）"
    rows = [f"{p.name}  ({p.stat().st_size} 字节)" for p in sorted(files)]
    return "\n".join(rows)

available_functions = {
    "calculator": calculator,
    "write_note": write_note,
    "read_note": read_note,
    "list_files": list_files,
}

# ④ 主循环：和 func_call.py 几乎一样 —— 这就是"Agent 的核心引擎"
SYSTEM = ("你是一个 Agent：目标是完成用户交代的任务。你可以调用工具来读写文件、做计算。"
          "每一步先思考再行动，直到任务真正完成，再给用户最终答复。")

def main():
    user_msg = input("你：")
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user_msg},
    ]
    step = 0
    while True:
        step += 1
        resp = client.chat.completions.create(model=MODEL, messages=messages, tools=tools)
        msg = resp.choices[0].message
        if msg.tool_calls:
            print(f"[第 {step} 步] Agent 决定调用工具：")
            messages.append(msg)                      # 原样回传模型订单（不能省）
            for tc in msg.tool_calls:
                name = tc.function.name
                args = json.loads(tc.function.arguments)
                print(f"   -> {name}({args})")
                func = available_functions.get(name)
                if func is None:
                    raise ValueError(f"未知工具：{name}")
                try:
                    result = func(**args)
                except Exception as e:
                    result = f"工具执行出错：{e}"
                print(f"   <- 结果：{result}")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result),
                })
            continue                                   # 调完工具，进入下一轮思考
        else:
            print("AI：" + (msg.content or "[模型返回空内容]"))
            break

if __name__ == "__main__":
    main()
