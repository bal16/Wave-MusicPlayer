# Wave Music Player

Local music player for your own files. No accounts, no streaming, no network calls — pick a folder, and it indexes your tracks into a local SQLite library.

The UI is a dark CustomTkinter window: a sidebar for navigation, a song list in the middle, and a player bar at the bottom. Metadata comes from TinyTag, storage from SQLModel/SQLite, logs from loguru.

## Status

All MVP phases are done and covered by 75 tests plus a manual smoke checklist:

- [x] Add folder → recursive `.mp3`/`.flac` scan on a worker thread with a progress dialog, tags stored in `data/app.db` (skips duplicates by path)
- [x] List library → rendered from the DB, auto-refreshes on change, favorite toggle via row-level `update_song()` fast-path (ADR-0001), search deferred
- [x] Playback → VLC primary with miniaudio fallback (auto-detected, overridable via `WAVE_AUDIO_BACKEND`); full-library queue with wrap-around; seek, volume, mute; embedded cover art with bundled fallback
- [x] Playlist → create/rename/delete, add songs from any row, remove without touching the library; playback queues the open view
- [x] Polish → threaded scan, lazy icons, no destroy-recreate refreshes, close always terminates

Playback smoke cases 1–8 pass via the miniaudio fallback; the VLC path needs a libvlc 3 machine and is still unverified. See `docs/TODO.md` for the checklist and `docs/` for the full plan.

## Run it

You need Python 3.11+ and a display (this is a desktop GUI, it won't start over plain SSH). No system audio dependency for the fallback path; the VLC backend needs a VLC install.

```bash
uv sync          # create .venv and install everything from uv.lock
uv run poe dev   # start the app with debug logging
```

`uv run poe start` runs it with default logging. Force an audio backend with `WAVE_AUDIO_BACKEND=vlc|miniaudio`.

## Common tasks

All tasks live in `pyproject.toml` (`[tool.poe.tasks]`), run them with `uv run poe <task>`:

| Task           | What it does                                              |
|----------------|-----------------------------------------------------------|
| `start`        | Run the app                                               |
| `dev`          | Run the app with debug logging                            |
| `check`        | Byte-compile all modules (works headless)                 |
| `lint`         | `ruff check` on the whole repo                            |
| `format`       | `ruff format` on the whole repo                           |
| `format-check` | Fail if any file isn't formatted                          |
| `test`         | `pytest`                                                  |
| `quality`      | `check` → `lint` → `format-check` → `test`                |
| `build`        | Onedir bundle into `dist/Wave/` via `wave.spec`           |
| `dist`         | Single-file binary into `dist/Wave`                       |
| `clean`        | Remove `build/` and `dist/`                               |

Add a dependency with `uv add <package>` (runtime) or `uv add --group dev <package>` (tooling). The lockfile is the source of truth — there is no `requirements.txt`.

## Layout

```txt
main.py               # entry point: logging, DB init, container wiring
view.py               # CTk root window, splash screen, layout grid
app/container.py      # composition root: engine → repo → service → controller
controllers/          # thin MainController: handlers, view routing, tickers
domain/               # Song/Playlist entities + repository/backend ABCs
infrastructure/       # SQLModel, TinyTag tagger, VLC/miniaudio backends
services/             # library, player (queue + auto-next), playlist logic
components/           # Sidebar, MainContent, PlayerBar, PlaylistOverview, dialogs
views/theme.py        # design tokens (colors, fonts, spacing)
utils/icons.py        # cached, lazy icon loader (assets/icons)
tests/                # pytest suite, GUI-free; manual smoke in docs/smoke-fase2.md
docs/                 # PRD, architecture, DB schema, style guide, smoke list, TODO
__old/                # legacy Tkinter/pygame OOP project, kept for reference (see __old/README.md)
```

`docs/` holds the PRD, architecture, DB schema, style guide, smoke list, TODO, plus `adr/` (decision records, e.g. ADR-0001 row-level song update).

## Build a binary

```bash
uv run poe build   # dist/Wave/ folder bundle, faster to debug
uv run poe dist    # single dist/Wave executable, for handing to someone
```

Icons are bundled from `assets/icons`; the database (`data/app.db`) and logs stay outside the bundle next to where you run it.

## Notes

- `data/` and `logs/` are local state, git-ignored by design.
- One ruff scope for the editor and the gate (`ruff check .` / `ruff format .`, config in `pyproject.toml`); `.vscode/settings.json` points the editor at the project's own ruff, `.markdownlint.yaml` covers docs.
