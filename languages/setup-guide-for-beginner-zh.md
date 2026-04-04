# 用于生成本文档的提示词

请参考 `install.sh` 和 `skillpilot.sh`，编写一份面向零基础用户的 Skill Pilot 安装与使用手册。
目标用户完全不懂 Shell 命令。
手册必须从下面这条命令开始：
`curl -fsSL https://skill-pilot.ai/install.sh | bash`

然后说明如何运行：
`./skillpilot.sh`

手册必须使用中文。
需要补充适合初学者理解的 Shell 基础知识，以及 macOS、Linux（Ubuntu）、Windows（通过 WSL Ubuntu）环境中会用到的软件说明。
整篇文档都用中文。

---

# Skill Pilot 安装与首次使用手册（Windows / macOS / Linux（Ubuntu））

这份手册写给第一次接触命令行的用户，包括：

- Windows 用户
- macOS 用户
- Linux（Ubuntu）用户

你不需要先懂编程，也不需要先懂 Shell。你只要按顺序操作即可。

本手册基于项目里的 `install.sh` 和 `skillpilot.sh` 实际流程编写，目标是带你完成两件事：

1. 在你的系统上安装 Skill Pilot 所需环境
2. 第一次启动 Skill Pilot

---

## 一、先知道你要做什么

你将会做两步：

1. 在终端里运行下面这条安装命令

```bash
curl -fsSL https://skill-pilot.ai/install.sh | bash
```

2. 安装完成后，进入 Skill Pilot 目录，再运行：

```bash
./skillpilot.sh
```

请注意：

- 这些命令要在 **Terminal（终端）** 里运行，不是在浏览器地址栏里运行。
- 命令里的空格、符号、大小写都要保持原样。
- `./skillpilot.sh` 前面的 `./` 不能省略。它表示“运行当前文件夹里的这个脚本”。

---

## 二、什么是 Terminal、Shell、命令

### 1. 什么是 Terminal（终端）

终端是一个“文字操作窗口”。  
你可以把它理解成一个不用鼠标、主要靠输入文字来控制电脑的地方。

不同系统里，打开方式不同：

#### macOS

1. 按 `Command + Space`
2. 输入 `Terminal`
3. 按回车

#### Linux（Ubuntu）

常见方式：

1. 按 `Ctrl + Alt + T`
2. 或在应用菜单里搜索 `Terminal`

#### Windows

Windows 用户不要直接在 PowerShell 或 CMD 里安装和运行 Skill Pilot。  
请先使用 **WSL（Windows Subsystem for Linux）**，并安装 **Ubuntu**。

后续请在 Ubuntu 终端里操作。

常见进入方式：

1. 打开 `Windows Terminal`
2. 选择 `Ubuntu`

或者在 PowerShell / CMD 里输入：

```bash
wsl -d Ubuntu
```

打开后，你会看到一个黑色、白色或半透明窗口，这都正常。

### 2. 什么是 Shell

Shell 是终端背后真正“听你命令”的程序。

常见的 Shell 有：

- `zsh`
- `bash`

你不需要现在区分它们的全部差异。对这份手册来说，你只需要知道：

- 你输入命令
- Shell 负责执行

### 3. 什么是命令

命令就是你在终端里输入的一行文字，例如：

```bash
pwd
```

按回车后，电脑就会执行它。

### 4. 这几个基础动作先记住

- `回车`：执行当前命令
- macOS：
  - `Command + C`：复制已选中的文字
  - `Command + V`：粘贴
- Linux（Ubuntu）图形终端（大多数情况下）：
  - `Ctrl + Shift + C`：复制已选中的文字
  - `Ctrl + Shift + V`：粘贴
  - 不同终端程序的快捷键可能略有不同；如果不生效，可以右键菜单复制 / 粘贴
- 为什么 Ubuntu 终端里常见的是 `Ctrl + Shift + C`：
  - 在大多数 Ubuntu 图形应用里，例如浏览器、文本编辑器，`Ctrl + C` 通常表示复制
  - 但在终端环境里，`Ctrl + C` 被保留给“中断信号（SIGINT）”
  - 它的作用是停止当前正在运行的命令或程序
  - 为了避免和“复制”冲突，终端通常会把剪贴板复制改成 `Ctrl + Shift + C`
- `Control + C`：中断当前正在运行的命令
- 用鼠标选中文字：可以复制报错信息

---

## 三、开始安装前的准备

开始前，请确保：

