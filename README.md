# 🃏 Capsa Big Two — Online Multiplayer + PWA

Game kartu Capsa Big Two dengan login Google, leaderboard global, dan bisa diinstall seperti APK.

---

## ✨ Fitur

| | |
|---|---|
| 🔐 Login Google | Via Firebase Auth (satu klik) |
| 👤 Mode Tamu | Bot & Hotspot saja (tanpa akun) |
| 🌐 Mabar Online | Room code, multiplayer via internet |
| 🤖 Lawan Bot | Offline, 2-4 pemain |
| 🏆 Leaderboard | Ranking global via Firestore |
| 📱 Install APK | PWA — install dari browser Android/iOS |

---

## 🔥 Setup Firebase

### 1. Buat Project
1. Buka [console.firebase.google.com](https://console.firebase.google.com) → **Add project**
2. **Authentication** → Get started → aktifkan **Google**
3. Tambahkan domain Render kamu di **Authorized domains**
4. **Firestore Database** → Create database → *test mode* → region `asia-southeast1`

### 2. Config Frontend (index.html)
1. ⚙️ Project Settings → **Your apps** → Add Web App
2. Copy `firebaseConfig` yang muncul
3. Paste ke `templates/index.html` bagian `FIREBASE_CONFIG`:
```js
const FIREBASE_CONFIG = {
  apiKey:            "AIza...",
  authDomain:        "namaproject.firebaseapp.com",
  projectId:         "namaproject",
  storageBucket:     "namaproject.appspot.com",
  messagingSenderId: "123456789",
  appId:             "1:123:web:abc"
};
```

### 3. Service Account (Backend/Leaderboard)
1. ⚙️ Project Settings → **Service accounts** → **Generate new private key**
2. Download file JSON → isinya nanti jadi env var di Render

---

## 🚀 Deploy ke Render

### 1. Push ke GitHub
```bash
cd ~/pokergame
git init
git add .
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/HendiST/pokergame.git
git push -u origin main
```

Kalau token expired:
```bash
git remote set-url origin https://$(gh auth token)@github.com/HendiST/pokergame.git
git push
```

### 2. Buat Web Service di Render
1. [render.com](https://render.com) → New → **Web Service**
2. Connect repo GitHub → pilih `pokergame`
3. Setting:
   - Runtime: **Python 3**
   - Build: `pip install -r requirements.txt`
   - Start: `gunicorn --worker-class eventlet -w 1 server:app`

### 3. Environment Variables di Render
| Key | Value |
|---|---|
| `SECRET_KEY` | string acak panjang, misal `capsa2024xyzXYZ` |
| `FIREBASE_CREDENTIALS` | paste **seluruh isi** JSON service account |

### 4. Auto-Deploy (GitHub Actions)
1. Render → Settings → **Deploy Hook** → copy URL
2. GitHub repo → Settings → **Secrets → Actions** → New secret
   - Name: `RENDER_DEPLOY_HOOK`
   - Value: URL deploy hook tadi
3. Sekarang setiap `git push` → otomatis deploy! 🎉

---

## 📱 Install sebagai APK (PWA)

### Android
1. Buka link Render di **Chrome**
2. Ketuk ⋮ → **"Tambahkan ke layar utama"** → Add
3. Icon Capsa muncul di homescreen seperti app native!

### iPhone
1. Buka di **Safari**
2. Ketuk ⬆️ Share → **"Add to Home Screen"**

---

## 🔄 Update Game

```bash
cd ~/pokergame
git add .
git commit -m "update: deskripsi perubahan"
git push
```
Auto-deploy dalam ~1 menit via GitHub Actions.

---

## 📁 Struktur File

```
pokergame/
├── server.py                    # Flask + SocketIO + Firebase Admin
├── game.py                      # Logika game Capsa
├── templates/index.html         # Frontend (login, game, leaderboard)
├── static/
│   ├── cards.js                 # Data kartu
│   ├── icon-192.png             # PWA icon
│   └── icon-512.png             # PWA icon
├── requirements.txt
├── Procfile
├── .gitignore
└── .github/workflows/deploy.yml # Auto-deploy ke Render
```

---

## 🔒 Firestore Security Rules (setelah go-live)

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /users/{id}        { allow read: if true; allow write: if false; }
    match /game_history/{id} { allow read: if true; allow write: if false; }
  }
}
```
