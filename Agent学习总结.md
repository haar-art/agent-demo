# 2026-09-02 Agent 学习总结

## 1. Agent 是什么（一句话 + Agent = ?）

- 自己写一句话定义
- 三要素：LLM / 工具 / 循环 —— 用自己话说各自干啥的

答案：Agent简单来说就是会思考，会调用工具，遇到问题会反复思考重做来解决问题的智能体。LLM是大模型它来决定是否调用工具；工具就是相当于大模型用来解决问题的技能包，大模型会从他这里调用合适的东西来解决他的问题；而循环是Agent重要组成部分，ReAct是通过思考后执行，然后最后将执行后的结果返回给大模型的闭环，而循环就是反复做一圈的机制

## 2. agent_v1.py vs func_call.py（升级了三处）

- SYSTEM 提示词 —— 它到底改了模型的啥"决策"
- 工具升级（write_note / read_note）—— 怎么让 Agent "有记忆"
- _safe_path 沙箱 —— 路径穿越是啥、怎么拦的

System提示词主要改了模型的自主决策能力，它从原本的单纯的调用工具变成了agent主动调用工具，自己主动思考该怎么做，如何做失败了该怎么重新做来解决问题的决策能力；

工具升级：他先让agent把每次运行调用工具的过程和结果写进文档里，就是write note，而大模型下次调用的时候就可以就可以阅读这些文档后就能明白，上次都做了些什么，以达到记忆的目的，当然，这种记忆方式必须得主动，如果想升级成长久记忆的话，得再继续给他升级这个后续，等我做了再讨论；

沙箱：路径穿越，就是当你的路径有"../"时，AI就可能会一层一层往上跨越，可能会修改到系统文件windows或者user之类的；怎么拦的：sandbox会把所有问题锁在沙箱里，所有内容都在沙箱里进行，我是这么理解的。

## 3. ReAct 循环

- Reason / Act / Observe 三步各自的含义
- 每步对应 agent_v1.py 哪一行

1. Reason（思考）：模型看 messages 决定下一步要不要调工具。

   resp = client.chat.completions.create(model=MODEL, messages=messages, tools=tools)
   msg = resp.choices[0].message

2. Act（行动）：模型返回 tool_calls，等于"下订单"。

   if msg.tool_calls:
       print(f"[第 {step} 步] Agent 决定调用工具：")
       messages.append(msg)

3. Observe（观察）：执行工具，把结果塞回历史。

   result = func(**args)
   except Exception as e:
       result = f"工具执行出错：{e}"
   print(f"   <- 结果：{result}")
   messages.append({
       "role": "tool",
       "tool_call_id": tc.id,
       "content": str(result),
   })

## 4. 4 个工具一览（calculator / write_note / read_note / list_files）

- 每个一句话：干啥、有啥坑（calculator 的字符白名单、write_note 走 _safe_path、list_files 的 pattern 用 fnmatch）

- calculator=计算器，坑：eval前先过滤字符白名单，防止执行无关代码（eval 能跑任意 Python，白名单把输入锁死在 数字+运算符）
- write_note：把文件写进 Sandbox 里。坑：走 _safe_path，给越权路径（如 ../../xxx）会被拦截并抛 ValueError，但主循环把异常接住变成"工具执行出错"字符串喂回模型，程序不崩
- read_note：阅读sandbox文件。坑：文件不存在时返回"文件不存在"字符串，不抛异常，所以 Agent 不会崩
- list_files：列出 Sandbox 文件。坑：pattern 用 fnmatch 通配（认 *.txt 不认正则）；沙箱为空时不报错，返回一句提示字符串，循环不会断

## 5. 700GB 误删事件的启示

- 这事为啥会发生
- 我这个 demo 怎么防

这事儿是因为：开发者让 AI 帮忙清理文件，AI 拿到了删除权限、指令又含糊，结果把不该删的大目录（约 700GB）删了。注意——这跟路径穿越不是一回事：路径穿越是用 ../ 逃出沙箱去碰系统文件（_safe_path 防那个），700GB 是「有删除权 + 范围太大」。

我这个 demo 防两层：① 把所有文件锁进沙箱里，碰不到外面的系统文件；② 根本没有 delete 函数，AI 想删也删不掉，没那个能力。

## 6. 自测答案（用自己的话，不背术语）

- Q1: 主循环是不是同一段？为什么
- Q2: 记忆靠啥 + Kiro Crew 的差在哪
- Q3: _safe_path 防啥
- Q4: Observe 对应代码哪段

q1：是同一段，主循环部分，除了system提示词变化了以外，其他地方本质上变化不大；

q2.Agent记忆主要靠write note文件，Agent会把每次项目的过程结果写进文件， Agent下次工作的时候会读取文件；
主要差在kiro crew的Agent是，自动记忆，新任务开始前自动阅读，而我的这个demo主要是要手动去阅读，我得告诉他先阅读上次的内容

q3._safe_path主要防路径穿越，注意../；

q4.Observe对应代码主要从主循环部分下边，result = func(**args) 开始，到 messages.append({role:tool...}) 结束
