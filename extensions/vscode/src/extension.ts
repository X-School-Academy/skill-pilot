try {
	require("module-alias/register");
} catch (e) {
	console.log("module-alias import error !");
}
import * as vscode from "vscode";
import { LeftPanelWebview } from "providers/left-webview-provider";

import loadingDecorationType from "./components/LoadingDecoration";
import { startService, endService } from "./remoteService";

import utils from 'utils'

let markdownDisplayView = null;

export function activate(context: vscode.ExtensionContext) {
	startService(context);

	const leftPanelWebViewProvider = new LeftPanelWebview(context?.extensionUri, {});
	
	let view = vscode.window.registerWebviewViewProvider(
		'left-panel-view',
		leftPanelWebViewProvider,
		{
			webviewOptions: {
				retainContextWhenHidden: true,
			},
		}
	);
	context.subscriptions.push(view);

	const commands = ['complete', 'fix', 'execute', 'translate', 'assistant', 'enter', 'inline'];

	commands.forEach(command => {
		let codeAssistantCommand = vscode.commands.registerCommand(
				`skill-pilot.assistant.${command}`,
				async () => {
					const activeEditor = vscode.window.activeTextEditor;
					if(!activeEditor) {
						return;
					}

					let openPanel = true;

					const selectionRange = activeEditor.selection;
					let code = await activeEditor.document.getText(selectionRange);
					let start_line = -1;
					let end_line = -1;
					let action = null;
					let reference = null

					let ext = activeEditor.document.fileName.split(".").pop();

					if(command == 'enter') {
						openPanel = false;
						const line = activeEditor.document.lineAt(activeEditor.selection.active.line)
						if(line.text.trim().length < 10) {
							return
						}

						action = 'inline-complete'

						code = line.text.trim()
						start_line = line.lineNumber
						end_line = start_line

						const range = line.range;

						vscode.window.setStatusBarMessage('Processing ...')
						activeEditor.setDecorations(loadingDecorationType, [range])

						activeEditor.edit((editBuilder) => {
							editBuilder.replace(range, line.text + '\n');
						});


						let ref_start_line = activeEditor.selection.active.line - 100
						let ref_end_line = activeEditor.selection.active.line - 1

						if(ref_start_line < 0) ref_start_line = 0
						if(ref_end_line < 0) ref_end_line = 0

						if(ref_end_line != activeEditor.selection.active.line) {
							let start = new vscode.Position(ref_start_line, 0); 
							let end = new vscode.Position(ref_end_line, activeEditor.document.lineAt(ref_end_line).text.length); 

							let range = new vscode.Range(start, end);

							reference = await activeEditor.document.getText(range)
						}

					} else if (command == 'inline') {
						openPanel = true; // without loading webview, it will not work
						action = 'inline-fix'
						const selectionRange = activeEditor.selection

						console.log(`${selectionRange.start.line}, ${selectionRange.end.line}`);

						if (selectionRange.start.line == selectionRange.end.line) {
							if (selectionRange.end.character - selectionRange.start.character < 10) {
								let document = activeEditor.document
								start_line = 0
								end_line = document.lineCount - 1
								code =  document.getText().trim()
							} else {
								const line = activeEditor.document.lineAt(activeEditor.selection.active.line);
								if(line.text.trim().length < 10) {
									return
								}

								//start_line = line.lineNumber
								//end_line = start_line
								code = line.text.trim()

								let ref_start_line = selectionRange.start.line - 100
								let ref_end_line = selectionRange.start.line - 1

								if(ref_start_line < 0) ref_start_line = 0
								if(ref_end_line < 0) ref_end_line = 0

								if(ref_end_line != selectionRange.start.line) {
									let start = new vscode.Position(ref_start_line, 0); 
									let end = new vscode.Position(ref_end_line, activeEditor.document.lineAt(ref_end_line).text.length); 

									let range = new vscode.Range(start, end);

									reference = await activeEditor.document.getText(range)
								}
							}

							activeEditor.setDecorations(loadingDecorationType, [selectionRange])

						} else {
							start_line = selectionRange.start.line
							end_line = selectionRange.end.line

							let start = new vscode.Position(start_line, 0); 
							let end = new vscode.Position(end_line, activeEditor.document.lineAt(end_line).text.length); 

							let range = new vscode.Range(start, end);
							activeEditor.setDecorations(loadingDecorationType, [range])

							code = await activeEditor.document.getText(range).trim();

							let ref_start_line = selectionRange.start.line - 100
							let ref_end_line = selectionRange.start.line - 1

							if(ref_start_line < 0) ref_start_line = 0
							if(ref_end_line < 0) ref_end_line = 0

							if(ref_end_line != selectionRange.start.line) {
								let start = new vscode.Position(ref_start_line, 0); 
								let end = new vscode.Position(ref_end_line, activeEditor.document.lineAt(ref_end_line).text.length); 

								let range = new vscode.Range(start, end);

								reference = await activeEditor.document.getText(range)
							}
						}

						vscode.window.setStatusBarMessage('Processing ...')
					}

					if(openPanel) await vscode.commands.executeCommand(`workbench.view.extension.view-left-panel`);

					const payload = {action, start_line, end_line, reference, code, fileExt: ext, command};

					console.log('payload', JSON.stringify(payload, null, 4));

					setTimeout(()=>{
						vscode.window.setStatusBarMessage('')
					}, 15000)

					leftPanelWebViewProvider.sendData(payload);
				}
			);
			context.subscriptions.push(codeAssistantCommand);
		}
	);

	const showAsMarkdownSidePage = vscode.commands.registerCommand('skill-pilot.assistant.markdown-side-view', (uri: vscode.Uri) => {
		if (markdownDisplayView) {
			markdownDisplayView.reveal(vscode.ViewColumn.Beside);	
		} else {
			markdownDisplayView = vscode.window.createWebviewPanel(
			'markdownView',
			'Markdown View',
			vscode.ViewColumn.Beside,
			{
				enableScripts: true
			}
			);

			markdownDisplayView.webview.html = getWebviewContent(markdownDisplayView.webview);

			markdownDisplayView.onDidDispose(() => {
				markdownDisplayView = null;
			}, null, context.subscriptions);
		}

		vscode.workspace.openTextDocument(uri).then(document => {
		  const markdownContent = document.getText();
		  markdownDisplayView.webview.postMessage({ type: 'markdown', content: markdownContent });
		});

	  });
	
	context.subscriptions.push(showAsMarkdownSidePage);

	const showAsMarkdownMainPage = vscode.commands.registerCommand('skill-pilot.assistant.markdown-view', (uri: vscode.Uri) => {
		if (markdownDisplayView) {
			markdownDisplayView.reveal(vscode.ViewColumn.One);	
		} else {
			markdownDisplayView = vscode.window.createWebviewPanel(
				'markdownView',
				'Markdown View',
				vscode.ViewColumn.One,  // Change this line to show in the main area
				{
					enableScripts: true
				}
			);
	
			markdownDisplayView.webview.html = getWebviewContent(markdownDisplayView.webview);
	
			markdownDisplayView.onDidDispose(() => {
				markdownDisplayView = null;
			}, null, context.subscriptions);
		}
	
		vscode.workspace.openTextDocument(uri).then(document => {
			const markdownContent = document.getText();
			markdownDisplayView.webview.postMessage({ type: 'markdown', content: markdownContent });
		});
	});

	context.subscriptions.push(showAsMarkdownMainPage);
	
}