- 你的电脑可以联网
- 终端可以正常打开
- 你愿意在安装过程中看到一些英文提示，这很正常

如果你是 Windows 用户，请先完成这一条：

- 先安装 WSL
- 在 WSL 中选择并安装 Ubuntu
- 后续在 `wsl -d Ubuntu` 进入的 Ubuntu 终端中安装和使用 Skill Pilot

可以简单理解为：

- Windows 本机负责提供桌面环境
- Ubuntu（WSL）负责运行 Skill Pilot 的命令行和开发工具

安装过程中，Skill Pilot 安装器可能会帮你安装这些工具：

- Xcode Command Line Tools（macOS）
- Linux Build Tools（Linux（Ubuntu） / WSL Ubuntu）
- Homebrew
- Git
- uv
- Python 3
- pnpm
- Node.js
- tmux
- wget
- ffmpeg

这些名字看起来很多，但你不用一项项手动处理。安装脚本会按顺序引导你。

---

## 四、正式开始安装

### 第 1 步：打开正确的终端环境

- macOS 用户：打开 `Terminal`
- Linux（Ubuntu）用户：打开系统终端
- Windows 用户：先进入 `Ubuntu (WSL)`，不要直接在 PowerShell 或 CMD 里继续

如果你是 Windows 用户，先执行：

```bash
wsl -d Ubuntu
```

进入 Ubuntu 后，再继续下一步。

### 第 2 步：复制并执行安装命令

把下面整行命令复制到终端，然后按回车：

```bash
curl -fsSL https://skill-pilot.ai/install.sh | bash
```

这条命令的意思可以简单理解为：

- `curl`：从互联网下载内容
- `https://skill-pilot.ai/install.sh`：安装脚本的网址
- `| bash`：把下载下来的安装脚本交给 Bash 执行

如果你是新手，只需要知道：  
这就是“启动安装器”的标准方式。

---

## 五、安装过程中会发生什么

安装器不是一下子全装完，而是会一屏一屏地解释，然后让你继续。

你会看到的内容会因为系统不同而略有区别。

### 1. Windows 用户会先看到什么

如果你直接在 Windows 环境里运行安装器，脚本会提示你：

- Windows 不适合直接运行这套 AI / 开发工具
- 应该先安装 WSL
- 应该选择 Ubuntu
- 然后在 Ubuntu 终端里重新运行安装命令

所以对 Windows 用户来说，正确流程是：

1. 先安装 WSL
2. 安装 Ubuntu
3. 打开 Ubuntu 终端，或执行：

```bash
wsl -d Ubuntu
```

4. 然后在 Ubuntu 里执行：

```bash
curl -fsSL https://skill-pilot.ai/install.sh | bash
```

### 2. macOS 用户会看到：Xcode Command Line Tools

这是 Apple 提供的命令行基础工具包。

它不是完整的 Xcode，而是一组开发工具，里面包括：

- `git`
- 编译器
- 一些基础命令行工具

如果你的 Mac 还没有安装，系统可能会弹出窗口提示安装。  
按照提示点继续即可。

如果安装器提示你：

- 先完成系统弹窗里的安装
- 然后回到终端按回车

那就照做。

### 3. Linux（Ubuntu）用户会看到：Linux Build Tools

如果你是 Linux（Ubuntu）用户，或者你是在 WSL Ubuntu 里安装，安装器通常会先解释并检查一组 Linux 基础构建工具。

你可能会看到类似这些内容：

- `gcc / g++`
- `make`
- `cmake`
- `pkg-config`

这些工具的作用可以简单理解为：

- 编译程序
- 安装依赖
- 构建某些需要本地编译的组件

如果系统里缺少这些工具，而你的系统使用 `apt-get` 或 `dnf`，安装器通常会尝试帮你安装。

### 4. Homebrew

Homebrew 是 Mac 上最常见的命令行软件管理器。

你可以把它理解成：

- 面向开发工具的“App Store”
- 但它不是图形界面，而是靠命令来安装

后面很多工具都靠 Homebrew 安装。

在 macOS 上它非常常见。  
在 Linux（Ubuntu）上，如果系统里还没有合适的包管理方式，脚本也可能使用它。

### 5. uv

`uv` 是 Python 环境管理工具。  
Skill Pilot 的核心引擎用 Python 编写，所以它很重要。

你可以简单理解为：

- 它负责管理 Python
- 它负责给项目准备独立环境
- 它比传统方式更快

### 6. Python 3

Python 是目前 AI 和自动化领域最重要的语言之一。  
Skill Pilot 的引擎和很多自动化能力都依赖它。

