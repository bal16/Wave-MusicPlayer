# Style Guide — Wave Music Player

> Cross-reference: [Architecture](architecture.md) · [PRD](PRD.md)
> Owner in code: `views/theme.py` — raw values live only there.
> New UI code must import tokens from `views/theme.py`, never hardcode hex/font tuples.
> Legacy modules (`view.py`, `components/*`, `config.py`) migrate gradually; `config.py`
> currently re-exports theme values for compat.

## 1. Tokens

| Token group | Values |
| ----------- | ------ |
| `Colors.bg_app` / `bg_sidebar` / `bg_player` | `#121212` / `#181818` / `#0f0f0f` |
| `Colors.surface` / `Colors.hover` | `#1e1e1e` / `#333333` |
| `Colors.accent` | `#2ccae6` (logo, active states) |
| `Colors.text_primary` / `text_muted` | `white` / `grey` |
| `Colors.progress_track` / `progress_fill` | `#333333` / `white` |
| `Fonts.sans` | `Arial` |
| `Fonts.header` / `row_title` / `menu` / `body` | bold 20 / bold 14 / 16 / 14 |
| `Spacing` paddings | s=5, m=10, l=20, xl=40 |
| Window | sidebar 200 wide, player 90 tall, main `1000x600` |

Helpers: `format_duration(sec) -> "m:ss"` (DB keeps float seconds),
`apply_dark_mode()` (call once at startup), cached icons in `utils/icons.py`.

## 2. Rules

1. Dark Spotify-like theme only. No gradients, no heavy shadows.
2. Buttons: transparent `fg_color`, `hover_color` = `hover` token.
3. Duration formatting never in SQL/service — view layer only.
4. No new hex literals or font tuples outside `views/theme.py`.
5. Icons via `utils/icons.load_icon(name, w, h)` (cached); no direct `Image.open` in views.
6. Playlist rows reuse song-row styling (transparent frame, muted meta text).
   Modal dialogs (`components/dialogs.py`) are `transient` + `grab_set` +
   `wait_window`, returning values (never callbacks into services).

## 3. Out of scope (post-MVP)

Album-art blur background, equalizer UI, light mode, drag-reorder affordances.
