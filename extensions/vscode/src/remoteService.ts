import * as vscode from 'vscode';
import { io, Socket } from 'socket.io-client';
import * as os from 'os';
import * as path from 'path';
import * as fs from 'fs/promises';
import utils from 'utils'

let socket: Socket = null;
let isStopped = false;
let localDevToken: string = null;
let activeContainerToken: string = null;

let context = null;
let rightPanel = null;
let rightPanelHtml = '';

const boltIconSVG = '<div style="width: 24px; height: 24px; display: inline-block; color: gray"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" class="w-6 h-6 inline mx-2 text-primary-blue opacity-80"><path fill-rule="evenodd" d="M14.615 1.595a.75.75 0 01.359.852L12.982 9.75h7.268a.75.75 0 01.548 1.262l-10.5 11.25a.75.75 0 01-1.272-.71l1.992-7.302H3.75a.75.75 0 01-.548-1.262l10.5-11.25a.75.75 0 01.913-.143z" clip-rule="evenodd"></path></svg></div>'

async function readFromConfig(key: string): Promise<string | null> {
    if (key == 'container_token' && localDevToken) {
        return localDevToken;
    }

    if(key == 'container_token' && process.env.JUNIORIT_CONTAINER_TOKEN) {
        return process.env.JUNIORIT_CONTAINER_TOKEN
    }

    const homeDir = os.homedir();
    if (!homeDir) {
        console.error('Error: Unable to find home directory.');
        return null;
    }

    const configFile = path.join(homeDir, '.juniorit', 'config');

    try {
        const content = await fs.readFile(configFile, 'utf-8');
        const data = JSON.parse(content);
        return data[key] as string | null;
    } catch (err) {
        console.error('Error reading config file:', err);
        return null;
    }
}

function emitContainerSignIn() {
    if (!socket || !activeContainerToken) {
        return;
    }

    const version = utils.version;
    socket.emit('container_event',  {
        type: 'sign-in',
        token: activeContainerToken,
        version,
        container_version: process.env.JUNIORIT_DEV_VER,
        src: 'vscode'
    });
}

export function setLocalDevToken(token: string) {
    if (!token || typeof token !== 'string') {
        return;
    }
    localDevToken = token.trim();
    if (!localDevToken) {
        return;
    }
    activeContainerToken = localDevToken;
    emitContainerSignIn();
}

