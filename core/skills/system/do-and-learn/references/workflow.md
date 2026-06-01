# Do and Learn Workflow

Use this reference when the `do-and-learn` skill is active.

## Step 1: Choose the Working Language

Use the user's language for the interview, explanations, learning files, final report, and optional tutorial.

Apply this priority:

1. If the user explicitly asks for a language, use that language.
2. If the user writes the task mostly in one language, use that language.
3. If the user mixes languages, use the language used for the actual task request unless they specify otherwise.
4. If no language preference is clear, use English.

If the detected language is uncertain and the task depends on nuance, ask one short confirmation question. Otherwise proceed with the best inference. Keep code identifiers, commands, filenames, APIs, and quoted source text in their original language unless translating surrounding explanation improves understanding.

Record the working language in `learning/README.md`.

## Step 2: Establish Shared Understanding

Interview the user before execution. Keep questions direct and grouped. Do not ask every possible question at once; continue until the answers are sufficient to proceed responsibly.

Cover these areas:

- Outcome: what should exist, change, or be decided when the task is complete
- Audience: who will use the result and what they need from it
- Context: why the task matters, current state, constraints, and deadlines
- Inputs: files, systems, examples, credentials, data, or existing decisions
- Quality bar: acceptance criteria, verification method, and failure modes
- Knowledge baseline: what the user already understands and where they feel uncertain
- Learning goal: what the user wants to understand after the task is done

Use teach-back when risk is high: summarize the plan and ask the user to confirm or correct it. Challenge vague or risky requirements with a better option and clear reasoning.

## Step 3: Run a Short Core Concept Check

Before execution, identify the core technologies, tools, services, formats, and domain concepts the agent will likely use for this task. Ask the user briefly whether they know or understand each concept well enough to follow what the AI will do.

This is not a test and the user does not need to pass it. Do not block execution because the user is unfamiliar with a concept. The purpose is to give the user enough pre-knowledge to understand the AI's actions in the "do first, learn afterwards" workflow, and to make later resume writing, course creation, and interview practice more useful.

Keep the check short:

- Ask about only the concepts that matter for understanding the task outcome and AI/tool choices.
- Group related concepts into one question when possible.
- Accept answers such as "I know it", "I don't know", "not sure", or "need intro".
- If the user knows the concept, move on without lecturing.
- If the user does not know or asks for an intro, give a brief explanation before execution.

Explain concept-level knowledge, not operational details. The user should understand what the technology or tool is for, why the AI will use it, and what kind of result or tradeoff it affects. Do not teach exact commands, UI steps, flags, parameters, or implementation procedure unless the user explicitly asks.

Examples:

- For an AWS CloudFront task, make sure the user roughly understands CloudFront and CDN: CloudFront is AWS's content delivery network, used to serve files through edge locations with lower latency and stable public URLs. The user does not need to know the exact AWS CLI commands or console steps before the agent configures it.
- For a video editing task using FFmpeg, make sure the user understands FFmpeg as a command-line media tool that can cut, convert, combine, compress, and inspect audio/video. The user does not need to know the exact filter graph or encoding parameters before the agent runs it.
- For a local database task using SQLite, make sure the user understands SQLite as a file-based database useful for small apps and local metadata. The user does not need to know SQL schema details before the agent builds it.

When giving an intro, keep it practical:

1. What it is
2. Why this task needs it
3. What the AI will probably use it for
4. What the user should watch for or verify at a high level

After the brief intro, continue with the task. Save the concept list and any intro notes in `learning/concepts.md` once the learning folder exists.

## Step 4: Calibrate the Learning Level

Infer the user's level from their answers:

- Beginner: unfamiliar with core terms, needs analogy, vocabulary, and step-by-step explanation
- Practical novice: understands the goal but not the implementation path or tradeoffs
- Working practitioner: can follow implementation details and wants decision reasoning
- Advanced: wants edge cases, architecture, performance, operations, and tradeoffs

State the assumed level briefly. Adjust if the user corrects it.

## Step 5: Create the Learning Folder

### Detect the task or project root directory

Before creating the learning folder, determine the root directory that owns this task. Apply these rules in order:

1. **Anchor file rule**: If the user references a file such as `requirements.md`, `update.md`, `issues.md`, `plan.md`, or `implementation.md`, treat its containing directory as the root.
   - Example: `workspace/tasks/aws-setup-task/requirements.md` → root is `workspace/tasks/aws-setup-task/`.
   - Example: `workspace/vibe-coding/my-app/plan.md` → root is `workspace/vibe-coding/my-app/`.
2. **Known location patterns**: When no anchor file is given, infer from the task type using these conventional roots:
   - Tasks: `workspace/tasks/{task-name}/`
   - Vibe coding projects: `workspace/vibe-coding/{project-name}/`
   - Learning-only items without a project: `workspace/learning/{topic-name}/`
3. **Highest-owning directory**: If the task spans multiple files or folders, pick the highest-level directory that exclusively owns the task. Do not go up into a shared parent like `workspace/tasks/`.
4. **Confirm with the user** when ambiguous (e.g., two candidate roots, or the referenced file is at a shared parent level) before creating files.
5. **No directory yet**: If the project directory does not exist, create it first using the appropriate pattern above, then create `learning/` inside it.

State the detected root directory before creating files, e.g. *"Detected task root: `workspace/tasks/aws-setup-task/`. I will create `workspace/tasks/aws-setup-task/learning/`."*

### Create the folder

Inside the detected root, create:

```text
{task-root}/learning/
└── README.md
```

Use the task/project root, never a global or shared location.

The README should include:

- Task title and plain text goal
- Working language
- User learning level and learning goals
- Requirement summary and acceptance criteria
- Links to knowledge notes
- Links to verification notes or outputs when useful
- Link to the optional tutorial if created later

Keep the README useful as an index. Move detailed explanations into separate files when a section grows beyond a short summary.

## Step 6: Capture Knowledge Notes

Create additional files under `learning/` only when they add useful structure. Recommended names:

- `requirements.md`
- `concepts.md`
- `implementation-notes.md`
- `verification.md`
- `tradeoffs.md`
- `tutorial.md` or a course-creator-specific filename

Each knowledge file should tie explanations to the actual task. Prefer:

- the core concepts checked before execution
- why this decision was made
- what alternative was rejected and why
- what concept the user needs to understand
- how to verify the behavior
- what mistakes to avoid next time

Avoid generic textbook content unless it directly supports the user's task.

## Step 7: Execute the Task

Perform the task using the appropriate project skills and tools. Keep the user informed at decision points. If a major decision is needed, explain the tradeoff and ask for approval.

During implementation, update learning files when:

- requirements change
- a key technical concept appears
- an important decision or tradeoff is made
- verification reveals something the user should understand

## Step 8: Verify and Report

Verify the task using the project's normal quality bar. Update `learning/README.md` and any relevant notes with what was verified.

In the final report, include:

- what was completed
- what was verified
- where the learning folder is
- any assumptions or remaining risks

## Step 9: Offer Completion Options

After the task is finished, ask:

```text
You finished this task. What would you like to do next?

1. Get the key points for how to add this skill or task experience to your resume.
2. Take an online interactive course for the skills you learned by doing this task before a mock interview.
3. If you have learned the materials and mastered the skills, start a hiring-manager-style interview for this task.
```

If the user chooses option 1:

1. Use the `resume-interview` skill.
2. Turn the completed task, implementation choices, tradeoffs, and verification results into resume-ready points.
3. Keep claims credible. Do not invent metrics, scale, production usage, or business impact.
4. Include short interview-defense notes when useful so the user can explain the resume claims.

If the user chooses option 2:

1. Use the `course-creator` skill.
2. Create the interactive course in the task's `learning/` folder.
3. Base the tutorial on the completed task, the user's level, and the knowledge notes.
4. Update `learning/README.md` to link to the course file.
5. Verify the course file exists and is linked.
6. After the course is complete, offer option 3 again if the user wants to practice the interview.

If the user chooses option 3:

1. Use the `resume-interview` skill.
2. Act as the hiring manager interviewing the user as the candidate.
3. Ask one question at a time, listen to the user's answer, and probe with realistic follow-ups.
4. Ground questions in the completed task, the learning notes, implementation decisions, verification, and tradeoffs.
5. Delay detailed scoring until the interview segment ends unless the user asks for immediate feedback.

If the user declines all options, leave the learning folder as the durable learning artifact.