脚本要求版本至少为：

- Python 3.9 或以上

如果你机器上没有合适版本，安装器会帮你装。

### 7. pnpm

`pnpm` 是 Node.js 的包管理器。

Skill Pilot 的网页界面基于 Next.js，而 Next.js 属于 Node.js 生态，所以这里需要它。

### 8. Node.js

Node.js 是让 JavaScript 在电脑上运行的环境。

这里主要用于：

- Skill Pilot 的 Web 界面
- 某些 AI CLI 工具
- 前端开发相关能力

脚本要求版本至少为：

- Node.js 18 或以上

### 9. tmux

`tmux` 很关键。

它的作用是：

- 即使你关掉终端窗口，后台任务也能继续存在
- 方便你和 AI 共用一个终端会话
- Skill Pilot 启动服务时会依赖它

如果没有 `tmux`，`skillpilot.sh` 会直接报错并拒绝启动。

### 10. wget

`wget` 是命令行下载工具。  
很多自动化任务和技能会用它下载文件。

### 11. ffmpeg

`ffmpeg` 是音视频处理工具。  
Skill Pilot 的媒体处理能力依赖它。

---

## 六、安装位置怎么选

安装器会让你选择项目安装在哪个文件夹。

通常会给出类似这几个选项：

1. `~/workspace/skill-pilot`（推荐）
2. 当前目录下的 `skill-pilot`
3. 自定义路径

对于零基础用户，建议直接选：

```text
1
```

也就是：

```text
~/workspace/skill-pilot
```

这里的 `~/` 表示你的个人主目录。  
在不同系统里通常类似：

```text
macOS:   /Users/你的用户名/
Linux（Ubuntu）:   /home/你的用户名/
WSL:     /home/你的用户名/
```

这是最适合个人使用的位置。

---

## 七、安装器下载项目时在做什么

安装器后面会执行一个叫 `git clone` 的动作，把 Skill Pilot 项目下载到你的电脑。

这里你只需要知道：

- `git` 是代码版本管理工具
- `git clone` 是把一个项目完整下载到本地

这和下载 zip 包不同。  
用 `git clone` 下载后，后续更新会更方便。

---

## 八、安装完成后你要做什么

安装器结束时，会提示你做下一步。

通常是两件事：

### 1. 让终端重新加载环境

如果安装器刚刚修改了你的 shell 配置，它会提示你执行类似命令：

```bash
source ~/.zshrc
```

如果它提示的是别的文件，就照它显示的命令执行。

如果你不想执行 `source ...`，也可以：

- 直接关闭 Terminal
- 再重新打开一个新的 Terminal 窗口

这两种方式都可以让新安装的命令生效。

### 2. 进入 Skill Pilot 目录

如果你刚刚选择的是推荐目录，那么执行：

```bash
cd ~/workspace/skill-pilot
```

这里的 `cd` 是“进入某个文件夹”的意思。

你可以把它理解成：

- Finder 里双击进入文件夹
- 只不过这是命令行版本

---

## 九、第一次运行 Skill Pilot

进入项目目录后，执行：

```bash
./skillpilot.sh
```

请注意：

- 必须先 `cd` 到 Skill Pilot 项目目录
- 然后再执行 `./skillpilot.sh`

如果你只输入：

```bash
skillpilot.sh
```

在很多情况下是找不到的。  
因为它不是系统全局命令，而是当前项目里的脚本文件。

---

## 十、第一次运行时会看到什么

`./skillpilot.sh` 默认执行的是 `start`，也就是“启动 Skill Pilot”。

如果这是第一次运行，它会先进入首次配置向导，然后再启动服务。

你大概率会看到这些步骤。

### 1. 首次配置向导

如果 `config/.env` 还不存在，脚本会自动进入首次设置。

它会向你解释一些概念，然后让你选择。

### 2. 选择监听地址

通常会让你选：

1. `127.0.0.1`
2. `0.0.0.0`

如果你是单机使用、只想自己在这台 Mac 上打开，请选：

```text
1
```

也就是：

```text
127.0.0.1
```

这是最安全、最简单的选项。

含义可以这样理解：

- `127.0.0.1`：只有你这台电脑自己能访问
- `0.0.0.0`：同一局域网里的其他设备也可能访问

零基础用户建议优先选：

- `127.0.0.1`

### 3. 选择端口

它会让你确认几个端口，默认通常是：

- 生产模式引擎：`3001`
- 开发模式引擎：`3002`
- 开发模式 WebUI：`3003`

