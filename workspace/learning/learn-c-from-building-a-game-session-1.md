```yaml {"type":"meta"}
last_step: 3
```



```yaml {type: meta}
title: Learn C from building a game - Session 1
slug:  learn-c-from-building-a-game-session-1
during: 40 mins
```

```markdown {during: 1000}
### Topics in this session:

1. Introduction to the T-Rex game in Google Chrome.
2. Set up your Linux cloud development server instantly.
3. Link your Dev Container with JuniorIT.AI's Discord Bot.
4. Explore the starter project and your cloud development environment.
5. Learn some basic coding knowledge.
6. About the starter project

```

```markdown {type: control, action: continue, timeLeft:40}
Are you ready?

Press the button below to continue.
```

```markdown {during: 1000}
### 1. Introduction to the T-Rex game in Google Chrome.

If you are using the Chrome browser, you can play the T-Rex game by typing **chrome://dino** into the address bar or by visiting [https://juniorit-ai.github.io/t-rex-runner/](https://juniorit-ai.github.io/t-rex-runner/).

This serves as your starter project to learn C through game development:
[https://juniorit-ai.github.io/t-rex-runner/juniorit/](https://juniorit-ai.github.io/t-rex-runner/juniorit/).

Many students learn coding effectively in school, but don't know how to build a project afterwards. This is because teachers provide coding knowledge but often neglect teaching how to create a project. When you learn coding, you may encounter concepts that are challenging to grasp in their abstract form without practical application in a project. At JuniorIT.AI, we emphasize building a project from day one, even if you have no prior coding experience. We then introduce you to basic coding knowledge with the assistance of AI.

We start with C because nearly all programming languages, such as Java, Python, and JavaScript, have their roots in C. Once you understand C, you can quickly master other programming languages.

Code is essentially a form of English. We will guide you on how to read and modify the starter project's code, even if you have no prior coding experience. Afterwards, we will teach you how to use AI to explain code, write code, and check your code for errors.
```

```markdown {type: control, action: continue, timeLeft: 35}
Please explore the game and understand how you learn coding with JuniorIT.AI.

Then click the button below.
```

```yaml {type: form, action: test, ref:ask}
- type: checkbox
  name: q20231111-1105
  label: "Please select all the statements below that are correct."
  options:
    - Code is essentially a form of English; even if you don't know coding, you might still understand some code.
    - Nearly all programming languages, such as Java, Python, and JavaScript, have their roots in C.
    - Once you understand C, you can quickly master other programming languages.
    - Many students learn coding effectively in school but don't know how to build a project afterwards.
  value: [0,1,2,3]
```

```markdown {during: 1000}
### 2. Set up your Linux cloud development server instantly.

As almost all cloud servers run on Linux, starting to learn coding on Linux is a more effective and professional approach.

Now, let's set up your Linux development environment by following the steps below:

#### Fork and create your GitHub repository

1. Sign up for or sign in to a free GitHub account. 
>Ref to video: [https://www.youtube.com/watch?v=2gT74fLQ3tg](https://www.youtube.com/watch?v=2gT74fLQ3tg)

2. Fork the repository at [https://github.com/juniorit-ai/gamecraft](https://github.com/juniorit-ai/gamecraft).
>Ref to video: [https://www.youtube.com/watch?v=LJsWonAhiNg](https://www.youtube.com/watch?v=LJsWonAhiNg)

3. Enable GitHub Page support to your repository's root directory in the repository settings, then you can share your game with your friends and family. 
>Ref to video: [https://youtu.be/sL9pA2oAewY](https://youtu.be/sL9pA2oAewY) (it can take up to several mintues to activate after setup)

#### Lanuch your dev container (Codespace) from your GitHub repository
>Ref to video:  [https://youtu.be/n9p25TLvCNY](https://youtu.be/n9p25TLvCNY)

1. Open your your GitHub repository in your web browser
2. Click the green button `<> Code` in the top right
3. Select the Codespaces tab
4. Then click the green button `Create Codespace on main`

>It will take up to 2 mins to setup. If your codespace takes long time to load, you can refresh the web page to fix the loading issue.

* Note: You can use Github Codespaces for free for up to 60 hours per month. 

* Additionally, you can set up your development environment with Visual Studio Code/Docker installed, which we will learn about later.

```

