Similar to /vibe-coding

we need to create a new webui screen /skill-pilot-development mapping to folder `core/development` (for menu Skill Pilot: Development)

1. Update Projects to Features
2. New project to New Feature
3. In the new feature(project pop up), we have form
   - Feature Name: text field with auto complete dropdown
     - if input the feature name, it is a new feature
     - if select from the dropdown, then show two radio buttons: Update, Bug/Issues after feature name
     - feature dropdown: core/features/*.md, show the markdown file name without extension
   - Related feattures
     - show auto complete dropdown from core/features/*.md with an add button (do not show added features, one feature only added once), once click add button, then
     - list the added feature name as list
   - requirement/update/issue text features as vibe-coding
4. depending on new feature or update/ bugs, create files
  `core/development/{feature-name}/requirements.md`, or `update.md`, `issues.md`
  for the created file, append content below (refine the text):

  The related feature files for reference:
  - file path 1
  - file path 2

5. all actions buttons similar to vibe-coding project, but update `Deploy` button to name `Merge`
6. for each feature folder have the same new request button as vibe coding, but with `Related feattures` forms, and create the file same as #4 to append the reference files

Create system agent skills for Skill Pilot development

   - `skill-pilot-feature-create`
   - `skill-pilot-feature-refine`
   - `skill-pilot-feature-initial`: will create a new branch
   - `skill-pilot-feature-plan`
   - `skill-pilot-feature-implement`
   - `skill-pilot-feature-review`
   - `skill-pilot-feature-test`
   - `skill-pilot-feature-merge`: merge and switch code to user branch, finish the development
   - `skill-pilot-feature-update`
   - `skill-pilot-feature-fix-issues`