如果你没有特殊需求，直接按回车接受默认值即可。

### 4. 检查 AI CLI 工具

脚本会检查你的电脑里有没有这些 AI 命令行工具：

- `claude`
- `copilot`
- `codex`
- `gemini`
- `opencode`

如果没装，它可能会建议帮你自动安装一部分工具。

对于新手，你可以按提示继续。  
这一步的目的，是让 Skill Pilot 后续能调用不同的 AI 代理。

### 5. 选择默认 AI 代理

如果检测到多个可用工具，脚本会让你选默认使用哪个。

你只需要输入对应编号即可。

这项设置后面还能改，不用太紧张。

### 6. 自动生成本地配置

脚本会自动写入一些配置文件，例如：

- `config/.env`
- `config/settings.json5`
- `config/ai_providers.json5`

你不需要手工创建这些文件。

---

## 十一、启动成功后会发生什么

首次配置完成后，`skillpilot.sh` 会正式启动 Skill Pilot。

它会：

- 使用 `tmux` 在后台启动服务
- 检查服务是否已经可访问
- 在有图形界面的系统里，尽量自动帮你打开浏览器

默认生产模式下，Skill Pilot 会使用一个后台 tmux 会话：

- `sp-engine-prod`

如果启动正常，终端通常会显示可访问地址，常见是：

```text
http://127.0.0.1:3001/
```

如果配置里生成了认证 token，浏览器打开的地址可能会自动带上参数，这属于正常情况。

---

## 十二、以后怎么再次启动和停止

### 再次启动

下次使用时，通常只要：

```bash
cd ~/workspace/skill-pilot
./skillpilot.sh
```

### 停止运行

如果你想停止 Skill Pilot，可以执行：

```bash
./skillpilot.sh stop
```

---

## 十三、给零基础用户的 Shell 入门知识

下面这些知识不难，但会让你少踩很多坑。

### 1. 当前目录很重要

终端里的很多命令都和“你现在在哪个文件夹”有关。

例如：

```bash
./skillpilot.sh
```

它的意思是：

- 运行“当前文件夹里”的 `skillpilot.sh`

如果你不在项目目录里，这条命令就可能失败。

### 2. `cd` 是切换文件夹

例如：

```bash
cd ~/workspace/skill-pilot
```

意思是进入 Skill Pilot 项目目录。

### 3. `pwd` 是查看你现在在哪

例如：

```bash
pwd
```

它会显示你当前所在的完整路径。

如果你不确定自己是不是已经进入项目目录，可以先运行：

```bash
pwd
```

### 4. `ls` 是查看当前目录里有什么

例如：

```bash
ls
```

如果你已经进入正确目录，通常能看到：

- `skillpilot.sh`
- `install.sh`
- `core`
- `config`

### 5. `./文件名` 表示运行当前目录里的文件

例如：

```bash
./skillpilot.sh
```

这和双击文件不一样。  
它是告诉 Shell：请执行当前目录里的这个脚本。

### 6. 遇到卡住，不一定是坏了

安装工具时，可能会出现下面几种情况：

- 终端好像停了一会儿
- 一段时间没有新输出
- 系统弹出窗口让你确认

这不一定是出错。  
尤其是安装 Homebrew、Xcode 命令行工具、Node.js 时，等待几分钟是正常的。

### 7. `Control + C` 是“停止当前命令”

如果你确认某个命令真的卡死了，或者你想取消操作，可以按：

```text
Control + C
```

这会中断当前命令。

---

## 十四、不同系统里你会接触到的软件，分别是干什么的

### Terminal

终端程序，负责让你输入命令。

在不同系统里常见的终端是：

- macOS 的 `Terminal`
- Linux（Ubuntu）的系统终端
- Windows 上通过 `Windows Terminal + Ubuntu (WSL)`

### zsh

macOS 默认常见 Shell。  
它负责解释你输入的命令。

### Bash

另一种常见 Shell。  
这次安装命令里是把脚本交给 `bash` 执行。

### WSL

WSL 是 Windows 提供的 Linux 兼容环境。  
如果你是 Windows 用户，应该在 WSL 的 Ubuntu 里安装和运行 Skill Pilot，而不是直接在 PowerShell 或 CMD 里运行。

### Ubuntu

Ubuntu 是最常见、最适合新手的 Linux 发行版之一。  
`install.sh` 对 Windows 用户的引导流程，也是让你先安装 WSL，再选择 Ubuntu。

