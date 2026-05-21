export const Hooks = async ({ project, directory, worktree }) => {
  const cwd = directory ?? worktree ?? project?.worktree ?? process.cwd()
  const run = async (hookName: string, payload: Record<string, unknown>) => {
    try {
      const proc = Bun.spawn(["core/bin/hook", hookName, "--agent", "opencode"], {
        cwd,
        stdin: "pipe",
        stdout: "pipe",
        stderr: "pipe",
      })
      proc.stdin.write(JSON.stringify(payload))
      proc.stdin.end()
      await proc.exited
    } catch (err) {
      console.error(`[hooks] ${hookName} failed:`, err)
    }
  }

  return {
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
