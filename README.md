# ZIP2APK STUDIO v4 — Production (GitHub Pages + Actions)

Ini **source website produksi**, bukan APK demo, bukan simulasi, dan tidak menyertakan ZIP contoh. Proses sebenarnya membuat APK Android dari ZIP website yang **kamu unggah sendiri**.

## Deploy dari HP

1. Buat satu repository GitHub, misalnya `username/zip2apk`. Ekstrak paket ini, unggah **seluruh isinya** ke root repository termasuk folder tersembunyi `.github` (jangan upload hanya file ZIP yang belum diekstrak).
2. Pastikan file `.github/workflows/build-apk.yml` ada di repository. Buka **Settings → Actions → General**, izinkan workflow berjalan, dan aktifkan workflow permissions **Read and write permissions** jika diperlukan untuk membuat GitHub Release.
3. Buka **Settings → Pages → Deploy from a branch → main → / (root)**. Kalau default branch bukan `main`, pilih branch yang digunakan.
4. Tunggu Pages dipublikasikan. Buka HTTPS `https://USERNAME.github.io/NAMA_REPO/` melalui Chrome Android.
5. Daftarkan wajah pada browser itu, lalu masuk dengan verifikasi kamera langsung. Ini **pengenalan wajah lokal** yang disimpan di IndexedDB browser, bukan sistem anti-deepfake tersertifikasi atau verifikasi identitas jarak jauh.
6. Untuk memulai kompilasi dari tombol website, buat *fine-grained Personal Access Token* di GitHub untuk **repository tersebut saja**, dengan izin **Contents: Read/Write**, **Actions: Read/Write**, dan **Metadata: Read**. Token jangan disimpan di kode publik. Salin token di field browser saat akan build.
7. Masukkan `owner/repository`, nama aplikasi, dan package ID unik (misalnya `com.pemilik.aplikasi`). Pilih ZIP yang berisi website statis dengan `index.html`, lalu tekan **Unggah ZIP & kompilasi APK**.
8. Website mengunggah ZIP ke repository, menjalankan `workflow_dispatch`, dan menampilkan status asli job GitHub Actions. Compiler asli dijalankan di runner: **Android SDK + Gradle**. Ketika berhasil, APK di-*sign*, diperiksa menggunakan `apksigner`, dipasang ke emulator Android, dibuka, lalu **GitHub Release** dibuat.
9. Setelah job benar-benar sukses, tombol **Unduh file APK untuk instalasi** muncul. Download dan instal APK menggunakan dialog konfirmasi Android. Android tidak mengizinkan website memasang APK diam-diam seperti Google Play.

## Batasan nyata

- Input adalah **ZIP website statis siap jalan**, bukan sembarang ZIP. Untuk React/Vite, unggah ZIP **hasil build `dist`**; proyek source yang belum dibuild, backend Node/PHP, APK lain atau program desktop tidak otomatis bisa dikonversi.
- Batas ZIP: 18 MiB, maksimal 1500 entri dan 110 MiB setelah ekstraksi. ZIP berpassword, symlink, traversal path, dan ZIP dengan `index.html` tidak jelas ditolak.
- **GitHub Pages adalah hosting statis**. Build APK dijalankan oleh GitHub Actions; build membutuhkan koneksi, kuota GitHub runner, dan izin PAT. Jika Actions gagal (dependensi Android, emulator, kuota, signing), APK **tidak** ditandai berhasil atau dirilis.
- **Jangan gunakan repo publik untuk ZIP sensitif.** ZIP input menjadi bagian riwayat Git, termasuk jika kemudian dihapus. Jika repository privat, mengunduh GitHub Release juga bisa memerlukan login GitHub.
- APK menggunakan Android WebView; fitur asli Android di luar yang didukung WebView perlu implementasi native tambahan. Aplikasi yang mengandalkan API/backend eksternal tetap memerlukan endpoint eksternal tersebut.
- Tanda tangan APK secara default dibuat baru per build, sehingga untuk **update** aplikasi yang sama diperlukan signing key persisten. Simpan `APK_KEYSTORE_BASE64`, `APK_KEYSTORE_PASSWORD`, `APK_KEY_ALIAS`, dan `APK_KEY_PASSWORD` di **Settings → Secrets and variables → Actions**, lalu gunakan key yang sama untuk build berikutnya. Jangan unggah keystore ke repo.
- **Keamanan wajah lokal memiliki keterbatasan**: IndexedDB tidak bisa mengamankan backend, dan tantangan blink/gerak kepala tidak menjamin penolakan deepfake. Hak build tetap dikendalikan token GitHub.

## Struktur file produksi

```
index.html                         Website UI, verifikasi wajah, ZIP upload, Actions status, unduh APK
.github/workflows/build-apk.yml   Build Android dan pemeriksaan APK pada runner GitHub
.nojekyll                          Menjaga file Pages dipublikasikan tanpa Jekyll
tools/build_apk.py                Generator proyek Android WebView dan compiler Gradle
tools/emulator_smoke.sh           Verifikasi instalasi, peluncuran, dan pemuatan website di emulator
README.md                         Petunjuk ini
```

**Penting tentang status:** validasi source dan pengujian lokal tidak sama dengan keberhasilan kompilasi Android sebenarnya. Karena tidak ada Android SDK, emulator, dan akses ke GitHub runner dalam lingkungan penulisan paket ini, hasil build dari GitHub hanya dapat dinyatakan berhasil saat run yang kamu jalankan di repository milikmu selesai **success** dan menerbitkan APK. Tidak ada indikator "lulus" yang dibuat-buat pada website.
