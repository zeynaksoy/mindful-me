# 🌿 Mindful-Me: Zihinsel Farkındalık Asistanı

<p align="center">
  <img src="https://img.shields.io/badge/Flask-3.1.3-black?style=for-the-badge&logo=flask" alt="Flask">
  <img src="https://img.shields.io/badge/Python-3.x-blue?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/SQLite-3-blue?style=for-the-badge&logo=sqlite" alt="SQLite">
  <img src="https://img.shields.io/badge/Bootstrap-5.3-purple?style=for-the-badge&logo=bootstrap" alt="Bootstrap">
  <img src="https://img.shields.io/badge/Chart.js-Latest-ff6384?style=for-the-badge&logo=chartdotjs" alt="Chart.js">
</p>

<p align="center">
  <b>Duygularını takip et. Kalıplarını keşfet. Daha bilinçli yaşa.</b>
</p>

---

## 📖 Proje Özeti

**Mindful-Me**, kullanıcıların günlük ruh hallerini kayıt altına almasını, bu verileri yapay zeka destekli bir analiz motoru ile yorumlamasını ve veriye dayalı kişiselleştirilmiş içgörüler (insights) elde etmesini sağlayan bir **zihinsel farkındalık ve yaşam koçluğu** web uygulamasıdır.

Kullanıcı; uyku süresini, stres seviyesini ve günlük aktivitelerini sisteme girerek zaman içinde kendi duygusal örüntülerini keşfedebilir. Uygulama bu verileri analiz ederek "*Spor yaptığın günlerde mutluluk ortalaman %23 daha yüksek*" gibi anlamlı çıkarımlar üretir.

---

## ✨ Öne Çıkan Özellikler

| Özellik | Açıklama |
|---|---|
| 🤖 **AI Destekli Günlük Analizi** | Girilen metni duygu (Pozitif/Negatif/Nötr), puan (0–10) ve anahtar kelimeler ile analiz eder |
| 📅 **Dinamik Mood Takvimi** | GitHub contribution graph tarzında, son 30 günün ruh hali ızgarası |
| 📊 **Akıllı İstatistik Sistemi** | Uyku, stres ve aktivite verileri arasındaki korelasyonları hesaplar |
| 🔌 **REST API** | `/api/v1/entries` endpoint'i ile tüm kayıtlara JSON formatında erişim |
| 👤 **Kullanıcı Profil Yönetimi** | Avatar yükleme, kişisel istatistikler ve profil sayfası |
| 🎨 **Glassmorphism Tasarım** | Yumuşak degradeli arka plan, buzlu cam kartlar ve mikro-animasyonlar |
| 🔍 **Arama ve Filtreleme** | Geçmiş kayıtlarda anahtar kelime araması ve tarihe göre sıralama |
| 🗑️ **Kayıt Yönetimi** | Her kayıt için onaylı silme işlemi |

---

## 🖼️ Ekran Görüntüleri

> Uygulamayı yerel ortamda başlatarak aşağıdaki sayfaları inceleyebilirsiniz:
>
> - **Ana Sayfa:** `http://127.0.0.1:5000/`
> - **Profil Sayfası:** `http://127.0.0.1:5000/profile`
> - **REST API:** `http://127.0.0.1:5000/api/v1/entries`

---

## 🛠️ Kullanılan Teknolojiler

