function getNonce() {
    let text = '';
    const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    for (let i = 0; i < 32; i++) {
        text += possible.charAt(Math.floor(Math.random() * possible.length));
    }
    return text;
}

let isLocal = process.env.JUNIORIT_DEV_MODE == '1' ? true : false

isLocal = true

export default {
    getNonce,
    isLocal,
    host: isLocal ? 'http://localhost:3000' : 'https://juniorit.ai',
    socket: process.env.JUNIORIT_SOCKET_URL || (isLocal ? 'http://localhost:3001' : 'https://www.juniorit.ai'),
    version: '0.0.12'
};