```markdown {type: control, action: continue, timeLeft: 30}
After the dev container completes its setup, you will be presented with your development environment: a web version of the Visual Studio Code editor featuring a Linux terminal window.


While we are waiting for your codespace setup , please check our video below for how to use Visual Studio Code editor.
>Ref to video: [https://www.youtube.com/watch?v=-HmzbFBSjiM](https://www.youtube.com/watch?v=-HmzbFBSjiM)

Once your codespace / dev container is ready to use, please click the button below.
```


```markdown {during: 1000}
### 3. Link your Dev Container with JuniorIT.AI's Discord Bot and checkout your starter project.

Before we start further, let's link your Dev Container with JuniorIT.AI's Discord Bot first. 

Please follow the steps below.
> Ref to video: [https://www.youtube.com/watch?v=LKwRkS7ElBw](https://www.youtube.com/watch?v=LKwRkS7ElBw)

1. Open your Discord desktop app or web app and navigate to the JuniorIT.AI server.
2. Enter the following slash command in the chat box of any channel (Do not send to the JuniorIT.AI's Discord Bot): 

   \`\`\`
   /dev-link
   \`\`\`

3. JuniorIT.AI's Discord Bot will then provide you with a one-time sign-in shell command as shown:

   \`\`\`
   juniorit YOUR-ONE-TIME-SIGN-IN-TOKEN
   \`\`\`

4. Copy and execute the shell commands in your VS Code's terminal window as follows:
   
   \`\`\`
   juniorit YOUR-ONE-TIME-SIGN-IN-TOKEN
   juniorit get
   \`\`\`
   
After that, you can follow the subsequent instructions to checkout your starter project.

```

```markdown {type: control, action: continue, cmd: ':get_online_container', regx:'v1.0.4', error: 'No required dev containner found!', timeLeft: 38}
Have you done all the steps above?

If YES, please press the button below.
```

```markdown {during: 1000}
### 4. Explore the starter project and your cloud development environment.

#### Explore the starter project

Before we discover your cloud development environment, let's run the starter project first.

Please execute the shell commands below in your VS Code's terminal window one by one.
>Ref to video: [https://youtu.be/mnx7nspmkYA](https://youtu.be/mnx7nspmkYA)

  \`\`\`
  cd ~/workspace/clang_session_1
  make clean
  make
  make run
  \`\`\`

> The Linux `make` command is used to build and maintain groups of programs and files from the source code, it is one of the most frequently used commands by the developers.

Please follow the instructions in the dev container to open your web browser. You should see the starter project displayed there, showing a T-Rex image.

> Your can terminate the Dev Web Server process by press `Ctrl + C` shortcut, or simply close the termial window and open another one from the top `Terminal` menu.

Starting today, we will assist you in building a game with AI, similar to the one found at  [https://juniorit-ai.github.io/t-rex-runner/juniorit/](https://juniorit-ai.github.io/t-rex-runner/juniorit/), We'll then guide you to add keyboard events, sound, more images, and collision detection to create a game ready for sale on various platforms, including iOS, Android, Web, Windows, Mac, and Linux in C language. You can choose the platform(s) you wish to target for your game.

Additionally, we will guide you in understanding the entire game engine developed by us in the C language. This will show you how you can use C, a non-object-oriented programming language, unlike C++, to grasp the logic of how C++ implements classes. This approach will enable you to master C++ in a much shorter time when you need to learn it.
```

```markdown {type: control, action: continue, history: 'make', error: 'Please make sure you have run the commands above in the dev container!', timeLeft: 30}
Once you have explored the starter project 

Then click the button below.
```

