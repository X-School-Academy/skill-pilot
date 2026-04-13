<div align="center">

[English](AGENTS.md) | [中文](languages/agents-zh.md)

</div>

---

# AI 代理系统文档

## 概述

Skill Pilot 代理系统是一个灵活的框架，用于创建和管理 AI 代理。

## 基本概念

### 代理

代理是可以执行技能并相互通信的自主实体。

### 技能

技能是代理可以执行的原子操作。

### 协作

代理可以相互协作来完成复杂任务。

## 创建代理

```python
from skill_pilot import Agent

agent = Agent(name="MyAgent")
```

## 定义技能

```python
@agent.skill
def process_data(data: dict) -> dict:
    # 处理数据
    return processed_data
```

## 代理通信

```python
# 发送消息给另一个代理
response = agent.send_message(target_agent="OtherAgent", message="Hello")
```

---

<div align="center">

[English](AGENTS.md) | [中文](languages/agents-zh.md)

</div>