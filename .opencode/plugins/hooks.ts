export const Hooks = async ({ project, directory, worktree }) => {
  const cwd = directory ?? worktree ?? project?.worktree ?? process.cwd()
  const runHook = async (hookName: string, agent: string, payload: Record<string, unknown>) => {
    const proc = Bun.spawn(["core/bin/hook", hookName, "--agent", agent], {
      cwd,
      stdin: "pipe",
      stdout: "pipe",
      stderr: "pipe",
    })
    proc.stdin.write(JSON.stringify(payload))
    proc.stdin.end()
    const stdout = await new Response(proc.stdout).text()
    const stderr = await new Response(proc.stderr).text()
    const code = await proc.exited
    if (code !== 0) {
      throw new Error(stderr || `${hookName} failed`)
    }
    return stdout.trim() ? JSON.parse(stdout) : {}
  }

  const run = async (hookName: string, payload: Record<string, unknown>) => {
    try {
      await runHook(hookName, "opencode", payload)
    } catch (err) {
      console.error(`[hooks] ${hookName} failed:`, err)
    }
  }

  return {
    "tool.execute.before": async (input, output) => {
      const result = await runHook("env_guard", "opencode", {
        tool_name: input.tool,
        tool_input: output.args,
        cwd,
      })
      if (result?.decision === "deny") {
        throw new Error(result.reason ?? "Reading .env files is blocked")
      }
    },
    event: async ({ event }) => {
      const sessionID = event?.properties?.sessionID ?? event?.sessionID ?? event?.session_id ?? event?.sessionId
      switch (event.type) {
        case "session.created":
          await run("session_start", { event })
          break
        case "message.updated": {
          const role = event?.message?.role ?? event?.role
          if (role === "user") {
            await run("user_prompt", { event })
          } else if (role === "assistant" || role === "agent" || role === "model") {
            await run("agent_stop", { event })
          }
          break
        }
        case "session.deleted":
          await run("session_end", { event })
          break
        default:
          if (sessionID) {
            await run("opencode_event", { event })
          }
          break
      }
    },
  }
}
