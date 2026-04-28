---
name: dart
description: "Dart and Flutter development tools: analyze, test, format, pub commands, hot reload, widget tree inspection, symbol resolution, and workspace management."
---

## Tools

Select the tool that matches the task. Read its reference file only when you are ready to invoke it.

- **add_roots** — Adds one or more project roots. Tools are only allowed to run under these roots, so you must call this function before passing any roots to any other tools. ([details](references/add_roots.md))
- **analyze_files** — Analyzes the entire project for errors. ([details](references/analyze_files.md))
- **connect_dart_tooling_daemon** — Connects to the Dart Tooling Daemon. You should get the uri either from available tools or the user, do not just make up a random URI to pass. When asking the user for the uri, you should suggest the "Copy DTD Uri to clipboard" action. When reconnecting after losing a connection, always request a new uri first. ([details](references/connect_dart_tooling_daemon.md))
- **create_project** — Creates a new Dart or Flutter project. ([details](references/create_project.md))
- **dart_fix** — Runs `dart fix --apply` for the given project roots. ([details](references/dart_fix.md))
- **dart_format** — Runs `dart format .` for the given project roots. ([details](references/dart_format.md))
- **get_active_location** — Retrieves the current active location (e.g., cursor position) in the connected editor. Requires "connect_dart_tooling_daemon" to be successfully called first. ([details](references/get_active_location.md))
- **get_runtime_errors** — Retrieves the most recent runtime errors that have occurred in the active Dart or Flutter application. Requires "connect_dart_tooling_daemon" to be successfully called first. ([details](references/get_runtime_errors.md))
- **get_selected_widget** — Retrieves the selected widget from the active Flutter application. Requires "connect_dart_tooling_daemon" to be successfully called first. ([details](references/get_selected_widget.md))
- **get_widget_tree** — Retrieves the widget tree from the active Flutter application. Requires "connect_dart_tooling_daemon" to be successfully called first. ([details](references/get_widget_tree.md))
- **hot_reload** — Performs a hot reload of the active Flutter application. This is to apply the latest code changes to the running application. Requires "connect_dart_tooling_daemon" to be successfully called first. ([details](references/hot_reload.md))
- **hover** — Get hover information at a given cursor position in a file. This can include documentation, type information, etc for the text at that position. ([details](references/hover.md))
- **pub** — Runs a pub command for the given project roots, like `dart pub get` or `flutter pub add`. ([details](references/pub.md))
- **pub_dev_search** — Searches pub.dev for packages relevant to a given search query. The response will describe each result with its download count, package description, topics, license, and publisher. ([details](references/pub_dev_search.md))
- **remove_roots** — Removes one or more project roots previously added via the add_roots tool. ([details](references/remove_roots.md))
- **resolve_workspace_symbol** — Look up a symbol or symbols in all workspaces by name. Can be used to validate that a symbol exists or discover small spelling mistakes, since the search is fuzzy. ([details](references/resolve_workspace_symbol.md))
- **run_tests** — Run Dart or Flutter tests with an agent centric UX. ALWAYS use instead of `dart test` or `flutter test` shell commands. ([details](references/run_tests.md))
- **set_widget_selection_mode** — Enables or disables widget selection mode in the active Flutter application. Requires "connect_dart_tooling_daemon" to be successfully called first. ([details](references/set_widget_selection_mode.md))
- **signature_help** — Get signature help for an API being used at a given cursor position in a file. ([details](references/signature_help.md))