### Xcode Command Line Tools

这是 macOS 的命令行基础工具包。  
如果你是 Mac 用户，安装器通常会先检查它。

### Linux Build Tools

这是 Linux（Ubuntu）或 WSL Ubuntu 中的一组基础构建工具，例如 `gcc`、`g++`、`make`、`cmake`、`pkg-config`。

如果你是 Linux（Ubuntu）/ WSL 用户，安装器通常会先检查这一组工具。

### Homebrew

Mac 命令行软件管理器，用来安装很多开发工具。

### Git

代码版本管理工具。  
Skill Pilot 安装项目时会用它克隆代码仓库。

### Python

AI、自动化、脚本开发的核心语言之一。  
Skill Pilot 引擎依赖它。

### uv

现代 Python 项目与环境管理工具。  
Skill Pilot 用它准备 Python 环境和依赖。

### Node.js

运行 JavaScript/TypeScript 的环境。  
Skill Pilot 的 Web 界面依赖它。

### pnpm

Node.js 生态的包管理器。  
用来安装网页界面相关依赖和部分 AI CLI。

### tmux

终端复用工具。  
Skill Pilot 用它把服务放到后台持续运行。

### wget

命令行下载工具。

### ffmpeg

音视频处理工具。

---

## 十五、最常见的几个问题

### 1. 我把命令粘贴到浏览器里了，为什么不行

因为这些命令只能在 Terminal 里执行，不能在 Safari 或 Chrome 的地址栏里执行。

### 2. 终端提示 `command not found`

通常有几种可能：

- 你还没重开终端
- 你还没执行安装器提示的 `source ~/.zshrc`
- 你不在正确目录
- 你把 `./skillpilot.sh` 写成了 `skillpilot.sh`

优先尝试：

1. 关闭 Terminal 再重新打开
2. 执行 `cd ~/workspace/skill-pilot`
3. 再执行 `./skillpilot.sh`

### 3. 提示找不到 `tmux`

这说明安装阶段没有把 `tmux` 安装成功。

最简单的处理方法是重新运行安装器：

```bash
curl -fsSL https://skill-pilot.ai/install.sh | bash
```

### 4. 浏览器没有自动打开

这不一定是错误。

你可以手动看终端输出里显示的地址，例如：

```text
http://127.0.0.1:3001/
```

然后复制到浏览器打开。

### 5. 我已经安装过一次，还需要再跑安装器吗

通常不需要。  
你只要进入项目目录执行：

```bash
./skillpilot.sh
```

就可以再次启动。

---

### 6. 我是 Windows 用户，应该在哪个环境里运行

请在：

- `Ubuntu (WSL)`

里运行，而不是在：

- `PowerShell`
- `命令提示符 CMD`

如果你还没进入 Ubuntu，可以先执行：

```bash
wsl -d Ubuntu
```

然后再运行安装命令。

## 十六、给新手的推荐操作路线

如果你只想最快完成安装，请照着下面做：

1. 打开正确的终端环境
2. 运行：

```bash
curl -fsSL https://skill-pilot.ai/install.sh | bash
```

3. 安装位置选：

```text
1
```

4. 如果安装器提示执行 `source ~/.zshrc`，就执行它
5. 进入项目目录：

```bash
cd ~/workspace/skill-pilot
```

6. 启动：

```bash
./skillpilot.sh
```

7. 首次向导里：

- 监听地址优先选 `127.0.0.1`
- 端口默认直接回车
- AI CLI 按提示继续
- 默认 AI 代理按编号选择

补充：

- Windows 用户先执行 `wsl -d Ubuntu`
- macOS 用户先打开 `Terminal`
- Linux（Ubuntu）用户先打开系统终端

---

## 十七、你至少要记住的 5 条命令

```bash
curl -fsSL https://skill-pilot.ai/install.sh | bash
cd ~/workspace/skill-pilot
./skillpilot.sh
./skillpilot.sh stop
pwd
```

它们分别表示：

- 下载并运行安装器
- 进入项目目录
- 启动 Skill Pilot
- 停止 Skill Pilot
- 查看当前所在目录

---

## 十八、结语

如果你之前完全没接触过命令行，不要被终端窗口吓到。  
这次你真正需要记住的，核心只有两步：

```bash
curl -fsSL https://skill-pilot.ai/install.sh | bash
```

然后：

```bash
cd ~/workspace/skill-pilot
./skillpilot.sh
```

只要你是在 Terminal 里按顺序执行，这就是正确路径。
