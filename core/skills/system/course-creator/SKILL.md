---
name: course-creator
description: Create interactive courses and assignments for students in the project's markdown format. Use when asked to create a new course, educational module, or assignment.
---

# AI Builder - Course Creator

This skill enables the creation of structured, interactive, and engaging courses and assignments. It focuses on clear learning goals, audience targeting, and the use of the project's specialized markdown block system.

## When to Use This Skill

- User wants to create a new educational course or module.
- User wants to design an assignment or quiz.
- User provides a topic and asks for a structured learning path.
- User needs to update an existing course with new interactive elements.

## Your Roles in This Skill

- **Product Manager**: Define the course goal, identify the target audience, and determine the appropriate duration.
- **Technical Writer**: Draft the educational content, ensuring clarity, accuracy, and tone appropriate for the audience.
- **Project Manager**: Structure the course into a logical sequence of steps and sections.
- **Backend Developer**: Implement interactive elements using specialized markdown blocks (code editors, forms, shell validation).

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role} [and {Role}, ...], I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order to create a high-quality interactive course:

### Step 1: Define the Foundation

As a **Product Manager**, define the core parameters:
1.  **Goal**: What should the student be able to DO after completing this course?
2.  **Audience**: Who is this for? (e.g., High school student, beginner developer, professional).
3.  **Duration**: How long should it take? (Minimum 20-30 minutes recommended).

### Step 2: Research and Content Mapping

As a **Technical Writer**, research the topic:
1.  Search the internet for up-to-date information, common pitfalls, and best practices.
2.  Map out the key concepts to be covered.
3.  Identify opportunities for hands-on practice (interactive code) and validation.

### Step 3: Design the Structure

As a **Project Manager**, organize the course into sections:
1.  **Introduction**: Goals and objectives.
2.  **Theory/Explanation**: Core concepts with examples.
3.  **Interactive Practice**: Guided coding or terminal tasks.
4.  **Assessment**: Quizzes or final projects.
5.  **Conclusion**: Summary and next steps.

### Step 4: Implement with Markdown Blocks

As a **Backend Developer**, author the course file at `workspace/learning/{slug}.md`. You MUST use the specialized markdown blocks.

**References:**
- Refer to `core/webui/docs/markdown-block-docs.md` for the full block specification.
- Refer to `core/webui/docs/assignment-sample.md` for a complete example.

**Key Requirements:**
- Every course MUST start with a `yaml {"type":"meta"}` block.
- Use `markdown {"during":1000}` for reading sections.
- Use `markdown {"type":"control","action":"continue"}` to gate progress.
- Use `python {"type":"code","action":"run"}` (or other languages) for interactive coding.
- Use `yaml {"type":"form"}` for quizzes.
- Use `tabs` for comparing multiple solutions or languages.

### Step 5: Final Review and Validation

As a **Technical Writer**, review the course for:
- Tone consistency.
- Correct use of escaped inner code fences (````).
- Accuracy of technical examples.

## Key Principles

- **Interactivity First**: Don't just provide text. Use code blocks, terminal tasks, and forms to keep students engaged.
- **Escaping**: Always remember to escape inner triple-backticks as ````.
- **Conciseness**: Keep individual steps short. Use the `during` property to control flow.
- **Student-Centric**: Use language and examples that match the defined audience level.
