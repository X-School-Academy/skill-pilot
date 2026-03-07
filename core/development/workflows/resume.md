For terminal workflow execuation 
1. change the temp task folder name

from

 .skillpilot/temp/terminal-workflow/20260307-220748-a97e1e32

to 

.skillpilot/temp/terminal-workflow/{lower-case-instruction-file-path}
the file path is related to project root and replace /, ' ' etc to '-', and remove `.md` extension name

2. when click Execute button webui tasks, first check the task folder if exist (merge with the current save api when click execute)
- if not exist, no any update, follow the current code logic
- if exist, Add a checkbox option after Reference Files: [ ] Resume
  - if resume not checked, the current logic do not change
  - if resume checked
    - do not remove the task folder
    - run the agent node as worflow only for the node has no output file created or skip, so we will not run the nodes which have already done, and the output file is exist in the temp task folder

