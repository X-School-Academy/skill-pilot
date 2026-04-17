# Skill Pilot Doctor Message Guide

This is a user-facing guide for beginners.

Traditional software often ships with a static FAQ for troubleshooting.

Skill Pilot is different:

- you can ask AI for the answer
- you can also ask AI to do the troubleshooting work for you

The goal of `./skillpilot.sh doctor` is not only to explain the problem, but also to help resolve it.

## Basic idea

Open doctor mode from the Skill Pilot project folder:

```bash
./skillpilot.sh doctor
```

Or write your problem directly:

```bash
./skillpilot.sh doctor "skillpilot.sh start does not open the WebUI"
```

## How to enter a multi-line message

First run:

```bash
./skillpilot.sh doctor
```

Then, when you see `Question:`, start your message with `"""` and end it with `"""`.

Example:

```text
Question: """
I ran ./skillpilot.sh start.
I expected the WebUI to open.
Instead I saw an error about a port already being in use.
Please help me fix it.
"""
```

Use this when you want to paste:

- a longer explanation
- multiple symptoms
- several command results
- a short bug report with expected and actual behavior

## How to draft a good doctor message

A good message usually includes 3 things:

1. What you tried
2. What happened
3. What you want

Simple pattern:

```text
I ran <command>.
I expected <expected result>.
Instead I saw <error or problem>.
Please help me fix it.
```

## Best beginner examples

### Install problems

```text
I ran bash install.sh.
It stopped in the middle and I do not know what to do next.
Please help me finish the installation.
```

```text
I ran bash install.sh on my Mac.
It says tmux is missing.
Please help me install what is needed.
```

```text
I ran bash install.sh.
It says pnpm or uv is not found.
Please explain what that means and help me fix it.
```

### Start problems

```text
I ran ./skillpilot.sh start.
I expected the WebUI to open.
Nothing opened.
Please help me find the problem.
```

```text
I ran ./skillpilot.sh start.
It says a port is already in use.
Please help me understand that and fix it.
```

```text
I ran ./skillpilot.sh start --dev.
I do not understand the difference between dev and normal mode.
Please explain and help me choose the right one.
```

### Doctor and provider problems

```text
I ran ./skillpilot.sh doctor.
It says opencode is not installed.
Please help me install it and continue.
```

```text
I want to use doctor, but I do not know which AI provider I should choose.
Please explain the options in simple words.
```

### Command line confusion

```text
I do not understand terminal, shell, or command line.
Please explain only what I need in simple words so I can use Skill Pilot.
```

```text
I do not know which folder I should run the command from.
Please help me check my current folder and tell me the next command.
```

### Git and GitHub confusion

```text
I do not know Git or GitHub.
Please explain only the minimum I need to use Skill Pilot.
```

```text
A command showed a git error.
Please explain what it means and what I should do next.
```

### Bug report style

```text
I think Skill Pilot has a bug.
I clicked or ran <what you did>.
I expected <expected behavior>.
But I got <actual behavior>.
Please investigate it.
```

## If you do not know the exact error

That is okay.

You can still ask like this:

```text
I tried to start Skill Pilot, but something failed.
I do not understand the error.
Please ask me for the exact commands or output you need.
```

## If you want doctor to do more than explain

You can ask doctor to act, not only answer.

Examples:

```text
Please help me diagnose this install problem step by step.
```

```text
Please tell me the exact commands to run, one at a time.
```

```text
Please inspect the project files and find the likely cause.
```

```text
Please help me stop Skill Pilot safely and restart it.
```

```text
Please help me understand the error first, then help me fix it.
```

## What makes a bad doctor message

These are harder to solve:

```text
not working
```

```text
error help
```

```text
start broken
```

These are better:

```text
I ran ./skillpilot.sh start and it did not open the browser.
Please help me diagnose it.
```

```text
I ran bash install.sh and it stopped after a dependency step.
Please help me continue.
```

## Short template you can copy

```text
I ran:

I expected:

I got:

My system is:

Please help me:
```

## Final advice

You do not need to know the perfect technical words.

Just describe:

- what you typed
- what you saw
- what you wanted to happen

Then `./skillpilot.sh doctor` can help explain it, troubleshoot it, and often do part of the work with you.
