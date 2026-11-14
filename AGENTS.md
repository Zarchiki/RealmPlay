# Agent Collaboration Rules

Several agents work in this repository at the same time.

1. **Before any patch:** read `PATCH_NOTES.md` (newest entry first) and check `git status` and file timestamps for the files you plan to edit. Do not overwrite files that changed since you last read them.
2. **After any patch:** add a new entry at the top of `PATCH_NOTES.md` with: what changed, files touched, rules or warnings for other agents, verification done, and pending next steps.
3. Keep existing notes intact; only add new entries.
4. Prefer new modules over large edits to shared monoliths (`server.py`). Frontend logic lives in `static/js/app_main.js`, not inline in `static/index.html`.

