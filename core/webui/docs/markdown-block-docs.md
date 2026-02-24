# Assignment Markdown Blocks (CourseBlock)

This document describes the **supported fenced code blocks** for authoring an assignment/course markdown file rendered by `frontend/components/blocks/course.block.tsx`.

Key idea: **Only fenced code blocks are rendered**. Normal markdown paragraphs outside code fences are ignored.

## How Parsing Works

- The course markdown is parsed with `remark-parse`.
- Each top-level fenced block becomes an AST `code` node with:
  - `lang`: the info-string language (e.g. `markdown`, `yaml`, `tabs`, `python`).
  - `meta`: the rest of the info-string after the language.
- `meta` is parsed with `relaxed-json` (`RJSON.parse`), so relaxed JSON like `{during: 1000}` and single quotes are accepted.
  - Recommendation: prefer strict JSON (double quotes) for consistency.
- Step progression:
  - The first code block is index `0` (course meta).
  - Steps start at index `1`.
  - Some blocks auto-advance (call the step callback immediately); others gate progression (e.g. `control`, `form`).

## Escaping Inner Code Fences

Because most steps are themselves inside a fenced code block, any inner triple-backtick fences must be **escaped** as `\```...` in the source file.

Many blocks unescape before rendering with:
- `replaceAll('\\```', '```')`

So inside a `markdown` (or `tabs`, etc.) step, write inner fences like:

```text
\```bash
echo hello
\```
```

## File Skeleton (Minimal)

```yaml {"type":"meta"}
title: Example Assignment
slug: example-assignment
# free-form; used by other pages/services
id: 999
# often used by the platform
duration: 45 minutes
token: YOUR_TOKEN
```

```markdown {"during":300}
# Welcome
This is the first visible step.
```

```markdown {"type":"control","action":"continue","timeLeft":45}
```

```markdown {"type":"control","action":"submit"}
```

## Supported Blocks

### 1) Course Meta (Required First Block)

- Fence language: `yaml`
- Must be the **first** fenced block in the file.
- `course.block.tsx` loads this YAML and treats it as the course metadata.
- The `meta` JSON on this fence is not used by `course.block.tsx`, but existing content uses `{ "type": "meta" }`.

Example:

```yaml {"type":"meta"}
title: Version Control and Secure Communication with Git, GitHub, and SSH
slug: version-control-and-secure-communication-with-git,-github,-and-ssh
duration: 45 minutes
token: 66fe7280284245f2a8f98b56f04653fb
id: 143
```

### 2) Markdown Content (Default Renderer)

- Fence language: `markdown` (or omit language)
- When `meta.type` is not one of the special types below, the step renders via `MarkdownPlay.block.tsx`.

Meta (parsed by `MarkdownPlay.block.tsx`):
- `during` (number, ms): delay before step auto-advances.
- `type: "code"` (string): renders the entire content as a code block (rare).

Example:

```markdown {"during":1000}
## Section Title

Here is a code sample (escaped):

\```bash
git status
\```
```

### 3) Control Block (Continue/Submit/Nest End/Use Skill)

- Fence language: `markdown`
- `meta.type: "control"`
- Renders `ControlBlock`.

Meta (read by `course.block.tsx`, passed as props):
- `action` (string, required):
  - `"continue"`: shows a Continue button.
  - `"submit"`: shows a Submit button + feedback textarea.
  - `"use_skill"`: shows a "Use Agent Skill" button + request textarea. Redirects to `/` with a new session prompt.
  - `"nestEnd"`: immediately completes the step (used for nested flows).
- `skill_name` (string, required for `"use_skill"`): the name of the system skill to invoke.
- `timeLeft` (number, optional): shown next to the Continue button.
- `warning` (boolean, optional): if true, a failed `sendCommand()` can still allow continue.
- `ref` (string, optional): passed to `FormBlock` as `refInfo` and shown on error. Use `"ask"` to show an inline Chat prompt, or `"ai"` to show a generic AI-help hint.
  - If starts with `http`, rendered as a link.
  - Special values: `"ai"`.
