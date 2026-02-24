update webui

Left nav menu

New Terminal -> rename to `New Session`, point to route `/`, in any page, click `New Session`, should redirect to `/`, in `/` route, gray and disable this menu item

in `/` screen, click button 'Start', the main area should show the terminal window `/terminal`, using iframe with parameter ai agent, and prompt

in the backend, should run the ai agent cli with prompt in tmux mode with session name `webui-live-xxx`

When/only to close this tmux session
1. close by button by user
2. close the browser window after 10 seconds - there should be a heartbeat with the backend in any available way or create a new one
3. before kill the backend core engine
4. if nav to other screen, just release the `/terminal` iframe window resource and close the related websocket

Terminals -> rename to `Live Sessions`, point to route `/terminals`

Use existing api `/api/terminal/tmux/sessions` to get any tmux session created by webui, and `/api/terminal/tmux/kill` to close a live session

In page `Live Sessions`, display the live sessions with action buttons: Connect, Close

Connect: the main area should show the terminal window `/terminal` in iframe by attached to the tmux session using a new websocket
Close: close the tmux session by api `/api/terminal/tmux/kill`

if no live sessions, just show no live sessions, create one by clicking the New Session button

if click `Live Sessions`, when main area is showing the terminal, we should regard it as hide the current live session window (release resource, and close the websocket)


terminal iframe window in the main panel - there should have a padding on each side, auto zoom when window resize
