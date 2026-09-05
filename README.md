# Wave Music Player

Local music player for your own files. No accounts, no streaming, no network calls — pick a folder, and it indexes your tracks into a local SQLite library.

The UI is a dark CustomTkinter window: a sidebar for navigation, a song list in the middle, and a player bar at the bottom. Metadata comes from TinyTag, storage from SQLModel/SQLite, logs from loguru.

## Status

Honest snapshot — this is a rewrite in progress:

- [x] Add folder → scans `.flac` files, reads tags, stores them in `database.db` (skips duplicates)
- [ ] List library → the song list still shows placeholder rows, real DB rendering is next
- [ ] Playback → the player bar is UI only; no audio backend is wired yet

See `TODO.md` for the checklist and `docs/PRD.md` for the full plan.

## Run it

You need Python 3.11+ and a display (this is a desktop GUI, it won't start over plain SSH).

```bash
uv sync          # create .venv and install everything from uv.lock
uv run poe dev   # start the app with debug logging
```

`uv run poe start` runs it with default logging.

## Common tasks

All tasks live in `pyproject.toml` (`[tool.poe.tasks]`), run them with `uv run poe <task>`:

| Task           | What it does                                              |
|----------------|-----------------------------------------------------------|
| `start`        | Run the app                                               |
| `dev`          | Run the app with debug logging                            |
| `check`        | Byte-compile all modules (works headless)                 |
| `lint`         | `ruff check` on new/tooling files                         |
| `format`       | `ruff format` on new/tooling files                        |
| `format-check` | Fail if those files aren't formatted                      |
| `test`         | `pytest`                                                  |
| `quality`      | `check` → `lint` → `format-check` → `test`                |
| `build`        | Onedir bundle into `dist/Wave/` via `wave.spec`           |
| `dist`         | Single-file binary into `dist/Wave`                       |
| `clean`        | Remove `build/` and `dist/`                               |

Add a dependency with `uv add <package>` (runtime) or `uv add --group dev <package>` (tooling). The lockfile is the source of truth — there is no `requirements.txt`.

## Layout

```txt
main.py               # entry point: logging setup, creates View + Controller
view.py               # CTk root window, splash screen, layout grid
controller.py         # folder scan + TinyTag parsing + DB writes
config.py             # colors, fonts, icon handles
models/               # SQLModel tables (Song, Playlist) + engine
components/           # Sidebar, MainContent, PlayerBar, SplashScreen
utils/                # IconManager (bundle-aware asset paths)
tests/                # pytest suite (schema + icon paths; GUI is manual)
docs/                 # PRD, architecture, DB schema
__old/                # legacy Tkinter/pygame version, kept for reference
```

`docs/` has three cross-linked files: `PRD.md` (scope and roadmap), `architecture.md` (current vs target design, audio backend decision), `schema.md` (tables and query rules).

## Build a binary

```bash
uv run poe build   # dist/Wave/ folder bundle, faster to debug
uv run poe dist    # single dist/Wave executable, for handing to someone
```

Icons are bundled from `assets/icons`; the database and logs stay outside the bundle next to where you run it.

## Notes

- `database.db` and `logs/` are local state, git-ignored by design.
- Lint/format scope is deliberately narrow (`tests/`, `utils/icon_manager.py`) until the in-progress UI files stabilize — see the tooling commit for context.
