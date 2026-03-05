Update WebUI, tasks -> execute -> workflow -> run action

1. pass an extra url param to new session page
- `workflow` = workflow file path relative to the project root
- in the prompt, add workspace path information and mention that any intermediate file that needs to be saved should be saved to the task workspace (the folder where the instruction file is located)

2. once the user clicks the start button on the new session page

- create a workflow execute thread in the backend
- create tmux session name: sp-workflow-execute
- only one workflow execute thread should exist in the backend; if the `sp-workflow-execute` tmux session is killed, the thread should be terminated too
- only one `sp-workflow-execute` tmux session should exist; kill any existing one when the core engine reloads (re-read `.env` on start; refer to `core/bin/tool-cli engine-reload`)
- if a new workflow execute thread is created, check for any existing thread and `sp-workflow-execute` tmux session, and kill all of them before starting a new session

3. refer to `core/bin/run-workflow`, and update `core/bin/run-workflow` as well
- `core/bin/run-workflow` runs the workflow in the background without a terminal (AI permissions use the skill agent settings)
- `workflow execute thread` runs the workflow in a web terminal or native terminal based on the user's selection (other AI agent permissions use the new session WebUI settings)

4. for each AI agent node prompt

- use the workflow prompt in the new session screen as system prompt
- then add the AI agent node prompt (refer to what `core/bin/run-workflow` currently uses)
- if the AI agent node has upstream inputs (not the `START` node), then add:
  your upstream inputs are located in the files
  `.skillpilot/temp/workflow/uid1.md` 
  `.skillpilot/temp/workflow/uid2.md`
  ...
  read them to get all the information you need
- then add your current AI agent node UID: `xxx`. Once you finish your task, you need to write the output result to the `.skillpilot/temp/workflow/uid.md` file

5. update `core/bin/run-workflow` to use these new prompts

6. for `workflow execute thread`, run the workflow in a web terminal or native terminal based on the user's selection

- first clear folder `.skillpilot/temp/workflow/` to make it empty
- ref to `core/bin/tool-cli new_agent_session "<prompt>"`
- for each AI agent node, dispatch the prompt to the AI agent in the tmux session, then monitor whether the `.skillpilot/temp/workflow/node-uid.md` file exists
- once the file exists, check the tmux session window; if the task is finished, it will say `.skillpilot/temp/workflow/node-uid.md` was created
- then, similar to `core/bin/tool-cli new_agent_session "<prompt>"`, start the next AI agent node (by terminating the AI agent and creating a new one with the correct prompt and permission)
- once all nodes are finished, terminate the workflow execute thread, but leave the tmux session window and the AI agent, as the user may review the result in the console window

7. for `core/bin/run-workflow`, use the path `.skillpilot/temp/background-workflow` as the output file path
for `workflow execute thread` in the terminal, use the path `.skillpilot/temp/terminal-workflow` as the output file path