const assignmentEvent = async (payload) => {
    if(payload.type == 'terminal_close_all') {
        vscode.window.terminals.forEach(terminal => terminal.dispose());
    }

    else if(payload.type == 'terminal_new') {
        const name = payload.name ?? ''
        const shell = payload.shell ?? '/bin/bash'
        let args = payload.arg ? [payload.arg] : []
        if(payload.directory) args = [`cd ${payload.directory}; exec bash`]
        const terminal = vscode.window.createTerminal(name, shell, args)
        terminal.show()
        if(payload.follow) {
            terminal.sendText(payload.follow, true);
        }
    }

    else if(payload.type == 'terminal_focus') {
        let activeTerminal = vscode.window.activeTerminal

        if(!activeTerminal) {
            activeTerminal = vscode.window.createTerminal()
        }

        activeTerminal.show()
    }

    else if(payload.type == 'terminal_sent_text') {
        let activeTerminal = vscode.window.activeTerminal

        if(!activeTerminal) {
            activeTerminal = vscode.window.createTerminal('', '/bin/bash')
        }
        activeTerminal.show()
        
        activeTerminal?.sendText(payload.text, payload.addNewLine ?? false);
    }

    else if (payload.type == 'notebook_add_cell') {
        // file, lang, code
        try {
            const fullPath = payload.file.startsWith('~') ? payload.file.replace('~', os.homedir()) : payload.file;
            await fs.access(fullPath);
            const fileUri = vscode.Uri.file(fullPath);

            let fileEditor: vscode.NotebookEditor = null;
            for (const editor of vscode.window.visibleNotebookEditors) {
                
                if (editor.notebook.uri.path === fileUri.path) {
                    //fileEditor = await vscode.window.showTextDocument(editor.document, editor.viewColumn);
                    fileEditor = await vscode.window.showNotebookDocument(editor.notebook);
                    break;
                }
            }

            if(!fileEditor) {
                const notebook = await vscode.workspace.openNotebookDocument(fileUri);
                fileEditor = await  vscode.window.showNotebookDocument(notebook, {viewColumn: vscode.ViewColumn.One});
            }

            let lang = payload.lang ?? 'python';
        
            const notebook = fileEditor.notebook;
            const cellCount = notebook.cellCount;
            const codeCell = new vscode.NotebookCellData(vscode.NotebookCellKind.Code, payload.code, lang);

            const notebookEdit = vscode.NotebookEdit.insertCells(cellCount, [codeCell]);
            const edit = new vscode.WorkspaceEdit();
            edit.set(notebook.uri, [notebookEdit]);

            vscode.workspace.applyEdit(edit);
        } catch (e) {
            console.error(e)
        }
    } else if (payload.type == 'notebook_add_execute') {
        // file, lang, code
        try {
            const fullPath = payload.file.startsWith('~') ? payload.file.replace('~', os.homedir()) : payload.file;
            await fs.access(fullPath);
            const fileUri = vscode.Uri.file(fullPath);

            let fileEditor: vscode.NotebookEditor = null;
            for (const editor of vscode.window.visibleNotebookEditors) {
                
                if (editor.notebook.uri.path === fileUri.path) {
                    //fileEditor = await vscode.window.showTextDocument(editor.document, editor.viewColumn);
                    fileEditor = await vscode.window.showNotebookDocument(editor.notebook);
                    break;
                }
            }

            if(!fileEditor) {
                const notebook = await vscode.workspace.openNotebookDocument(fileUri);
                fileEditor = await  vscode.window.showNotebookDocument(notebook, {viewColumn: vscode.ViewColumn.One});
            }

            let lang = payload.lang ?? 'python';
        
            const notebook = fileEditor.notebook;
            const cellCount = notebook.cellCount;

            const codeCell = new vscode.NotebookCellData(vscode.NotebookCellKind.Code, payload.code, lang);

            const notebookEdit = vscode.NotebookEdit.insertCells(cellCount, [codeCell]);
            const edit = new vscode.WorkspaceEdit();
            edit.set(notebook.uri, [notebookEdit]);

            vscode.workspace.applyEdit(edit).then(() => {
                let index = notebook.cellCount - 1;

                if (index < 0) {
                    return;
                }
            
                const cell = notebook.cellAt(index);
                if (cell.kind !== vscode.NotebookCellKind.Code) {
                    return;
                }
                // https://code.visualstudio.com/api/references/commands
                vscode.commands.executeCommand('notebook.cell.execute', { start: index, end: index + 1 });
            });
            
        } catch (e) {
            console.error(e)
        }
    }
    
    else if (payload.type == 'editor_add_code') {
        // file, lang, code
        const fullPath = payload.file.startsWith('~') ? payload.file.replace('~', os.homedir()) : payload.file;
        try {
            await fs.access(fullPath)
            
            const fileUri = vscode.Uri.file(fullPath);

            let fileEditor: vscode.TextEditor = null

            for (const editor of vscode.window.visibleTextEditors) {
                if (editor.document.uri.path === fileUri.path) {
                    fileEditor = await vscode.window.showTextDocument(editor.document, editor.viewColumn);
                    break;
                }
            }

            if(!fileEditor) {
                const document = await vscode.workspace.openTextDocument(fileUri);
                fileEditor = await  vscode.window.showTextDocument(document, vscode.ViewColumn.One);
            }

            const lastLine = fileEditor.document.lineAt(fileEditor.document.lineCount - 1);
            let codeToInsert = lastLine.text.length == 0 ? `\n${payload.code}` : `\n\n${payload.code}`;
            if(fileEditor.document.lineCount == 1) codeToInsert = payload.code;

            fileEditor.edit(editBuilder => {
                editBuilder.insert(new vscode.Position(fileEditor.document.lineCount, 0), codeToInsert);
            });

        } catch (e) {
            console.error(e)
        }
    }

    else if(payload.type == 'right_panel') {
        if (rightPanel) {
            console.log('right_panel show')
            rightPanel.reveal(vscode.ViewColumn.Beside);
        } else {
            console.log('right_panel new')
            // Create a new webview panel
            rightPanel = vscode.window.createWebviewPanel( 'rightWebview', // Identifies the type of the webview. Used internally
                'Instructions', // Title of the panel displayed to the user
                {
                    viewColumn: vscode.ViewColumn.Beside,
                    preserveFocus: true
                },
                {
                    enableScripts: true
                } 
            );

            rightPanel.webview.onDidReceiveMessage(assignmentEvent);

            rightPanel.onDidDispose(() => {
                console.log('right_panel onDidDispose')
                rightPanel = null;
            }, null, context.subscriptions);
        }

        if (payload.url && typeof payload.url === 'string') {
            // URL takes precedence over body/html when both are present.
            rightPanel.webview.html = getWebviewUrlContent(rightPanel.webview, payload.url);
            return;
        }

        if (payload.clear) rightPanelHtml = ''

        if (payload.body.html) {
            payload.body.html = payload.body.html.replaceAll('__BoltIcon__', boltIconSVG)
            rightPanelHtml += payload.body.html
        }

        payload.body.html = rightPanelHtml

        console.log('right_panel', payload.body)
        rightPanel.webview.html = getWebviewContent(rightPanel.webview, payload.body);
    }

    else if(payload.type == 'open_file') {
        const fullPath = payload.file.startsWith('~') ? payload.file.replace('~', os.homedir()) : payload.file;
        try {
            await fs.access(fullPath)
            
            const fileUri = vscode.Uri.file(fullPath);

            let fileEditor = null

            for (const editor of vscode.window.visibleTextEditors) {
                if (editor.document.uri.path === fileUri.path) {
                    fileEditor = await vscode.window.showTextDocument(editor.document, editor.viewColumn);
                    break;
                }
            }

            if(!fileEditor) {
                const document = await vscode.workspace.openTextDocument(fileUri);
                fileEditor = await  vscode.window.showTextDocument(document, vscode.ViewColumn.One);
            }

            if (payload.fromLine) {
                let fromLine = payload.fromLine ?? 1
                let startChar = payload.startChar ?? 0

                let toLine =  payload.toLine ?? fromLine
                let endChar = payload.endChar ?? 0

                const range = new vscode.Range(fromLine*1 - 1, startChar*1, toLine*1 - 1, endChar*1);
                fileEditor.revealRange(range, vscode.TextEditorRevealType.InCenter);

                fileEditor.selection = new vscode.Selection(range.start, range.end);
            }
        } catch (e) {
            console.error(e)
        }
    }

}

