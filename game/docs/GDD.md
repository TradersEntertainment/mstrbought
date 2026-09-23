# Tarihe Bi' Dokun — Oyun Tasarım Belgesi (GDD)

> **Çalışma adı:** *Tarihe Bi' Dokun* (EN: *Poking History*)
> **Bölüm 1:** *Zamanatör 3000 — 1453* (EN: *The Chrono-Matic 3000 — 1453*)
> **Tür:** Birinci şahıs komedi-macera, hafif aksiyon
> **Motor:** Godot 4 · **Platform:** PC (Windows/Linux) → Web → (sonra) konsol
> **Dil:** Türkçe + İngilizce (baştan iki dilli)
> **Hedef:** 15–20 dakikalık oynanabilir demo
> **Belge sürümü:** 0.1 — 2026-09-23

---

## 1. Tek cümlelik özet

Kendini tarih uzmanı sanan bir belgesel bağımlısı, emekli komşusunun koli bandıyla tutturulmuş zaman makinesiyle **1453 İstanbul kuşatmasının ortasına** düşer. "Gelecekten gelen bilgisiyle" Fatih Sultan Mehmet'e yardım etmeye çalışır, ama herkes ondan daha zekidir.

## 2. Oyuncu fantezisi

Herkesin aklından en az bir kere "şimdiki aklımla / şu eşyayla geçmişe gitseydim..." geçmiştir. Oyun bu fanteziyi hem **gerçekleştiriyor** hem de **alaya alıyor**. Gidiyorsun, ama bildiklerin yarım, eşyaların saçma, tarihteki insanlar da sandığından çok daha akıllı.

## 3. Tasarım sütunları

| # | Sütun | Anlamı |
|---|-------|--------|
| 1 | **Her seçim bir espri** | Her eşya, her diyalog seçeneği ve her başarısızlık bir espri ödülü verir. Başarısız olmak da eğlenceli olmalı. |
| 2 | **Durumun saçmalığı, kişinin değil** | Monty Python tarzı absürtlük dünyada ve durumlarda olur. Tarihi figürler (özellikle Fatih) aklı başında ciddi karakterlerdir. |
| 3 | **Çanta = oyun tarzı** | Başta seçilen 5 eşya çözüm yollarını, diyalogları ve sonları değiştirir. Tekrar oynama nedeni budur. |
| 4 | **Tarih kırılabilir** | Oyuncu tarihi gerçekten bozabilir. Dünya bunu hem 1453'te hem 2026'da (telefondaki Vikipedi) gösterir. |
| 5 | **Küçük ama cilalı** | 20 dakikalık, baştan sona oynanan ve paylaşılabilir bir demo; yarım kalmış 2 saatten iyidir. |

## 4. Mizah rehberi

**Ton:** Monty Python absürtlüğü. Dördüncü duvar yıkılabilir, oyun kendi bütçesiyle dalga geçebilir, bürokrasi her yerdedir.

**Kurallar:**
1. **Fatih ciddi karakterdir.** 21 yaşında, birkaç dil bilen, matematik ve mühendisliğe meraklı bir dahi. Espri onun "senden hep bir adım önde olmasından" çıkar, onunla dalga geçilmez.
2. **Din, etnik köken ve kutsal değerler espri malzemesi değildir.** Bizans tarafı da kötü adam değildir, onlar da kendi dertlerinde komik insanlardır.
3. **Anakronizm serbest, yalan tarih bilgisi etiketlidir.** Oyun gerçek tarihi (bkz. §15) bilir; yanlışları kahramanın ağzından ya da "Lise Tarih Kitabı"ndan gelir ve oyun bunları düzeltir.
4. **Kahraman hedefe koyulan kişidir.** Espri çoğunlukla onun kendine güveninin boşa çıkmasıdır.
5. **Başarısızlık = ödül.** Her "yakalandın" ekranı özgün bir espri sahnesidir (bkz. §9.4).

**Tekrar eden espriler (running gags):**
- **"Bütçe nedeniyle..."** Pahalı sahneler karton dekor, ağızla yapılmış ses efekti ya da haritada ilerleyen bir okla geçiştirilir.
- **Hikmet Amca'nın telsizi.** En kritik anlarda cızırdar: *"O kırmızı düğmeye basma... bastın mı?"*
- **Telefonun şarjı.** Her kullanımda düşer ve %1'de oyunun en dramatik müziği çalar.
- **Vikipedi düzenleme savaşı.** Tarih bozuldukça sayfa değişir, "tartışma sayfası" giderek çıldırır.
- **Nöbetçi ikilisi Hasan ile Hüseyin.** Her karşılaşmada kimin kim olduğunu tartışırlar.

