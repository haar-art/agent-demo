"""可录屏的「AI 工作笔记」演示页。

运行：
  使用项目 README 中的虚拟环境 Python 执行本文件。
  浏览器会打开 http://127.0.0.1:8787

网页只是把 agent_v1.py 的读、写、计算工具换成更容易看懂的界面；
模型仍需通过 .env 中的 API 配置真实调用。
"""

import json
import os
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


ROOT = Path(__file__).parent
SANDBOX = ROOT / "sandbox"
LOG_NAME = "worklog.txt"
LOG_PATH = SANDBOX / LOG_NAME

load_dotenv(ROOT / ".env")
SANDBOX.mkdir(exist_ok=True)

API_KEY = os.getenv("OPENAI_API_KEY")
BASE_URL = os.getenv("OPENAI_BASE_URL")
MODEL = os.getenv("OPENAI_MODEL")
client = OpenAI(api_key=API_KEY, base_url=BASE_URL) if API_KEY and MODEL else None


def safe_path(filename: str) -> Path:
    """仅允许访问 sandbox，避免演示 Agent 碰到电脑其他文件。"""
    target = (SANDBOX / filename).resolve()
    if target.parent != SANDBOX.resolve():
        raise ValueError("只能操作演示用的工作笔记")
    return target


def calculator(expression: str):
    allowed = set("0123456789+-*/().% ")
    if not set(expression) <= allowed:
        return "计算式里有不允许的字符"
    try:
        return eval(expression, {"__builtins__": {}}, {})
    except Exception as exc:
        return f"计算失败：{exc}"


def write_note(filename: str, content: str):
    path = safe_path(filename)
    path.write_text(content, encoding="utf-8")
    return f"已记进工作笔记：{filename}"


def read_note(filename: str):
    path = safe_path(filename)
    if not path.exists():
        return "工作笔记还是空的：还没有这条记录"
    return path.read_text(encoding="utf-8")


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "做四则运算。需要算数时必须调用。",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_note",
            "description": "把结果记进工作笔记。只能写 sandbox 内的文件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["filename", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_note",
            "description": "读取过去写下的工作笔记。",
            "parameters": {
                "type": "object",
                "properties": {"filename": {"type": "string"}},
                "required": ["filename"],
            },
        },
    },
]

FUNCTIONS = {
    "calculator": calculator,
    "write_note": write_note,
    "read_note": read_note,
}

SYSTEM = """你是一个演示用的 AI 助手。用非常口语、简短的中文回答。
你可以计算、读工作笔记、写工作笔记。每次涉及过去的记录，必须先读取 worklog.txt；
每次涉及计算，必须调用计算工具；用户要求记下结果时，必须写入 worklog.txt。
不要提 API、函数、代码或技术术语。"""


def run_agent(prompt: str) -> dict:
    if client is None:
        raise RuntimeError("还没有配置 API。请检查 .env 中的 OPENAI_API_KEY 和 OPENAI_MODEL。")

    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": prompt},
    ]
    actions = []
    for _ in range(8):
        response = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS)
        message = response.choices[0].message
        if not message.tool_calls:
            return {"answer": message.content or "我做完了。", "actions": actions}

        messages.append(message)
        for call in message.tool_calls:
            name = call.function.name
            arguments = json.loads(call.function.arguments)
            action_name = {
                "calculator": "算了一下",
                "read_note": "翻了翻工作笔记",
                "write_note": "记进了工作笔记",
            }.get(name, name)
            try:
                result = FUNCTIONS[name](**arguments)
            except Exception as exc:  # 让观众能看到出错，而不是整个网页白屏
                result = f"没做成：{exc}"
            actions.append({"name": action_name, "result": str(result)})
            messages.append({"role": "tool", "tool_call_id": call.id, "content": str(result)})
    raise RuntimeError("这次思考步骤太多，请再试一次。")