export async function startService(ctx: vscode.ExtensionContext) {

    // if not in a dev container(JUNIORIT_DEV_VER is undefined), it should start in test mode
    //if(!process.env.JUNIORIT_DEV_VER && !utils.isLocal) return
    if(socket != null) return

    context = ctx

    isStopped = false

    let token = null

    while (!(token = await readFromConfig('container_token'))) {
        if(isStopped) return;
        await new Promise(resolve => setTimeout(resolve, 1000));
    }

    const host = utils.socket;
	const version = utils.version;
    activeContainerToken = token;

    socket = io(host, {reconnection: true, reconnectionDelay: 1000, reconnectionDelayMax:15000});

    socket.on('connect', () => {
        socket.sendBuffer = [];
        console.log('Connected to the remote server');
        socket.emit('container_event',  {type: 'sign-in', token: activeContainerToken, version, container_version: process.env.JUNIORIT_DEV_VER, src: 'vscode'});
    });

    socket.on('server_event', (payload) => {
        if(payload.type == 'sign-in-request') {
            socket.emit('container_event',  {type: 'sign-in', token: activeContainerToken, version, container_version: process.env.JUNIORIT_DEV_VER, src: 'vscode'});
        } else {
            console.log(payload)
        }
    });

    socket.on('assignment_event', assignmentEvent);

    socket.on('disconnect', () => {
        console.log('Disconnected from the remote server');
    });
}

export function endService() {
    isStopped = true;

    if(socket) {
        socket.close();
    }
}

// Check if socket is currently connected
export function isSocketConnected(): boolean {
    return socket !== null && socket.connected === true;
}

// Force reconnect the socket, calls onResult with connection status
export function reconnectSocket(onResult?: (connected: boolean) => void): void {
    if (!socket) {
        console.log('Socket not initialized, cannot reconnect');
        onResult?.(false);
        return;
    }

    console.log('Forcing socket reconnection...');

    const timeout = setTimeout(() => {
        socket.off('connect', onConnect);
        onResult?.(socket.connected === true);
    }, 5000);

    const onConnect = () => {
        clearTimeout(timeout);
        socket.off('connect', onConnect);
        onResult?.(true);
    };

    socket.once('connect', onConnect);
    socket.disconnect();
    socket.connect();
}


