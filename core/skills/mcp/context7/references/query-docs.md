# query-docs

Retrieves and queries up-to-date documentation and code examples from Context7 for any programming library or framework.

You must call 'Resolve Context7 Library ID' tool first to obtain the exact Context7-compatible library ID required to use this tool, UNLESS the user explicitly provides a library ID in the format '/org/project' or '/org/project/version' in their query.

Workflow: call first without researchMode. If that doesn't answer the question, retry with researchMode: true. Do not call each tool more than 3 times per question

## Usage
```bash
core/bin/tool-cli request '{"server_id": "context7", "tool_name": "query-docs", "arguments": {}}'
```
**Do not use any Python helper code to invoke the `core/bin/tool-cli` command. Run as shell command with arguments directly.**

## Arguments Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "libraryId": {
      "type": "string",
      "description": "Exact Context7-compatible library ID (e.g., '/mongodb/docs', '/vercel/next.js', '/supabase/supabase', '/vercel/next.js/v14.3.0-canary.87') retrieved from 'resolve-library-id' or directly from user query in the format '/org/project' or '/org/project/version'."
    },
    "query": {
      "type": "string",
      "description": "The question or task you need help with. Be specific and include relevant details. Good: 'How to set up authentication with JWT in Express.js' or 'React useEffect cleanup function examples'. Bad: 'auth' or 'hooks'. The query is sent to the Context7 API for processing. Do not include any sensitive or confidential information such as API keys, passwords, credentials, personal data, or proprietary code in your query."
    },
    "researchMode": {
      "description": "Retry the query with deep research: spins up sandboxed agents that read the actual source repos and runs a live web search, then synthesizes a fresh answer. Set true on retry if you weren't satisfied with the first answer and want a more thorough one. Requires an API key \u2014 you can get one free at https://context7.com.",
      "type": "boolean"
    }
  },
  "required": [
    "libraryId",
    "query"
  ]
}
```
