# ZIP2APK STUDIO v5 — GitHub Pages production update

Proyek ini menerima ZIP website statis yang berisi `index.html`, mengunggahnya ke repository GitHub, memicu GitHub Actions untuk membangun APK Android, dan menampilkan tombol unduh jika build berhasil. **GitHub Pages sendiri tidak dapat mengompilasi APK**, sehingga Actions diperlukan. File yang dipilih adalah ZIP milik pengguna, bukan file tes.

## Perbaikan masalah HP

- Area pemilih file penuh dapat diketuk dengan file picker native Android; status ZIP muncul sebelum build.
- Upload ZIP memakai XMLHttpRequest dengan progres jaringan riil dan timeout yang menjelaskan kegagalan.
- Token GitHub tidak dikosongkan bila build gagal, sehingga percobaan ulang tidak perlu mengisi lagi. Token tidak disimpan ke IndexedDB.
- Kamera langsung menyala saat pengguna mengetuk tombol; setelah model wajah siap, 2 hasil deteksi dicocokkan otomatis, kemudian halaman build terbuka.
- Pencocokan wajah tanpa liveness challenge **tidak dapat memastikan wajah asli, bukan foto/video/deepfake**. IndexedDB sendiri bukan autentikasi server. Token GitHub adalah pengamanan akses Actions yang sesungguhnya.

## Deploy

1. Ekstrak ZIP proyek, unggah **isi** folder ke root repository GitHub. Pastikan file `.github/workflows/build-apk.yml` benar-benar ikut terunggah.
2. Settings > Pages: pilih Deploy from a branch, `main`, `/ (root)`; simpan.
3. Settings > Actions > General: izinkan Actions. Di Workflow permissions pilih **Read and write permissions** (jika tersedia pada repository tersebut).
4. Buat GitHub fine-grained token terbatas hanya untuk repository builder dengan **Contents: Read and write** dan **Actions: Read and write**. Jangan pernah menyimpan token dalam file atau commit publik.
5. Buka situs HTTPS GitHub Pages; daftar wajah satu kali pada browser HP. Berikutnya satu ketukan kamera untuk login otomatis.
6. Isi repository `owner/repo`, token, nama app, package ID, lalu ketuk kotak besar **Pilih ZIP**. Tunggu ZIP valid, tekan **Unggah ZIP & buat APK asli**.
7. Progres upload jaringan tampil persentase aktual. GitHub Actions menjalankan Android SDK, Gradle, `apksigner`, emulator install/launch, lalu membuat Release untuk APK yang benar-benar berhasil.
8. Jika gagal, tekan link **Buka log GitHub Actions** untuk melihat langkah yang merah. Koreksi sesuai pesan log, lalu coba kembali.

**Batas:** hanya ZIP website HTML/CSS/JS jadi (bukan source React/Vite tanpa build, atau ZIP proyek Android). Maksimal 18 MiB compressed, 110 MiB diekstrak. File `index.html` berada di root atau dalam satu folder. Aplikasi WebView memerlukan resource web eksternal tetap tersedia melalui internet jika source ZIP menggunakannya. APK debug atau release tidak otomatis masuk Google Play; Android meminta izin instalasi dari browser.

**Repository publik**: ZIP pengguna dan riwayat commit akan terlihat oleh orang lain. Untuk input privat gunakan repository builder privat dengan pengaturan Pages yang didukung plan, atau pisahkan frontend Pages publik dari repository builder privat (input repository bisa berbeda dari repository Pages).

## Hal yang belum bisa diverifikasi di sini

Semua uji lokal dijalankan pada browser Chromium, Python, dan pemeriksaan struktur workflow. APK release hanya dapat dibuktikan setelah GitHub Actions memakai Android SDK benar-benar berhasil dan emulator menerima APK. Tanpa token/repository akses, kami tidak dapat menyatakan build atau instalasi telah sukses di GitHub. GitHub Actions mengembalikan status real-time dan tidak merilis APK ketika pemeriksaan gagal.