- `cmd` (string, optional): if present, clicking Continue triggers a remote shell command.
- `dir` (string, optional, default `/tmp`): remote working directory for `cmd`.
- `regx` (string, optional): regex to validate shell output.
  - If the string starts with `/.../flags`, it is treated as a JS regex literal.
  - Note: if you set `cmd`, you should also set `regx` (otherwise `course.block.tsx` may throw at runtime).
- `error` (string, optional): error to display if regex/history check fails.
- `history` (string, optional): regex that must match the terminal history before running `cmd`.

Examples:

Continue-only (no command):

```markdown {"type":"control","action":"continue","timeLeft":30}
Read the content above, then continue.
```

Use Agent Skill:

```markdown {"type":"control","action":"use_skill","skill_name":"course-creator"}
```

### 4) Chat Block (Ask AI)

- Fence language: `markdown`
- `meta.type: "chat"`
- Renders `ChatBlock`.

Common meta fields (used by `chat.block.tsx`):
- `api` (string, default `"chat"`): REST endpoint suffix used by the UI.
  - Typically `"chat"`.
  - Some deployments use `"code"`.
- `button` (string, optional): button label (default comes from i18n, e.g. “Ask now”).
- `optional` (boolean, optional): if true, the step auto-advances immediately.
- `readOnly` (boolean, optional): makes the input editor read-only.
- `topic` (string, optional): preferred language/topic.
- `dropdown` (boolean, optional): set to `false` to hide topic dropdown.
- `general` (boolean, optional): set to `false` to avoid “any” defaulting.
- `extraInfo` (boolean, optional): set to `false` to hide the extra info textarea.
- `action` (string, optional): currently used for `"translate"`.

Notes:
- `promptFor` is emitted by `api-server/app/course.ts` but is currently not used by `chat.block.tsx` (safe to omit when writing markdown by hand).

Example:

```markdown {"type":"chat","api":"chat","button":"Ask AI"}
Generate a basic Git workflow script that initializes a repository, commits, and pushes to GitHub.
```

### 5) Bash Block (Clickable Terminal Commands)

- Fence language: `markdown`
- `meta.type: "bash"`
- Renders `BashBlock`.

Meta:
- `during` (number, ms, optional): delay before step auto-advances.

Content rules:
- Each non-empty line is a command.
- Lines starting with `#` are treated as comments and shown above the next command.

Current behavior note:
- `BashBlock` currently renders commands and copy-to-clipboard only. It does not directly send terminal events to VS Code.

Example:

```markdown {"type":"bash","during":300}
# Create a new repo
mkdir demo-repo
cd demo-repo

# Initialize git
git init
```

### 6) Code Check Block

- Fence language: `markdown`
- `meta.type: "vscode"`
- Renders `VSCodeBlock` (`frontend/components/blocks/vscode.block.tsx`).

Meta:
- `during` (number, ms, optional)
- `vscode` (boolean, optional): if true, mirrors content to VS Code right panel via `right_panel`.
- `shell` (string, optional): shell command list shown in right panel; quick-send icons emit `terminal_sent_text`.
- `clear` (boolean, optional): clears accumulated right-panel HTML before appending.

Example:

```markdown {"type":"vscode","vscode":true,"shell":"pwd\nls -la","clear":true}
Open the file:
- Verify your code in `README.md` and continue.
- [1:0-20:0](/workspace/project/README.md)
- [1:0-1:0](#new)
- [1:0-1:0](#focus)
- [1:0-1:0](#/workspace/project)
```

Link behavior:
- File link emits `open_file`.
- `#new`, `#focus`, `#close`, and `#/path` emit terminal events (`terminal_new`, `terminal_focus`, `terminal_close_all`, `terminal_new` with `directory`).

### 7) Container Block (Provision Dev Container)

- Fence language: `markdown`
- `meta.type: "container"`
- Renders `ContainerBlock`.

Meta:
- `containerType` (number, required):
- `action` (string, optional): generated as `"container"` by `api-server/app/course.ts`, currently ignored by the frontend.
  - `0` = CPU container
  - `> 0` = show GPU environment selector (options 1..3)
