# MSTR SEC Filings Monitor Telegram Bot

Bu Telegram botu, MicroStrategy (Strategy Inc., CIK `0001050446`) şirketinin SEC EDGAR sistemine sunduğu Form 8-K bildirimlerini anlık olarak izler. Yeni bir bildirim algılandığında, bildirimi **Groq API (Llama 3)** üzerinden Türkçe olarak analiz eder ve anında Telegram kanalınıza veya grubunuza bildirim gönderir.

## Özellikler

- ⚡ **Yüksek Hızlı Polling (High-Speed Mode)**: Pencereler **ABD Doğu Saati'ne (ET)** göre belirlenir — EDGAR'ın yayın yaptığı saat dilimi. Türkiye sabit UTC+3 iken ET yaz saatiyle kaydığı için, pencereyi TRT'ye sabitlemek yılda iki kez bir saatlik kayma yaratır (MSTR'ın 07:55-08:25 ET bandı yazın 14:55-15:25 TRT, kışın 15:55-16:25 TRT'ye denk gelir).
  - **07:30-09:30 ET** (haftalık 8-K bandı — yazın 14:30-16:30 TRT, kışın 15:30-17:30 TRT): her **0.25 saniyede** bir.
  - **06:00-18:00 ET** (EDGAR'ın geri kalan yayın günü): her **2 saniyede** bir.
  - Kalan saatler ve hafta sonu: 60 saniyede bir.
  - Kaynaklar: her tick'te `data.sec.gov/submissions` (SEC'in "1 saniyeden az" gecikme belirttiği tek uç nokta; değişmediğinde ucuz bir 304 döner ve belge adını doğrudan taşır), saniyede en fazla bir kez atom feed, 5 saniyede bir EFTS.