## 5. Karakterler

### 5.1 Tolga (oyuncu karakteri) — konuşan kahraman
- **Kim:** 34 yaşında, sigorta şirketinde çalışıyor, gece 3'te belgesel izliyor ve kendini tarih uzmanı sanıyor.
- **Kişiliği:** Çok konuşur, laf sokar, kendine fazla güvenir; özünde iyi niyetli ve korkaktır.
- **Kıyafeti:** Gri eşofman, terlik (çorapla), sırt çantası. 1453'te bu kıyafet her yerde başka bir şey sanılır: derviş, Frenk, deli.
- **Oynanışta:** Diyalog seçenekleri onun ağzından yazılır. Oyuncu *ne söyleneceğini* değil, *Tolga'nın hangi saçmalığı söyleyeceğini* seçer.
- **Replik örneği:** *"Sakin ol Tolga. 20 tane belgesel izledin. Sen bu işin uzmanısın. ...Fethin tarihi neydi? 1435? 1543? Bir 5, bir 3, bir 4 vardı."*

### 5.2 Hikmet Amca (mucit) — emekli, kendini dahi sanan komşu
- **Kim:** Emekli elektrik teknisyeni. Garajında "Zamanatör 3000"ü yapmış. Her şeyi koli bandıyla tamir eder.
- **Rolü:** Tolga'nın çantasına bantladığı telsizle oyun boyunca araya girer; yarı anlatıcı, yarı ipucu sistemidir. İpuçları çoğunlukla yanlıştır ama bazen dâhicedir.
- **Replik örnekleri:**
  - *"Evladım, makinede sadece bir sorun var: çalışıyor. Bunu hiç beklemiyordum."*
  - *"Padişah'a benden selam söyle. Bir de sor, o toplar kaç volt?"*
- **Gizli yönü:** Gizli sonda Fatih'in makineyi ondan daha iyi tamir ettiğini öğrenince bozulur.

### 5.3 Sultan II. Mehmed (Fatih) — ciddi karakter
- **Kim:** 21 yaşında genç padişah. Soğukkanlı, meraklı, keskin zekâlı.
- **Rolü:** Demonun son "boss"u bir diyalog bulmacasıdır. Tolga'nın "gelecek bilgileri"nin çoğunu zaten biliyordur (gemileri karadan yürütme planı çoktan uygulanmıştır).
- **Onu etkileyen:** Bilgi değil, **merak uyandıran şeyler**: hesap makinesi, Rubik küpü, bir mühendislik fikri, dürüstlük.
- **Replik örneği:** *"Gemileri karadan mı yürütelim diyorsun? ...Dün yürüttük. Sen de üstlerinden birinin önünde kayıyordun. Hatırladın mı?"*

### 5.4 Tercüman Lütfi
- Yedi dil bildiğini iddia eder; Tolga'nın modern Türkçesini "tercüme" eder.
- **Espri motoru:** Deyimleri birebir çevirir. "Kafayı yedim" → *"Bu adam bir kafa yemiş, efendim. Kimin kafası olduğu henüz bilinmiyor."*
- Otağa giden **Yol B**'nin anahtarıdır.

### 5.5 Usta Urban (topçu)
- Macar top dökümcüsü. Huysuz, mükemmeliyetçi, büyük toplara takıntılı.
- Tolga ona "bu top çatlayacak" diye uyarmaya çalışır; Urban bunu mesleki hakaret sayar.
- **Yol C**'nin anahtarıdır: telefonun hesap makinesini görünce ona "cin" der ve cini satın almak ister.

### 5.6 Aşçıbaşı Kadri
- Ordugâhın mutfağının hâkimi. Leblebiyi hayatında ilk kez görür ve hemen yeni bir yemek icat etmeye kalkar.
- **Yol A**'nın anahtarıdır: aşçı kılığı ve "Sultan'ın sofrasına yeni lezzet" bahanesi.

### 5.7 Nöbetçiler Hasan ile Hüseyin
- İki yeniçeri. Hangisinin Hasan olduğu konusunda anlaşamazlar.
- Gizlilik bölümlerinin "koruma" NPC'leridir; şüphelenme mantıkları bilerek aptalcadır ama tutarlıdır.

### 5.8 Kapı Bekçisi (Sorucu Ağa)
- Otağın kapısında durur ve Holy Grail'deki köprü bekçisi gibi **üç soru** sorar. Cevaplar çantadaki eşyalara göre değişir.
- *"Adın ne? Buraya niye geldin? ...Bir devenin günde kaç okka su içtiğini bilir misin?"*

