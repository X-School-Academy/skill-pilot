We need to add a start screen which as the first screen of webui

So add a new menu item in the left menu called "Explore" in the most top of the menu list (then a separator), as the webui's home page.

It will loadding data from a json file with format below at `core/engine/data/showcases.json5` by an engine core api, and display the data in the start screen:

```json
{
    [{
        "category": "Category Name",
        "description": "Learn how to use the webui and get started with your projects.",
        "thumbnail": "thumbnail.png",
        "samples": [
            {
                "id": "sample1",
                "title": "Sample Name",
                "description": "A sample project to demonstrate the features of the webui.",
                "thumbnail": "sample1.png",
                "video": "optional file or url of the showcase video",
                "tutorial": "optional file or url of the tutorial video or webpage",
                "prompt": "prompt str",
                "git_tag": "tag_name or null",
                "use_worktree": true,
                "skills": [],
                "tools": [],
                "files": [],
                "links": [ # optional
                    {
                        "name": "Link Name",
                        "url": "https://example.com/link"
                    }
                ],
                "popularity": 100,
                "level": 1, // 1 to 10, 1 is the easiest, 10 is the hardest
                "rate": 4.5
            }
        ]
    }]
}

The category name will have

- Basic - basic knowledge and skills for using AI agents for beginners
- Videos - create videos with AI agent by prompting
- Games - create games with AI agent by prompting
- Websites - create websites with AI agent by prompting
- Slides - create slides with AI agent by prompting
- Mobile Apps - create mobile apps with AI agent by prompting
- Tutorials - create tutorials for learning with AI agent by prompting
- MCP Servers - create MCP servers with AI agent by prompting
- AI Agent Skills - create AI agent skills with AI agent by prompting
- AI Agents - create AI agent apps with AI agent by prompting
- Extensions - create Skill Pilot extensions with AI agent by prompting
- Skill Pilot Development - Skill Pilot development with AI agent by prompting

Thumbnail is optional, or use the first letter of each word using random background color as the thumbnail

In the start screen, we will have 3 display modes: by category, by popularity and by level in tile view. The default display mode is by category.
by category: it will display the category thumbnail and category name (show descriotion when hover), and when click the category, it will display the samples in that category.
by popularity, it will display the hottest samples in descending order of popularity, and show the sample thumbnail, name (show description when hover)
By level, it will display the samples in ascending order of level, and show the sample thumbnail, name (show description when hover)

When click the sample, it will open a new screen to show the sample detail screen:

the sample detail screen will have 3 columns layout, the left column is the main menu of webui, in the middle column is the sample detail content, and the right column is the related action buttons and links.


Sample detail content - midedle column - main area to show the sample detail content, it will show the sample title, description,:


thumbnail image
  video | tutorial : once click thumbnail, or vidoe link, it will open a video player to play the video
  if click tutorial link, it will open a video player to play the tutorial video, or open a new tab to show the tutorial webpage

Title
description

prompt: show the prompt in markdown format, and add a copy button to copy the prompt to clipboard

the prompt including path string in format like @path, it should show as a link, and when click the link, it will open a file manager tab to show the path or file in the file manager


Right column - width is same as the left column, it will show the related action buttons and links:

- action button: Use Template
- git tag
- use worktree: if true, show a button "Open in Worktree", when click it will open the sample project in a new worktree
- skills: show the agent skill names, when click, open the agent skill path in the file manager
- tools: show the tool names, when click, open the tool path in the file manager
- files: show the files list, when click the file, it will open the file in the file manager
- links: show the links list, when click the link, it will open the link in a new tab

Use Template - only working in prod mode

1. first show settings model, with the following options after user click the "Use Template" button:

[x] usig worktree - default to the sample setting, and allow user to change it
[x] checkout out tag: tag name - only show when git_tag is not null, allow user to uncheck it to use the current branch
[x] start in dev mode - default to true if the sample setting is to use worktree, otherwise default to false, allow user to change it

> Warning: update the default settings only you are experted at Skill Pilot AI agent development, otherwise, it may cause unexpected issues

[Start Template] button

2. if worktree true, create a new git worktree, using the current project folder name plus "_{sample_id}" as the new worktree folder name, and checkout the git tag if git_tag is not null, then start the webui in dev mode with the new worktree folder, and open webui new session page with the prompt
in worktree, always using dev mode
   - if the worktree folder already exists, ask to remove or continue with the existing worktree folder, if remove, it will remove the existing worktree folder and create a new one, if continue, it will use the existing worktree folder to start the webui in dev mode, and open webui new session page with the prompt
   - if dev mode webui already running, check if the running webui is using the same worktree folder, if yes, it will open webui new session page with the prompt, if no, it will ask to stop the running webui and start a new one with the worktree folder
   - show loading indicator untill the dev webui worktree is ready, then open webui new session page with the prompt

3. if worktree is false,  it will open webui new session page with the prompt - prod mode



when we create worktree, we should do

git stash push -u -m "save local changes"
git worktree add ../myrepo-new -b new-branch
cd ../myrepo-new
git stash apply
cd ../myrepo-original
git stash apply
git stash drop

after create worktree, we also create a soft link of config/.env to the new worktree path's config file