// this method is called when your extension is deactivated
export function deactivate() { 
	endService();
}

function getWebviewContent(webview: vscode.Webview): string {
	const host = utils.host;
	const version = utils.version;

	const body = `<iframe id="juniorit-embedded-markdown-page" src="${host}/embedded/vscode-markdown?version=${version}" style="border:0;" allowfullscreen="" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>`;

	return `<html>
			<head>
				<meta charSet="utf-8"/>
				<meta http-equiv="Content-Security-Policy" 
						content="default-src 'self' ${host};
						img-src vscode-resource: https:;
						font-src ${webview.cspSource};
						style-src ${webview.cspSource} 'unsafe-inline';
						script-src ${webview.cspSource} 'unsafe-inline';
						">             

				<meta name="viewport" content="width=device-width, initial-scale=1.0">

				<style>
					body, html, iframe {
						height: 100%;
						width: 100%;
						margin: 0;
						padding: 0;
					}
				</style>
			</head>
			<body>
				${body}
				<script>
					(function () {
						const vscode = acquireVsCodeApi();
					
						let iframeLoaded = false;
						let pendingData = null;
					
						const iframe = document.getElementById('juniorit-embedded-markdown-page');
					
						const reloadIframe =  setInterval(() => {
							iframe.src = iframe.src;
						}, 5000);
					
					
						const onMessage = async (event) => {
							const data = event.data;
					
							if(data === 'juniorit-embedded-vscode-md-page-ready') {
								iframe.contentWindow.postMessage('juniorit-vscode-md-reply', '*');
								iframeLoaded = true;
								clearInterval(reloadIframe);
								if(pendingData !== null) {
									iframe.contentWindow.postMessage(pendingData, '*');
									pendingData = null;
								}
								return;
							}
					
							if(iframeLoaded) {
								iframe.contentWindow.postMessage(data, '*');
							} else {
								pendingData = data;
							}
						};
					
						window.addEventListener('message', onMessage);
					}());
				</script>
			</body>
		</html>`;
  }
  