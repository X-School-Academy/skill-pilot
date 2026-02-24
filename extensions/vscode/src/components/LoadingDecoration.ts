import * as vscode from "vscode";

const loadingDecorationType = vscode.window.createTextEditorDecorationType({
    after: {
        contentText: 'Loading...',
        margin: '0 0 0 1em',
        color: new vscode.ThemeColor('terminal.ansiYellow')
    }
});

export default loadingDecorationType