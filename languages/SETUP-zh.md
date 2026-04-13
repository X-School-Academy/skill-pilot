<div align="center">

[English](SETUP.md) | [中文](languages/setup-zh.md)

</div>

---

# Skill Pilot 安装指南

## 前置要求

- Python 3.8 或更高版本
- pip 包管理器

## 安装步骤

### 1. 克隆仓库

```bash
git clone https://github.com/X-School-Academy/skill-pilot.git
cd skill-pilot
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 验证安装

```bash
python -c "import skill_pilot; print(skill_pilot.__version__)"
```

## 配置

编辑 `config.yaml` 文件来配置 Skill Pilot：

```yaml
agents:
  - name: Agent1
    type: OpenAI
    model: gpt-4
```

## 手动安装

如果你希望手动安装，请按照以下步骤进行：

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # 在 Windows 上使用 `venv\Scripts\activate`

# 安装依赖
pip install -r requirements.txt

# 运行测试
pytest tests/
```

## 故障排除

### 问题：导入错误

**解决方案：** 确保你在正确的目录中并且虚拟环境已激活。

### 问题：依赖冲突

**解决方案：** 尝试升级 pip：`pip install --upgrade pip`

---

<div align="center">

[English](SETUP.md) | [中文](languages/setup-zh.md)

</div>