# Pazar günü yapılacaklar (İstanbul uyarlamasının sonu)

> **DURUM 23 Kasım 11:40 UTC:** A, B ve C yapıldı. **0.99.125 yayında** (main 88ed3d3c, site 0578246; CI Release #339
> başarılı, indirmeler yüklendi). Birleşik dal `wip/ist2-birlesik` = f1f007c5. Tam paket 456/456 PASS, menüye dönüş 2/2; tek denetim satırı
> (17'de Müfide'nin yolu) düzeltildi, hedefli 13 koşuda temiz. Henüz eski surda: 31o (yeni surun ardında şehir yok; E
> maddesi) ve 17o'nun uzak surları; 21o yeraltında. Sıradaki iş: görsel program (G, H, I) ve E'deki "surun ardı boş".
> **23 Kasım 18:22 UTC:** sahibi "31o ve 17o'yu hallet" dedi. İki yardımcı açıldı: TAŞIMA 13 (31o surun ardı, 8y
> kalıbı; `wip/ist2-tasima13`, yazı `gorev/prompt_T13_31o.txt`) ve TUR 15 (17o uzak surlar; `wip/ist2-tur15`, yazı
> `gorev/prompt_T15_17o.txt`). Teslimden sonra birleştir, tam paket, 0.99.126.
> **24 Kasım 01:50 UTC:** ikisi teslim etti, raporlar ve kareler (tam boy) kabul; `wip/ist2-birlesik` = 3f787c70 (iki
> birleştirme + benim düzeltmem: 31o'nun v2 kurulumu artık bölüm açılışında, yükleme perdesinin altında; eskiden başlık
> kartından sonra 30–50 sn donuk kararmış ekran). 31o dört çeşit + `--eskisur=31o` + 17o PASS, denetim 0. Sözleşme ve
> CITYCHECK/menüye dönüş koşusu (`gorev/dog126b.sh`), sonra tam paket (`gorev/tam126.sh`), temizse 0.99.126
> (`gorev/surum126.py`, `gorev/qa126.md`). Sahibine kareler: `kareler/0_99_126/`.
> **24 Kasım 06:35 UTC: 0.99.126 YAYINDA** (main 7f3814ce, parent 88ed3d3c; `wip/0.99.126`; birleşik cd7f4532; site
> a456e3d; CI Release #340 = 45341370406). Tam paket (`gorev/tam126b.sh`, f957694c) 4×114 PASS, denetim 0, menüye dönüş 2/2.
> **İstanbul uyarlaması tamam: eski surda bölüm kalmadı** (E maddesi kapandı; 21o yeraltında). Sahibinin 8y notları (L)
> 0.99.126'da: rampa görünür, keçiler yerde, donuk bekleme yok. **G16 güncelleyici** teslim edildi, kabul edildi ve birleşik
> dala alındı (e956ba36; Windows değiştirmesi gerçek Windows'ta denenmedi, her hata yolu eski exe'yi geri koyar; ilk gerçek
> deneme 0.99.127 → 0.99.128 geçişinde sahibinin makinesinde olacak). **G17 denetim** sürüyor (`wip/denetim17`).
> Göz kontrolü: `tests/_ist/bakis_kare.*` (otomatik oyun sırasında oyuncunun göz hizasından dört yön, 2×2 kare) yeni sura
> bağlı 33 bölümde koşuyor; bulgular 0.99.127'ye.
> **24 Kasım 08:50 UTC:** CI #340 (0.99.126) TESTLERDE DÜŞTÜ (20 `--difficulty=2` VISAUDIT personhidden D20_G_REPELLED;
> yerelde 0/8) → indirmeler yüklenmedi. Düzeltme (`chapter20.gd _see_giust`: hat doluysa komutan yana gelir; 20'nin 10
> çeşidi PASS) yayın ağacına (cd7f4532 + yalnız bu dosya; güncelleyici 0.99.127'de kalır): main 6ec065b6 → VERSION
> değişmediği için CI tetiklenmedi, etiket gönderimi proxy'de 403 → `.github/release-mirrors.txt`'e `#` açıklama satırı
> (okunmaz) ile main 503b14e8 → **CI #341 (45359520591)**. Birleşik dal 3e79cb5c + mirrors.
> Göz kontrolü bulguları: `devir/GOZ_KONTROLU_BULGULAR.md`, kareler `kareler/0_99_127/`.
> **09:00 UTC:** G18 açıldı (göz kontrolü bulguları 1–4; danışman kökü düzeltti: hub'da şehrin Romanos öğesinin
> `pos.y`'si yama sınırı dışında doğal yükseklikte okunuyor → "iç kuşak" düzlük kaydı peribolosu +0,12'ye çekiyor; çözüm
> `sur_oturtma.ic_y_ozel`). session_01RAjzxKy6HZWoDH7rF8FX1J → `wip/goz18`.
> **10:20 UTC:** CI #341 de düştü: 20 `--difficulty=2` D20_G_DONE (aynı kök; şafak repliği). Yerel tekrar `--max-fps 20`
> olmadan yapılmıştı (0/8; CI 2/2). Düzeltme `_giust_hatti_ac()` iki replikte; 20 FPS'de 8/8 PASS. main d8d34273 → **CI #342
> (45373873762)**. QA dersi taslağı `$S/qa127.md`.
> **10:35 UTC: G18 TESLİM** (rapor `docs/_kanit_goz18/rapor.md` dalda): hub iç kuşak düzlüğü set zemininde (sonda +0,12 →
> −0,08; kapalı yollar birebir aynı), 18b Blakherna Sarayı temsili pencereli/kapılı (`landmarks1453.gd`), 25 "aya" parçası
> evleri tam model (`byz_city.gd _build_fill`); 36b hendek ucu teşhis (hendek içinden görünüyor; dokunulmadı). Birleşik
> 898fec23. G18 geçitteki toprağın setin `SurDibiEtek`'i olduğunu buldu. Yönetici kökü ölçtü: kapı kesiği VAR, ama kapıyı
> iki yandan tutan kulelerin geçide bakan yan kenarının eteği (`sur_oturtma_ag.gd kule()`) geçide giriyordu (8y'de de).
> Düzeltme: geçide bakan kule kenarına etek yok + komşu köşede normal harmanlanmaz. 8y ve 10h geçidi temiz (kareler).
> Doğrulama `gorev/dog127e.sh`: sözleşme altılısı aynı, ZFIGHT 0, 27 kapılı bölüm koşusu PASS → 0e9989f6.
> **11:40 UTC:** CI #342 TESTLER GEÇTİ (paketleme sürüyor). **G17 teslim** (rapor dalda; durum "Bitti" küçük harf): dört
> denetim pakette (görünmez zemin/alet/donuk KESİN, hayvan ADAY), aşçı kökü (`_face_listeners` Soldier), 8y hendek köprüsü
> ayakları, öküzler. Açık: bütün bölümlerin PACE taraması (`tests/_denetim17/pace_tarama.sh`, 6–8 sa) koşulmadı; 26/26o
> Sultan'ın atı (AyakHayvan eğim 17°). Birleşik 3d747148 (G16+G17+G18+etek+20). Tam paket `gorev/tam127.sh` koşuyor.
> **11:50 UTC: 0.99.126 İNDİRMELERİ YAYINDA** (CI #342 başarılı: testler, paket, GitHub Releases ve açık depo yüklendi;
> `releases/latest` → v0.99.126). main d8d34273.
> **13:55 UTC: 0.99.127 main'de** (4c703023; birleşik b583705a; site ec22418) → **CI #343 (45408223153)**. İlk güncelleyici
> sürümü: release.yml artık `dist_ham/` + `guncelleme.json` yüklüyor → CI sonrası açık depoda `guncelleme.json` var mı bak.
> Tam paket tam127: 4×114 PASS; düşüren 3 satır: 31o =petrion_bad personhidden (düzeltildi, 4 çeşit PASS), 26 =nophoto
> Squad overlap ve ESYATEST gomuk=1 (yük altında; tek başına 4/4 temiz) → **AÇIK İŞLER** aşağıda.
>
> **15:25 UTC: 0.99.127 YAYINDA** (CI #343 başarılı, bütün adımlar yeşil). Açık depoda `releases/latest` → v0.99.127;
> `releases/latest/download/guncelleme.json` 200 (`surum` 0.99.127, motor 4.4.1, windows 1290221824 B, linux 1262389712 B,
> sha256'lar); ham ikililer GET 206 (MZ / ELF). Oyunun kendi denetimi gerçek ağda: `GUNCELLEME uzak=0.99.127 yerel=0.99.127
> yeni=hayir kod=200`. 0.99.128 çıkınca 0.99.127 kullananlar menüde bandı görür (Windows değiştirmesinin ilk gerçek denemesi).
> **PACE taraması BİTTİ** (14:10–15:32, `gorev/pace_hepsi.sh`, çıktılar `devir/pace_127/`): 62 bölümün hepsi PASS;
> 16 bölümde 27 DONUKAUDIT (> 4 sn). Yanlış alarm (denetimin meşru listesinde olmayan etkin mini oyun): 35o denge (43,1 +
> 7,3 sn; `phase="slope"`, `balance`), 34o kalıp kırma/kol (38,9), 43o drone pilotajı (25,3). Gerçek adayları: 30 (11,3 sn
> D30_D_EMPEROR, sur tepesi), 17 (10,6 D17_N_LIFT; 8,7 D17E_H_SPY; 5,7 D17E_G_END), 38o (8,1 / 5,6 / 5,1), 35o 9,7
> (D35O_D_01), 24o / 29o / 31o (6,1), 12 (×5 ~5,5 eşya incelemesi), 25 / 26 / 6 / 10a / 30o (4,2–5,0). → 0.99.128 G19:
> denetime "etkin mini oyun" kuralı (denge/drone/tokmak; oyuncunun girdisi işliyor) + gerçek beklemelerin kök düzeltmesi.
> **25 Kasım 05:25 UTC: sahibi "yükleme sorunu, Yanıt vermiyor" dedi.** Kök: bölüm dünyası `_ready`'de tek seferde; v2
> kurucuları `LoadingScreen.pump` çağırmıyor; bölüm ortası kurulumlarda perde yok. **G19 yükleme** açıldı:
> session_01RAjzxKb4yV64iDSc3rLT7v → `wip/yukleme19` (yazı `gorev/prompt_G19_yukleme.txt` + danışman 27 düzeltme).
> **25 Kasım 09:00 UTC: G19 teslim etti (033a6d71), birleşti (288ea111).** v2 açılışlarında en uzun boşluk 29–37 sn →
> 0,6–1,0 sn; perde çarkı/çubuğu artık canlı (RenderingServer); yükleme soğuk ~53 → ~40, ılık ~37 → ~29 sn; önbellek
> artık bölge değişiminde ve her oturumda silinmiyor. B6 (uzak ordugâh ertelemesi) yapılmadı; hub_sehir atlanamadı
> (üçgen karması). Benim eklerim (kayıtsız, tam paket koşuyor): YUKLEMEAUDIT_KESIN eşiği 2500 → 5000 ms (26 aya ön
> testte 2784 ms: CI'ı boşuna düşürürdü), 13 =city Tolga anında perde (30 sn boş beyaz ekran yerine), çubuk eğrisi
> 0,08 → 0,04 (yarıda dolmuş görünüyordu), `tests/load_time.gd` ertelenmiş (hiç ölçmüyordu), `horn_world.gd` nabızları
> (bölüm ortası HornWorld 2,5 sn → ölçülecek). Tam paket `$S/tam128.sh` 08:59 → temizse 0.99.128 (`$S/surum128.py`,
> `$S/qa128.md`; kopyaları `gorev/`).
> **25 Kasım 11:07 UTC: 0.99.128 YAYINDA (CI #344 45601474425 koşuyor).** Tam paket (288ea111 + eklerim): 455/456,
> denetim 0 (18 satırın hepsi VISAUDIT_ADAY: 26/26o/35o at ve öküz), menüye dönüş 2/2, yükleme adayı 232 satır, en
> uzun 2,3 sn (13 h3_ordugah, 4 parça yükte; `horn.north_shore>horn.city.plan`), KESIN 0. Tek düşüş 37o `=lose`: bot
> çekişi yazı tura (%50), fıçı için art arda 3 iyi çekiş → ~%6 koşuda çıkış hiç olmuyor, `_duel_won` varsayılan true;
> belirli yapıldı (54a7460b), 7/7 (4 aynı anda). Birleşik acf560ab; main 85b8f77f (parent 4c703023, docs/_* hariç),
> wip/0.99.128; site c255bef. Bekçi `gorev/bekle_yayin.sh 0.99.128 7000` (guncelleme.json).
> **13:45 UTC: CI #344 testte düştü** (38o VISAUDIT float: iki CityLife devriye eri aynı y'de 0,8 m havada). Kök:
> `_spawn_patrol` izin ilk noktası reisin y'sinde, `_form` tek karede y'yi izden alıyor; er oynamayınca `_place`
> düzeltmiyor. Düzeltme 0092d611 + sonda `tests/_ci344/devriye_yamac.gd` (eski 112/112 havada, yeni 0); hedefli
> 15/15 PASS. main 0e7baa6f (mirrors satırıyla yeniden tetik), CI #345 45626896067; site 09799b2.
> **14:45 UTC: CI #345 de düştü:** (a) ESYATEST gomuk=1 (AÇIK İŞ (2)): zorla dondurulan kalas sallanırken 4,8 cm zeminde
> (42 koşuda 3, `ESYA_IZ=1` izi) → `_zemin_batmasi` ile 0–12 cm yukarı; sonda `tests/_ci344/esya_gomuk_sonda.gd` eski 1 /
> yeni 0; 36/36 PASS. (b) 36b overlap (−11,1; 21,0): Giustiniani'nin dönüş yeri savunucu yolunda (8'de 6) → TOPLAN +
> (−2,4; 0,8); ayrıca iki yürüyüş aynı adamı çekiştiriyordu (tam üst üste yürüyüş) → yürüyüş sırası + üst üste bekleme.
> Sondalı 8/8, hedefli 16/16 PASS. da88172c; main 2a951cc6, CI #346 45651160219 (16:07).
> **17:25 UTC: 0.99.128 YAYINDA.** CI #346 testler PASS (16:08–17:09), paket, guncelleme.json (surum 0.99.128, exe
> 1290242240 B), macOS, Releases, açık depo PASS; releases/latest = v0.99.128; ham ikililer iniyor (206). Sahibine
> rapor: oyun içi güncelleyiciyle güncelle (ilk gerçek Windows denemesi), büyük bölümleri dene.
> **25 Kasım ≈18:00 UTC: sahibi 43o drone karesi:** "bu şehrin yeri doğru mu, ne alaka surlar dibinde". Kararları:
> SARAY VE KANÇILARYA İÇERİ (300–500 m) + LYKOS ŞERİDİ BOSTAN. Plan `devir/plan.md` başı: G21 lykos (yazı
> `gorev/prompt_G21_lykos.txt`, Fable incelemesi) → 0.99.129; G22 saray içeri → 0.99.130; Faz 3 (G23, sorulacak):
> eski dünya kara surları hâlâ SiegeField kutu.
> Kalan (yeni açık iş 12): 36b karşı uç sırasında savunucular ≤ 0,15 sn 0,12–0,29 m yanından geçiyor (eskiden de; denetim
> 3 ardışık ister).
> **26 Kasım 12:55 UTC — 0.99.129 main c1f150cf (CI Release #347 45823466771 koşuyor), site 798fcdd.** Tam paket temiz
> (6fe9d426: 4 parça çıkış 0, FAIL 0, denetim 0, menüye dönüş 2/2). Birleşik dd0f6dd1. Önceki not:
> **26 Kasım 10:40 UTC — 0.99.129 tam paketi koşuyor:** G21 (Lykos bostan) + G22 (saray/kançılarya ~400 m içeri) +
> G22b (eski meydan yerinin dolgusu: yol, evler, bostan, bağ, harabe, nöbet yeri) + 31o `clear_line` + 26 sürekli bekçi +
> 22o hendek şeridi. Birleşik `wip/ist2-birlesik` = 6fe9d426. Sahibine kareler `kareler/0_99_129/`.
> **AÇIK İŞLER (0.99.130 adayları; yeni):** (13) Bölüm 7 uçuşunda uzak arazi katmanı hub düzlemesini örtüyor: surun dibi
> uzaktan yeşil (`dunya.gd` kaba ızgara; G22b raporu "hâlâ kötü"). (14) Akış sırası: bir bölgeye ilk girişte sur yolu
> merdivenleri surun kendisinden birkaç saniye önce geliyor (23 bostan bakışı, ~30 sn'de düzeliyor). (15) İç mahalle
> köşeleri havadan seyrek (toprak halka). (16) Eski dünyada iç mahalleye yol yok. (17) Faz 3 / G23: eski dünyanın kara
> surları hâlâ SiegeField kutu modeli (sahibine sorulacak).
> **AÇIK İŞLER (0.99.129 adayları; eski):** (9) 37o `=lose` VISAUDIT overlap Duelist↔Soldier (0.2,-2.8,24.3): 16 koşuda
> 1 (eski kodla); yalnız test kurgusunda (ally_cap 0, z 24'teki azaplar kalkmıyor, Cenevizli içlerinden geçiyor).
> (10) HornWorld `_city_east` "plan" adımı yükte 1,5–2,3 sn (tek nabız); gerekirse plan içine nabız. (11) B6 uzak
> ordugâh ertelemesi; 11 açılışı 998 ms sınırda; pencereli ilk kare 2,6–3,5 sn (gölgelendirici ısıtma yok).
> **AÇIK İŞLER (0.99.128 adayları):** (1) 26 =nophoto Squad overlap (iki tam pakette; `chapter26.gd` BEKCI26 katmanları,
> yedek bölük sık nizam); (2) ESYATEST yük altında gomuk=1; (3) bütün bölümlerin PACE (gerçek hız) donuk taraması
> `tests/_denetim17/pace_tarama.sh` koşulmadı (6–8 sa; sahibine söz verildi); (4) 26/26o/35o Sultan'ın atı ön toynaklar
> havada (AyakHayvan eğim 17°); (5) 36b hendek ucu kalınlıksız gri levhalar (hendek içinden görünüyor); (6) 42b talim
> meydanının çevresi boş ova; (7) görsel program: toplar/kızaklar, çadırlar, gölge rengi, duman, 38o çıplak tepe, 25 koyu
> meydan, Blakherna Sarayı kütle; (8) sahibi Meshy Pro alırsa 8y kapı önü + ordugâh denemesi (8–10 model + Forward+).

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
  **→ 31o için KAPANDI (TAŞIMA 13, 24 Kasım):** 8y kalıbı (SurHub + IstBaglama "fallen31o"), `ESKI_VARSAYILAN = []`.
  Kalanlar (görsel tura): tepeden caddenin çevresinde ~57 m seyrek kuşak (`sehir.gd` ~3159: oyun alanı tek daire; uzun
  alanı şerit boyunca küçük dairelere bölmek), v2 kurulumunda `LoadingScreen.pump` yok (bütün hub bölümlerinde perde donuk),
  v2 ziyareti başına menüye dönüşte 680 sahipsiz düğüm, v2 statik önbellekleri evre geçişinde +92 MB, 17o uzak surlar gece
  çok koyu, 17o `in_world=false` ölü yolu eski kutu (oynanmıyor). Ayrıntı: dalların `docs/_kanit_ist2_tasima13|tur15/rapor.md`.

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

## L. Sahibinin oynayış notları (24 Kasım sabahı, 0.99.125, 8y → 9)
Hatalar (0.99.126'ya düzeltme; kök neden ölçüldü, kanıt `kareler/0_99_126/8y_*`):
1. **Dış kapı ile köprü arası "havada"**: toprak rampanın yalnız çarpışması vardı, görünen ağı yoktu (`sur_oyun_ag.gd`
   `pis()` tek ağı kendi içine pişirip siliyordu). Oyuncu görünmez rampada yürüyor, kapı eşiği havada duruyor görünüyordu.
   Aynı yol 26/31o Romanos köprüsünde de var. Düzeltme: tek ağ pişirilmez (ebeveyniyle birleşir).
2. **Keçiler havada** (ova keçisi 3,5 m, pazar keçisi 2,5 m): `Goat` zemini hep y 0 sanıyordu; 8y ovası yeni surda 3,5 m
   aşağıda. Düzeltme: `Goat.zemin` (bölümün zemin işlevi).
3. **Pazarda donup kalma**: Hasan 1,35 m/sn ile dolambaçlı yoldan ~24 sn yürüyor, oyuncu 9 sn'de varıp donuyordu. Düzeltme:
   Hasan 2,8 m/sn; son sahne Hasan varmadan başlamaz, oyuncu bu arada serbest.
4. **Aşçı havayı karıştırıyor** (kepçe kazanın dışında): inceleniyor.
Neden yakalanmadı (dürüst): VISAUDIT yalnız kişileri (Person/Soldier) denetliyor, hayvanları değil; görünmez zemin (çarpışma
var, görüntü yok) için hiç denetim yok; otomatik test yürüyüşleri hızlı kipte (Hasan bekleme süresi ölçülmüyor); yardımcı
kareleri yolun ileri bakışlarıydı, dönüp kapıya bakan kare yoktu. → **Denetim genişletmesi (yardımcı işi):** hayvanlar ve
duran eşyalar için havada/gömük denetimi; "görünmez zemin" denetimi (oyuncunun bastığı çarpışmanın üstünde görünen yüzey yok);
gerçek hızda "bekleme" denetimi (oyuncu donuk kalma süresi > N sn → uyarı).
Görsel (görsel programa, G/H/K ile birlikte):
- Ordugâh boş ("hiç asker kimse yok"), birimler kötü; çadırlar ve kapılar "aşırı kötü" → sahibi: "Blender MCP kullanırız";
  toplar vb. de Blender'da üretilecek. Not: bu, sanatçı + Blender hattının (I.1) ilk listesi: çadır (Osmanlı otağı ve asker
  çadırı), kapı (sur kapısı kanadı, çadır kapısı), top, pazar tezgâhı, asker birimleri.

## M. Fragmanlar (27 Kasım)
- Sahibi: "Napolyon–Hitler atışmasının fragmanını at", "Zaman Bürosu'ndaki bütün komik anlar", "genel fragman: en heyecanlı anlar".
- Gönderildi:
  - Napolyon–Hitler (11 sn);
  - Zaman Bürosu derlemesi (1:55, 11 an).
  - Araç: `tools/trailer/montage.gd` `set=story_buro` (`BURO_REEL`), kurgu `story_cut.py --music bureau.ogg`. Oyun deposu e24440c7.
- Hata ve kökü: ilk gönderilen Napolyon–Hitler parçasında Napolyon'un Rusya repliği sessizdi.
  - Replik pencere açılmadan başlıyordu; pencere açılırken "önceki sahnenin sesi" diye susturuluyordu.
  - `buro_reel` artık pencereyi bekliyor. Her replik ham kayıtta ölçüldü (`devir/gorev/ses_denet.py`; 27/27 sesli).
  - Not: STORY/STORY2'deki eski `buro_atisma` adımları hâlâ aynı açığa sahip (t 0,4'te `_fg_seq`).
- Genel fragman GÖNDERİLDİ (1:10, 1080p, 12 an, `battle_ottoman`, −15 LUFS); sayfada en üstte (artifact 7FFsSLc1heoRuRkVsZhikm v9, 720p).
  - Kayıt: `SET=story_aksiyon kaydet.sh aksiyon_1080 1920x1080 only=0,3,4,5,10,11,12,15,16,17,18,19` (~99 dk) + tüfekçi yeniden çekimi
    `only=4` (tg_1080, 7 dk). Kurgu: `devir/gorev/kurgu_genel.sh` (kesim noktaları içinde).
  - Tüfekçi: fragmanda bot önce namluya bakar, ≤0,6 sn sonra atılır (Gunner._bot_dodge, yalnız flags.trailer; ac6790f2).
  - Bilinen: düello HUD'unun iki satırlık tuş ipucu düello çekimlerinde görünüyor; top çekiminde TOP görev listesi sağda.
    İstenirse story_aksiyon'da gizlenir ve 3 düello çekimi yeniden kaydedilir (~40 dk).

## N. Aksiyon cilası (27 Kasım, sahibinin fragman ön kaydı notları) — oyun deposu wip/ist2-birlesik b18c6834
- Elde eşya: savaş bölümlerinde el boş (Items.EMPTY_HAND: 20, 20o, 26, 26o, 28o, 29, 29o, 30, 30o, 36b, 37o, arena);
  top başında çanta eşyası cebe girer (CannonCrew); 2'de kumanda kalır (kırmızı düğme repliği).
- Tüfekçiden kaçış: Player.dive (Boşluk + A/D, nişan sırasında), bot da kullanır; düelloda yok (UI_GUNNER_WARN_DUEL).
- 30o merdiven: yan yatık omuzda (basamaklar dik), iki el alt dikmede (hold_both), bot surlara bakar.
- 30 sur düellosu: rakip görünen açık yerde doğar (_duel_spot). 20 tüfek: mazgal açıklığı + tahta atış basamağı.
- 30o kule tepesi düz beyaz kutular yalnız eski sette. 26 taşıyıcı: Person "geri_yuru" (gövde gidiş yönüyle çekişmez).
- HUD.bark: beklerken sahne değişirse bırakır. HareketHis iniş yayı alt adımlı (büyük deltada NaN; kamera taşıyordu).
- Fragman: telefon yalnız uygun çekimlerde; kişilerden ayrışma; tüfekçi kule tepesinde, tüfek nişanda; 30 düello çekimi.
- Bilinen: 26 taşıma poternada kapı kanadının dibinden geçiyor (fragmandan çıkarıldı); ok yağmurunda askerlere çok yakın.
- 0.99.131 YAYINDA (27 Kasım ~16:50 UTC): tam paket 456/456, denetim 0, menü dönüşü 2/2. main 9ef13a48 (parent ea58ea74),
  wip/0.99.131, birleşik f0a89112, site 8e7580a. CI başarılı: releases/latest v0.99.131, guncelleme.json 0.99.131.