PAGE = r'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI 的工作笔记</title>
<style>
  * { box-sizing: border-box; } body { margin:0; min-height:100vh; color:#19221e; font-family:"Microsoft YaHei",system-ui,sans-serif; background:#f6f3ea; }
  main { max-width:1180px; margin:auto; padding:54px 30px; } .eyebrow { color:#6c7e51; font-weight:700; letter-spacing:2px; font-size:14px; }
  h1 { margin:12px 0 8px; font-size:48px; letter-spacing:-2px; } .sub { margin:0 0 34px; color:#69716d; font-size:18px; }
  .grid { display:grid; grid-template-columns:1.15fr .85fr; gap:22px; } .panel { background:#fffefb; border:1px solid #e5dfd1; box-shadow:0 10px 30px #372f1710; border-radius:20px; padding:26px; }
  .panel h2 { margin:0 0 8px; font-size:20px; } .hint { color:#727a73; font-size:14px; margin:0 0 20px; }
  .choices { display:grid; gap:10px; } button { font:inherit; text-align:left; border:1px solid #d8dfcc; background:#f9fbf5; padding:15px 17px; border-radius:12px; cursor:pointer; color:#243322; transition:.15s; }
  button:hover { background:#edf4e3; border-color:#91a871; transform:translateY(-1px); } button.small { font-size:13px; padding:8px 11px; color:#70766b; background:#fff; }
  textarea { width:100%; min-height:75px; resize:vertical; border:1px solid #d8dfd1; border-radius:12px; padding:12px; font:inherit; } .send { background:#45652f; color:white; border:0; margin-top:10px; font-weight:700; width:100%; text-align:center; }
  .status { margin-top:22px; min-height:126px; background:#f1f5eb; border-radius:14px; padding:16px; } .status p { margin:0 0 9px; line-height:1.6; } .answer { font-size:18px; font-weight:700; }
  .action { color:#53634e; font-size:14px; padding-top:7px; border-top:1px dashed #ccd7c2; margin-top:7px; } .notehead { display:flex; justify-content:space-between; align-items:center; }
  pre { white-space:pre-wrap; min-height:255px; margin:18px 0 0; padding:18px; border-radius:12px; background:#fff8af; color:#4f4824; font:16px/1.8 ui-monospace,Consolas,monospace; box-shadow:inset 0 0 0 1px #eadf7f; }
  .empty { color:#9a9260; } .footer { color:#7c837c; font-size:13px; margin-top:16px; } @media(max-width:760px) { main{padding:30px 16px;} h1{font-size:36px;} .grid{grid-template-columns:1fr;} }
</style>
</head>
<body><main>
  <div class="eyebrow">零基础也能看懂的 AI 演示</div><h1>AI 的工作笔记</h1>
  <p class="sub">它不会自动记住昨天，但可以翻一翻自己写下的记录。</p>
  <div class="grid"><section class="panel"><h2>交代给 AI 一件事</h2><p class="hint">按顺序点三次，就能演示“忘记 → 记下 → 想起”。</p>
    <div class="choices"><button onclick="ask('读取 worklog.txt，告诉我我上次算的结果。')">① 问它：昨天我们做了什么？</button>
    <button onclick="ask('计算 1234 × 5678，把算式和结果写进 worklog.txt，最后告诉我完成。')">② 让它算一题，并记下来</button>
    <button onclick="ask('读取工作笔记 worklog.txt，告诉我上次的计算结果。')">③ 再问一次：昨天算的结果是什么？</button></div>
    <p class="hint" style="margin:20px 0 8px">也可以换成你自己的任务：</p><textarea id="custom" placeholder="例如：把今天要做的事记进工作笔记"></textarea><button class="send" onclick="ask(document.getElementById('custom').value)">交给 AI</button>
    <div class="status" id="status"><p class="answer">准备好了。</p><p>从第 ① 步开始试试。</p></div></section>
    <aside class="panel"><div class="notehead"><div><h2>AI 的工作笔记</h2><p class="hint" style="margin:4px 0 0">只有这里写过的，它下次才知道。</p></div><button class="small" onclick="resetLog()">清空演示</button></div><pre id="note" class="empty">（这里还是空的）</pre><div class="footer">演示文件只保存在本项目的 sandbox 文件夹中。</div></aside>
  </div></main>
<script>
const status = document.getElementById('status'), note = document.getElementById('note');
function esc(s){ const d=document.createElement('div'); d.textContent=s; return d.innerHTML; }
async function refresh(){ const r=await fetch('/api/note'); const d=await r.json(); note.textContent=d.content || '（这里还是空的）'; note.className=d.content?'':'empty'; }
async function ask(prompt){ if(!prompt.trim()) return; status.innerHTML='<p class="answer">AI 正在处理…</p><p>它会自己决定要不要翻笔记、计算或记下来。</p>'; try { const r=await fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt})}); const d=await r.json(); if(!r.ok) throw Error(d.error); let html='<p class="answer">'+esc(d.answer)+'</p>'; (d.actions||[]).forEach(a=>html+='<div class="action">'+esc(a.name)+'：'+esc(a.result)+'</div>'); status.innerHTML=html; await refresh(); } catch(e) { status.innerHTML='<p class="answer">这一步没跑起来。</p><p>'+esc(e.message)+'</p>'; } }
async function resetLog(){ await fetch('/api/reset',{method:'POST'}); status.innerHTML='<p class="answer">演示已清空。</p><p>现在再问它“昨天做了什么”，它会找不到记录。</p>'; await refresh(); }
refresh();
</script></body></html>'''


class Handler(BaseHTTPRequestHandler):
    def send_json(self, body: dict, status: int = 200):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/":
            data = PAGE.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif self.path == "/api/note":
            self.send_json({"content": LOG_PATH.read_text(encoding="utf-8") if LOG_PATH.exists() else ""})
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self):
        try:
            if self.path == "/api/reset":
                LOG_PATH.unlink(missing_ok=True)
                self.send_json({"ok": True})
                return
            if self.path != "/api/ask":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            size = int(self.headers.get("Content-Length", "0"))
            prompt = json.loads(self.rfile.read(size)).get("prompt", "")
            if not isinstance(prompt, str) or not prompt.strip():
                self.send_json({"error": "先写一句想交代给 AI 的话。"}, 400)
                return
            self.send_json(run_agent(prompt.strip()))
        except Exception as exc:
            self.send_json({"error": str(exc)}, 500)

    def log_message(self, _format, *_args):
        return  # 不把访问日志刷进录屏终端


if __name__ == "__main__":
    address = "http://127.0.0.1:8787"
    server = ThreadingHTTPServer(("127.0.0.1", 8787), Handler)
    print(f"演示页已启动：{address}")
    print("录完后回到终端按 Ctrl+C 关闭。")
    webbrowser.open(address)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n演示页已关闭。")
    finally:
        server.server_close()