- `timeLeft` (number, optional)
- `warning` (boolean, optional)
- `ref` (string, optional)

Example:

```markdown {"type":"container","containerType":0,"timeLeft":45}
```

### 8) Audio Response Block

- Fence language: `markdown`
- `meta.type: "audioResponse"`
- Renders `AudioResponse.block.tsx`.

Meta:
- `fromLang` (string, required)
- `toLang` (string, required)
- `audioUrl` (string, required): the reference audio to play when passed.

Example:

```markdown {
  "type":"audioResponse",
  "fromLang":"en",
  "toLang":"en",
  "audioUrl":"/audio/sample.mp3"
}
Please describe what you learned today in 30 seconds.
```

### 9) Slides Block (Horizontal Carousel)

- Fence language: `slides`
- Or use `meta.type: "slides"` with any language.
- Each **top-level child block inside the slides fence** becomes one slide.
- No auto-play. Users navigate with left/right buttons or bottom dots.
- Each slide is rendered with `MarkdownRenderer`, so nested supported blocks are allowed.

Example:

```slides {"minHeight":260}
\```markdown
### Slide 1
Welcome to the session.
\```

\```markdown {"type":"chat","button":"Ask AI"}
Explain the difference between `git fetch` and `git pull`.
\```

\```yaml {"type":"list","tag":"ul"}
- Key point A
- Key point B
- Key point C
\```
```

### 10) Memory Card Block (Flip Cards)

- Fence language: `memory-card`
- Or use `meta.type: "memory-card"` with language `yaml`.
- Supports two authoring formats:
  1. YAML cards format (`cards: [{front, back}]`)
  2. Slides-style child blocks with meta:
     - `card_name`: card id/title
     - `card_face`: `front` or `back`
- Cards render in responsive grid layout and flip on click.
- For YAML format, per-card `title` is not required.
- Front/back content is markdown and can include escaped inner fenced blocks.

Example:

```memory-card {"title":"Git Fundamentals","cardMinHeight":180}
cards:
  - front: |
      What does `git status` show?
    back: |
      It shows:
      - branch status
      - staged changes
      - unstaged changes
      - untracked files

  - front: |
      What does `git add .` do?
    back: |
      Adds changed/new files in current directory tree to staging.

  - front: |
      What does `git commit -m "msg"` do?
    back: |
      Creates a commit from staged changes with commit message `"msg"`.
```

Slides-style example (same block syntax as current blocks, only extra `card_name`/`card_face` meta):

```memory-card {"title":"Git Fundamentals (Slides Style)","cardMinHeight":180}
\```markdown {"card_name":"git-status","card_face":"front"}
What does `git status` show?
\```

\```markdown {"card_name":"git-status","card_face":"back"}
It shows working tree/staging state and untracked files.
\```

\```markdown {"card_name":"git-commit","card_face":"front"}
What does `git commit -m "msg"` do?
\```

\```markdown {"card_name":"git-commit","card_face":"back"}
Creates a commit from staged changes.
\```

\```markdown {"card_name":"git-add","card_face":"front"}
What does `git add .` do?
\```

\```markdown {"card_name":"git-add","card_face":"back"}
Stages changed/new files under current directory tree.
\```
```

### 9) Interactive Code Block (Editor + Run/AI Actions)

- Fence language: any (e.g. `python`, `javascript`, `php`, `react`, `dart`, `go`, `rust`, etc.)
- Must set `meta.type: "code"` (otherwise it falls back to a plain rendered code fence).
- Renders `CodeBlock`.

Common meta fields (used by `code.block.tsx`):
- `action` (string, default `"run"`): controls the primary action.
  - `"run"`: run code / send to executor.
  - `"none"`: disable actions (display-only).
  - `"complete"`: AI completes the code (used by `api-server/app/course.ts`).
  - `"edit"`: AI edits/fixes the code (used by `api-server/app/course.ts`).