- 🧠 **Groq Llama 3 Analizi**: Gelen bildirimi Groq API aracılığıyla saniyeler içinde analiz ederek Bitcoin alımı, satımı, finansman (ATM hisse satışı, tahviller) veya tercihli hisse senedi (STRC, STRF) durumunu çıkarır.
- 🛠️ **Çift Katmanlı Ayrıştırma (Fallback)**: Groq API'sinde veya anahtarında bir sorun oluşursa, yerleşik BeautifulSoup tablosu ayrıştırıcısı devreye girer.
- 💾 **Kalıcı SQLite Veritabanı**: Bildirim geçmişini ve alım verilerini kaydeder (Railway Volumes ile uyumludur).
- 💬 **Telegram Bot Komutları**:
  - `/data` veya `/history` - En son portföy özetini ve son 6 alımın geçmişini gösterir.
  - `/insider` - Polymarket içeriden takip özetini şimdi kanala gönderir.
  - `/insider_test` - Özeti kanala göndermeden sadece size gösterir (canlı doğrulama için).
  - `/markets_test` - Polymarket'te bulunan açık MSTR marketlerini oranlarıyla listeler.
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
| `POLL_INTERVAL_NORMAL` | `60` *(EDGAR kapalıyken)* |
| `POLL_INTERVAL_CRITICAL` | `0.25` *(8-K bandında)* |
| `POLL_INTERVAL_FAST` | `2` *(EDGAR'ın yayın günü)* |
| `ULTRA_WINDOW_ET` | `07:30-09:30` *(ET, opsiyonel)* |
| `FAST_WINDOW_ET` | `06:00-18:00` *(ET, opsiyonel)* |
| `TELEGRAM_LINK_PREVIEW` | `false` *(önizleme açmak gecikme ekler)* |
| `POLYMARKET_INSIDERS` | *(boş)* — takip edilecek cüzdanlar; boşsa özellik kapalı |
| `POLYMARKET_DIGEST_AT_TRT` | `14:00` *(TRT)* |
| `POLYMARKET_DIGEST_DAYS` | `fri,sun,mon` *(boş = özet kapalı)* |
| `POLYMARKET_WHALE_TITLE` | `MicroStrategy Insider balinası` *(bildirimin ilk satırındaki özne)* |
| `POLYMARKET_MIN_USD` | `100` *(bu tutarın altındaki hareketler gösterilmez)* |
| `POLYMARKET_MIN_DELTA_PCT` | `5` *(pozisyonun %5'inden küçük değişim gürültü sayılır)* |
| `POLYMARKET_LIVE_INTERVAL_S` | `3600` *(sitedeki balina panelinin tazelenme aralığı)* |
| `POLYMARKET_MARKETS` | `true` *(market kataloğu; cüzdan listesinden bağımsız)* |
| `POLYMARKET_SEARCH_TERMS` | `microstrategy,mstr,strategy bitcoin` *(Gamma araması; pozisyonsuz marketleri bulur)* |
| `POLYMARKET_TOPIC_RE` | `\b(bitcoin\|btc\|treasury\|holdings\|stack)\b` *(panele hangi marketler girsin)* |
| `POLYMARKET_ODDS_ALERT_PCT` | `0` = kapalı *(pozitif değer oran uyarısını açar)* |
| `RECONCILE_MAX` | `30` *(açılışta kurtarılacak azami eksik hafta)* |

> ⚠️ Bu tablonun eski hali `POLL_INTERVAL_CRITICAL=2` diyordu; kodun varsayılanı ise
> `0.25` idi. README'yi izleyerek kurulan bir Railway servisi kritik pencerede
> **8 kat yavaş** çalışıyordu. Railway panelindeki mevcut değeri kontrol edin.

### 3. Sağlık Kontrolü (Healthcheck)

`railway.json` dosyası `healthcheckPath` olarak `/health` ve restart politikası olarak
`ALWAYS` tanımlar. `/health`, polling döngüsü tik atmayı bıraktığında 503 döner —
böylece kilitlenen bir bot sessizce beklemek yerine yeniden başlatılır.

Railway panelinde **App Sleeping** ayarının **kapalı** olduğundan emin olun: uyuyan
bir konteynerde polling döngüsü tamamen durur.

### 4. Dağıtım (Deploy)
Bot, dizinde yer alan `Dockerfile` sayesinde Railway tarafından otomatik olarak Docker imajı olarak oluşturulup çalıştırılacaktır. Projeyi Railway'e bağlamanız yeterlidir.

---

## Polymarket İçeriden Takip

### Özet hangi günler gider

**Cuma, Pazar, Pazartesi** — `POLYMARKET_DIGEST_DAYS`.

MSTR alım 8-K'sını **Pazartesi sabahı** yayınlıyor (07:55-08:25 ET bandı), yani
balinanın pozisyonu üç anda değerli: Cuma haftanın bahisleri girilmişken, Pazar
açıklamadan bir gün önce, Pazartesi açıklamadan hemen önce. Salı-Perşembe ve
Cumartesi düştü — dosyalamaya uzaklar ve saatlik balina uyarısının zaten
söylediğini tekrarlıyorlardı.

Pazartesi özeti dosyalamadan **önce** düşmek zorunda ve düşüyor: 14:00 TRT yazın
07:00 ET, kışın 06:00 ET, yani bandın 30-90 dakika öncesi. TRT sabit UTC+3 ama ET
yaz saatiyle kayıyor, o yüzden bu iki mevsim için ayrı ayrı test ediliyor.

`seconds_until_digest` ile `digest_due` **aynı gün kümesini** okur. Ayrı
kalsalardı döngü bir güne doğru uyur, uyanınca "bugün değil" der ve özet sessizce
hiç çıkmazdı; bir test her gün ve saat için uyanılan anın due olduğunu doğruluyor.

---

Belirlediğiniz Polymarket cüzdanlarının **yeni** bahis hareketlerini seçili
her gün 14:00 TRT'de kanala gönderir: açılan, kapanan ve büyütülen/küçültülen
pozisyonlar. Tam pozisyon dökümü değil, sadece son özetten bu yana değişenler.

Cüzdanları `POLYMARKET_INSIDERS` ile verirsiniz; profil linkini olduğu gibi
yapıştırabilirsiniz:

```
POLYMARKET_INSIDERS=Balina=https://polymarket.com/profile/0xa0c3...?via=betmoar
```

### Bilinmesi gerekenler

- **Uç noktalar canlıda doğrulanmadı.** `data-api.polymarket.com` bu kodun
  yazıldığı ortamdan erişilemiyordu. Alan adları belgelerden alındı, kod her
  ihtimale karşı savunmacı yazıldı ve ilk cevabın şeklini bir kez loglar.
  Deploy sonrası **`/insider_test`** ile doğrulayın — bu komut özeti kanala
  göndermeden sadece size gösterir.
- **403 görmek olağan.** Polymarket'in önünde bot koruması var ve Railway bir
  veri merkezi IP'si. O gün özet atlanır, saklanan pozisyon anlık görüntüsü
  korunur, ertesi gün iki günlük hareket olarak raporlanır — veri kaybolmaz.
- **Önce gönderilir, sonra kaydedilir.** Anlık görüntü ancak mesaj kanala
  ulaştıktan sonra güncellenir. Tersi olsaydı, arada bir çökme o günün
  hareketlerini kalıcı olarak silerdi.
- **İlk gün sadece "takibe alındı" der.** Yeni bir cüzdanın tüm pozisyonları
  "yeni açıldı" gibi görünürdü; onun yerine tek satır yazılır.
- **Saat neden 14:00.** Yazın 07:00 ET, kışın 06:00 ET — SEC ultra
  penceresinin (07:30-09:30 ET) dışında. 14:30 TRT yazın tam 07:30 ET'ye,
  yani pencerenin açıldığı dakikaya denk gelirdi.

---

## Balinalara Göre Beklenti (dashboard paneli)

Takip edilen Polymarket cüzdanlarının **MSTR marketlerindeki** açık
pozisyonlarını sitede gösterir. Telegram özetiyle aynı cüzdanları kullanır ama
tamamen ayrı çalışır: kendi tablosuna (`polymarket_live`) saatte bir yazar,
dijestin fark alma temelini (`polymarket_positions`) hiç ellemez — o tablo
yalnızca başarılı Telegram gönderiminden sonra yazılabilir, saatlik yazmak
dijestin hareketleri sessizce kaybetmesine yol açardı.

**Okuma mantığı.** Market başlığından sorunun alım mı satım mı olduğu
çıkarılır, sonra balinanın tuttuğu tarafla birleştirilir:

| Soru | Balina | Panel |
|---|---|---|
| alım | Evet | MSTR **alacak** |
| alım | Hayır | MSTR **almayacak** |
| satış | Evet | MSTR **satacak** |
| satış | Hayır | MSTR **satmayacak** |

Fiil çekimlerinin hepsi tanınır — Polymarket soruları ulaç yazar ("announce
**selling** any Bitcoin"), ve ilk sürüm yalnızca `sell|sells|sold` eşleştirdiği
için panel apaçık bir satış sorusuna "yorum yok" diyordu. Ayrıca üçüncü bir
sınıf var: **eşik soruları** ("announce holding 1M+ BTC by December 31") →
Evet ise MSTR **tutacak**, Hayır ise **tutmayacak**.

Sınıflandırılamayan bir başlık (örn. "Will MicroStrategy be added to the
S&P 500?") **yorumsuz** gösterilir — market ve olasılık görünür, beklenti
sütunu boş kalır. Çıkaramadığımız bir şeyi uydurmuyoruz. Başlıkta
`bitcoin|btc|treasury|holdings|stack` geçmiyorsa hiçbir yorum yapılmaz: bu
koruma olmadan "be **added** to the S&P 500" alım sayılıp panelde "MSTR
alacak" yazıyordu.

**Bu bir bahistir, şirket açıklaması değil.** Panel dipnotu bunu söyler.

### Balinası olmayan marketler

Cüzdan uç noktası yalnızca **birinin tuttuğu** pozisyonları döner, yani hiç
balinası olmayan bir marketi asla göremez. Haftalık yenilenen
`will-microstrategy-announce-a-bitcoin-purchase-<hafta>` marketi tam olarak
böyleydi. Onlar için marketin kendisi Gamma katalog API'sinden çekilir
(`polymarket_markets` tablosu) ve panelde balina satırı yerine marketin
"evet" oranıyla görünür.

Sabit slug yazılmaz. Slug her hafta değişiyor (`…-september-1-7` →
`…-september-8-14`), soru şablonu bir kez zaten değişti
(`purchase-bitcoin` → `announce-a-bitcoin-purchase`) ve marketler bir
`pastSlugs` alanı taşıyor, yani Polymarket slug'ları yerinde de değiştiriyor.
Bunun yerine `POLYMARKET_SEARCH_TERMS` ile arama yapılır, sonuçlar
`POLYMARKET_MARKET_RE` ile süzülür; arama boş dönerse açık marketler
sayfalanarak taranır.

Bu katman `POLYMARKET_INSIDERS`'dan **bağımsızdır** — cüzdan listesi boş olsa
bile marketler ve oranları panelde görünür. `POLYMARKET_MARKETS=false` ile
tamamen kapatılabilir.

Canlıda doğrulamak için Telegram'dan **`/markets_test`**: Gamma'dan o an ne
döndüğünü kanala göndermeden size listeler. Uç nokta bu kodun yazıldığı
ortamdan erişilemediği için ilk cevabın şekli ayrıca bir kez loglanır
(`GAMMA /public-search first-response shape`).

### Konu filtresi: hangi marketler panele girer

"MSTR marketi" ile "MSTR'ın **bitcoin** marketi" aynı soru değil. Katalog ilk
açıldığında 55 market geldi ve ~50'si gürültüydü:

```
Will MicroStrategy (MSTR) hit (LOW) $110 in September?   %50 evet   yorum yok
Will MicroStrategy be margin called in 2026?             %4  evet   yorum yok
Michael Saylor federally charged by December 31, 2026?   %7  evet   yorum yok
```

Polymarket MSTR üzerinde bir **fiyat merdiveni** işletiyor — onlarca likit
olmayan market tam %50'de duruyor. Bunlar `POLYMARKET_TOPIC_RE` ile eleniyor;
elle kara liste yok, konu testi 55'i 5'e indiriyor.

Aynı regex sınıflandırıcının konu koruması olarak da kullanılıyor: "okuyabilir
miyiz" ile "panele girmeli mi" aynı soru, iki ayrı regex zamanla birbirinden
kopardı.

**Balina satırları bu filtreden muaftır.** Takip edilen cüzdanın parası bir
markette duruyorsa, okunamasa bile panelde kalır — para bilgidir. Filtre
yalnızca pozisyonsuz katalog marketlerine uygulanır.

Daha önce kaydedilmiş gürültü satırları için ayrı bir migration yok: başarılı
her çekimden sonra filtreyi geçemeyen satırlar siliniyor, yani regex ileride
daraltılırsa panel bir sonraki turda kendini temizliyor. Başarısız çekimde
budama çalışmaz — boş cevap paneli silmemeli.

### Bildirimin şekli

İlk satır tek başına her şeyi söyler, detay altta:

```
🐋 MicroStrategy Insider balinası bu hafta bitcoin alınmayacak beti alıyor

🟢 YENİ: Will Microstrategy announce a Bitcoin purchase September 1-7? — No
   5.000 adet @ $0.18 → $900
   → bitcoin alınmayacak beti

0xa0c3…5b9a · Balina
Bu bir bahis, şirket açıklaması değil.
```

Cümle üç parçadan kurulur: **ne zaman** + **bahis ne diyor** + **balina ne yaptı**.

- *Ne zaman* market başlığından değil **`end_date` alanından** gelir. "September
  1-7" metindir ve Polymarket'in başlık metninden anlam çıkarmak bu botu üç kez
  kırdı. ≤7 gün "bu hafta", ≤31 gün "bu ay", ötesi "31 Aralık'a kadar". Tarih
  yoksa ifade **düşer** — yanlış "bu hafta" yazmaktansa hiç yazmamak iyidir.
- *Bahis ne diyor* `whale_verdict`'ten türer, yani sınıflandırıcı tek yerde
  kalır; sadece özne MSTR yerine bitcoin olur ("almayacak" → "bitcoin
  alınmayacak").
- *Balina ne yaptı* açıyor / büyütüyor / azaltıyor / kapatıyor.

Tek uyarıda birden fazla hareket olabilir. Başlık **en büyüğünü** (dolar
bazında) anlatır; hepsi aynı yöndeyse `+N hareket daha`, zıt yönlerdeyse
`en büyük hareket` notu düşer. Zıt bahisler tek bir kesin yargıya karıştırılmaz.

Okunamayan bir market için yorum uydurulmaz: "bir Polymarket marketinde yeni
pozisyon açıyor" denir ve market adı hemen altta durur.

### Telegram uyarıları

Saatlik döngü **balina hareketini** bildirir: açılan, kapanan veya büyütülen
pozisyon, yalnızca MSTR marketlerinde.

**Oran hareketi uyarısı varsayılan olarak kapalıdır** (`POLYMARKET_ODDS_ALERT_PCT=0`).
Kanal takip edilen balinanın hareketleri için; oranlar sitede görünür ama
Telegram'a düşmez. Pozitif bir puan değeri uyarıyı açar.

Kanala giden her şey, tam liste: **balina hareketi**, **14:00 günlük özet**
(o da yalnızca balina pozisyonları) ve **SEC dosyalama alarmları**.

İkisi de **son uyarılan** değere göre ölçülür, son görülene göre değil: saatte
5 puanlık bir kayma aksi halde hiçbir zaman eşiği geçmezdi. Ve bu değerler
yalnızca **başarılı gönderimden sonra** ilerler (`alerted_size`,
`alerted_price`), yani bir Telegram kesintisi hareketi geciktirir, kaybetmez.
Site tarafı (`size`, `yes_price`) her saat ilerlemeye devam eder — tek tablo,
iki saat.

Uyarılar sabah 07:30-09:30 ET bandında da gider. O bandın gate'i HTML
ayrıştıran döngüler için var; bu döngü cüzdan başına küçük bir JSON çekiyor ve
sinyalin en değerli olduğu saat dosyalamadan hemen önceki saat.

**Bilinçli bir kör nokta:** cüzdanın *bütün* pozisyonlarını kapatması
bildirilmez. HTTP 200 + boş liste, yanlış bir adresten veya bir edge
hatasından gelen cevapla birebir aynı görünüyor; onu kapanış saymak API her
takıldığında her açık pozisyon için sahte "KAPANDI" bildirimi demekti. Kısmi
çıkışlar bildirilir, çünkü onlar cevabın gerçek olduğunu kanıtlayan
pozisyonlarla birlikte gelir.

Bir cüzdanın **ilk** senkronu sessizdir: adres yeni eklendiğinde zaten açık
olan her bahis "yeni hareket" diye kanala düşmez. Bu, anlık görüntünün boş
olmasından değil ayrı bir işaretten (`polymarket_seen`) okunur — çünkü her
şeyi kapatmış bir balinanın anlık görüntüsü de boştur.

---

## Veri tazeliği

Sayfanın başlığındaki **"Veri: <tarih>"** damgası, `Son sorgu`'dan farklı
olarak *verinin* yaşını gösterir. 4 günden eskiyse sarıya, 10 günden eskiyse
kırmızıya döner ve telefonda da görünür.

Bu damga bir olay sonrası eklendi: boş bir veritabanıyla açılışta tüm eski
8-K'lar ayrıştırılmadan "işlendi" işaretleniyordu ve poller onları bir daha
görmüyordu. Site yedi hafta boyunca Temmuz ortasını gösterdi, üstünde her
saniye tıkırdayan bir `Son sorgu` ile. Artık hem engelleniyor
(`mark_current_filings_processed` elindeki en yeni haftadan öteye geçmiyor),
hem de açılışta `reconcile_missing_history()` eksik haftaları alarm atmadan
geri dolduruyor.
