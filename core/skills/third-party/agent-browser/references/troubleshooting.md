# Troubleshooting

Use this reference when `core/bin/agent-browser` fails during initialization, connection, navigation, interaction, or snapshot capture.

## Common Issues

- Never use `--remote-debugging-port` for setup or troubleshooting. Use Chrome's remote debugging page and `core/bin/agent-browser` connection options instead.
- `pnpm` not found: install pnpm first, then retry.
- Chrome not detected: ensure Chrome is running with remote debugging enabled.
- CDP WebSocket URL not reachable: check that the chrome-devtool-proxy binary is running on the host and firewall allows the connection.
- `Auto-launch failed: CDP WebSocket connect failed: IO error: Connection refused (os error 61)`: run `core/bin/agent-browser close` to close any existing browser session, then retry the original command.
- `snapshot` returns empty: the page may still be loading; run `core/bin/agent-browser wait --load networkidle` before snapshot.
