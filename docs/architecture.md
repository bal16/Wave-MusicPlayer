# Architecture — Wave Music Player

> Cross-reference: [PRD](PRD.md) · [Schema](schema.md)

## 1. Arsitektur saat ini (hasil audit)

Niatnya MVC, praktiknya **View-heavy + Fat Controller + Model ganda**:

```txt
main.py → View(ctk.CTk) ──creates──▶ Sidebar / MainContent / PlayerBar / SplashScreen
        → MainController(engine, view)  ← View.set_controller()
              └── add_music_from_folder(): listdir + TinyTag + mapping + dedup + commit (semua di 1 method)
models/schema.py + models/database.py   ← model asli (bagus)
model.py (CounterModel — template mati, tidak dipakai)
```

Masalah utama (dengan lokasi):

1. **Konstruktor ber-side-effect:** `controller.py:22` menjalankan `view.mainloop()` di `__init__` → tidak testable.
2. **Coupling sirkular:** `Sidebar.py:52` memanggil `self.master.controller.add_music_from_folder()` langsung. Batalkan dialog (`""`) → `os.listdir("")` crash. Tambah lagu → UI tidak refresh (tanpa event).
3. **View salah tanggung jawab (sebagian diperbaiki Fase 0–1):** `init_db()` sudah pindah ke `main.py` (splash hanya visual); `refresh_song_list()` tinggal sebagai shim deprecated ke `show_songs()`; `change_main_content()` masih memakai pola `destroy()` + bikin frame baru (hapus di Fase 4).
4. **Component mati:** `MainContent` 9 lagu dummy tanpa callback; `PlayerBar` tombol/slider tanpa command + `btn_volume` didefinisikan 2x (baris 70 & 76); belum ada library audio di `pyproject.toml`.
5. **Config rapuh:** `config.py:12-15` `icons.load()` saat import; `models/database.py:4` path DB relatif CWD + engine global + `check_same_thread=False`.
6. **Filter sempit:** cuma `.flac`, non-rekursif (`os.listdir`), blocking UI.

## 2. Arsitektur target (berlapis, dependency satu arah)

```txt
views --callback--> controllers --call--> services --call--> domain/interfaces
  <--update--         <--event--              ▲ infrastructure implements interfaces
```

Target folder (migrasi bertahap, UI belakangan — sesuai PRD Fase 0):

> Status Fase 0 ✅: `domain/`, `infrastructure/{db,models,song_repository,audio_tagger}.py`,
> `services/library_service.py`, `app/container.py`, `controllers/main_controller.py`,
> `views/theme.py`, `utils/icons.py` sudah ada. `models/` dan `controller.py` tinggal
> sebagai shim re-export; `model.py` dihapus. `views/` baru berisi `theme.py` —
> `main_view/sidebar/song_list/player_bar` dijadwalkan Fase 1–2. Aturan gaya di
> [Style Guide](style-guide.md).

```txt
main.py               # bootstrap saja
config.py             # konstanta murni, tanpa load icon saat import
app/container.py      # wiring: engine → repo → service → view → controller
domain/entities.py    # Song, Playlist (dataclass, tanpa SQLModel/Tk)
domain/interfaces.py  # SongRepository (ABC), PlayerBackend (ABC), EventBus
infrastructure/db.py          # engine + init_db + session factory (path absolut)
infrastructure/models.py      # SQLModel (pindahan models/schema.py) — lihat schema.md
infrastructure/song_repository.py  # SQLModel implementation
infrastructure/audio_tagger.py     # bungkus TinyTag: path → SongDraft
infrastructure/player_vlc.py       # PlayerBackend via python-vlc
services/library_service.py   # scan_folder(), list_songs(), toggle_favorite()
services/player_service.py    # play/pause/next/seek/volume + state + listener
controllers/main_controller.py# tipis: handle_* saja, run() gantikan mainloop di __init__
views/main_view.py + splash.py + sidebar.py + song_list.py + player_bar.py
utils/icons.py + utils/event_bus.py
```

Aturan:

- `views` **tidak boleh** import controller/service/repo. Hanya expose `on_add_folder`, `on_select`, `on_play`, … bertipe `Callable`.
- `controllers` pegang `service + view`, **bukan** `Engine`.
- `services` pegang `interface`, bukan SQLModel langsung → bisa di-test dengan repo fake.
- `infrastructure` satu-satunya layer yang tahu SQLModel/VLC/TinyTag.

## 3. Hubungan antar class