- `button` (string, optional): label for the action button.
- `runButton` (string, optional): alternate run label.
- `readOnly` (boolean, optional)
- `optional` (boolean, optional): auto-advance immediately.
- `minHeight` / `maxHeight` (string, optional): CSS sizes (e.g. `"120px"`, `"50vh"`).
- `rawCode` (boolean, optional): affects some language modes (notably PHP).
- `codeOnly` (boolean, optional): hides some surrounding UI (and auto-advances the step immediately).
- `handBtn` (boolean, optional): show the hand icon (Ask AI about selected code).
- `commentBtn` (boolean, optional): show the pencil icon (Ask AI to add comments).
- `title` (string, optional): used by `tabs` inner blocks as the tab label.
- `from` (string, optional): when set to `"chat"`, shows some assistant UI affordances.

Example:

```python {"type":"code","action":"run","button":"Run"}
print("hello")
```

### 10) YAML List Block

- Fence language: `yaml`
- `meta.type: "list"`
- Renders `ListBLock`.

Meta:
- `tag` (string, optional): `"ol"` for ordered list; anything else -> unordered.
- `default` (boolean, optional): if true, shows “Ask AI” toggles for items even without a suffix.

YAML value:
- A YAML list.
- Each item can be:
  - a string
  - an object `{ "Title": ["Child 1", "Child 2"] }`
- Optional per-item “Ask AI language”: append `#<lang>` to the end of the item text (regex is `/#([a-z]{0,10})$/`).

Example:

```yaml {"type":"list","tag":"ol","default":true}
- What is Git?#any
- What is a commit?#any
- Branches:
  - What is a branch?#any
  - When do you create one?#any
```

### 11) YAML Form Block (Quiz/Test)

- Fence language: `yaml`
- `meta.type: "form"`
- Renders `FormBlock`.

Meta:
- `row` (boolean, optional): for `checkbox`/`radio`, render options horizontally.
- `order` (boolean, optional): if true, prefixes options with `1.`, `2.`, ...
- `ref` (string, optional): passed to `FormBlock` as `refInfo` and shown on error. Use `"ask"` to show an inline Chat prompt, or `"ai"` to show a generic AI-help hint.
- `video` (string, optional): video hint shown on error.

Note:
- `api-server/app/course.ts` currently generates form meta like `{type: 'form', refInfo: 'ask'}` for selection tests, but `frontend/components/blocks/course.block.tsx` passes `meta.ref` into `FormBlock` (not `meta.refInfo`). When authoring markdown by hand, prefer `ref: "ask"` / `ref: "ai"`.

YAML schema:
- A YAML array of question objects.
- Supported `type` values: `text`, `textarea`, `select`, `radio`, `checkbox`.

Fields by type:
- Common:
  - `type` (string)
  - `name` (string, required): unique DOM id/name
  - `label` (string, required): supports inline markdown
  - `markdown` (string, optional): rendered above the input
  - `hint` (string, optional): markdown shown when “Show Hint?” clicked
- `text`:
  - `placeholder` (string, optional)
  - `value` (string, required): expected answer (case-insensitive)
- `textarea`:
  - `rows` (number, optional)
  - `placeholder` (string, optional)
  - `value` (string, required)
- `select`:
  - `options` (string[], required)
  - `value` (number, required): correct option index (0-based)
- `radio`:
  - `options` (string[], required)
  - `value` (number, required): correct option index (0-based)
- `checkbox`:
  - `options` (string[], required)
  - `value` (number[], required): list of correct option indices (0-based)

Example:

```yaml {"type":"form","row":false,"order":true,"ref":"ask"}
- type: text
  name: q1
  label: What command initializes a git repository?
  placeholder: e.g. git ...
  value: git init
  hint: |
    \```bash
    git init
    \```

- type: select
  name: q2
  label: Which command shows the working tree status?
  options:
    - git log
    - git status
    - git diff
  value: 1
```

#### Linking Form Results to “Related Content” (uuid)

`course.block.tsx` stores `relatedContents[meta.uuid] = node.value` for **any** step that sets `meta.uuid`.