```markdown {during: 1000}
#### Linux Basic Bash commands

>Bash, short for "Bourne Again Shell" is a Unix shell and command language. It is widely used as the default shell for many Unix-based systems, including Linux and macOS.

Here are some Linux shell commands, we will use in this session.

1. **pwd**: 
   - Stands for 'print working directory'.
   - Displays the full directory path of the current working directory.

2. **cd**: 
   - **cd** is the command for 'change directory'.
   - **cd ~/** navigates to the user's home directory.
   - **cd ../** moves up one directory level from the current directory.

3. **mkdir**: 
   - Short for 'make directory'.
   - Used to create a new directory in the specified path.

4. **rm file and directory**: 
   - **rm** stands for 'remove'.
   - Used to delete files and directories.
   - To remove a directory, the flag **-r** (recursive) is used.

5. **touch**: 
   - Used to create a new empty file or update the timestamp of an existing file.

6. **ls -l**: 
   - **ls** is the command to 'list' contents of a directory.
   - The **-l** option lists files and directories with detailed information like permissions, number of links, owner, group, size, and timestamp of last modification.


Or you can use the AI prompts below to learn more knowledge for Linux shell commands
```

```yaml {type: list, tag:ol, default: true}
  - I am new to Linux. Can you provide some basic Linux shell commands for practice?
  - How can I list the files in a directory by their creation time using a Linux shell command?
  - What is the purpose of the 'touch' command in Linux shell?
  - How can I forcibly remove a directory using a Linux shell command?
  - Replace this or update the prompts above with your question.
```

```markdown {type: control, action: continue; timeLeft:25}
Please click the **hand raise icon** in the end of each question to ask AI and check the answer.

Then click the button below.
```

```yaml {type: form, action: test, ref: ai}
- type: checkbox
  name: q20231111-1146
  label: "Please select all the statements below that are correct."
  options:
    - "`pwd`: Print the current working directory."
    - "`list -l`: List the contents of the current directory in long format, showing details."
    - "`mkdir <directory_name>`: Create a new directory."
    - "`touch <file_name>`: Create an empty file."
    - "`rm -r <directory_name>`: Remove a directory."
  value: [0,2,3,4]
```

```markdown {during: 1000}
#### The most simple C program 

Now let's do some practice for these shell commands.

In the VS Code terminal window, run shell commands below one by one.
>Ref to video: [https://youtu.be/scqkBc5DSW8](https://youtu.be/scqkBc5DSW8)
```

```markdown {type: code}
cd ~/workspace
pwd

mkdir test
ls -l
cd test
pwd

echo "int main(){}" > test.c
ls -l
gcc test.c
ls -a
./a.out

cd ..
ls
rm -r test
ls
```

```markdown {type: control, action: continue, history:'main', error: 'Please make sure you have run the commands above in the dev container!', timeLeft:20}
Once you have finished the pratice, 

Then click the button below.
```

```markdown {during: 1000}
If no errors, congratulations, you have a C language development environment in a dev container.

The code below is the simplest C coding application. Although it does nothing, it is often used to verify if your C compiler is available on your computer.
C Compiler will igore the whitespace, so it can be written just as a simple string "int main(){}"

  \`\`\`c {type: code, action: none}
  int main() {

  }
  \`\`\`

>In C, if the return type of main is int and you don't explicitly return a value, the program returns 0 by default, which generally indicates successful execution.

If there's any other shell command you don't understand, you can open the assistant window in the JuniorIT.AI's VS Code extension for assistance. It has been automatically installed and can be found in the VS Code left toolbar (it should be the last icon – the JuniorIT.AI logo).

Or you can use below's AI assistant box for help.
```

```markdown {type:chat, action: code, button: "Ask AI"}
Please explain the below shell commands for me.

echo "int main(){}" > test.c
gcc test.c
./a.out 

```