### Backend
- **[Flask 3.1](https://flask.palletsprojects.com/)** — Python web framework
- **[Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/)** — ORM (veritabanı yönetimi)
- **[Flask-Migrate](https://flask-migrate.readthedocs.io/)** — Veritabanı şeması versiyonlama
- **[Flask-WTF / WTForms](https://flask-wtf.readthedocs.io/)** — Form doğrulama ve CSRF koruması
- **[Werkzeug](https://werkzeug.palletsprojects.com/)** — Güvenli dosya yükleme
- **[SQLite](https://www.sqlite.org/)** — Hafif ilişkisel veritabanı

### Frontend
- **[Bootstrap 5.3](https://getbootstrap.com/)** — Duyarlı (responsive) arayüz bileşenleri
- **[Chart.js](https://www.chartjs.org/)** — Etkileşimli grafikler (çizgi, çubuk, heatmap)
- **Vanilla CSS** — Glassmorphism efektleri, CSS Grid takvim ızgarası, animasyonlar

---

## ⚙️ Kurulum ve Çalıştırma

### Gereksinimler
- Python 3.9 veya üzeri
- pip

### Adım 1 — Depoyu Klonlayın
```bash
git clone https://github.com/kullanici-adi/mindful-me.git
cd mindful-me
```

### Adım 2 — Sanal Ortam Oluşturun
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### Adım 3 — Bağımlılıkları Yükleyin
```bash
pip install -r requirements.txt
```

### Adım 4 — Veritabanını Başlatın
```bash
flask db upgrade
```

### Adım 5 — Uygulamayı Başlatın
```bash
flask run
```

Tarayıcınızda `http://127.0.0.1:5000` adresine giderek uygulamayı kullanabilirsiniz.

---

## 🔌 API Referansı

### `GET /api/v1/entries`
Tüm günlük kayıtlarını JSON formatında döndürür.

**Opsiyonel Query Parametreleri:**

| Parametre | Tür | Açıklama | Örnek |
|---|---|---|---|
| `limit` | `int` | Dönen kayıt sayısını sınırlar | `?limit=10` |
| `mood` | `string` | Belirli bir ruh haline göre filtreler | `?mood=mutlu` |

**Örnek Yanıt:**
```json
{
  "status": "ok",
  "count": 2,
  "entries": [
    {
      "id": 1,
      "mood": "mutlu",
      "text": "Bugün harika bir gündü...",
      "timestamp": "2026-05-26T10:30:00",
      "sleep_hours": 7.5,
      "stress_level": 3,
      "activities": "spor, yürüyüş",
      "ai_analysis": {
        "sentiment": "Pozitif",
        "score": 9,
        "keywords": "harika, güzel, mutlu",
        "advice": "Bu enerjiyi çevrendekilerle paylaşabilirsin."
      }
    }
  ]
}
```

---

## 📁 Proje Yapısı

```
mindful-me/
├── app/
│   ├── __init__.py          # Uygulama fabrikası (Application Factory)
│   ├── models.py            # SQLAlchemy modelleri (User, MoodEntry)
│   ├── forms.py             # WTForms form sınıfları
│   ├── routes.py            # Tüm view fonksiyonları ve API endpoint'leri
│   ├── static/
│   │   └── avatars/         # Yüklenen kullanıcı avatarları
│   └── templates/
│       ├── index.html       # Ana sayfa (dashboard)
│       └── profile.html     # Kullanıcı profil sayfası
├── migrations/              # Flask-Migrate veritabanı göç dosyaları
├── config.py                # Uygulama yapılandırması
├── run.py                   # Uygulama giriş noktası
├── requirements.txt         # Python bağımlılıkları
└── README.md
```

---

## 🗺️ Yol Haritası (Gelecek Özellikler)

- [ ] 🔐 Flask-Login ile tam kullanıcı kimlik doğrulama sistemi
- [ ] 🤖 OpenAI GPT API entegrasyonu ile gerçek zamanlı NLP analizi
- [ ] 📧 Günlük hatırlatıcı e-posta bildirimleri
- [ ] 📱 Progressive Web App (PWA) desteği
- [ ] 🌐 Flask-Babel ile çok dil desteği (İngilizce, Türkçe)
- [ ] 📤 Verileri CSV / PDF olarak dışa aktarma

---

## 🤝 Katkıda Bulunma

1. Bu repoyu fork'layın
2. Yeni bir branch oluşturun: `git checkout -b feature/yeni-ozellik`
3. Değişikliklerinizi commit'leyin: `git commit -m 'feat: yeni özellik eklendi'`
4. Branch'inizi push'layın: `git push origin feature/yeni-ozellik`
5. Pull Request açın

---

## 📄 Lisans

Bu proje [MIT Lisansı](LICENSE) ile lisanslanmıştır.

---

<p align="center">
  🌿 <b>Mindful-Me</b> — Verilerle daha farkındalıklı bir yaşam için.<br>
  <i>Made with ❤️ using Flask & Python</i>
</p>

## 🚀 Kurulum
1. `git clone https://github.com/zeynaksoy/mindful-me.git`
2. `pip install -r requirements.txt`
3. `flask run`
