# func_call.py —— Function Calling 最小可运行骨架
# 核心：模型只下订单（tool_calls），你的 Python 真正执行，再把结果喂回去
# 这是 agent_v1.py 的前身：只有工具 + 循环，没有"目标感/记忆/护栏"，所以是"半个 Agent"
import os, json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# ① 加载密钥（.env 在仓库根目录）
load_dotenv(Path(__file__).parent / ".env")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL"))
MODEL = os.getenv("OPENAI_MODEL")

# ② 工具说明书（"菜单"）——只给模型看，它据此下订单
tools = [{
    "type": "function",
    "function": {
        "name": "calculate_cashflow",
        "description": "计算每月现金流 = 月收入 - 月支出。用户想了解每月能剩多少钱时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "income":   {"type": "number", "description": "月收入（元）"},
                "expenses": {"type": "number", "description": "月支出（元）"},
            },
            "required": ["income", "expenses"],
        },
    },
},
{
    "type": "function",
    "function": {
        "name": "calculate_passive_ratio",
        "description": "计算被动收入占总收入的百分比。用户提到被动收入、睡后收入、财务自由进度时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "passive_income": {"type": "number", "description": "月被动收入（元）"},
                "total_income": {"type": "number", "description": "月总收入（元）"},
            },
            "required": ["passive_income", "total_income"],
        },
    },
},
]

# ③ 真正干活的 Python 函数（订单的"执行方"，模型碰不到）
def calculate_cashflow(income, expenses):
    return income - expenses
def calculate_passive_ratio(passive_income, total_income):
    if total_income == 0:
        return 0.0
    return (passive_income / total_income) * 100

available_functions = {
    "calculate_cashflow": calculate_cashflow,
    "calculate_passive_ratio": calculate_passive_ratio,
}

# ④ 主流程
def main():
    user_msg = input("你：")
    messages = [{"role": "user", "content": user_msg}]

    while True:
        resp = client.chat.completions.create(model=MODEL, messages=messages, tools=tools)
        msg = resp.choices[0].message

        if msg.tool_calls:
            messages.append(msg)  # 原样回传模型订单
            for tc in msg.tool_calls:
                name = tc.function.name
                args = json.loads(tc.function.arguments)
                func = available_functions.get(name)
                if func is None:
                    raise ValueError(f"未知工具：{name}")
                result = func(**args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result),
                })
            continue  # 调完工具，继续下一轮
        else:
            # 模型终于说话了
            print("AI：" + (msg.content or "[模型返回空内容]"))
            break

if __name__ == "__main__":
    main()