```yaml {type: form, action: test, ref: ask}
- type: checkbox
  name: q20231115-1307
  label: "Please select all the statements below that are correct."
  options:
    - "`gcc` is the C language compiler."
    - "`a.out` is the default compiled file name generated by gcc."
    - "`./a.out` The ./ prefix specifies that the program should be executed from the current directory."
    - "`echo hello > test.txt` The > symbol is used to redirect the output of the echo command to the file specified."
    - "`int main(){}` It is an invalid C code syntax."
  value: [0,1,2,3]
```

```markdown {during: 1000}
### 5. Learn some basic coding knowledge.

Please run shell command below in VS Code's terminal to open the file playground/helloworld.c in vscode, and check the source code 

*In a shell script, a string that starts with `#` is a comment to help you understand the script. DO NOT copy and run any string that starts with `#`.*

>Ref to video: [https://youtu.be/1jXZq3AQf0g](https://youtu.be/1jXZq3AQf0g)

  \`\`\`
  # you may use `pwd` command to check your corrent direcotry and use a different command, ex. `cd playground`
  cd ~/workspace/clang_session_1/playground 

  # jcode is JuniorIT.AI's special tool designed to help you quickly open one text file in your current VS Code
  jcode helloworld.c
  \`\`\`

Then run shell command below

   \`\`\`
   # Instead of generating the default compiled file name 'a.out', we use '-o' to specify the executable file name 'helloworld'.
   gcc helloworld.c -o helloworld
   ls -l
   ./helloworld

   # remove the generated executable file
   rm helloworld

   # 'jcscript' is JuniorIT.AI's special tool designed to help you quickly test C code, just as you would test other scripting languages.
   jcscript helloworld.c

   \`\`\`

You can discover more about the basic syntax of C programming with the help of AI now
```

```yaml {type: list, tag:ol, default: true}
- Please write a "Hello, World!" application in C?
- Does my program need the main function in C, and what is its purpose?
- How do I write single-line comments in C?
- How do I write multi-line comments in C?
- Does whitespace matter in C?
- Do I need curly braces in C, and what is their purpose if they are needed?
- Do I need to use semicolons in the end of each line in C?
```

```markdown {type: control, action: continue, history: 'helloworld.c', error: "Please make sure your have checked and tested the helloworld code as the instructions above!", timeLeft:15}
Please click the **hand raise icon** in the end of each question to learn each concept with AI.

Then click the button below.
```

```markdown {type: code}
/*+
  This is JuniorIT.AI's special comments style: starts with /*+ and ends with +*/, AI will ignore these comments automatically
+*/
```

```yaml {type: form, action: test, ref: ask}
- type: checkbox
  name: q11-02-10-37
  label: "Please select the correct description below:"
  options:
    - "`/*this is a multiple line comment*/` syntax in C."
    - "`//this is a single line comment` syntax in C."
    - "Whitespace is not a concern in C coding; I can use any amount of whitespace to format my code."
    - "If I want to disable some code without deleting it, I just need to comment it out."
  value: [0, 1, 2, 3]
```

```markdown {during: 1000}
### 6. About the starter project

#### The mini remote file explorer 

In your dev container, which functions like a remote cloud computer, you cannot upload and download files directly, but we have a special tool to help you.
>Ref to video: [https://youtu.be/v1QRJX84WOQ](https://youtu.be/v1QRJX84WOQ)

Please run the shell commands below:

   \`\`\`
   #just to make sure you are in the root of your project
   cd ~/workspace/clang_session_1

   # change your corrent working directory to the project's `res` directory
   cd res

   jfiles

   # ctrl + c to exit the process

   \`\`\`


`jfiles` is a special tool from JuniorIT.AI, designed to help you quickly download or upload files to your development container. 

You can upload PNG or JPG image files to this directory, and they will be automatically loaded by the game engine.

>please make sure to remove any files not used in the `res` folder, or it will increase your game's loading time.

JuniorIT.AI has prepared AI-generated background and sprite images for you at [https://d2sdz7s4ni6kmi.cloudfront.net/juniorit/game-image-template.zip](https://d2sdz7s4ni6kmi.cloudfront.net/juniorit/game-image-template.zip) to use in your game or you can use the `/img2img` slash command in our Discord server's `#ai-sprites` channel to have your version.

You need to remove the background of a sprite image before using in the game. You can use this free online service easily [https://www.adobe.com/express/feature/image/remove-background](https://www.adobe.com/express/feature/image/remove-background).

```

```markdown {type: control, action: continue, history: 'jfiles', error: 'Please run shell jfiles, and exit by ctrl + c, then contine!', timeLeft:10}
Once you have explored the JuniorIT.AI mini development container's web file explorer,

Click the button below to continue.
```

```markdown {during: 1000}
#### Code search skill

Now, let's explore the starter project's code.
>Video for beginner: [https://www.youtube.com/watch?v=SLGvRDGA5rU&t=217s](https://www.youtube.com/watch?v=SLGvRDGA5rU&t=217s)

>Video with more knowledge: [https://youtu.be/SLGvRDGA5rU](https://www.youtube.com/watch?v=SLGvRDGA5rU)

Please run the shell commands below, or open the file `src/main.c` directly in VS Code:

    cd ~/workspace/clang_session_1
    jcode src/main.c

The code in this file is the entry point of your game. It sets up the game window size, creates a scene, adds the scene to the game, sets the scene as the current scene, and then runs the game loop.

You can read the code easily with the knowledge we just learned.

Then run the shell commands below, or open the file `src/FirstScene.c` directly in VS Code:

    jcode src/FirstScene.c

This is the first scene of your game. 

You will write most of the logic in this file. 

But for now, you can ignore almost all the code; just focus on the four lines below:

  \`\`\`c {action: none}  
  static Sprite *sprite = NULL; // on the top of the file

  Scene *scene = (Scene *)thiz; // in the function `first_scene_init`

  sprite = new_sprite("t-rex.png");
  scene->add_child(scene, sprite);
  \`\`\`

The below shell commands are very important to a developer, please try it now:

   \`\`\`bash
   cd ~/workspace/clang_session_1

   # search string `static Sprite` in folder `src` 
   grep -rn 'static Sprite' src 

   # search string `rex.png` in folder `src` 
   grep -rn rex.png src 
   \`\`\`

The commands will show you the code is in which file and at which line. Or you can search the keyword in the VS Code's Edit menu: Find in Files.

#### Update the code by yourself

In our game engine, we refer to any image as a sprite, including the background image.

You can update the file `src/FirstScene.c` to add a background and replace the sprite image as the code below:

  \`\`\`c {action: none}  
  static Sprite *sprite = NULL; // on the top of the file
  static Sprite *background = NULL;

  Scene *scene = (Scene *)thiz; // in the function `first_scene_init`

  background = new_sprite("your-background-image.png");
  scene->add_child(scene, background);

  sprite = new_sprite("your-sprite-image.png");
  scene->add_child(scene, sprite);
  \`\`\`

Just as you paint on a canvas, you need to add the background sprite first, then other sprites. Otherwise, the background image will cover the other sprites you added.

Please make sure to put your PNG/JPG image in the `res` folder; the game engine will load it automatically.

```

```markdown {type: control, action: continue, history: 'grep', error: 'Please make sure you have finished all the content above!', timeLeft:5}
Once you have explored the starter project's code

Click the button below to continue.
```

```markdown {type: control, action: end}
Congratulations! You have completed the online task.

***You may take a rest and complete the assigned task within 7 days from the date of receiving this assignment.***

When you are ready, please read the clang_session_1/README.md file in your project for the requirements and complete the code in the project's `src` directory on your own.

Once you have completed the project as specified, please execute the following shell command to submit your project for review:

`cd ~/workspace/clang_session_1`

`juniorit submit`

Normally, we will review your project within 1 to 2 business days.

By the way, we have prepared a handbook for you for this session. It's located at `clang_session_1/docs/handbook.md` and includes all the AI prompts and key concepts you should know.

Good luck, and enjoy your coding journey in game development.

```