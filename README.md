# AI-Roleplay Chat Application

Aplikasi roleplay chat berbasis AI dengan long-term memory, sistem relationship, lore/world knowledge, dukungan multi-karakter, dan text-to-speech menggunakan VoiceVox.

## Fitur Utama

- **Multi-Provider LLM**: Mendukung model lokal via LM Studio, OpenAI API resmi, atau Gemini API. Anda dapat mengatur provider yang berbeda untuk fungsi Chat, Terjemahan (ID ke JP), dan Ekstraksi Memori.
- **Long-term Memory**: Karakter mengingat pengguna, hubungan, kejadian, dan fakta dunia menggunakan Semantic Search (`sentence-transformers`).
- **VoiceVox Text-to-Speech**: Percakapan Bahasa Indonesia secara otomatis diterjemahkan ke Bahasa Jepang untuk dibacakan oleh VoiceVox dengan intonasi anime.
- **Automatic Memory Extraction**: Ringkasan memori diekstrak setiap beberapa giliran (bisa berjalan secara synchronous atau di background thread).
- **Web UI Clean & Modern**: Dibangun menggunakan Flask, websockets untuk streaming, dan HTML5 Audio. Pengaturan config dapat diakses langsung melalui halaman web.

## Persyaratan Sistem

- Python 3.11+
- [LM Studio](https://lmstudio.ai/) (untuk menjalankan LLM lokal)
- [VoiceVox](https://voicevox.hiroshiba.jp/) (untuk engine TTS)

## Instalasi

1. Buka terminal, masuk ke folder project ini.
2. Install dependensi Python:
   ```bash
   pip install -r requirements.txt
   ```
   *(Catatan: Saat pertama kali dijalankan, sistem akan mengunduh model `sentence-transformers` secara otomatis)*

## Setup Eksternal

### 1. Setup LM Studio
- Buka LM Studio, muat model instruksional favorit Anda (misal: Llama-3-8B-Instruct atau model roleplay yang fasih Bahasa Indonesia).
- Pergi ke tab **Local Server**, pastikan berjalan di port `1234`.
- Aktifkan fitur **CORS** (Cross-Origin Resource Sharing) di LM Studio jika diperlukan.

### 2. Setup VoiceVox
- Buka aplikasi VoiceVox.
- Biarkan berjalan di latar belakang (default port adalah `50021`).

## Cara Menjalankan

1. Jalankan server Flask:
   ```bash
   python main.py
   ```
2. Buka web browser dan navigasi ke:
   ```
   http://127.0.0.1:5000
   ```
3. Klik tombol **⚙️ Settings** di pojok kanan atas untuk menyesuaikan konfigurasi provider (Local, OpenAI, Gemini) dan API keys jika Anda menggunakannya. Pastikan klik **Save Configurations**.

## Struktur Karakter

Setiap karakter memiliki folder di dalam `characters/`. Contoh `rin_tohsaka`:
- `character.txt`: Definisi persona, gaya bicara, dan VoiceVox Speaker ID.
- `lore.txt`: Latar belakang cerita statis.
- `memory/`: Menyimpan file JSON dinamis untuk `user.json`, `relationship.json`, `events.json`, `world.json`, `temporary.json`.
