# Pazar günü yapılacaklar (İstanbul uyarlamasının sonu)

Hazırlandığı an: 17 Kasım. Durum: 0.99.123 yayında (yeni surda 15 bölüm); 0.99.124 tam testte (yeni surda 27 bölüm).
Görev yazıları hazır ve danışman (Fable) incelemesinden geçti: `devir/gorev/prompt_C12_fon.txt`, `devir/gorev/prompt_A14.txt`.
Taban dal: `wip/ist2-taban19` = a38ad405.

## A. Son taşıma (1 yardımcı, ≈3–4 saat)
1. **8y**: siper kenarında çömelen asker yerden 18 cm havada. Kök neden bulunacak, tek zemin yapılacak; sonra 8y yeni sete
   geçer (bugün geçici anahtarla eski sette).
2. **13, 23, 24**: şehir meydanı (hub) bölümleri yeni dünyaya ve yeni sura. 24'ün ikinci yarısı Ayasofya'da; iki dünya temiz
   birleşmezse 24 eski sette kalır.
3. **Uzaktan görünen şehir meydanı**: başka bölümlerden bakınca hâlâ kutu sur var.
4. **31o**: fetihten sonra Romanos iç kapısı ve yıkık şehir.
5. **41o** (gedikli sur) ve **42b** (sağlam sur, 7 Nisan): talim meydanları; sur arkada.
6. **17o** (Haliç'in karşı kıyısından uzak surlar): ölçülecek. **21o** (lağım, yeraltı): taşınacak sur yok, doğrulanacak.
7. **10h gedik molozu**: soluk beyaz, yuvarlak dev kayalar gibi; koyu, köşeli taş ve tuğla parçası olacak.

## B. Görünüş turu (1 yardımcı, aynı anda, ≈3–4 saat)
1. **Romanos kapısının kemeri**: iri, parlak turuncu bloklar (oyuncak gibi) → gerçek ölçü tuğla/taş; kapı kanadına tahta
   damarı ve çivi. (8y, 6b, 7b, 10h, 12b ve 26'nın finalinde görünüyor.)
2. **Harpuşta** (mazgal dişlerinin taş başlığı): yakından koyu, yeşilimsi, pürüzsüz kapak gibi → kaba yontu, açık ton.
   Bütün surlarda (kara, Blakherna, deniz).
3. **Sur yolu ve rıhtım döşemesi**: yakından kiremit-kahve, iri, düz → gerçek ölçü taş, gri-bej, aşınmış.
4. **Şehirde Haliç ve Marmara kıyı surları**: çoğu hâlâ eski kutu dişli (yalnız 96 m'lik dilimler yeni) → yeni deniz suru
   kalemiyle; uçuş bölümünde (7) ve havadan karede görünür.
5. **Blakherna**: pavez (büyük kalkan) düz levha; zemin iki ton keskin sınır; saray önünde ince beyaz çubuk sütunlar.
6. Yetişirse: hendeğin dış kıyısı cetvel gibi düz; 250 m'den uzak deniz surları eski kutu; 17/19'da kıyı arazisi rıhtımı
   örtüyor ve sur ucunda kopukluk.

## C. Sürüm 0.99.125 — "İstanbul uyarlaması tamam"
Birleştirme + kendi doğrulamam (≈1 saat), tam test paketi (≈1,5 saat), GitHub derlemesi (≈1,5–2 saat), sürüm notu
(yeni surdaki bütün bölümler + kalan varsa açıkça).

## D. Senden karar bekleyenler
1. **10h gediği**: yeni surda oyunun gediği dış surda ve şehir yanından ulaşılamıyor; gedik şimdilik iç surun dibinde
   (sur gövdesinde yarık görünmüyor). (A) şehir meydanına gedik kesimi + iç poterna eklenir, yürüyüş ≈20 m uzar;
   (B) bugünkü gibi kalır. Önerim: B, görünüşü düzelterek.
2. **Kapı kanatları**: şehir meydanında Romanos'un iç ve dış kapısı açık duruyor (eskisinde de açıktı). Kuşatmada kapalı
   mı olsun?
3. **Ek Claude hesabı**: oyun için ayrı hesap düşünüyorsan, geçmeden önce bu klasördeki devir dosyaları yeterli; yeni
   hesaptaki oturum buradan devam eder.
4. **ElevenLabs anahtarı**: sohbette paylaşılan anahtarı sil ya da yenile.

## E. İzlenen küçük açıklar (Pazar'a şart değil)
- 26'da yedek askerleri ayıran yeni düzeltme gerçek bir iç içe geçmede henüz hiç tetiklenmedi (çalıştığı kanıtlanmadı).
- 26o eski sette (geri dönüş seçeneği) bir koşuda açıklanamayan başarısızlık; 10 tekrarda çıkmadı.
- 30o'da düşmanın dış kenardan atılması yeni sette daha sık (17 koşuda 5, eskide 12'de 1).
- 17 eski sette Büro sahnesinde bir kez yürüme denetimi satırı (kök neden bulunamadı).
- 12b'de bölümün kendi ordugâhı ile yeni dünyanın ordugâhı üst üste görünebilir.
- **Yeni sette surun ardı boş (23 Kasım, 0.99.125 tam paketi):** `SurSetSahne` ova alanını `world = false` kurar; eski setin
  surun ardına kurduğu yürünür şehir (WorldWalk) ve yaşayan kalabalık (CityLife) yeni sette yok. 31o'da CITYCHECK yakaladı
  (tepeden karede yanık caddenin ötesi boş kum) → 31o bu sürümde varsayılan eski sette (`SurSet.ESKI_VARSAYILAN`,
  `--yenisur=31o`). Aynı eksik daha önce taşınan sur bölümlerinde de olabilir (26/26o vb.; oyuncu oralarda surun dibinde
  kalıyor): görsel programda yeni setin ardına şehir (v2 şehri ya da CityLife) bağlanmalı, sonra 31o yeniye geçer.

## F. İstanbul bittikten sonra (senin önceki isteklerin; sırası sende)
1. **Keşif denemesi**: çatılarda hareket, nöbetçiler, sızma görevi, serbest zaman (Ayasofya–Yerebatan mahallesi).
2. **Yerebatan notları**: Yakovos uzaktan seslensin, kayık hep sürülebilsin, diyalog sırasında hareket/kilit göstergesi
   (kuyuya düşüş efekti 0.99.123'te yapıldı).
3. **Metin taraması**: dönem karakterleri kendine "Bizanslı" dememeli (Romalı / Rum).
4. Tolga'nın hareketinde nefes sesi yok (kitaplıkta uygun ses yok).

## G. İstanbul'dan sonra ilk iş: KARAKTER DİLİMİ ("grafikler AI slop" eleştirisi; sahibi: en çok karakterler)
1. Sanat yönü: tek karakter (Bizans askeri) 3–4 üslupta örnek kare → sahibi seçer; karakterlerle dünya aynı dili konuşur.
2. Teknik yol: kodla kurulan parça parça gövde yerine iskeletli, tek parça (deriye bağlı) model; bugünkü sistemler
   (ayak IK, yığılma, tırmanma, el hareketleri, kumaş) bu iskeleti sürer. Uzak kalabalık için bugünkü hafif model kalır.
3. Kaynak: deneme için ücretsiz ve ticari kullanıma açık (CC0) taban insan modelleri + Blender'da dönem giysileri
   (para yok, hızlı); eleştiri sürerse ana kadro (Tolga, Niko, Hikmet, İmparator, Giustiniani) için 3B sanatçı.
4. Deneme dilimi: Tolga'nın birinci şahıs kolları/elleri (oyuncu hep görüyor) + Bizans askeri + 1 ana karakter, tek
   sahnede (12b sur yolu ya da Bölüm 20 gedik); aynı insanlara gösterilir.
5. Sahibinden: sanatçı bütçesi var mı (varsa önce ana kadro).

## H. Sahibinin hedefi (17 Kasım): "grafikleri gören oyunu oynamak istesin, o kadar abartalım"
Program (İstanbul bitince, karakter dilimiyle başlar; çok haftalık):
1. Güçlü, kendine has sanat yönü (önerim: sıcak, resimsi, stilize; komedi tonuna uyar, az varlıkla çok iyi görünür).
2. Görüntüleme kipini yükseltmek (gl_compatibility → Forward+: ortam gölgesi, dolaylı ışık, sis, iyi gölge, renk
   düzenleme) — tek başına en büyük sıçrama; bedeli en düşük donanım şartı ve test hattının (yazılımsal Vulkan) uyarlanması.
3. Karakterler (iskeletli, yüz ifadeli; ana kadro için sanatçı), birinci şahıs eller.
4. Dokular ve malzemeler (CC0 fotoğraf tabanlı + üsluba göre boyama), ağaçlar ve bitki örtüsü.
5. Sahne sahne ışık ve atmosfer (gün batımı, duman, ateş ışığı, toz), ara sahnelerde kamera ve alan derinliği.
6. Arayüz (yazı tipi, menüler, altyazı kutusu) aynı üsluba.
7. Ölçü: önce|sonra 3 kareyi 5–10 kişiye göster, "oynamak ister misin" sorusu.
İlk dilim: 12b sur yolu gün batımında (renderer + ışık + 3 karakter + dokular), fragman kalitesinde.
Sahibinden: üslup tercihi, sanatçı bütçesi, en düşük donanım (Vulkan destekli ekran kartı) kabulü.

## I. Sahibinin girdileri (19 Kasım, mola sırasında)
1. **Bütçe: 500–1000 $** ("blender'da show yapabiliriz"). Önerilen bölüşüm: %15–20 üslup çizimi (12b sur yolu, gün batımı,
   İmparator ve Tolga), %60–70 modüler karakter seti (1 stilize erkek beden + 5–6 baş: Tolga, Niko, Hikmet, İmparator,
   Giustiniani, sıradan yüz; değiştirilebilir giysi parçaları: Bizans zırhı, Osmanlı kaftanı, sarık, miğfer, sakallar,
   Tolga'nın takımı; birinci şahıs kollar/eller; konuşma, göz kırpma, gülme, kızma yüz ifadeleri), %10–20 düzeltme turları.
   Şartlar: ücretli tek karakterlik deneme, aşamalı ödeme, tam ticari kullanım hakkı + .blend kaynak dosyaları,
   "yapay zekâyla üretilmiş model yok". İlan metni (TR + EN) ve teknik şartnameyi (iskelet/kemik adları, üçgen sınırı,
   doku boyutu, glTF) ben yazarım: sahibi istediğinde ya da Pazar.
2. **MotionBricks** (NVIDIA, https://github.com/NVlabs/motionbricks): 350 000+ hareket klibiyle eğitilmiş, hedef pozlardan
   gerçek zamanlı karakter hareketi üretiyor; açık kaynak (önceden eğitilmiş modeller, yazım araçları, Newton ile örnek
   uygulama). Sahibi: "grafik geliştirdikten sonra kullanacağız". Ne zaman: karakterler iskeletli modele geçtikten SONRA.
   Nasıl: bugünkü poz sistemine (ayak IK, yığılma, tırmanma) hedef poz üreticisi ya da çevrimdışı animasyon klibi üretici.
   Kullanmadan önce kontrol: (a) lisans ticari bir Steam oyununa izin veriyor mu (NVIDIA araştırma lisansları bazen ticari
   kullanımı yasaklar); (b) çalışma zamanı (Python/GPU → Godot'da doğrudan mı, ONNX ile mi, yoksa yalnız çevrimdışı mı);
   (c) iskelet uyumu (eğitim iskeleti ↔ sanatçının iskeleti: sanatçı şartnamesine yazılacak).

## J. Sahibinin sorusu (20 Kasım): "Horizon Zero Dawn gibi geniş alanda özgür koşulan İstanbul ne kadar sürer, 3 Claude Max yeter mi?"
Gösterdiği seviye (4K, AAA) kod hızıyla değil sanat varlığıyla gelir: binlerce elde yapılmış model, doku, bitki, hareket
yakalama ve büyük bir ekip. Hesap sayısı bu darboğazı çözmez. Ulaşılabilir hedef: bugünkü v2 dünyasının (`dunya.gd`: arazi
parçaları yakında 6 m'den uzakta 48 m'ye, oyuncu çevresinde çarpışma, şehir kurucusu) üstünde serbest dolaşılan bir İstanbul
ve stilize ama çekici bir görünüş.
- Aşama 1 (Pazar): İstanbul taşıması biter (0.99.125).
- Aşama 2 (≈1–2 hafta): görsel dilim (12b): Forward+, ışık ve atmosfer, 3 yeni karakter; aynı insanlara gösterilir.
- Aşama 3 (≈2–4 hafta): tek mahalle (Ayasofya–Yerebatan–Hipodrom) serbest dolaşım: akış yüklemesi, kalabalık, bitki örtüsü,
  keşif buluşları, çatılar; orta sınıf ekran kartında 60 kare/sn hedefi.
- Aşama 4 (aylar): bütün şehir + surlar + ordugâh; çevre sanatı için ek sanatçı/varlık bütçesi.
- Hesap: 1 ek hesap (toplam 2) yerinde; 3 hesap ancak sanat hattı kurulduktan sonra anlamlı (darboğaz: sanat, benim
  birleştirme/doğrulama hızım, test makinesi). Çoklu hesap kuralları claude.ai'de kontrol edilecek.
Süreler tahmindir, ölçüm değil.

## K. Fable ikinci göz (23 Kasım, TUR 14 + TAŞIMA 12 kareleri): görsel programın ilk üç turu
Özet: sur taşı artık inandırıcı; "AI slop" hissi surun yanındaki her şeyden geliyor (karakter, ev, zemin, sis, ufuk, ışık).
- **A. Atmosfer ve ışık:** mesafeye bağlı sıcak pus (yakında sıfır; bugün 20 m'deki kule siliniyor, 42b süt beyazı), ton
  eşleme/pozlama, bulutlu gök + uzak arazi/şehir silueti, temas gölgesi/köşe kararması, gece için ayrı ışık kurgusu (soğuk ay +
  sıcak meşale; bugün gece = gündüzün mavi-gri karartılmışı, kapı kanadı gece kararmıyor).
- **B. Tek ressam: karakter + ev:** karakterler düz renk + kalın siyah çizgi + iri kafa, sur yarı gerçekçi doku → iki ayrı
  oyun gibi; tek dil seç (görüntüleme kipi kararıyla birlikte). Evler: dokusuz pastel düzlem, siyah kutu saçak/pencere, levha
  kepenk, çizgi film alevi, boya turuncusu çatı, tuğla şeridi surunkinden iri → evleri sur gölgelendiricisine (sıva, ahşap,
  kiremit), çatı doygunluğu yarıya.
- **C. Zemin ve birleşim:** kapı önünde halka desenli gri zemin, yeşil/turuncu altıgen parke, çime cetvelle kesilmiş meydan
  (42b), sur dibi bıçak gibi toprağa giriyor, kaide suyun üstünde (ıslak hat/köpük yok) → geçiş etekleri, tek zemin paleti;
  sura büyük ölçekli kir/yağmur izi/gülle hasarı; düz yüzeylerde ince moiré (dane frekansı mesafeyle sönsün).
- Küçükler: harpuşta yan yüzü yakında hâlâ koyu zeytin bant; kapı kanadı fazla temiz/açık (kir, çürüme, is); 23 ve 31o
  karelerini güncel dalda yeniden çek (eski kemer o dallarda kalmıştı).
- Sonra bir "afiş karesi" (kapı + muhafız + alçak güneş) hedef ölçütü olarak çekilir.
