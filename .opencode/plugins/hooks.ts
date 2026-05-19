export const Hooks = async ({ project, client, $, directory, worktree }) => {
  const cwd = directory ?? worktree ?? project?.worktree ?? process.cwd()
  const run = async (hookName: string) => {
    try {
      await $`core/bin/hook ${hookName}`.cwd(cwd)
    } catch (err) {
      console.error(`[hooks] ${hookName} failed:`, err)
    }
  }

  return {
    event: async ({ event }) => {
      switch (event.type) {
        case "session.created":
          await run("session_start")
          break
        case "session.deleted":
          await run("session_end")
          break
      }
    },
  }
}
