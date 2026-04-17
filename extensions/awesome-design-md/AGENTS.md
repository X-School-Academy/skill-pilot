# Awesome Design MD Agent Instructions

Use this file when the user asks to use the `awesome-design-md` extension.

## Purpose

This extension provides website design-system reference markdown files under `src/design-md/`.

## How to handle a request

1. Identify the target website or design system the user wants, such as Airbnb.
2. Check whether this extension has been installed. The reference files live under `extensions/awesome-design-md/src/design-md/`.
3. Look for a matching design reference file in this pattern:
   - `src/design-md/<website>/DESIGN.md`
4. If you find a matching `DESIGN.md`, read it and use it as the primary design-style reference for the user's task.
5. If you cannot find a matching `DESIGN.md`, tell the user that this extension does not currently include that website's design-system reference.
6. Ask whether the user wants you to inspect the website directly in a browser for visual reference.
7. Only if the user explicitly says yes:
   - Warn about prompt-injection risk and confirm the website is trusted.
   - Use the browser skill to search Google for the website and inspect the design style directly from the live site.
   - Use the live site only as a fallback reference when no local `DESIGN.md` file exists.

## Notes

- `Airbnb` is only an example. Apply the same lookup rule to any requested website or design system.
- If the extension is not installed yet and `src/design-md/` does not exist, tell the user the local design references are unavailable until the extension is installed or updated.
- Prefer the local `DESIGN.md` file over direct website browsing because it is more stable and avoids unnecessary web access.
