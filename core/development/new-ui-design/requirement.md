Update core/webui and core/engine

Move the current default `core/webui/pages/index.tsx` to `core/webui/pages/courses/index.tsx`, and create a new `core/webui/pages/index.tsx` file as the Home Screen with the following content:

Header logo: Same as the current index.tsx.
Home Screen (top right): Show the Agent provider selector (default: gemini), as in the current index.tsx.
Home Screen (left menu):

- New Terminal
- Terminals

--

- Courses

-workspace-
- Learning
- Projects 
- Research
- Tasks

-System-
- Development

-Commercial Project-
- Dev Swarm

- Processes
- Remote Clients
- Skills
- MCP Servers
- Schedule
- Extensions
- Profile

(Note: `-xxx-` indicates a menu separator)

Home Screen (Right/Main panel):

* Home (default path `/`):

Display a headline title in the top middle: "Skill Pilot", with the subtitle: "Do anything first, then learn anything you want." Follow this with a text input box and a "Start" button. Clicking the "Start" button should open `/terminal` using the default AI agent CLI, passing the prompt from the text input box. If closed, return to the default Home content.

* New Terminal:

Open `/terminal` in the right panel. The shell command should be the default AI agent binary CLI (e.g., gemini), without an initial prompt. If closed, return to the default Home content.

* Terminals:

Show a list of current live web terminals in the main screen, or indicate if there are no active terminals. Clicking any entry should open that terminal. Unless a terminal is explicitly closed (via a button or closing the browser window), it should remain live, allowing multiple terminals to run simultaneously.

* Courses:

The current courses screen, but with a "Back" button in the top left (under the header bar) to return to the Home Screen.

* Dev Swarm:

Route `/dev-swarm`, but with a "Back" button in the top left (under the header bar) to return to the Home Screen. Update the logo text from 'AI Code\n Dev Swarm' to 'Skill Pilot\n Dev Swarm'.

For all other menu items, use placeholders.