### 5.9 Denetçi Nihat Zamanoğlu (Zaman Bürosu)
- Takım elbiseli, dosya taşıyan, sonsuz sabırlı bir memur. **Paradoks Metresi** eşiği aşınca belirir.
- Tolga'ya **Form Z-1453**'ü (üç nüsha, ıslak imza) doldurtur. Bu, oyuncuyu engelleyen ama komik bir bürokrasi mini oyunudur.
- Bir sonun sahibidir (bkz. §10).

### 5.10 Çandarlı Halil Paşa (arka plan, opsiyonel)
- Kuşatmaya karşı çıkan temkinli sadrazam. Tolga'yı "barış elçisi" sanıp kendi planına alet etmeye çalışabilir.
- Demoda sadece bir yan diyalog ve bir sonun ipucudur; ileride genişletilebilir.

## 6. Hikaye

### 6.1 Önbilgi
2026, İstanbul, gece 03:12. Tolga yine bir fetih belgeseli izliyor ve "Ah ben orada olsaydım, şimdiki aklımla..." diye iç çekiyor. Kapı çalıyor: pijamalı Hikmet Amca. *"Evladım, gel bir bak şuna. Büyük bir buluş yaptım ve deneyecek birine ihtiyacım var. Tercihen sigortalı."*

### 6.2 Olay örgüsü (demo)
1. **Garaj:** Tolga Zamanatör'ü görüyor, çantasını hazırlıyor, tarihi girmeye çalışıyor. **1453** yazıyor, makine bunu **14:53** okuyor. Hikmet makineye tekme atıyor. Işık.
2. **22 Nisan 1453:** Tolga, Osmanlı gemilerinin karadan Haliç'e indirildiği yağlı kızakların üstüne düşüyor. Arkasında bir kadırga yokuş aşağı geliyor. **Koş!**
3. **Yakalanma:** Kovalamaca sonunda Zağanos Paşa'nın askerleri onu "garip giyimli casus" olarak yakalıyor. **(Bütçe sahnesi:** ana ordugâha yolculuk haritada kesik çizgili bir okla gösterilir. Hikmet: *"Bu sahneye bütçe yetmedi evladım."*)
4. **Ordugâh:** Tolga çadırdan kaçıyor. Amacı Padişah'ın otağına varmak. 3 yol var (§8.3).
5. **Otağ kapısı:** Sorucu Ağa'nın üç sorusu.
6. **Huzur:** Fatih'le diyalog bulmacası. Tolga'nın her "gelecek bilgisi" boşa çıkıyor, ama doğru eşya ve doğru tavırla Fatih'in ilgisini çekebiliyor.
7. **Son:** Paradoks puanı ve verilen kararlara göre 4 sondan biri (§10).

### 6.3 Büyük resim (demo sonrası)
Zamanatör her seferinde yanlış bir döneme atıyor. Gelecek bölüm fikirleri §14'te. Hikmet Amca ile Denetçi Nihat seriyi bağlayan karakterlerdir.

## 7. Oynanış mekanikleri

