# Smoke Test Fase 2 (F3 Play) — checklist manual ±5 menit

> Backend asli (VLC/miniaudio) tidak bisa diuji headless — daftar ini adalah
> acceptance PRD F3. Jalankan di mesin dengan speaker + VLC terinstall.
> Pembagian grill: checklist ini dieksekusi manusia, hasilnya dilaporkan
> sebelum Fase 2 dinyatakan selesai.

## Persiapan

1. `uv run poe start` (atau `python main.py`).
2. Klik ➕ Add → pilih folder berisi minimal 1 MP3 + 1 FLAC.
3. Cek log: `Audio backend: VLC` (atau `miniaudio (fallback)` bila tanpa VLC).

## Kasus uji

| #   | Langkah                                            | Harapan                                             |
| --- | -------------------------------------------------- | --------------------------------------------------- |
| 1   | Klik sebuah baris lagu                             | Bunyi; judul/artis tampil di PlayerBar              |
| 2   | Tunggu ±5 detik                                    | Slider + label waktu berjalan tiap detik            |
| 3   | Tekan play/pause 2x                                | Berhenti → lanjut dari posisi yang sama             |
| 4   | Drag slider ke tengah, lepas                       | Lompat akurat (±1 dtk, cocokkan label waktu)        |
| 5   | Next di lagu terakhir / Prev di lagu pertama       | Wrap (tidak berhenti/mati)                          |
| 6   | Biarkan 1 lagu habis (atau pakai file pendek)      | Auto-next ke lagu berikut                           |
| 7   | Geser volume slider; tekan tombol 🔊 2x            | Volume berubah; mute → bisu → kembali seperti semula|
| 8   | Klik ♡ di PlayerBar                                | Lagu tampil ♥; list ikut refresh                    |
| 9   | Tutup app, jalankan `WAVE_AUDIO_BACKEND=miniaudio` | Bunyi via fallback; kasus 1–7 tetap lolos           |

## Bila gagal

- App abort/crash saat play di backend VLC → cek versi VLC (`vlc --version`).
  Snapshot libvlc 4.0-dev diketahui abort di level C bersama `python-vlc`;
  paksa fallback (`WAVE_AUDIO_BACKEND=miniaudio`) dan catat versi VLC di laporan.
- Tidak ada suara di kedua backend → cek device audio OS + volume OS.
- Seek melompat jauh → catat format file + backend; lampirkan baris log `Now playing`.
