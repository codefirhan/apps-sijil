# 🕌 Bot Telegram Laporan Pelaksanaan Amanah

Bot Telegram untuk pencatatan dan pencetakan dokumen **Laporan Pelaksanaan Amanah** secara otomatis ke dalam format **Gambar (Foto)** dan **File PDF** berorientasi lanskap, yang persis dengan template dokumen fisik resmi.

---

## 📌 Fitur Utama

1. **Pengelolaan Nama Pelapor (Bisa Banyak Nama):**
   - Mendukung penambahan nama pelapor baru sebanyak mungkin tanpa batasan.
   - Menu pengelolaan nama interaktif:
     - ➕ **Tambah Nama Baru**: Cukup ketik nama baru melalui chat bot.
     - 👤 **Pilih / Ganti Nama**: Tombol daftar seluruh nama yang tersimpan dengan indikator nama aktif (`✅`).
     - 🗑️ **Hapus Nama**: Menghapus nama yang sudah tidak digunakan.

2. **Ahad Ke (Pekan ke-1 s/d 5):**
   - Nilai pilihan user (misal Ahad ke-2, 3, 4, 5) tersimpan permanen dan **tercetak persis sesuai pilihan** di header laporan (tidak akan kembali/ter-reset ke 1).
   - Dapat diubah langsung dengan 1 klik pada tombol `[ Ahad 1 ]` s/d `[ Ahad 5 ]` sebelum mencetak laporan.

3. **Data Statis & Khusus:**
   - **Posko**: Selalu otomatis `TANGKIL`.
   - **Piket**: Dibuat statis tidak hadir (`Hadir :    Tidak : ✓`).
   - **Keterangan Catatan Kaki**: 4 butir petunjuk pengisian di bawah tabel.

4. **Pengajian & Jijyah (Tata Krama):**
   - **Pengajian**: Pilihan input *Hadir (Iya)* atau *Tidak* untuk pekan tersebut.
     - Jika Hadir: `Hadir : ✓    Tidak :`
     - Jika Tidak: `Hadir :      Tidak : ✓`
   - **Jijyah**:
     - Pilihan tombol cepat: `2000` atau `67000`
     - Opsi **Manual**: Pengguna dapat mengetikkan nominal bebas melalui chat.
     - Opsi Kosongkan.
     - Tercetak di kolom `Jijyah : [nominal]`.

5. **Pencatatan Harian Interaktif & Kolom Keterangan Otomatis:**
   - **Pilih Tanggal**: Tombol cepat untuk *Hari Ini*, *Kemarin*, atau *Ketik Tanggal Bebas*.
   - **Solat Malam**: Jam pelaksanaan (contoh `03:30 s/d 04:10`) & jumlah dzikir (`10.000` / `20.000`). Jika tidak melaksanakan, pilih/ketik alasan (misal `Terlewat`, `Kesiangan`, `Halangan`, dll).
   - **Solat Dhuha**: Ya (✓) atau Tidak (sertakan alasan, misal `Terlewat`, `Halangan`, `Uzur Syar'i`).
   - **Puasa Senin & Kamis**: Ya (✓) atau Tidak (sertakan alasan, misal `Halangan`, `Sakit`, `Uzur Syar'i`).
   - **Solat Rowatib**: Pilihan 1 s/d 5 waktu. Jika tidak full 5 waktu (4, 3, 2, 1, 0 waktu), pengguna diminta menyertakan alasan (misal `Halangan`, `Terlewat`, `Safar`, dll).
   - **Tampilan Keterangan di Dokumen**: Pada saat cetak laporan (PDF/Gambar), kolom **KETERANGAN** secara otomatis menampilkan hari dan alasan bagi ibadah yang tidak dilaksanakan atau tidak full (contoh: `SELASA: Terlewat`, `SELASA: Halangan`, `SENIN: Halangan`). Baris tabel secara dinamis menyesuaikan tinggi baris agar teks rapi dan tidak tumpang tindih.

6. **Fitur Edit & Kelola Inputan (Fleksibel & Cepat):**
   - Akses mudah melalui menu **✏️ Edit Data Inputan**, perintah `/edit`, atau dari tampilan **Rekap Data**.
   - **Pilihan Riwayat Cepat**: Menampilkan daftar laporan tanggal-tanggal terakhir yang tersimpan untuk pelapor aktif, atau opsi ketik tanggal bebas.
   - **Dashboard Ringkasan Detail**: Menampilkan status lengkap laporan untuk tanggal yang dipilih sebelum diedit.
   - **Edit Per Butir Tanpa Mengulang**:
     - 🌙 Ubah Solat Malam (status Ya/Tidak, jam, dzikir, alasan).
     - ☀️ Ubah Solat Dhuha (status Ya/Tidak, alasan).
     - 🍃 Ubah Puasa (status Ya/Tidak, alasan).
     - 🕌 Ubah Solat Rowatib (1 s/d 5 waktu atau 0).
     - 🗓 Ubah Ahad Ke (pekan 1 s/d 5, otomatis tersinkronisasi ke seluruh pekan).
     - 🕌 Ubah Pengajian & 💰 Jijyah (khusus hari Ahad / pekanan).
   - **Hapus Inputan (Delete)**: Dilengkapi dialog konfirmasi untuk menghapus data laporan tanggal tertentu jika terjadi salah input.

7. **Format Cetak Laporan (Gambar & PDF):**
   - **🖼 Kirim Sebagai Gambar (Foto)**: Muncul langsung di chat Telegram, tidak perlu aplikasi pembaca PDF, mudah diperbesar dan diteruskan ke WhatsApp.
   - **📄 Kirim Sebagai Dokumen PDF**: File dokumen PDF asli untuk dicetak ke printer fisik (Landscape A4).
   - **📦 Kirim Keduanya**: Mengirimkan gambar pratinjau sekaligus dokumen PDF resminya.

---

## 📂 Struktur File

```
apps-sijil/
├── bot.py                # Handler utama Bot Telegram & alur percakapan
├── database.py           # SQLite (laporan, pekan_info, daftar_nama, user_settings)
├── pdf_generator.py      # Generator PDF & perender Gambar PNG (PyMuPDF)
├── run.py                # File startup dengan pengecekan bot token
├── test_app.py           # Unit test otomatis
├── requirements.txt      # Dependensi Python
├── .env                  # Token bot Telegram Anda
└── README.md             # Dokumentasi