When a `form` is submitted, the UI reports test results under the key `elements[0].name` (the first question name).

If you want the reported test to include a `relatedContent` payload, set a previous step’s `meta.uuid` to match the **first question name**.

Example:

```python {"type":"code","uuid":"q1"}
# code the user is being tested on
print("hello")
```

```yaml {"type":"form"}
- type: text
  name: q1
  label: What does the program print?
  value: hello
```

### 11a) Generated Selection Test (From `api-server/app/course.ts`)

The course generator represents single/multiple choice tests as a **one-question** YAML `form` block:

- Single choice: `type: radio`, `value: <correctIndex>`
- Multiple choice: `type: checkbox`, `value: [<correctIndex>, ...]`
- The question `name` is a generated `uuid` so results can be correlated.

Example (single choice):

```yaml {"type":"form","ref":"ask"}
- type: radio
  name: 9f5b0c8f1c1c4c0e9c8a7b6a5d4e3f21
  label: What does `git init` do?
  options:
    - Deletes the repository
    - Initializes a new repository
    - Pushes changes to GitHub
  value: 1
```

Example (tabs + follow-up test):

```tabs {"uuid":"9f5b0c8f1c1c4c0e9c8a7b6a5d4e3f21"}
\```bash {"title":"Option A"}
echo A
\```

\```bash {"title":"Option B"}
echo B
\```
```

```yaml {"type":"form","ref":"ask"}
- type: radio
  name: 9f5b0c8f1c1c4c0e9c8a7b6a5d4e3f21
  label: Which option prints B?
  options:
    - Option A
    - Option B
  value: 1
```

### 12) YAML Notebook Block

- Fence language: `yaml`
- `meta.type: "notebook"`
- Renders `NotebookBlock`.

Meta:
- `bookType` (string, required): `"notebook"` or `"codebook"` (the generator uses lowercase `"codebook"`; anything other than `"notebook"` is treated as codebook mode).
- `file` (string, required): destination file name/path used by the VS Code integration.
- `lang` (string, required): language for syntax highlighting.
- `during` (number, ms, optional)

YAML value:
- A YAML array of blocks:
  - `instruction` (string, markdown)
  - `code` (string)
  - `prompt` (string): used to generate an “Ask AI” prompt.

Example:

```yaml {"type":"notebook","bookType":"notebook","file":"main.py","lang":"python"}
- instruction: |
    Write a function.
  code: |
    def add(a, b):
      return a + b
  prompt: |
    Explain what this code does and improve naming.
```

### 13) YAML Media Block

- Fence language: `yaml`
- `meta.type: "media"`
- Renders `MediaBlock`.

Meta:
- `during` (number, ms, optional)

YAML value:
- A YAML array of objects:
  - `url` (string, required)
  - `title` (string, optional)

Supported URLs:
- Images: `.jpeg`, `.jpg`, `.gif`, `.png`
- YouTube URLs (embedded)
- Audio: `.mp3` or `.wave` (note: code checks for `.wave`)
- Otherwise treated as video

Example:

```yaml {"type":"media"}
- url: https://www.youtube.com/watch?v=dQw4w9WgXcQ
  title: Watch this clip
- url: /img/example.png
  title: Screenshot
```

### 14) Tabs Block (Multiple Code Editors Under Tabs)

- Fence language: `tabs`
- Renders `CodeTabsBlock`.

Outer meta (optional):
- `rawCode` (boolean)
- `minHeight` / `maxHeight` (string)
- `uuid` (string, optional): used by the generator to associate follow-up tests with the tabs content (`relatedContents[uuid]`).
Content:
- Markdown that contains **multiple inner fenced code blocks**.
- Inner fences can include per-tab meta, e.g. `{ "title": "Client" }`.
- Because this is nested inside a top-level fence, inner fences usually must be written escaped as `\```...` in the source.

Example:

```tabs {"minHeight":"140px"}
\```python {"title":"Python"}
print("hello")
\```

\```javascript {"title":"JavaScript"}
console.log('hello')
\```
```

