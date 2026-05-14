# Guide: Creating `requirements.md` by Reverse Engineering Existing Code

## Purpose

Use this guide when the code already exists and the user needs a clean `requirements.md`.

The goal is to recover the customer, Product Manager, or Tech Lead requirements from the implemented behavior without turning `requirements.md` into an implementation summary.

The authoring role for this file is **Product Manager or Tech Lead**. Write from the viewpoint of someone defining the product contract, developer-facing integration contract, and acceptance criteria.

## Output

Create or update the `requirements.md` file requested by the user.

The file should describe what the feature must do, how it is configured, and what acceptance criteria define success.

It should not describe how the code is organized internally.

## Reverse Engineering Workflow

1. Identify the feature boundary.

   Find the user-visible feature, command, route, UI area, skill, workflow, or configuration entry that represents the feature. Record the boundary in plain product terms.

2. Inspect the existing behavior.

   Read only the files needed to understand the behavior. Focus on:

   - User-facing inputs and outputs
   - Configuration keys and expected values
   - CLI arguments or API contract details
   - Permissions, safety constraints, and failure behavior
   - Integration points with other user-visible systems
   - Existing tests that reveal expected behavior

3. Translate implementation into Product Manager / Tech Lead requirements.

   Convert code facts into Product Manager or Tech Lead requirements:

   - Implementation fact: "The code reads setting X from config file Y."
   - Requirement: "The feature must support setting X in config file Y."

   - Implementation fact: "Function A calls function B."
   - Requirement: Omit the function call if both functions are internal implementation details.

   - Implementation fact: "The feature depends on an existing public command, config key, API route, skill, workflow, or service contract."
   - Requirement: "The feature must integrate with that existing command, config key, API route, skill, workflow, or service contract."

   - Implementation fact: "The CLI accepts flag Z."
   - Requirement: "The CLI must support flag Z."

   - Implementation fact: "The UI includes a form wizard."
   - Requirement: Describe the user workflow and expected outcome, not the component implementation.

4. Separate requirements from implementation details.

   Keep `requirements.md` focused on what must be true.

   Move these details to `implementation.md` instead:

   - Internal file layout
   - Function names
   - Class names
   - Helper modules
   - Control flow between functions
   - Test file names
   - Framework-specific internals
   - Refactoring notes

5. Keep necessary Product Manager / Tech Lead details.

   Some details are valid requirements because developers need them to build or integrate the feature correctly.

   Keep details such as:

   - Required configuration file names, for example `config/ai_providers.json5`
   - Required configuration keys and values, for example `default.background_llm: "skill-pilot"`
   - Required command names or wrapper paths, when they are part of the product contract
   - Required environment variables
   - Required CLI flags
   - Required compatibility behavior with existing systems
   - Required safety or fallback behavior

6. Write acceptance criteria.

   Acceptance criteria should be testable from the outside. They should describe observable behavior, not specific code structure.

## Recommended `requirements.md` Structure

Use this structure unless the feature needs something different:

```markdown
# <Feature Name> Requirements

## Goal

<Short description of the user or platform outcome.>

## Users / Consumers

<Who uses this feature: end user, developer, background service, workflow, skill, UI page, etc.>

## Functional Requirements

- <What the feature must do.>
- <What inputs it accepts.>
- <What outputs or side effects it produces.>

## Configuration

- <Required config file, key, value, or environment variable.>
- <Default behavior when config is missing.>

## Interfaces

- <Required CLI command, route, skill name, workflow name, or UI entry point.>
- <Required arguments or request fields.>

## Safety and Constraints

- <Permissions, network, filesystem, privacy, fallback, or failure behavior.>

## Compatibility

- <Existing behaviors that must not change.>
- <Systems that must continue working.>

## Acceptance Criteria

- <Externally verifiable success condition.>
- <Externally verifiable failure or fallback condition.>
```

## What Belongs in `requirements.md`

Good requirements:

- "The feature must support selecting the background LLM provider through `default.background_llm` in `config/ai_providers.json5`."
- "The CLI must accept `--model <model>` to override the configured default model."
- "If required endpoint configuration is missing, the feature must fail with a clear error."
- "Terminal sessions must continue using the normal provider selection."

## What Does Not Belong in `requirements.md`

Move these to `implementation.md`:

- "The implementation lives in `module_x.py`."
- "Function `load_provider_config()` reads the config."
- "Class `ProviderConfig` stores the settings."
- "The route calls helper A, which calls helper B."
- "The test file `test_feature.py` verifies the behavior."

## Review Checklist

Before finishing `requirements.md`, check:

- Does the document read like a Product Manager or Tech Lead request rather than a code walkthrough?
- Are all user-visible behaviors captured?
- Are required config keys, environment variables, commands, and compatibility constraints included?
- Are internal functions, classes, helper files, and module-level control flow excluded?
- Are acceptance criteria observable from the outside?
- Could a developer implement the feature from the requirements without needing to know the current code structure?
- Could a reviewer compare the existing code against the requirements and identify gaps?

## Practical Rule

If a detail is part of the contract between the feature and its users, operators, configuration, CLI, API, or neighboring systems, keep it in `requirements.md`.

If a detail only explains how the current code achieves the contract, move it to `implementation.md`.
