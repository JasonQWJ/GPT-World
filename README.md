# GPT-World Server

一个基于GPT搭建的世界，世界中的主观个体和客观物体均由GPT来支持其行动。
世界由多个环境构成，使用者可以（1）轻松地创建自己的环境，以及其中的主体和客体并挂载到世界上，（2）创造自己的agent并让其能访问自己或其他的世界。

Server 是开源的、分布式的，每个人都可以 host 自己的服务器和朋友们分享。


The dump file format of Agent is 

See `agent_format.json`.

If you need to modify the underlying function agent (if you are user, just skip)

See `agent_tool.py` and `agent_long_term_memory.py` and `agent.py` and `agent_prompt.py`.

Create your own environment just using a few sentences

See `environment_creation_utils.py`.

The dump file format of Environment is

See `environment_format.json`.

If you need to modify the underlying function of environment (if you are user, just skip)

See `environment.py`.

Run a server & environment

```
python run_server.py
```

