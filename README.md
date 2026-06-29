# MSTR SEC Filings Monitor Telegram Bot

Bu Telegram botu, MicroStrategy (Strategy Inc., CIK `0001050446`) şirketinin SEC EDGAR sistemine sunduğu Form 8-K bildirimlerini anlık olarak izler. Yeni bir bildirim algılandığında, bildirimi **Groq API (Llama 3)** üzerinden Türkçe olarak analiz eder ve anında Telegram kanalınıza veya grubunuza bildirim gönderir.

## Özellikler

- ⚡ **Yüksek Hızlı Polling (High-Speed Mode)**: Türkiye saatiyle (TRT) pazartesiden cumaya **14:59 - 15:10** arasındaki kritik dönemde SEC EDGAR API'sini her **2 saniyede bir** sorgular. Diğer saatlerde ise 5 dakikada bir kontrol eder.
- 🧠 **Groq Llama 3 Analizi**: Gelen bildirimi Groq API aracılığıyla saniyeler içinde analiz ederek Bitcoin alımı, satımı, finansman (ATM hisse satışı, tahviller) veya tercihli hisse senedi (STRC, STRF) durumunu çıkarır.
- 🛠️ **Çift Katmanlı Ayrıştırma (Fallback)**: Groq API'sinde veya anahtarında bir sorun oluşursa, yerleşik BeautifulSoup tablosu ayrıştırıcısı devreye girer.
- 💾 **Kalıcı SQLite Veritabanı**: Bildirim geçmişini ve alım verilerini kaydeder (Railway Volumes ile uyumludur).
- 💬 **Telegram Bot Komutları**:
  - `/data` veya `/history` - En son portföy özetini ve son 6 alımın geçmişini gösterir.
  - `/status` - Botun aktif durumunu, anlık çalışma modunu (Normal/High-Speed) ve zaman damgalarını gösterir.

---

## Kurulum ve Yerel Çalıştırma

1. Repoyu klonlayın:
   ```bash
   git clone https://github.com/TradersEntertainment/mstrbought.git
   cd mstrbought
   ```

2. Gerekli kütüphaneleri yükleyin:
   ```bash
   pip install -r requirements.txt
   ```

3. `.env` dosyasını oluşturun (şablondan kopyalayarak):
   ```bash
   cp .env.example .env
   ```
   Aşağıdaki değişkenleri doldurun:
   - `TELEGRAM_BOT_TOKEN`: BotFather'dan aldığınız API token.
   - `TELEGRAM_CHAT_ID`: Bildirimlerin atılacağı Telegram kanal adı (örn: `@kanal_adi`) veya sohbet ID'si.
   - `GROQ_API_KEY`: Groq API anahtarınız.
   - `DB_PATH`: Yerel geliştirme için `mstr_state.db` olarak kalabilir.

4. Botu başlatın:
   ```bash
   python bot.py
   ```

---

## Railway Dağıtımı (Deployment) ve Kalıcı Depolama (Volume)

Railway üzerinde kalıcı depolama (Volume) eklemek, botun yeniden başlatıldığında verileri ve alım geçmişini kaybetmemesi için kritiktir.

### 1. Railway Volume Ekleme
1. Railway projenizde **New** -> **Volume** butonuna tıklayın.
2. Volume adını belirleyin ve **Mount Path** alanına `/data` yazın.
3. Bu volume'ü bot servisinizle ilişkilendirin.

### 2. Çevre Değişkenleri (Environment Variables)
Railway paneline gidip aşağıdaki çevre değişkenlerini ekleyin:

| Değişken Adı | Değer / Açıklama |
| :--- | :--- |
| `TELEGRAM_BOT_TOKEN` | *Telegram bot tokenınız* |
| `TELEGRAM_CHAT_ID` | *Telegram chat/kanal ID'niz* |
| `GROQ_API_KEY` | *Groq API keyiniz* |
| `DB_PATH` | `/data/mstr_state.db` (Volume içine kaydedilmesi için mutlaka bu olmalı) |
| `POLL_INTERVAL_NORMAL` | `300` *(Varsayılan: 5 dakika)* |
| `POLL_INTERVAL_CRITICAL` | `2` *(Kritik saatlerde varsayılan: 2 saniye)* |

### 3. Dağıtım (Deploy)
Bot, dizinde yer alan `Dockerfile` sayesinde Railway tarafından otomatik olarak Docker imajı olarak oluşturulup çalıştırılacaktır. Projeyi Railway'e bağlamanız yeterlidir.
