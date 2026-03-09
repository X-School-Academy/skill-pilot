Update the WebUI:

1. Change the `Projects` menu text in the left navigation bar to `Vibe Coding`.
2. Make the Vibe Coding page based on the current Tasks page.
3. On the Vibe Coding screen:
   - Change `Tasks` to `Projects`.
   - Change `Add Task` to `New`.
   - Support any text files, including the files that are currently supported.
4. Map `vibe-coding` to the folder `workspace/vibe-coding`.

Most features should remain the same as Tasks, with only small text and file-location changes. However, there are fixed file names for different features under `workspace/vibe-coding/{project-name}/`:

- `requirements.md`
- `plan.md`
- `implement.md`
- `update.md`
- `issues.md`

1. Update the `Add Task` button to `New`, with these options:

- `New Project`
  - The form should include:
  - `Project Name`: automatically create a folder using the format `project-name`. If the folder name already exists, add a suffix such as `_1` or `_2`.
  - `Requirements`: save to `workspace/vibe-coding/{project-name}/requirements.md`.
- `Update Request`
  - Show an auto-complete project dropdown, defaulting to the current project.
  - Save the Update Request text area to `workspace/vibe-coding/{project-name}/update.md`.
- `Bug/Issue Report`
  - Show an auto-complete project dropdown, defaulting to the current project.
  - Save the bug/issue report text area to `workspace/vibe-coding/{project-name}/issues.md`.

2. For `requirements.md`, replace the `Execute` button with these buttons:
   - `Refine`: use the prompt `Use agent skill vibe-coding-project-refine to refine the @{requirement file path related to root of the project}`, then send it and redirect to the new session page.
   - `Initial`: use the prompt `Use agent skill vibe-coding-project-initial to init the project defined at @{requirement file path related to root of the project}`, then send it and redirect to the new session page.
   - `Plan`: use the prompt `Use agent skill vibe-coding-project-plan to make a development plan for requirement @{requirement file path related to root of the project}`, then send it and redirect to the new session page.

   If `requirements.md` is deleted, also remove the folder `workspace/vibe-coding/{project-name}`. Show a warning and require the user to type `delete` in the confirmation form before deletion.

3. For `plan.md`, change the `Execute` button to `Implement`, then use the prompt `Use agent skill vibe-coding-project-implement to implement the code as the @{plan file path related to root of the project}`, then send it and redirect to the new session page.

4. For `implement.md`, remove the `Execute` button and add these buttons:

- `Review`: use the prompt `Use agent skill vibe-coding-project-review to review the code of the implementation of the @{implement file path related to root of the project}`, then send it and redirect to the new session page.
- `Test`: use the prompt `Use agent skill vibe-coding-project-test to test the code of the implementation of the @{implement file path related to root of the project}`, then send it and redirect to the new session page.
- `Deploy`: use the prompt `Use agent skill vibe-coding-project-deploy to deploy the code of the implementation of the @{implement file path related to root of the project}`, then send it and redirect to the new session page.

5. For `update.md`, change the `Execute` button to `Update Code`, then use the prompt `Use agent skill vibe-coding-project-update to update the code based on the update request defined in @{update file path related to root of the project}`, then send it and redirect to the new session page.

6. For `issues.md`, change the `Execute` button to `Fix Issues`, then use the prompt `Use agent skill vibe-coding-project-fix-issues to fix the issues defined in @{issues file path related to root of the project}`, then send it and redirect to the new session page.


Create all the system agent skills start with vibe-coding-project-* for most standard coding project, but 

- vibe-coding-project-create: create workspace/vibe-coding/{project-name}/requirements.md by prompt instead from webui form
- vibe-coding-project-initial: init git repo in github
- vibe-coding-project-deploy: deploy to aws ec2 instance

I will update these agent skills later to best fit user's request