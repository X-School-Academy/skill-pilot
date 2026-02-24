# Sparse Checkout Import Reference

## Goal

Import one skill folder from a large remote repository without cloning everything.

## Manual equivalent commands

```bash
tmp_dir="$(mktemp -d .skillpilot/temp/skill-import-XXXXXX)"
repo_dir="$tmp_dir/repo"
git clone --filter=blob:none --no-checkout "<repo-url>" "$repo_dir"
cd "$repo_dir"
git sparse-checkout init --cone
git sparse-checkout set "<remote-skill-folder>"
git checkout
```

Then copy:

```bash
cp -R "$repo_dir/<remote-skill-folder>" "<destination-parent>/"
```

Optional destination default:

- `core/skills/third-party`

## License file handling checklist

After copy, check these names in order:

- `LICENSE`
- `LICENCE`
- `LICENSE.md`
- `LICENCE.md`
- `COPYING`
- `COPYING.md`

Flow:

1. If one exists inside imported skill folder, keep it there.
2. Else if one exists at cloned repository root, copy it to imported skill folder as `LICENSE`.
3. Else create imported skill `LICENSE` with:
   - `unknown licence`
   - `source: <repo-url>`

## Notes

- Ensure `.skillpilot/temp/` exists before `mktemp`.
- Use an exact folder path from the remote repository root.
- If destination already exists, stop and ask whether to replace or import to another folder.