## Non-Interactive Fallback Code Blocks

If a fenced block doesn’t match the special cases above (e.g. `meta.type` is missing), `course.block.tsx` falls back to rendering it as markdown content via `MarkdownPlay`.

That means:
- ` ```mermaid ... ``` `, ` ```plantuml ... ``` `, and ` ```latex ... ``` ` can be displayed inside a `markdown` step (escape them as `\```...`).
- A plain ` ```python ... ``` ` without `{ "type": "code" }` will display as a static code fence (not an interactive editor).

## VS Code Event Contract (Webpage <-> WebUI <-> Extension)

This section documents the currently implemented event pipeline across:
- `frontend/components/blocks/course.block.tsx`
- `webui/socket_service.py`
- `vscode-juniorit/src/remoteService.ts`

Route:
1. Frontend emits `assignment_event` with `local_dev_token`.
2. WebUI routes that event to the matching signed-in container session.
3. VS Code extension handles the payload in `assignmentEvent(...)`.

### Direct API Dispatch to VS Code

You can also send events to VS Code extension clients directly via WebUI API:

- Endpoint: `POST /api/vscode/event`
- Purpose: send one payload to all connected VS Code extension clients for a `local_dev_token`.
- Behavior: returns error if no VS Code client is connected for that token.

Request body:

```json
{
  "local_dev_token": "YOUR_LOCAL_DEV_TOKEN",
  "payload": {
    "type": "right_panel",
    "url": "https://example.com/docs",
    "dst": "vscode"
  }
}
```

Success response:

```json
{
  "payload": {
    "sent": 1
  },
  "error": null
}
```

Error response (no VS Code clients connected):

```json
{
  "payload": null,
  "error": "No VS Code extension clients connected for this local_dev_token"
}
```

Notes:
- `payload` must be a JSON object.
- `local_dev_token` can be omitted only if server-side `LOCAL_DEV_TOKEN` is configured.
- Delivery is fan-out: all connected VS Code clients under that token receive the same `assignment_event`.

### Events emitted from `CourseBlock`

- `type: "shell"`: used by `control` block validation (`cmd`, `dir`, `regx`, `error`). This is routed to the container side for command validation, not a direct VS Code command.
- `type: "get-container"`: used by `container` block polling.
- `type: "terminal_sent_text"`: emitted when explicitly called by integration code (payload includes `text`, `addNewLine`, `dst: "vscode"`).
- `type: "notebook_add_cell"` / `type: "notebook_add_execute"` / `type: "editor_add_code"`: emitted by `notebook` block actions.

### Events handled by VS Code extension (`remoteService.ts`)

- `terminal_close_all`
- `terminal_new` (`name`, `shell`, `arg`, `directory`, `follow`)
- `terminal_focus`
- `terminal_sent_text` (`text`, `addNewLine`)
- `notebook_add_cell` (`file`, `lang`, `code`)
- `notebook_add_execute` (`file`, `lang`, `code`)
- `editor_add_code` (`file`, `code`)
- `right_panel` (`url` optional, `body.html` optional, optional `body.shell`, optional `clear`; if `url` and `body` are both present, `url` is used)
- `open_file` (`file`, optional `fromLine/startChar/toLine/endChar`)

### Right-panel clickable command links

The extension right-panel webview supports a JSON-link pattern:

```markdown
[Open README](#{%7B%22type%22%3A%22open_file%22%2C%22file%22%3A%22%2Fworkspace%2FREADME.md%22%7D)
```

The `href` must start with `#{...}` (URL-encoded JSON object). On click, that JSON payload is sent back to `assignmentEvent(...)` in the extension.

### Not currently implemented

- No direct `"open_url"` event handler in `vscode-juniorit/src/remoteService.ts`.
- No generic "execute arbitrary VS Code command ID" event from course markdown.

### Author Cookbook (Markdown Block -> JSON Payload)

For each action below, the markdown block is shown first, then the resulting/expected payload.

Example: notebook append + execute