const getWebviewContent = (webview, body) => {

    return`
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta viewport="width=device-width, initial-scale=1.0">
        <meta http-equiv="Content-Security-Policy" 
                                content="default-src 'self';
                                img-src vscode-resource: https:;
                                font-src ${webview.cspSource};
                                style-src ${webview.cspSource} 'unsafe-inline';
                                script-src ${webview.cspSource} 'unsafe-inline';
                                ">  
        <title>My Instructions</title>
        <style>
            .icon {
                opacity: 0.8;
                cursor: pointer;
                transition: opacity 0.3s;
            }
            .icon:hover {
                opacity: 0.6;
            }
        </style>
    </head>
    <body style="background-color:#fff; color: #000; font-size: medium; line-height: 150%;">
        ${body.html}
        <script>
            console.log("start script");
            const vscode = acquireVsCodeApi();
    
            function sendMessage(payload) {
                vscode.postMessage(payload);
            }
        
            function createIcon(svgContent) {
                const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
                icon.setAttribute('viewBox', '0 0 24 24');
                icon.setAttribute('fill', 'currentColor');
                icon.style.width = '24px';
                icon.style.height = '24px';
                icon.classList.add('icon');
                icon.innerHTML = svgContent;
                return icon;
            }
    
            function createComponent(content, sendText) {
                if(!content) return null;

                const container = document.createElement('div');
                container.style.opacity = '0';
                container.style.transition = 'opacity 1s ease-in-out';
    
                let comments = '';
    
                content.split('\\n').forEach(line => {
                    if (line.indexOf("#") === 0) {
                        comments += comments ? '\\n' + line : line;
                        return;
                    }
    
                    const rowContainer = document.createElement('div');
                    rowContainer.style.display = 'flex';
                    rowContainer.style.flexDirection = 'row';
                    rowContainer.style.alignItems = 'end';
    
                    const commandDiv = document.createElement('div');
                    commandDiv.style.flex = '1';
                    commandDiv.style.color = '#333';
                    commandDiv.style.backgroundColor = '#eee';
                    commandDiv.style.borderRadius = '0.375rem';
                    commandDiv.style.margin = '5px 0';
                    commandDiv.style.padding = '5px 10px';
    
                    if (comments) {
                        comments.split('\\n').forEach(row => {
                            const commentLine = document.createElement('div');
                            commentLine.textContent = row + ' ';
                            commandDiv.appendChild(commentLine);
                        });
                        comments = ''; // Reset comments
                    }
    
                    const lineDiv = document.createElement('div');
                    lineDiv.style.display = 'flex';
                    lineDiv.style.flexDirection = 'row';
                    lineDiv.style.marginTop = '5px';
    
                    const lineText = document.createElement('div');
                    lineText.style.flex = '1';
                    lineText.textContent = line;
    
                    // Create icons with onclick events
                    const iconsDiv = document.createElement('div');
    
                    // DocumentDuplicateIcon
                    const duplicateIcon = createIcon('<path d="M7.5 3.375c0-1.036.84-1.875 1.875-1.875h.375a3.75 3.75 0 0 1 3.75 3.75v1.875C13.5 8.161 14.34 9 15.375 9h1.875A3.75 3.75 0 0 1 21 12.75v3.375C21 17.16 20.16 18 19.125 18h-9.75A1.875 1.875 0 0 1 7.5 16.125V3.375Z"/><path d="M15 5.25a5.23 5.23 0 0 0-1.279-3.434 9.768 9.768 0 0 1 6.963 6.963A5.23 5.23 0 0 0 17.25 7.5h-1.875A.375.375 0 0 1 15 7.125V5.25ZM4.875 6H6v10.125A3.375 3.375 0 0 0 9.375 19.5H16.5v1.125c0 1.035-.84 1.875-1.875 1.875h-9.75A1.875 1.875 0 0 1 3 20.625V7.875C3 6.839 3.84 6 4.875 6Z"/>');
                    duplicateIcon.onclick = () => sendText ? sendText(line, false) : null;
    
                    // DocumentArrowDownIcon
                    const arrowDownIcon = createIcon('<path fill-rule="evenodd" d="M5.625 1.5H9a3.75 3.75 0 0 1 3.75 3.75v1.875c0 1.036.84 1.875 1.875 1.875H16.5a3.75 3.75 0 0 1 3.75 3.75v7.875c0 1.035-.84 1.875-1.875 1.875H5.625a1.875 1.875 0 0 1-1.875-1.875V3.375c0-1.036.84-1.875 1.875-1.875Zm5.845 17.03a.75.75 0 0 0 1.06 0l3-3a.75.75 0 1 0-1.06-1.06l-1.72 1.72V12a.75.75 0 0 0-1.5 0v4.19l-1.72-1.72a.75.75 0 0 0-1.06 1.06l3 3Z" clip-rule="evenodd"/><path d="M14.25 5.25a5.23 5.23 0 0 0-1.279-3.434 9.768 9.768 0 0 1 6.963 6.963A5.23 5.23 0 0 0 16.5 7.5h-1.875a.375.375 0 0 1-.375-.375V5.25Z"/>');
                    arrowDownIcon.onclick = () => sendText ? sendText(line, true) : null;
    
                    // ClipboardIcon
                    const clipboardIcon = createIcon('<path fill-rule="evenodd" d="M10.5 3A1.501 1.501 0 0 0 9 4.5h6A1.5 1.5 0 0 0 13.5 3h-3Zm-2.693.178A3 3 0 0 1 10.5 1.5h3a3 3 0 0 1 2.694 1.678c.497.042.992.092 1.486.15 1.497.173 2.57 1.46 2.57 2.929V19.5a3 3 0 0 1-3 3H6.75a3 3 0 0 1-3-3V6.257c0-1.47 1.073-2.756 2.57-2.93.493-.057.989-.107 1.487-.15Z" clip-rule="evenodd"/>');
                    clipboardIcon.onclick = () => {
                        navigator.clipboard.writeText(line).then(function() {
                        }).catch(function(err) {
                            console.error('Error in copying text: ', err);
                        });
                    };
    
                    iconsDiv.appendChild(duplicateIcon);
                    iconsDiv.appendChild(arrowDownIcon);
                    iconsDiv.appendChild(clipboardIcon);
    
                    lineDiv.appendChild(lineText);
                    lineDiv.appendChild(iconsDiv);
    
                    commandDiv.appendChild(lineDiv);
                    rowContainer.appendChild(commandDiv);
                    container.appendChild(rowContainer);
                });
    
                return container;
            }

            const handleClick = (event) => {
                let target = event.target;

                while (target && target.tagName !== 'A') {
                    target = target.parentNode;
                }

                if(!target) return; 

                console.log('handleClick', target.tagName)
    
                if (target.tagName === 'A' && target.getAttribute('href').startsWith('#{')) {
                    event.preventDefault();
    
                    const href = target.getAttribute('href').substring(1);
                    const payload = JSON.parse(decodeURIComponent(href));
    
                    sendMessage(payload);
                }
            };

            document.addEventListener('click', handleClick);
    
            const content = \`${body.shell ?? ''}\`;
            const element = createComponent(content, (line, isExecute) => {
                const payload = {type: 'terminal_sent_text', text: line, addNewLine: isExecute};
                sendMessage(payload);
            
            });

            if(element) {
                document.body.appendChild(element);
                // Fade in the element
                setTimeout(() => { element.style.opacity = '1'; }, 0);
            }

        </script>
    </body>
    </html>
    
`

}

const escapeHtmlAttr = (value: string): string => {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

const getWebviewUrlContent = (webview, url: string) => {
    const safeUrl = escapeHtmlAttr(url);

    return`
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta viewport="width=device-width, initial-scale=1.0">
        <meta http-equiv="Content-Security-Policy"
                                content="default-src 'none';
                                frame-src https: http:;
                                style-src ${webview.cspSource} 'unsafe-inline';
                                ">
        <title>Instructions</title>
        <style>
            html, body {
                margin: 0;
                padding: 0;
                width: 100%;
                height: 100%;
                overflow: hidden;
                background: #fff;
            }
            iframe {
                border: 0;
                width: 100%;
                height: 100%;
            }
        </style>
    </head>
    <body>
        <iframe src="${safeUrl}" referrerpolicy="no-referrer-when-downgrade"></iframe>
    </body>
    </html>
`
}
