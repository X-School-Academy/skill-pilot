# Category: Browser Tasks — Types

Browser-driven automations using `agent-browser`. The runtime agent flow must handle remote-site safety through the relevant browser skill behavior, including prompt-injection risk warnings before navigating to non-trusted sites. Do not put those generic warnings into user-authored `requirements.md`, `update.md`, or `issues.md` files. Use headed mode for local development.

Primary audiences: AI agent learners, business owners.

## Types

### BR1. Search and extract
- Open a site, run a search, and return structured results.
- Examples: scrape latest GitHub releases of a repo; fetch a stock quote; pull a hotel-room list.

### BR2. Form fill and submit
- Fill out a multi-step form, take screenshots at each step, and submit.
- Examples: token / API-key signup flows, contact-form submissions, account creation in a sandbox.

### BR3. Web console operations
- Drive an admin web console (AWS, Cloudflare, Vercel) through the UI when no CLI exists.
- Always paired with a security-warning intro.

### BR4. Login + scoped action
- Log in via stored credentials and perform one scoped action (post, comment, like, archive).
- Examples: post a draft to a CMS, archive read emails, label issues in a tracker.

### BR5. Browser test recording
- Record a user flow and produce a Playwright / Puppeteer test from the trace.

### BR6. Visual diff / regression
- Screenshot a page now vs. a baseline and diff them.
- Examples: marketing-page change detection, post-deploy smoke checks.