```yaml {"type":"notebook","bookType":"notebook","file":"/workspace/project/notebooks/demo.ipynb","lang":"python"}
- instruction: |
    Add and run this cell.
  code: |
    print("Hello from notebook cell")
  prompt: |
    Explain what this cell does.
```

```json
{
  "type": "notebook_add_execute",
  "file": "/workspace/project/notebooks/demo.ipynb",
  "lang": "python",
  "code": "print(\"Hello from notebook cell\")",
  "dst": "vscode"
}
```

Example: append code to a normal editor file

```yaml {"type":"notebook","bookType":"codebook","file":"/workspace/project/src/main.py","lang":"python"}
- instruction: |
    Append this code to the file.
  code: |
    print("Hello from editor_add_code")
  prompt: |
    Improve this snippet for production use.
```

```json
{
  "type": "editor_add_code",
  "file": "/workspace/project/src/main.py",
  "lang": "python",
  "code": "print(\"Hello from editor_add_code\")",
  "dst": "vscode"
}
```

Example: shell validation on Continue

```markdown {
  "type":"control",
  "action":"continue",
  "cmd":"git status --short",
  "dir":"/workspace/project",
  "regx":"(M|A|\\?\\?)",
  "error":"Please modify or add at least one file before continuing."
}
Click Continue to validate your workspace state.
```

```json
{
  "type": "shell",
  "cmd": "git status --short",
  "dir": "/workspace/project",
  "regx": "(M|A|\\?\\?)",
  "error": "Please modify or add at least one file before continuing."
}
```

Example: create terminal (`terminal_new`)

```markdown {"type":"vscode"}
- [1:0-1:0](#new)
- [1:0-1:0](#/workspace/project)
```

```json
{
  "type": "terminal_new",
  "directory": "/workspace/project",
  "dst": "vscode"
}
```

Example: send text to terminal (`terminal_sent_text`)

```markdown {"type":"vscode","vscode":true,"shell":"git status\npnpm dev","clear":true}
Right panel will show shell commands with quick-send icons.
```

```json
{
  "type": "terminal_sent_text",
  "text": "git status",
  "addNewLine": true,
  "dst": "vscode"
}
```

Example: open file and select range (`open_file`)

```markdown {"type":"vscode"}
- [12:0-20:0](/workspace/project/README.md)
```

```json
{
  "type": "open_file",
  "file": "/workspace/project/README.md",
  "fromLine": 12,
  "startChar": 0,
  "toLine": 20,
  "endChar": 0,
  "dst": "vscode"
}
```

Example: right panel with clickable actions (`right_panel`)

```markdown {"type":"vscode","vscode":true,"shell":"ls -la\npnpm -v","clear":true}
- [1:0-20:0](/workspace/project/README.md)
- [1:0-1:0](#new)
```

```json
{
  "type": "right_panel",
  "clear": true,
  "body": {
    "html": "<h3>Quick Actions</h3><ul><li><a href=\"#{%7B%22type%22%3A%22open_file%22%2C%22file%22%3A%22%2Fworkspace%2Fproject%2FREADME.md%22%7D}\">Open README</a></li><li><a href=\"#{%7B%22type%22%3A%22terminal_new%22%2C%22name%22%3A%22Project%20Shell%22%2C%22directory%22%3A%22%2Fworkspace%2Fproject%22%7D}\">Open Project Terminal</a></li></ul>",
    "shell": "ls -la\npnpm -v"
  },
  "dst": "vscode"
}
```

Example: right panel open URL (`right_panel.url`, takes precedence over `body`)

```markdown
No direct course markdown block emits `right_panel.url` today.
```

```json
{
  "type": "right_panel",
  "url": "https://example.com/docs",
  "body": {
    "html": "<p>This is ignored when url is present.</p>"
  },
  "dst": "vscode"
}
```

Notes:
- `dst: "vscode"` is used in current integration payloads and should be kept for compatibility.
- For right-panel links, `href` must start with `#{...}` where `{...}` is URL-encoded JSON.
- The same payloads can be sent through `POST /api/vscode/event` for direct server-to-VSCode dispatch.
