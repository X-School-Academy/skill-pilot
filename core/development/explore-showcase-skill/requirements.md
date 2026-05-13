> the commit version below is just to indicate the current codebase git log version
> commit 2a7e5400bd0cbd41e5f5f284075ae1217615eb3f 
> please keep this commit version as we will use it as checkpoint for reverse engineering learning later

First, we need to update the data structure defined at `core/engine/data/AGENTS.md`

1. add `goals` field to the supported sample fields, which will be a short description in markdown list format of the expected outcome or result after the user completes the showcase task.
2. add `zip-files-url` field to the supported sample fields to support the zip file url, which will be auto unzipped to `workspace/showcases/{showcase_slug_id}/` when the user starts to ask AI agents to do the task with the prompt string.
3. add `video_prompt` field to the supported sample fields which will be used to create the video for this showcase.
4. add `tutorial_prompt` field to the supported sample fields which will be used to create the online interactive tutorial or tutorial video for this showcase.
5. add `terms` string array field to the supported sample fields which are the terms of the technologies which are related to this showcase, and the users can use each term to learn more afterwards.
6. for links field, we will add a extra key `prompt` as [`{ name, url, prompt }`], which will be used to create the linked resource url with the prompt string

Then update the explore showcase webUI page to add two new sections after the prompt section:
1. Goals section to display the expected outcome or result in markdown format after the user completes the showcase task, which is from the `goals` field in the sample yaml file.
2. Keywords section under the prompt section.
The keywords will be separeted  by comma, and each keywords will be clickable popup and linked to a url "https://skill-pilot.ai/explore/terms?slug={showcase_slug}&term={term}", the term should be format as kebab case string.

For files field, we will only display the file name in the UI, without the path information. and the file name will be clickable to show the file content in a popup window with file manager UI.

Last, create a new system agent skill named "explore-showcase" with requirements as below:

## There are 4 audiences of this project:

1. AI agent learners: to learn how to use AI agents to solve problems.
2. AI agent builders: to learn how to build AI agents.
3. Job seekers: Learning more deeply about not only AI agent technology but also traditional software development technology, to get a job in the AI agent industry.
4. Business owners: who want to use AI agents to run an AI-native business.

Our concept is "Do first, learn afterwards".

We will provide some showcases or prompt templates for the users to do with AI first, then learn the related knowledge and skills only when they need to afterwards.

the template data are at `core/engine/data`, we will put the showcase thumbnails at `core/webui/public/showcases` organized by the showcase categories. the thumbnails will also support url links.

## There are several types of the showcases with which users can do with Skill Pilot AI agents:

1. Use browser to do something, like search, setup token from a website, aws web console operations, etc.
2. Create videos, audio books, most are for education or social media, like youtube, tiktok, etc.
3. Create slides, documents, spreadsheets, etc. for work or education.
4. Create online interactive tutorials for self learning
5. Vibe coding a small project without coding knowledge by prompting the AI agent to do the coding. e.g. create a website, create a game, create a mobile app, AI related MCP servers, Agent skills, AI agents, or a npm, pip package, etc.
6. Do some researches, like technical research, market research, etc.
7. Use Skill Pilot AI agents to schedule some automation tasks, like calendar management, email management, etc.
8. Control Skill Pilot AI agents remotely by Discord bot, and receive notifications from the bot, like the status of the task which is running with Skill Pilot AI Agents, or human loop need the user to approve, etc.
9. Develop new features for Skill Pilot AI agents, such as creating new skills, updating UI, and new extensions, bug fixing, etc.
10. Learning how to build a Skill Pilot AI agent by reverse engineering:
  - remove a feature of agent skill or update existing code to create bugs or issues for users to fix or improve
  - draft a feature or agent skill `requirements.md` as per `core/development/explore-showcase-skill/reverse-engineering-guide.md` or create file `update.md` or `issue.md` for the bug fixing task or improvement task.
  - then ask the users to implement the feature or agent skill by themselves with the `requirements.md` drafted.
11. Learning how to build a project or game by reverse engineering:
  - provide a project or game git url,
  - draft a requirements.md for the project or game as per `core/development/explore-showcase-skill/reverse-engineering-guide.md`
  - keep any assets of the existing project or games.
  - then ask the users to implement the project or game by themselves with the `requirements.md` drafted, and the assets provided. or create the assets by themselves with the help of Skill Pilot AI agents.
12. Skill Pilot AI agent codeware related task or code analysis tasks showcases, such as:
   - check update
   - code restore
   - make contribution
   - create documentation
   - Learn license and compliance

## The content of each showcase

1. A thumbnail image for the showcase, with a title and a short description.
2. A short prompt string, which will be used for users to guide AI agents to do the task.
3. the files will be referenced in the prompt string
 - the files will be placed at `workspace/showcases/{showcase_slug_id}/`
   - `requirements.md` if have
   - `update.md` if have
   - `issue.md` if have
   - `assets/` if have
  - the files can be zip file url, but it will be auto unzipped to `workspace/showcases/{showcase_slug_id}/` when the user starts to ask AI agents to do the task with the prompt string.
  - there will be no `requirements.md` if the content is too short and can be directly included in the prompt string
4. other fields in the sample yaml file:
 - request: the request for this task, in this case, we will leave the prompt as blank place holder, to let user to draft the prompt by themselves, such as "Please draft a prompt to ask AI agents to do the task, and the prompt should include the reference files if have"
 - git_tag: the git commit version or tag, mostly for the reverse engineering showcases
 - workflow: the agent worflow will be used in this showcase.
 - skills: the agent skills will be used in this showcase.
 - extensions: the agent extensions will be used in this showcase.
 - tools: the agent tools will be used in this showcase, such as ffmpeg, etc.
 - in_mode:  view the result in skill pilot's which instance: development or production.
   - if in_mode is prod, it will execute in the skill pilot prod instance, and see results in the prod webui, for non skill pilot development related showcases, as the prod instance is more stable for users to do the task. such as vibe coding, creating content, doing research, do some automation tasks, etc.
   - if in_mode is dev, it will execute in the skill pilot prod instance, and see results in the dev webui, most for the skill pilot development, as the webui will be hot reloaded, user can see the changes in real-time. (if user execute the task in the dev instance web terminal, it can be broken easily due to hot reloading, so we will execute the task in the prod web terminal, and monitor the result in the dev instance)
 - directory: the root directory for this showcase. the requirement.md, update.md, issue.md, and assets/ will be copied to this directory from `showcases/{showcase_slug_id}/`, such as `core/development/{new-feature-name}/` or `workspace/vibe-coding/{project-name}/`, etc. if the directory is not specified, it will be default to `workspace/showcases/{showcase_slug_id}/`

 **Update system agent skills vibe coding and codeware to copy any requirements.md files to the appropriate directory if the files are not already there**
--
This agent skill will follow the user's instructions to update the data at folder `core/engine/data` and create the reference files at `workspace/showcases/{showcase_slug_id}/` for the showcases or create zip file and upload to aws s3, and unzip the file to `workspace/showcases/{showcase_slug_id}/` when the user starts to ask AI agents to do the task.
