

```markdown {"during":1000}
#### Objectives in this session:

In this course, you will learn how to set up your own personal AI assistant using OpenClaw.

1. Understand what **OpenClaw** is and why it's a powerful tool for AI automation.
2. Compare **AWS** and **Azure** free cloud solutions specifically for students.
3. Learn the high-level steps to deploy OpenClaw on a cloud instance.
4. Gain the knowledge to choose the best cloud path for your personal projects.

OpenClaw is an open-source autonomous AI agent that can run 24/7 on your own server. Unlike many web-based AI tools, you own the data and control the "brain" of your agent!
```

```markdown {"type":"control","action":"continue","timeLeft":0}
```

```markdown {"during":1000}
### 1. What is OpenClaw?

OpenClaw (formerly known as Clawdbot) is a "conversation-first" AI agent. Think of it as a personal assistant that lives in your chat apps (like Discord, Telegram, or WhatsApp) and can perform tasks for you.

**Key Features:**
*   **Autonomous:** It can execute multi-step tasks without you needing to guide every single click.
*   **Open Source:** The code is free to use, modify, and host yourself.
*   **Always On:** By running it on a cloud server, your assistant is available 24/7.
*   **Data Privacy:** Since it runs on *your* server with *your* API keys, your conversations aren't being used to train other people's models.

**How it works:**
OpenClaw uses Large Language Models (LLMs) like Claude (Anthropic), GPT-4 (OpenAI), or Gemini (Google) as its engine. It connects these "brains" to your chat apps and gives them tools to browse the web or run code.
```

```markdown {"type":"control","action":"continue","timeLeft":0}
```

```markdown {"during":1000}
#### Quick Knowledge Check: What makes OpenClaw different?

```

```yaml {"type":"form","refInfo":"ask"}
- name: openclaw_diff
  label: Why would a student choose to host OpenClaw themselves instead of just using a standard AI website?
  options:
    - Because it is the only way to use GPT-4.
    - To have 24/7 availability and full control over their data and API keys.
    - Because it is mandatory for high school students.
    - Because it doesn't require an internet connection.
  hint: The correct answer is B. Self-hosting gives you autonomy and privacy!
  type: radio
  value: 1
```

```markdown {"type":"control","action":"continue","timeLeft":0}
```

```markdown {"during":1000}
### 2. Choosing Your Cloud Platform

To keep OpenClaw running 24/7, you need a "Virtual Private Server" (VPS) in the cloud. As a student, you have two great free options.

#### Option A: Azure for Students (Microsoft)
*   **Credit:** $100 per year.
*   **Requirement:** A student email address (usually ends in `.edu`).
*   **Best Part:** **No credit card required!** This makes it the easiest option for most high schoolers.
*   **Renewal:** You can renew this every year as long as you are a student.

#### Option B: AWS Free Plan (Amazon)
*   **Credit:** Up to $200 in credits for the first 6 months.
*   **Requirement:** Usually requires a credit or debit card for identity verification.
*   **Best Part:** Gives you a larger initial credit to try bigger "instance sizes" (more powerful virtual computers).
*   **Note:** After 6 months, the credits expire, so you have to be careful with costs!
```

```markdown {"during":1000}
#### Comparison Table

| Feature | Azure for Students | AWS Free Plan |
| :--- | :--- | :--- |
| **Credit Amount** | $100 (Annual) | ~$200 (6 Months) |
| **Credit Card?** | No | Yes |
| **Sustainability** | Renewable yearly | One-time offer |
| **Target User** | Long-term learning | Intensive testing |
```

```markdown {"type":"control","action":"continue","timeLeft":0}
```

```markdown {"during":1000}
### 3. Deploying OpenClaw (High-Level Guide)

Whether you choose AWS or Azure, the general process of setting up OpenClaw is very similar.

#### Step 1: Create a Virtual Machine (Instance)
*   **On AWS:** You would create an **EC2 Instance** or a **Lightsail** server.
*   **On Azure:** You would create a **Virtual Machine** (Ubuntu Linux is recommended).
*   **Resource Tip:** OpenClaw runs best with at least **4GB of RAM**. Look for "Small" or "Medium" instance types.

#### Step 2: Prepare the Server
Once your server is running, you connect to it using **SSH** (Secure Shell). You'll need to install:
1. **Node.js** (Version 22 or higher).
2. **Git** (To download the OpenClaw code).

#### Step 3: Configure Your "Brain" (API Keys)
OpenClaw needs an API key to think. You can get these from:
*   **OpenRouter:** A great service for students that lets you access many models (like DeepSeek or Claude) with one account.
*   **Anthropic or OpenAI:** If you want to use their specific models directly.

#### Step 4: Run and Connect
After running the start command (`npm start`), OpenClaw will give you a Web UI link. From there, you can link your **Discord** or **Telegram** bot token so you can start chatting!
```

```markdown {"type":"control","action":"continue","timeLeft":0}
```

```markdown {"during":1000}
#### Final Knowledge Check: The Cloud Setup

```

```yaml {"type":"form","refInfo":"ask"}
- name: cloud_choice
  label: Which cloud platform is generally better for a student who does NOT have a credit card?
  options:
    - AWS Free Plan
    - Google Cloud Platform
    - Azure for Students
    - DigitalOcean
  hint: Azure for Students only requires a student email, not a credit card!
  type: radio
  value: 2
```

```markdown {"during":1000}
#### Practical Challenge
Ask an AI (like the one in this chat!) to explain the difference between a "managed container" (like Azure Container Apps) and a "virtual machine" (like AWS EC2) for running a bot like OpenClaw.
```

```markdown {"type":"chat","action":"code","button":"Ask AI","promptFor":"WithCode"}
Explain the difference between running OpenClaw on a Virtual Machine (VM) versus a Managed Container service (like Azure Container Apps or AWS Fargate). Which one is easier for a beginner to maintain?
```

```markdown {"type":"control","action":"use_skill","skill_name":"course-creator","timeLeft":0}
```

```markdown {"type":"control","action":"end"}
### Congratulations!
You've completed the introduction to OpenClaw and Cloud hosting. You now know:
1. What an autonomous AI agent is.
2. How to get $100+ of free cloud credits as a student.
3. The basic steps to move your AI from a local computer to the global cloud.

**Next Step:** Head over to the Azure or AWS portal and start your free account!
```
