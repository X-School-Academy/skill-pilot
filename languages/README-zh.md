<div align="center">

[English](README.md) | [中文](languages/readme-zh.md)

</div>

---

# Skill Pilot - 智能代理协作框架

Skill Pilot 是一个强大的框架，用于构建和编排多个 AI 代理系统。它提供了简洁的 API 来创建代理、定义技能并在代理之间进行通信。

## 🚀 快速开始

### 安装

按照 [SETUP.md](languages/setup-zh.md) 中的分步指南进行安装。

### 基础使用

```python
from skill_pilot import Agent, Skill

# 创建一个代理
agent = Agent(name="MyAgent")

# 定义一个技能
@agent.skill
def hello(name: str) -> str:
    return f"Hello, {name}!"

# 执行技能
result = agent.execute_skill("hello", {"name": "World"})
print(result)  # 输出: Hello, World!
```

## 📚 文档

- [SETUP.md](languages/setup-zh.md) - 安装和配置指南
- [CONTRIBUTING.md](languages/contributing-zh.md) - 贡献指南
- [DOCTOR-MESSAGE-GUIDE.md](languages/doctor-message-guide-zh.md) - 如何编写好的医生请求
- [AGENTS.md](languages/agents-zh.md) - 代理系统文档

关于初学者友好的医生请求示例，请参阅 [Skill Pilot Doctor Message Guide](languages/doctor-message-guide-zh.md)。

## 🤝 贡献

我们欢迎贡献！请查看 [CONTRIBUTING.md](languages/contributing-zh.md) 了解如何开始。

## 📝 许可证

此项目在 MIT 许可证下发布。

---

<div align="center">

[English](README.md) | [中文](languages/readme-zh.md)

</div>