```mermaid
classDiagram
  class MainView {
    +set_controller()
    +show_songs(songs)
    +show_track(song)
    +set_progress(sec, total)
  }
  class Sidebar {
    +on_add_folder: Callable
    +on_navigate: Callable
  }
  class SongList {
    +set_songs(songs)
    +on_select: Callable
    +on_favorite: Callable
  }
  class PlayerBar {
    +set_track(song)
    +on_play, on_next, on_seek, on_volume: Callable
  }
  class MainController {
    +run()
    +handle_add_folder(path)
    +handle_select_song(id)
    +handle_play_pause()
  }
  class LibraryService {
    +scan_folder(path) : int
    +list_songs() : list~Song~
  }
  class PlayerService {
    +play(song), pause(), seek(), set_volume()
    +subscribe(listener)
  }
  class SongRepository {
    <<ABC>>
    +add_all() +list_all() +get_by_id()
  }
  class SqlSongRepository {
  }
  class PlayerBackend {
    <<ABC>>
  }

  MainView *-- Sidebar
  MainView *-- SongList
  MainView *-- PlayerBar
  MainController --> MainView
  MainController --> LibraryService
  MainController --> PlayerService
  LibraryService --> SongRepository
  SqlSongRepository ..|> SongRepository
  PlayerService --> PlayerBackend
```

Wiring di `app/container.py` (pseudocode):

```python
engine = create_engine(abs_db_url)
repo = SqlSongRepository(engine)
library = LibraryService(repo, tagger=AudioTagger())
player = PlayerService(backend=VlcBackend())
view = MainView()                       # tanpa init_db di dalamnya
controller = MainController(view, library, player)
view.bind(on_add_folder=controller.handle_add_folder, ...)
controller.run()
```

## 4. Alur use-case

- **Add (PRD F1):** `Sidebar --on_add_folder--> Controller.handle_add_folder --scan (thread)--> LibraryService --publish library_changed--> EventBus --show_songs--> SongList`. Menggantikan `destroy()`-recreate.
- **List (PRD F2):** `Controller.handle_show_music --list_songs--> LibraryService --list_all--> Repo --> SongList.set_songs()`. Sumber kebenaran = tabel `song` di [Schema §2](schema.md#2-tabel).
- **Play (PRD F3):** `SongList --on_select(id)--> Controller --get_by_id--> Repo --play--> PlayerService --set_track/set_progress--> PlayerBar`. Posisi slider via `after(1000)`, event `media_end` → auto-next.

Aturan threading: TinyTag + VLC callback **tidak boleh** menyentuh widget langsung; selalu lewat `view.after(0, ...)` atau EventBus.

## 5. Backend audio: python-vlc vs alternatif

Jawaban atas pertanyaan: **ya, `python-vlc` pilihan yang tepat sebagai primer — tapi jangan di-hardcode, bungkus di balik `PlayerBackend` ABC + sediakan fallback tanpa dependensi sistem.**

| Kriteria                           | python-vlc ✅ primer                                           | pygame.mixer (dipakai `__old/`)     | just_playback / miniaudio (fallback)          |
| ---------------------------------- | -------------------------------------------------------------- | ----------------------------------- | --------------------------------------------- |
| FLAC + MP3 + OGG + M4A             | Ya, penuh                                                      | FLAC/seek lemah, `get_pos` kasar    | Ya (miniaudio native)                         |
| Seek akurat + durasi + event habis | Ya (`set_time`, `MediaPlayerEndReached`)                       | Tidak andal                         | Ya, cukup                                     |
| Install                            | `pip install python-vlc` **+ VLC desktop terinstall** (libvlc) | `pip` saja                          | `pip` saja                                    |
| Risiko                             | Path libvlc di Windows/Linux; user tanpa VLC = bisu            | Cocok untuk prototype, mentok di F3 | Fitur (queue, equalizer) lebih tipis dari VLC |
| Kecocokan                          | Kebutuhan PRD F3 (seek ±1 dtk, auto-next)                      | Nostalgia `__old/`, tidak cukup     | Cadangan saat VLC absen                       |

Rekomendasi konkret:

1. Definisikan `domain/interfaces.py::PlayerBackend` (`load/play/pause/seek/set_volume/get_pos/on_end`).
2. Implementasi pertama `infrastructure/player_vlc.py`. Di `container.py`, deteksi libvlc saat startup: kalau gagal, fallback ke `player_miniaudio.py` + log warning + banner di UI ("VLC tidak ditemukan, mode kompatibilitas").
3. Tambahkan ke `pyproject.toml` via `uv add`: `python-vlc` (wajib) + `miniaudio` atau `just_playback` (fallback). Jangan bawa `pygame` ke versi baru kecuali untuk transisi.
4. `PlayerService` tidak tahu VLC; ia hanya tahu ABC → ganti backend tanpa ubah UI/controller.

## 6. Langkah migrasi (tidak merusak yang jalan)

1. ✅ SELESAI — Tambah `domain/`, `infrastructure/song_repository.py`, `services/library_service.py`, `app/container.py`; `mainloop` pindah ke `run()`; `model.py` dihapus. Plus: `views/theme.py` (design system) + `utils/icons.py` (cached loader).
2. ✅ SELESAI — `init_db` dipanggil di `main.py`; DB path absolut (`data/app.db`, di-`gitignore`); `utils/icons` cached (lazy penuh saat refactor views).
3. ⚠️ SEBAGIAN — `master.controller` diganti callback (`Sidebar.on_add_folder`, `MainContent.on_select/on_favorite`); `set_songs()` selesai. Tersisa untuk Fase 2: `PlayerBar` wiring ke `PlayerService`.
4. Hapus pola `destroy()`-recreate; ganti dengan update data + EventBus.
