<div align="center">

[English](DOCTOR-MESSAGE-GUIDE.md) | [中文](languages/doctor-message-guide-zh.md)

</div>

---

# 医生消息指南

## 什么是医生消息？

医生消息是 Skill Pilot 框架中用于诊断和调试代理行为的特殊消息类型。

## 如何编写医生消息

### 基本结构

```
@doctor
问题描述：
代理名称：
预期行为：
实际行为：
日志信息：
```

### 示例

```
@doctor
问题描述：代理无法访问外部 API
代理名称：APIAgent
预期行为：应该成功检索数据
实际行为：返回超时错误
日志信息：
  [ERROR] Connection timeout after 30s
  [INFO] Retrying with exponential backoff
```

## 医生消息最佳实践

1. **清晰的问题陈述** - 准确描述你遇到的问题
2. **完整的上下文** - 包括代理名称、配置和相关日志
3. **可重现的步骤** - 提供可以重现问题的步骤
4. **预期vs实际** - 明确说明预期行为与实际行为的区别

## 获取帮助

有关更多帮助，请查看 [CONTRIBUTING.md](contributing-zh.md)。

---

<div align="center">

[English](DOCTOR-MESSAGE-GUIDE.md) | [中文](languages/doctor-message-guide-zh.md)

</div>