import { WebviewViewProvider, WebviewView, Webview, Uri, EventEmitter, window, commands, Position, Range, env} from "vscode";
import loadingDecorationType from "../components/LoadingDecoration";
import utils from '../utils'
import { setLocalDevToken, isSocketConnected, reconnectSocket } from "../remoteService";

export class LeftPanelWebview implements WebviewViewProvider {
	constructor(
		private readonly extensionPath: Uri,
		private _pendingData: any = null,
		private _view: any = null
	) {}
    private onDidChangeTreeData: EventEmitter<any | undefined | null | void> = new EventEmitter<any | undefined | null | void>();

    refresh(context: any): void {
        this.onDidChangeTreeData.fire(null);
        this._view.webview.html = this._getHtmlForWebview(this._view?.webview);
    }

	sendData(data) {
		data.sender = "vscode-juniorit";

		//console.log(data)
		
		if(this._view === null) {
			this._pendingData = data;
			return;
		}

		this._view.webview.postMessage(data);
	}

	//called when a view first becomes visible
	resolveWebviewView(webviewView: WebviewView): void | Thenable<void> {
		webviewView.webview.options = {
			enableScripts: true,
			localResourceRoots: [this.extensionPath],
		};
		webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);
		this._view = webviewView;
		this.activateMessageListener();
		if(this._pendingData !== null) {
			this._view.webview.postMessage(this._pendingData);
			this._pendingData = null;
		}
	}

	private activateMessageListener() {
		this._view.webview.onDidReceiveMessage(async (message) => {
			switch (message.action){
				//case 'SHOW_WARNING_LOG':
				//	window.showWarningMessage(message.data.message);
				//	break;
				case 'COPY_TEXT_FROM_WEBVIEW':
					await env.clipboard.writeText(message.data);
					break;
				case 'ACTION_RESPONSE_FROM_WEBVIEW':
					const activeEditor = window.activeTextEditor;
					if(!activeEditor) {
						return;
					}

					let data = message.data

					if ((data.action == 'inline-complete' || data.action == 'inline-fix') && data.payload) {
						//console.log(data)
						let start = new Position(data.start_line, 0);
						let end = new Position(data.end_line, activeEditor.document.lineAt(data.end_line).text.length);

						let range = new Range(start, end);

						activeEditor.edit((editBuilder) => {
							editBuilder.replace(range, data.payload);

							setTimeout(()=>{
								commands.executeCommand('editor.action.formatDocument');
							}, 1000)
						});
					}

					activeEditor.setDecorations(loadingDecorationType, [])
					window.setStatusBarMessage('')
					break;
				case 'SET_LOCAL_DEV_TOKEN':
					setLocalDevToken(message.data);
					break;
				case 'CHECK_CONNECTION_STATUS': {
					const isConnected = isSocketConnected();
					this._view.webview.postMessage({
						type: 'connection-status',
						connected: isConnected
					});
					break;
				}
				case 'RECONNECT_SOCKET': {
					reconnectSocket((connected) => {
						this._view?.webview.postMessage({
							type: 'connection-status',
							connected
						});
					});
					break;
				}
				default:
					break;
			}
		});
	}

	private _getHtmlForWebview(webview: Webview) {

		// Use a nonce to only allow a specific script to be run.
		// const nonce = Utils.getNonce();

		//const body = ReactDOMServer.renderToString((
		//	<LeftPanel message={"Tutorial for Left Panel Webview in VSCode extension"}></LeftPanel>
		//));

		const host = utils.host;
		const version = utils.version;

		const body = `
			<div id="error-panel" style="display: none;">
				<div style="padding: 20px; text-align: center;">
					<h2 style="color: #e74c3c; margin-bottom: 20px;">⚠️ Connection Error</h2>
					<p style="margin-bottom: 15px; line-height: 1.6;">
						Unable to connect to the JuniorIT WebUI server. Please ensure the server is running on the correct port.
					</p>
					<p style="margin-bottom: 20px; font-size: 0.9em; color: #555;">
						You can verify the server is ready by opening this URL in your web browser:
					</p>
					<div style="margin-bottom: 20px;">
						<a id="server-url" href="${host}/embedded/vscode-extension?version=${version}"
						   target="_blank"
						   style="color: #3498db; text-decoration: underline; word-break: break-all;">
							${host}/embedded/vscode-extension?version=${version}
						</a>
					</div>
					<button id="reconnect-btn" style="
						background-color: #3498db;
						color: white;
						border: none;
						padding: 10px 30px;
						font-size: 1em;
						cursor: pointer;
						border-radius: 5px;
						transition: background-color 0.3s;">
						🔄 Reconnect
					</button>
					<p style="margin-top: 15px; font-size: 0.85em; color: #777;">
						If the server is ready, click the button above to reconnect.
					</p>
				</div>
			</div>
			<iframe id="juniorit-embedded-vscode-page" src="${host}/embedded/vscode-extension?version=${version}" style="border:0;" allowfullscreen="" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>
		`;

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

						.panel-wrapper {
							display: flex;
							flex-direction: column;
							width: 100%;
						}

						.panel-info {
							font-size: 1.2rem;
							font-weight: bold;
							line-height: 2rem;
							display: flex;
							justify-content: center;
							align-items: center;
							margin: 1rem;
							text-align: center;
						}

						#error-panel {
							display: flex;
							align-items: center;
							justify-content: center;
							height: 100vh;
							width: 100%;
						}

						#reconnect-btn:hover {
							background-color: #2980b9;
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
							let connectionAttempts = 0;
							const maxAttemptsBeforeError = 3;
							const retryInterval = 1000; // 1 second for local connections

							const iframe = document.getElementById('juniorit-embedded-vscode-page');
							const errorPanel = document.getElementById('error-panel');
							const reconnectBtn = document.getElementById('reconnect-btn');

							function showError() {
								iframe.style.display = 'none';
								errorPanel.style.display = 'flex';
							}

							function hideError() {
								errorPanel.style.display = 'none';
								iframe.style.display = 'block';
								connectionAttempts = 0;
							}

							function attemptReload() {
								if (!iframeLoaded) {
									connectionAttempts++;
									if (connectionAttempts >= maxAttemptsBeforeError) {
										clearInterval(reloadIframe);
										showError();
									} else {
										iframe.src = iframe.src;
									}
								}
							}

							const reloadIframe = setInterval(attemptReload, retryInterval);

							// Reconnect button handler
							reconnectBtn.addEventListener('click', () => {
								hideError();
								connectionAttempts = 0;
								iframe.src = iframe.src;
								clearInterval(reloadIframe);
								const newReloadInterval = setInterval(() => {
									if (!iframeLoaded) {
										connectionAttempts++;
										if (connectionAttempts >= maxAttemptsBeforeError) {
											clearInterval(newReloadInterval);
											showError();
										} else {
											iframe.src = iframe.src;
										}
									}
								}, retryInterval);
							});

							const onMessage = async (event) => {
								const data = event.data;

								if(data === 'juniorit-embedded-vscode-page-ready') {
									iframe.contentWindow.postMessage('juniorit-vscode-reply', '*');
									iframeLoaded = true;
									hideError();
									clearInterval(reloadIframe);
									if(pendingData !== null) {
										iframe.contentWindow.postMessage(pendingData, '*');
										pendingData = null;
									}
									return;
								}

								// Forward connection-status response from extension to iframe
								if(data.type && data.type == 'connection-status') {
									if(iframeLoaded) {
										iframe.contentWindow.postMessage(data, '*');
									}
									return;
								}

								if(data.type && data.type == 'response') {
									vscode.postMessage({
										action: 'ACTION_RESPONSE_FROM_WEBVIEW',
										data
									});

									return;
								}

								if(data.type && data.type == 'local-dev-token') {
									vscode.postMessage({
										action: 'SET_LOCAL_DEV_TOKEN',
										data: data.token
									});
									return;
								}

								if(data.type && data.type == 'check-connection') {
									vscode.postMessage({
										action: 'CHECK_CONNECTION_STATUS'
									});
									return;
								}

								if(data.type && data.type == 'reconnect-socket') {
									vscode.postMessage({
										action: 'RECONNECT_SOCKET'
									});
									return;
								}

								if(data.key === 'c') {

									if(data.selectedText) {
										vscode.postMessage({
											action: 'COPY_TEXT_FROM_WEBVIEW',
											data:data.selectedText}
										);
									}

									return;
								} else if(data.key === 'v') {
									let text =  await navigator.clipboard.readText();
									if(text) {
										iframe.contentWindow.postMessage({
											sender:"vscode-juniorit",
											pasteText: text,
											targetFrame: data.frameId
										}, '*');
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
}
