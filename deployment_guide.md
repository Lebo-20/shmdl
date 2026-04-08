# 🚀 Deployment Guide: Shortmax Telegram Bot (Putty/Linux)

Ikuti langkah-langkah di bawah ini untuk memasang bot dari repo [Lebo-20/shmdl](https://github.com/Lebo-20/shmdl.git) ke VPS linux kamu.

---

### 1. Login dengan Putty (SSH)
* Buka **Putty**.
* Masukkan **IP Address Server**.
* Gunakan port **22** (default).
* Klik **Open**.
* Login dengan user (biasanya `root`) dan password server kamu.

---

### 2. Update Server & Instal Dependency
Update server dan instal paket yang dibutuhkan (Python, Git, FFmpeg):
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip git ffmpeg screen -y
```

---

### 3. Clone Repository dari GitHub
Pindah ke direktori home dan tarik kodenya:
```bash
cd ~
git clone https://github.com/Lebo-20/shmdl.git
cd shmdl
```

---

### 4. Instal library Python
Instal modul yang diperlukan:
```bash
pip3 install -r requirements.txt
```

---

### 5. Konfigurasi File `.env`
Salin isi `.env` lokal kamu ke server. Pakai `nano` untuk buat filenya:
```bash
nano .env
```
* **Tempel (Right click in Putty)** isi file `.env` kamu di sini.
* Tekan `CTRL+O`, lalu `ENTER` (untuk save).
* Tekan `CTRL+X` (untuk keluar).

---

### 6. Jalankan Bot (Background Mode)
Pakai `screen` supaya bot tetap jalan waktu Putty ditutup.

1.  **Buat sesi screen baru:**
    ```bash
    screen -S shmdl
    ```
2.  **Jalankan bot:**
    ```bash
    python3 main.py
    ```
3.  **Keluar dari tampilan (Detach):**
    * Tekan `CTRL+A` lalu tekan `D`.
    * Selesai, kamu bisa tutup Putty dan bot akan tetap jalan.

---

### Perintah Berguna
* **Cek bot lagi:** `screen -ls` (lihat daftar sesi) dan `screen -r shmdl` (masuk lagi ke sesi bot).
* **Update bot:**
    ```bash
    git pull origin main
    pip3 install -r requirements.txt
    ```
