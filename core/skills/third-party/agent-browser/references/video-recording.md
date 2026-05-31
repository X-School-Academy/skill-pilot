# Recording Demos

Produce polished, shareable demo videos with a visible cursor and minimal dead time.

## Key Principles

- **Minimize dead time** — chain commands with `&&` so tool-call overhead stays out of the video.
- **Visible cursor** — headless Playwright has no cursor; inject a fake one via DOM.
- **One chain per page** — navigation destroys the DOM cursor, so re-inject after every page change.
- **No `sleep` calls** — tool execution provides enough natural pacing.

## Step-by-step

### 1. Set up the page BEFORE recording

Navigate and snapshot **before** `record start`. Any time after recording starts is in the video.

```bash
core/bin/agent-browser open <url>
```
```bash
core/bin/agent-browser snapshot -i
```

Review the snapshot to identify element refs (`@e1`, `@e2`, …) and plan the interaction sequence.

### 2. Find element coordinates for mouse moves

Use `getBoundingClientRect()` to get the (x, y) center of each target element. Do this **before** recording starts so the lookup doesn't appear in the video.

```bash
core/bin/agent-browser eval "(() => {
  const el = document.querySelector('<selector>');
  const r = el.getBoundingClientRect();
  return JSON.stringify({ x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2) });
})()"
```

### 3. Inject a visible cursor

Headless Playwright doesn't render a cursor. Inject a DOM element that tracks mouse events:

```bash
core/bin/agent-browser eval "(() => {
  const c = document.createElement('div');
  c.style.cssText = 'width:20px;height:20px;border-radius:50%;background:rgba(255,50,50,0.85);position:fixed;top:290px;left:390px;z-index:999999;pointer-events:none;transition:top 0.15s ease,left 0.15s ease;box-shadow:0 0 8px rgba(255,50,50,0.5);';
  document.body.appendChild(c);
  document.addEventListener('mousemove', e => {
    c.style.top=(e.clientY-10)+'px';
    c.style.left=(e.clientX-10)+'px';
  });
})(); 'ok'"
```

**Re-inject after every navigation** — page transitions destroy the DOM element.

### 4. Chain all commands with `&&`

Every separate tool call adds seconds of dead time. Chain everything into as few bash calls as possible:

```bash
core/bin/agent-browser record start ./demo.webm && core/bin/agent-browser eval "<inject cursor>" && core/bin/agent-browser mouse move 400 300 && core/bin/agent-browser click @e1 && core/bin/agent-browser mouse move 600 200 && core/bin/agent-browser click @e2 && core/bin/agent-browser record stop
```

### 5. Use `mouse move` before every click

Move the cursor to the target first so viewers can follow the action:

```bash
core/bin/agent-browser mouse move 623 52 && core/bin/agent-browser click @e5
```

### 6. No `sleep` calls

Every millisecond counts. Tool execution itself provides enough natural pacing. Drop all `sleep` and `wait` calls entirely.

### 7. One chain per page

Since the cursor needs re-injection after navigation, structure as one `&&` chain per page. The recording persists across chains — only stop it in the final chain.

```bash
# Chain 1: first page → click navigates away
core/bin/agent-browser record start ./demo.webm && core/bin/agent-browser eval "<inject cursor>" && core/bin/agent-browser mouse move 400 300 && core/bin/agent-browser click @e5
```

```bash
# Chain 2: new page → finish
core/bin/agent-browser eval "<inject cursor>" && core/bin/agent-browser mouse move 200 150 && core/bin/agent-browser click @e3 && core/bin/agent-browser scroll down 200 && core/bin/agent-browser record stop
```

## Common Mistakes

- **Recording before the page is ready** — navigate and snapshot first.
- **Forgetting to re-inject the cursor after navigation** — the DOM element is gone.
- **Separate tool calls instead of `&&` chains** — adds seconds of blank screen.
- **Using `sleep` or `wait`** — unnecessary; tool execution provides natural pacing.
- **Clicking without `mouse move`** — clicks without visible cursor movement look jarring.