### 7.1 Temel kontroller
| Eylem | Klavye/Fare | Gamepad |
|-------|-------------|---------|
| Hareket | WASD | Sol analog |
| Bakış | Fare | Sağ analog |
| Zıplama | Space | A |
| Eğilme / gizlenme | Ctrl / C | B |
| Koşma | Shift | Sol analog bas |
| Etkileşim / konuş | E | X |
| Eşya kullan / fırlat | Sol tık | RT |
| Eşya göster (NPC'ye) | Sağ tık | LT |
| Çanta çarkı | Tab / fare tekerleği | LB/RB |
| Telefon | F | Y |

### 7.2 Çanta sistemi
- Garajda **10 eşya** var, çantaya **5 tane** sığıyor (§8).
- Her eşyanın 3 kullanımı vardır: **Kullan** (fiziksel etki), **Göster** (NPC tepkisi), **Ver** (NPC'ye bırakmak, geri alınamaz).
- **Göster matrisi:** Demodaki her konuşan NPC, çantadaki her eşyaya **özel bir replikle** tepki verir. 10 eşya × 8 NPC = 80 kısa replik. Bu, oyunun ana ödül döngüsüdür. Oyuncular bunu paylaşır, bu da oyunun reklamı olur.

### 7.3 Diyalog sistemi
- Dallanan diyalog ağaçları var. Her düğümde 2–4 Tolga repliği ve varsa bir **[Eşya göster]** seçeneği bulunur.
- Bazı seçeneklerin **ton etiketi** vardır: 😎 Ukala, 😰 Panik, 🤓 Belgesel bilgisi. Sonuçları NPC'ye göre değişir.
- "🤓 Belgesel bilgisi" seçenekleri **%50 yanlış** bilgi içerir; oyuncu hangisinin doğru olduğunu Vikipedi'ye bakarak anlayabilir (şarj harcar).

### 7.4 Şüphe Metresi (gizlilik)
- Ordugâhta her NPC'nin başının üstünde bir şüphe ikonu var: ❔ → ❓ → ❗.
- Eşofman, koşmak, telefonun ışığı ve anakronik konuşma şüpheyi **artırır**. Kılık, kalabalıkta durmak ve "yerel" diyalog seçimi şüpheyi **azaltır**.
- ❗ olunca kovalamaca başlar. Yakalanmak oyun sonu değildir: bir **"Yakalandın" skeci** oynatılır ve oyuncu en yakın kontrol noktasından devam eder.

### 7.5 Hafif aksiyon (silahsız)
- **Fırlatma:** Leblebi (dikkat dağıtır), testi (kırılır, ses çıkarır), yastık (sersemletir, 2 saniye).
- **Kovalamaca sahneleri:** Kızak kaçışı (açılış) ve ordugâh kaçışı. Engeller ve kaygan zeminlerle fiziğe dayalı komedi.
- **Doğaçlama:** Selfie çubuğu kısa menzilli dürtme aleti olarak kullanılabilir: *"Hop! Hop! Mesafe lütfen!"*
- Can barı yok. Çok darbe yersen sersemlersin ve yakalanırsın (§7.4).

### 7.6 Telefon (%14)
| Uygulama | İşlevi | Şarj maliyeti |
|----------|--------|---------------|
| Çevrimdışı Vikipedi | Doğru tarih bilgisi + tarih bozuldukça değişen sayfalar | %1 / açılış |
| Hesap makinesi | Urban ve Fatih'i etkiler ("cin") | %1 |
| Fener | Karanlıkta yol; NPC'lerde şüpheyi çok artırır | %1 / 10 sn |
| Kamera | Selfie. Her önemli NPC'yle "fotoğraf albümü" koleksiyonu | %1 |
| Müzik | Mehter parodisi / pop şarkı çalar, bir sahnede nöbetçiler dans eder | %2 |

- **%1'de** ağır dram müziği çalar. **%0'da** telefon "tuğla" eşyasına dönüşür: gerçek bir tuğla gibi fırlatılabilir.
- Powerbank şarjı +%40 artırır (tek kullanımlık).

### 7.7 Paradoks Metresi
- Tarihi bozan her eylem puan verir: bir NPC'ye gelecek bilgisi vermek, Urban'ın topunu "düzeltmek", Fatih'e modern bir eşya bırakmak.
- **Eşikler:**
  - **0–29:** Tarih sağlam. Vikipedi değişmez.
  - **30–59:** Vikipedi'de küçük tuhaflıklar ("İstanbul'un fethinde bir eşofmanlının da bulunduğu iddia edilmektedir[kaynak belirtilmeli]").
  - **60–89:** Denetçi Nihat ilk kez belirir ve **Form Z-1453** mini oyununu başlatır.
  - **90+:** Gerçeklik kırılır, sonlar açılır (§10).
- Metre ekranda gösterilmez. Değerini dolaylı olarak Vikipedi'den ve Hikmet'in telsizdeki panik seviyesinden anlarsın.

## 8. Eşyalar (10 eşya, 5 seçilir)

| # | Eşya (TR / EN) | Kullan | Göster/Ver — öne çıkan etkisi | Açtığı yol/son |
|---|----------------|--------|-------------------------------|----------------|
| 1 | **Telefon %14** / *Phone 14%* | Uygulamalar (§7.6) | Urban: "cin kutusu"; Fatih: gerçekten ilgilenir | Yol C, Gizli son |
| 2 | **Çakmak** / *Lighter* | Işık, fitil yakma | Hasan: "büyücü!", Hüseyin: "tütün var mı?" | Kızakta kestirme |
| 3 | **Lise Tarih Kitabı (9. sınıf)** / *High School History Book* | Oku: ipucu (yarısı yanlış) | Fatih kendi portresini görür: *"Burnumu büyük çizmişler."* | Leblebipolis sonu |
| 4 | **Bir poşet leblebi** / *Bag of Roasted Chickpeas* | Fırlat: dikkat dağıt | Aşçıbaşı yeni yemek icat eder | Yol A, Leblebipolis sonu |
| 5 | **Powerbank** / *Power Bank* | Telefonu şarj et (+%40) | Görünüşü yüzünden "kutsal taş" sanılır | — |
| 6 | **Koli bandı (Hikmet'in)** / *Duct Tape* | Tamir et / bağla / kapıyı kilitle | Urban çatlak topu bantlar (paradoks +20) | Gizli son (makine tamiri) |
| 7 | **Termos çay** / *Thermos of Tea* | İç: koşma süresi +; ver: dostluk | Nöbetçiler çay için 5 dakika mola verir | Gizlilik kolaylığı |
| 8 | **Selfie çubuğu** / *Selfie Stick* | Dürt / uzaktaki eşyayı al | Sorucu Ağa onu "asa" sanar, bir soruyu atlar | Kapı kestirmesi |
| 9 | **Kolonya (limon)** / *Cologne* | Sersemlemiş NPC'yi ayılt | Otağda herkesin eline döker: diplomasi bonusu | Huzurda bonus seçenek |
| 10 | **Rubik küpü** / *Rubik's Cube* | Oyna (hiçbir şey olmaz) | Fatih 40 saniyede çözer. Tolga'nın hayatı sorgulaması. | Fatih'le en iyi bağ |

**Denge notu:** Her yol en az 3 farklı eşya kombinasyonuyla açılabilmeli. Hiçbir 5'li seçim oyunu çözülemez hale getirmemeli: her bölgede "eşyasız" bir yedek çözüm olmalı (daha uzun, daha komik).

## 9. Demo akışı — bölüm bölüm

### 9.1 Bölüm 0 — Hikmet'in Garajı (≈3 dk)
- **Amaç:** Kontrolleri öğretmek, çanta seçmek, karakterleri tanıtmak.
- **Olaylar:**
  1. Kapı çalar, Hikmet garaja davet eder. Yürüme ve bakınma öğretilir.
  2. Garajda 10 eşya dağınık hâlde durur (bkz. §8). Her birine bakınca Tolga ve Hikmet atışan bir yorum yapar. Eşya alma öğretilir.
  3. Çanta dolunca Hikmet: *"Beşten fazla sığmaz. Ben denedim, çanta patladı, o yüzden koli bandı var."*
  4. Zamanatör paneli: oyuncu yılı tuşlarla girer. **1453 → 14:53.** Hikmet makineye tekme atar. Işık.
- **Gizli detay:** Garajın duvarında boş bir çerçeve var. Gizli sonda içinde bir portre belirir.

### 9.2 Bölüm 1 — Kızak Kaçışı, 22 Nisan 1453 (≈3 dk)
- **Amaç:** Güçlü bir açılış, fiziğe dayalı komedi, dünyayı tanıtmak.
- **Olaylar:**
  1. Tolga, gökten yağlı kızakların üstüne düşer. Kameranın ilk görüntüsü: tepeden aşağı inen bir kadırganın pruvası.
  2. **Koşu bölümü:** Kaygan kızaklar, yuvarlanan kütükler, şaşkın askerler. Çakmak varsa yağlı bir kütüğü yakıp bir kestirme açılabilir.
  3. Sonunda Haliç kıyısına düşer, Zağanos Paşa'nın askerleri etrafını sarar.
  4. **Bütçe sahnesi:** Ordugâha yolculuk, haritada kesik çizgili okla gösterilir. Hikmet'in telsiz yorumu.

### 9.3 Bölüm 2 — Ordugâh (≈8 dk)
- **Harita:** Küçük, yoğun bir açık alan: esir çadırı, mutfak, topçu alanı, tercüman çadırı, pazar yeri, otağa giden yol.
- **Başlangıç:** Tolga bir esir çadırında. Çıkış bulmacası: nöbetçi ikilisi Hasan ile Hüseyin'in "kim kim" tartışmasını kullanarak kaçmak.
- **Otağa giden 3 yol:**

| Yol | Anahtar NPC | Özeti | Önerilen eşyalar |
|-----|-------------|-------|------------------|
| **A — Mutfak** | Aşçıbaşı Kadri | Leblebiyi göster, "yeni lezzet"i Sultan'ın sofrasına taşıyan aşçı yamağı kılığına gir | Leblebi, Termos, Kolonya |
| **B — Tercüman** | Tercüman Lütfi | Lütfi'yi ikna et. Onun berbat tercümelerini düzeltmeye çalışırken Padişah'a "Frenk elçi" olarak götürül | Tarih kitabı, Telefon (Vikipedi) |
| **C — Topçu** | Usta Urban | Hesap makinesi "cin"i ile Urban'ı etkile; top denemesini izlemeye gelen Padişah'ın karşısına onun çırağı olarak çık | Telefon, Koli bandı, Rubik küpü |

- **Yedek yol (eşyasız):** Pazar yerinde 3 küçük iyilik yap: kaçan keçiyi yakala, kayıp mühür yüzüğünü bul, bir askerin mektubunu yaz. Karşılığında bir kaftan alırsın. Uzun, ama komik.
- **Yan içerik:** Çandarlı Halil Paşa'nın adamı Tolga'ya gizli bir mektup teklif eder. Kabul edersen paradoks artar, ayrıca bir son ipucu açılır.

### 9.4 "Yakalandın" skeçleri (tüm bölümlerde)
Her yakalanmada bir tanesi rastgele oynatılır (tekrar etmeyecek şekilde). Örnekler:
- Hasan ile Hüseyin, Tolga'yı kimin yakaladığını tartışırken Tolga ortada bekler. Kontrol noktasına dönülür.
- Ekran bir tarih kitabı sayfasına dönüşür: *"Sayfa 214: Kuşatma sırasında eşofmanlı bir casus yakalandı ve bulaşık yıkamaya verildi. Tarihe etkisi: yok."*
- Hikmet telsizden: *"Evladım, geri sarıyorum. Bu makinede geri sarma yoktu ama... bir şekilde oldu."*

### 9.5 Bölüm 3 — Otağ kapısı ve huzur (≈5 dk)
- **Kapı:** Sorucu Ağa'nın 3 sorusu. 3. soru her seferinde saçma bir sorudur. Yanlış cevapta *hafifçe* dışarı atılırsın (skeç). Selfie çubuğu bir soruyu atlatır.
- **Huzur — diyalog bulmacası:**
  - Fatih, Tolga'yı dinler. Tolga'nın her "gelecek bilgisi" için Fatih'in hazır bir karşılığı vardır.
  - Kazanmak için 3 **Merak Puanı** gerekir. Bunlar gelir:
    - ilginç bir eşyayı göstermekten (Rubik küpü, hesap makinesi, tarih kitabındaki portre),
    - dürüst bir itiraftan ("Aslında hiçbir şey bilmiyorum" = +1, bu Fatih'i en çok şaşırtan seçenektir),
    - bir mühendislik sorusundan (Urban'ın topu hakkında doğru bir yorum).
  - Kötü seçimler, Fatih'in Tolga'yı kibarca "danışman" olarak mutfağa göndermesiyle biter; oyuncu tekrar deneyebilir.
- **Kilit an:** Fatih sorar: *"Madem gelecektensin, söyle bakalım. Bu şehir alınacak mı?"* Oyuncunun cevabı, paradoks puanıyla birlikte sonu belirler.

## 10. Sonlar (demoda 4 son)

| Son | Koşul | Özeti |
|-----|-------|-------|
| **1. "Tarih Yerinde"** (gerçek son) | Paradoks < 30; kilit soruda "Bunu size söyleyemem" | Fatih gülümser: *"Doğru cevap."* Tolga'yı hediyelerle yolcu eder. Tolga 2026'ya döner, hiçbir şey değişmemiştir, ama çantasında 1453'ten kalma bir kaftan vardır. Hikmet: *"Bunu bana ver, garaja asacağım."* |
| **2. "Leblebipolis"** | Leblebi Aşçıbaşı'na verildi + tarih kitabı Fatih'e gösterildi + paradoks ≥ 60 | Leblebi orduya "moral yemeği" olur, şehir adını değiştirir. 2026'ya dönüşte her tabelada *Leblebipolis* yazar, Vikipedi'nin tartışma sayfası 40.000 mesaja ulaşmıştır. |
| **3. "Form Z-1453"** (bürokrasi sonu) | Paradoks ≥ 90 ya da Denetçi mini oyununda başarısızlık | Denetçi Nihat, Tolga'yı "Zaman Bürosu Bekleme Salonu"na alır. Sıra numarası: 4.582.119. Salonda başka dönemlerden gelmiş, eşofmanlı başka "Tolgalar" oturmaktadır. |
| **4. Gizli son: "Sultan'ın Tamiri"** | Koli bandı + Rubik küpü + telefon Fatih'e gösterildi, 3 Merak Puanı, Paradoks < 60 | Fatih bozuk Zamanatör'ün uzaktan kumandasını 3 dakikada tamir eder ve Tolga'yı **tam doğru** zamana geri gönderir. Garajdaki boş çerçevede artık Fatih'in makineyi tutarken yapılmış bir portresi vardır. Hikmet: *"...Benden iyi tamir etmiş. Kimse duymasın."* |

Demo, hangi sonla biterse bitsin, "**Bölüm 2 yakında: Zamanatör bu sefer [bulanık] yılına atıyor...**" kartıyla kapanır.

## 11. İki dil ve yerelleştirme

- **Kural:** Koda hiçbir yazı gömülmez. Tüm metinler anahtarlarla tutulur (`DLG_URBAN_CALC_01`, `ITEM_CHICKPEA_NAME`...).
- **Format:** Godot'nun yerleşik çeviri sistemi (`TranslationServer`), CSV kaynağı: `keys,tr,en`.
- **Kelime oyunları:** Birebir çevrilmez, her dil için ayrı yazılır. Anahtarın yanında `note` sütunu olur ("TR'de deyim esprisi; EN'de eşdeğer bir espri yaz").
  - Örnek: Lütfi'nin "kafayı yedim" tercümesi EN'de *"I'm losing my head"* → *"He says he is losing his head, Sultan. Shall I fetch the executioner to help him look?"*
- **Sabit kalan espriler:** "1453 → 14:53", görsel espriler, Leblebipolis (EN: *Chickpeapolis*).
- **Font:** Türkçe karakterleri (ğ, ş, ı, İ) destekleyen, el yazısına yakın bir font + okunaklı bir UI fontu.
- **Seslendirme:** Demoda gerçek seslendirme yok. Karakterler Animal Crossing tarzı **anlamsız mırıltılar** çıkarır, konuşmalar altyazıyla verilir. Maliyet sıfır, iki dilde de çalışır, komik bir etki verir.

## 12. Görsel ve ses yönü

### 12.1 Görsel
- **Low-poly çizgi film:** Abartılı oranlar (büyük kafalar, büyük eller), düz renkler, hafif kontur.
- **Renk paleti:** 1453 sahnesi sıcak toprak tonları, kırmızı-altın otağ ve Haliç'in turkuazıdır. 2026 garajı soğuk floresan, gri ve turuncu koli bandıdır.
- **"Bütçe" estetiği:** Bazı arka planlar bilerek karton dekordur. Bazı NPC'ler tahta çubuğa yapıştırılmış 2D figürlerdir ve bu oyunda açıkça söylenir.
- **Referanslar:** *Totally Accurate Battle Simulator* (oranlar), *Untitled Goose Game* (düz renkler), *Monty Python* kolaj animasyonları (geçiş sahneleri).

### 12.2 Ses
- **Müzik:** Mehter marşının komik aranjmanları (tuba, kazoo), gerilim anları için "ciddi" orkestra parodisi.
- **Ses efektleri:** Önemli anlarda bilerek ağızla yapılmış sesler ("pıııııv!", "güm!").
- **UI:** Telsiz cızırtısı, telefon bildirimleri, Denetçi'nin damga sesi.

## 13. Teknik plan (Godot 4)

### 13.1 Klasör yapısı (planlanan)
```
game/
  docs/            # tasarım belgeleri (bu dosya)
  project.godot
  scenes/
    levels/        # garage, slipway, camp, tent
    characters/    # player, npc_base, her NPC
    ui/            # dialogue_box, inventory_wheel, phone, wiki
  scripts/
    autoload/      # GameState, Inventory, Paradox, Dialogue, Suspicion
    player/
    npc/
    items/
  data/
    items/         # eşya tanımları (.tres Resource)
    dialogue/      # diyalog ağaçları (JSON)
    wiki/          # Vikipedi sayfa varyantları
  i18n/
    strings.csv    # keys,tr,en,note
  assets/
    models/ textures/ audio/ fonts/
```

### 13.2 Çekirdek sistemler (autoload)
| Sistem | Görevi |
|--------|--------|
| `GameState` | Bayraklar (flags), kontrol noktaları, seçilen yol, kayıt/yükleme |
| `Inventory` | 5 slot, kullan/göster/ver, eşya kaynakları |
| `Paradox` | Puan, eşik sinyalleri (Denetçi, Vikipedi, son hesaplama) |
| `Dialogue` | JSON diyalog ağaçlarını oynatır; koşullar (flag, eşya, paradoks) ve efektler |
| `Suspicion` | NPC başına şüphe değeri, algı konisi, kovalamaca tetikleme |

### 13.3 Diyalog verisi (örnek)
```json
{
  "id": "urban_intro",
  "nodes": {
    "start": {
      "speaker": "urban",
      "text": "DLG_URBAN_INTRO_01",
      "choices": [
        { "text": "DLG_TOLGA_CRACK_WARN", "tone": "smug", "next": "offended", "paradox": 5 },
        { "text": "DLG_TOLGA_ADMIRE",     "tone": "panic", "next": "flattered" },
        { "show_item": "phone", "next": "calc_djinn", "requires": { "battery_min": 1 } }
      ]
    }
  }
}
```

### 13.4 Performans hedefi
- Orta seviye bir dizüstü bilgisayarda 60 FPS, web sürümünde 30 FPS.
- Low-poly + düz renkli materyaller ve basit gölgeler kullanılacak.

## 14. Kapsam ve yol haritası

| Aşama | İçerik | Çıktı |
|-------|--------|-------|
| **M0 — Tasarım** | Bu belge, diyalog taslakları, eşya/NPC tepki matrisi | ✅ GDD v0.1 |
| **M1 — Oynanabilir garaj** | FPS kontrolcüsü, etkileşim, çanta seçimi, i18n altyapısı, Zamanatör paneli | Yürünebilen garaj sahnesi |
| **M2 — Kızak kaçışı** | Fiziğe dayalı koşu bölümü, kovalamaca, "bütçe" geçişi | İlk "vay be" anı |
| **M3 — Ordugâh** | Şüphe sistemi, 3 yol + yedek yol, 6 NPC, göster matrisi | Demonun gövdesi |
| **M4 — Huzur ve sonlar** | Fatih diyalog bulmacası, paradoks sistemi, 4 son, Vikipedi | Baştan sona oynanan demo |
| **M5 — Cila** | Ses, müzik, skeçler, EN çeviri geçişi, web build, test oyuncuları | Paylaşılabilir demo linki |

**Kapsam dışı (demo için):** Seslendirme, kuşatma finali (29 Mayıs), kayıt yuvaları, başarımlar.

**Gelecek bölüm fikirleri:**
- **Kanuni dönemi:** Mimar Sinan'a "deprem yönetmeliği" anlatmaya çalışmak.
- **Antik Mısır:** Piramit inşaatında proje yöneticisi olmak ("Bu bir Gantt şeması, firavunum").
- **1923:** Nüfus kâğıdını kaybetmiş bir zaman yolcusu olmak.
- **Truva:** "O at hediye değil!" diye bağırmak ve kimseyi inandıramamak.

## 15. Tarihsel notlar (doğruluk kontrolü)

Oyunun "doğru bildiği" gerçekler. Tolga'nın yanlışları bunlarla karşılaştırılarak yazılır.

- Kuşatma **6 Nisan 1453**'te başladı, şehir **29 Mayıs 1453**'te alındı.
- II. Mehmed **30 Mart 1432** doğumludur; kuşatma sırasında **21 yaşındaydı**.
- Osmanlı gemileri **22 Nisan 1453** gecesi Galata'nın arkasındaki tepelerden, yağlanmış kızaklar üzerinde karadan **Haliç'e** (Kasımpaşa tarafına) indirildi. Böylece Haliç'in girişindeki zincir aşılmış oldu.
- Macar dökümcü **Urban (Orban)** dev toplar döktü. Büyük topun kuşatma sırasında çatladığı rivayet edilir.
- Padişahın otağı kara surlarının karşısında, **Topkapı (St. Romanus)** kapısının karşısındaki tepede kuruluydu.
- **Zağanos Paşa** Galata/Haliç tarafındaki kuvvetleri yönetti. Sadrazam **Çandarlı Halil Paşa** kuşatmaya temkinli yaklaşıyordu.
- Bizans tarafında son imparator **XI. Konstantinos** ve Cenevizli komutan **Giovanni Giustiniani** vardı. Galata'daki Cenevizliler resmen tarafsızdı.
- **Leblebi:** Kökeni tartışmalıdır. Oyunda "ilk kez görülen" bir şey olarak kullanılması bilinçli bir anakronizm esprisidir (§4, kural 3).

## 16. Açık sorular

1. Oyunun resmi adı "Tarihe Bi' Dokun" mu olsun, başka bir öneri mi var?
2. Tolga'nın görünüşü: eşofman + terlik mi, yoksa takım elbise mi (iş çıkışı)?
3. Fatih'in diyalog yazımında dil ne kadar "dönem" kokmalı: sade günümüz Türkçesi mi, hafif Osmanlıca mı?
4. Demoda Bizans tarafından bir karakter olsun mu (ör. surdan bağıran, kendini haklı çıkarmaya çalışan bir Bizans askeri)?
5. Tolga'nın gerçek dünyadaki hayatı (iş, aile) sonlarda değişsin mi? Örneğin Leblebipolis sonunda sigortacı yerine "Leblebi Bakanı" olmak.
