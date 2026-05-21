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

## Step 3: Calibrate the Learning Level

Infer the user's level from their answers:

- Beginner: unfamiliar with core terms, needs analogy, vocabulary, and step-by-step explanation
- Practical novice: understands the goal but not the implementation path or tradeoffs
- Working practitioner: can follow implementation details and wants decision reasoning
- Advanced: wants edge cases, architecture, performance, operations, and tradeoffs

State the assumed level briefly. Adjust if the user corrects it.

## Step 4: Create the Learning Folder

Once the project or task directory is known, create:

```text
learning/
└── README.md
```

Use the task/project directory, not a global location. If the task spans multiple directories, choose the highest-level directory that owns the task. If no directory exists yet, create `learning/` after the project directory is created.

The README should include:

- Task title and plain text goal
- Working language
- User learning level and learning goals
- Requirement summary and acceptance criteria
- Links to knowledge notes
- Links to verification notes or outputs when useful
- Link to the optional tutorial if created later

Keep the README useful as an index. Move detailed explanations into separate files when a section grows beyond a short summary.

## Step 5: Capture Knowledge Notes

Create additional files under `learning/` only when they add useful structure. Recommended names:

- `requirements.md`
- `concepts.md`
- `implementation-notes.md`
- `verification.md`
- `tradeoffs.md`
- `tutorial.md` or a course-creator-specific filename

Each knowledge file should tie explanations to the actual task. Prefer:

- why this decision was made
- what alternative was rejected and why
- what concept the user needs to understand
- how to verify the behavior
- what mistakes to avoid next time

Avoid generic textbook content unless it directly supports the user's task.

## Step 6: Execute the Task

Perform the task using the appropriate project skills and tools. Keep the user informed at decision points. If a major decision is needed, explain the tradeoff and ask for approval.

During implementation, update learning files when:

- requirements change
- a key technical concept appears
- an important decision or tradeoff is made
- verification reveals something the user should understand

## Step 7: Verify and Report

Verify the task using the project's normal quality bar. Update `learning/README.md` and any relevant notes with what was verified.

In the final report, include:

- what was completed
- what was verified
- where the learning folder is
- any assumptions or remaining risks

## Step 8: Offer an Interactive Tutorial

After the task is finished, ask:

`Do you want me to create an online interactive tutorial for this task so you can learn it more deeply?`

If the user says yes:

1. Use the `course-creator` skill.
2. Create the tutorial in the task's `learning/` folder.
3. Base the tutorial on the completed task, the user's level, and the knowledge notes.
4. Update `learning/README.md` to link to the tutorial file.
5. Verify the tutorial file exists and is linked.

If the user says no, leave the learning folder as the durable learning artifact.
