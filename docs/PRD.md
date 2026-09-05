# PRD — Wave Music Player (Rewrite)

> Cross-reference: [Architecture](architecture.md) · [Schema](schema.md)

## 1. Konteks (buat yang lama tidak pegang proyek ini)

Proyek ini adalah **rewrite** dari tugas akhir OOP (`__old/`: Tkinter + `pygame.mixer`, file-based tanpa DB).

Versi lama (`__old/main.py`, 806 baris, 1 class raksasa `MusicPlayer(WINDOW)`):

- Add folder (khusus `.mp3`), add files, remove one/all — langsung ke `Listbox`, tanpa persistensi.
- Play/pause/next/prev, shuffle/repeat, volume/mute, slider seek (akurasinya lemah), album art via `audio_metadata`, global variables di mana-mana.

Versi baru (root repo saat ini):

- UI `customtkinter` gelap ala Spotify: `Sidebar` + `MainContent` + `PlayerBar` + `SplashScreen`.
- Persistensi SQLite via `SQLModel` (`models/schema.py`, `models/database.py`).
- Metadata via `TinyTag` (`controller.py: add_music_from_folder`).
- Status `TODO.md`: **Add Folder → DB sudah jalan. List Songs dan Play Songs belum.**

Dokumen ini mengunci scope agar List dan Play bisa diselesaikan tanpa redesign di tengah jalan.

## 2. Visi & pengguna

**Visi:** pemutar musik lokal yang ringan, offline-first, library persisten — bukan streaming.

**Pengguna:** diri sendiri + dosen/penilai OOP (butuh demo yang jalan dalam 2 menit tanpa setup aneh).

**Non-tujuan:** streaming, sync cloud, tag editor, equalizer, mobile.

## 3. Scope MVP

### F1 — Add library (SUDAH ADA, perlu hardening)

- Pilih folder → scan rekursif → baca tag → simpan ke DB, skip duplikat by `file_path`.
- Acceptance:
  - Batalkan dialog tidak crash (bug saat ini: `os.listdir("")`).
  - Support `mp3, flac` (keputusan terkunci — `ogg, m4a, wav` backlog pasca-MVP).
  - Scan >500 file tidak freeze UI (wajib worker thread + progress).
  - Lihat detail implementasi target di [Architecture §4](architecture.md#4-alur-use-case).

### F2 — List library (BELUM)

- Baca dari DB, render di `MainContent`, bukan dummy 9 lagu (`components/MainContent.py:24`).
- Search/filter by title/artist/album, sort by `added_at`, toggle `is_favorite`.
- Acceptance: tambah folder → list refresh otomatis tanpa restart; 1000 lagu tetap scroll lancar (lazy row / pagination).

### F3 — Play (BELUM)

- Klik lagu → play; prev/next, play/pause, seek slider, volume/mute, tampil judul/artis/durasi, auto-next saat lagu habis.
- Acceptance: FLAC + MP3 wajib bunyi; seek akurat ±1 dtk; slider jalan 1 detik sekali via `after()`, bukan thread UI.
- Backend: `python-vlc` sebagai primer — lihat keputusan di [Architecture §5](architecture.md#5-backend-audio-python-vlc-vs-alternatif).

### F4 — Playlist & Favorite (OPSIONAL, setelah F2+F3)

- Buat/rename/hapus playlist, tambah/hapus lagu, persisten di tabel link. Favorite = flag `is_favorite`, bukan tabel.
- Lihat model datanya di [Schema §2](schema.md#2-tabel).

## 4. Non-functional requirements

| Aspek         | Target                                                                                       |
| ------------- | -------------------------------------------------------------------------------------------- |
| Startup       | Splash → main < 3 dtk (DB `create_all` saja, tanpa scan)                                     |
| Responsivitas | Scan/parsing di worker thread; UI update via `after()`                                       |
| Persistensi   | SQLite file lokal, path absolut (bukan relatif CWD — bug saat ini di `models/database.py:4`) |
| Logging       | `loguru`, `logs/app_history.log` rotasi 1 MB                                                 |
| Testability   | Controller tanpa `mainloop()` di `__init__`; service bisa di-unit-test tanpa Tk              |

## 5. Out of scope eksplisit

Shuffle/repeat gaya versi lama (random ±2 index — buggy), album-art blur background, multi-folder watch, drag-and-drop. Boleh masuk backlog pasca-MVP, bukan sekarang.

## 6. Roadmap bertahap (sesuai pilihan: migrasi bertahap, opsi A)

1. **Fase 0 — Fondasi ✅ SELESAI:** `SongRepository` + `LibraryService` + `container.py`, `MainController` tipis (`run()` ganti `mainloop` di `__init__`), `model.py` dihapus, `views/theme.py` sebagai design system. UI tidak berubah; `models/` + `controller.py` lama tinggal sebagai shim.
2. **Fase 1 — F2 List:** `MainContent.set_songs()`, event `library_changed`, hapus dummy.
3. **Fase 2 — F3 Play:** `PlayerBackend` ABC + implementasi VLC + `PlayerService`, wiring `PlayerBar`.
4. **Fase 3 — F4 Playlist:** UI playlist + CRUD link table.
5. **Fase 4 — Polish:** worker-thread scan, lazy icon, path absolut DB, hapus `destroy()`-recreate frame.

## 7. Open questions — DIPUTUSKAN

1. Backend audio final: **ya** — `python-vlc` primer + fallback `miniaudio/just_playback` (detail di [Architecture §5](architecture.md#5-backend-audio-python-vlc-vs-alternatif)). Slot `PlayerBackend` ABC sudah ada di `domain/interfaces.py`; implementasi + `uv add` dijadwalkan Fase 2.
2. Playlist: **ditunda** sampai F2+F3 stabil (tetap F4 opsional).
3. Format minimum: **MP3+FLAC saja** hari pertama (`SUPPORTED_AUDIO_EXTENSIONS` di `infrastructure/audio_tagger.py`); OGG/M4A/WAV backlog pasca-MVP.
