# DURUM 26 Kasım 20:55 UTC — 0.99.130 main ea58ea74 (CI Release #348 45893821990 koşuyor; bekçi bekle_yayin.sh), site bb14360, birleşik 5d120649. Kum havuzu Pazar 20:00 TR

## Context
- 0.99.129 yayında (CI #347 başarılı, guncelleme.json 0.99.129).
- 0.99.130 adayı `wip/ist2-birlesik` 19d2e926:
  - G23: eski dünyanın kara surları yeni kalemle (kabul, kareler `kareler/0_99_130/`);
  - `Dressing._genis_zemin`: 27 Galata bahçe duvarı tepesi yürüyüş noktası olmaz. İlk tam pakette 27'nin yedi çeşidinde VISAUDIT float vardı; 17 hedefli koşu temiz.
- tam130 (yeniden) 18:30'da başladı ve süreçleri hâlâ çalışıyor (22 süreç, makine yeniden başlamadı: uptime 12:56). Parçalar ~53/114, fail 0, denetim 0. Yalnız bekçi görevi (bcez7y0g1) oturum yeniden başlayınca kayboldu.
- Sürüm notu `surum130.py` (Galata satırı eklendi), QA `qa130.md` (G23 dersleri + "yardımcının 'önceden de vardı' demesi kanıt değildir"), kareler hazır.
- Kum havuzu planı `devir/KUM_HAVUZU_PLANI.md` v2 (Fable iki tur, sahibinin kararları: oyuncuya açık + araç, 1453 Fatih, gerçek zamanlı + duraklat, önce prosedürel; bütün bölümler sabit haritada; GÖRSEL İNDİRİM YASAK). Başlangıç Pazar 29 Kasım 08:00 TR. Kota yenilenmesi Pazar 20:00 TR.

## Adımlar
1. Bekçiyi yeniden kur: `$S/bekle_bitti.sh $S/tam130_ozet.txt 7000` (run_in_background). Süreçler ölürse biten parçaların sonuçları okunur, eksik parça yeniden koşulur.
2. Temizse (fail 0, `^VISAUDIT ` 0, menüye dönüş 2/2) **0.99.130**:
   - VERSION; `qa130.md` → `docs/QA_DERSLER.md`; kayıt ve gönderim (wip/ist2-birlesik);
   - yayın ağacı `docs/_*` hariç, parent main c1f150cf; main + `wip/0.99.130`;
   - site `surum130.py --yaz`, gönder; CI ve `bekle_yayin.sh 0.99.130`.
   Denetim satırı çıkarsa: sondayla kök, düzelt, hedefli koşu, paketi yeniden.
3. Sahibine Türkçe rapor: 0.99.130 yayında, ne değişti, bilinen zayıflar; deniz surları (Marmara/Haliç) yeni kaleme geçirilsin mi sorusu.
4. Pazar 20:00 TR (sahibi: "20:00de"): kum havuzu D0 (envanter, bölüm × dünya matrisi, 1000 asker başarım sondası); kota yenilenince D1/D2 yardımcıları ve G-model (Blender örnekleri, indirim yasak).

## Doğrulama
- tam130: 4 parça çıkış 0, FAIL 0, DENETIM 0, MENURETURN 2.
- CI başarılı; releases/latest v0.99.130; guncelleme.json 0.99.130; site changelog 0.99.130.

# (Eski) DURUM 26 Kasım 05:50 UTC — G22 TESLİM EDİLDİ ama v2'de surun ardı BOŞ ÇAYIR; kap yine yeniden başladı

## Context
- **G22 teslim** `wip/saray22` 37ae2b7d (taban 618521d7). Testleri temiz (hub ×2 76/76, sözleşme altılısı aynı, ZFIGHT 0, yükleme süresi artmadı).
- Tam boy kareler:
  - İyi: saray avlusu + İmparator içeride (`sahip_2`); 43o eski dünyada sur ardı bostan/çadır (`sahip_1`).
  - **Kötü:** v2'de eski meydanın yeri (hub düzlemesi r 48) koca bir boş çayır (`v2_23/01_caddeden_sur`, `v2_6/04`, `05_tepeden`, `sahip_3`). Sahibinin kararı "boş çayır yok"; olduğu gibi yayınlanamaz.
  - Raporun öteki zayıfları: iç mahalle v2 oyun alanı eksen hizalı, köşelerde ~10 m boş toprak üçgeni; sur parçası döşemesi keskin kenarlı taş dikdörtgen; eski dünyada mahalleye yol yok.
- **tam129** (G22'siz, f6adcdb1): kap 03:08 sonrası yeniden başladı, özet yazılmadı. Parça günlükleri: 457 PASS, 0 FAIL, ama **2 denetim satırı**:
  - `VISAUDIT overlap chapter26 Squad|Duelist (-15.6,0,5.5)`
  - `VISAUDIT float chapter22o Person (-6.5,-8.1,34.1)`: ayak −8,1; altındaki çarpıştırıcı `Toprak_KuleDolguSet_Carp` −8,68; 0,58 m havada.
  - İkisi de yeni ve seyrek. G21/G22 dosyalarına dokunmuyorlar; kök bulunmalı.
- f6adcdb1 (31o `clear_line`) yerelde kayıtlı, **gönderilmedi**. Kap yeniden başladı: arka plan bekçileri yok; depolar, Godot ve `$S` yerinde.

## Adımlar
1. **f6adcdb1'i gönder** (`wip/ist2-birlesik`).
2. **G22b: sur ardını doldur.** G22 oturumuna (session_01RAjzxKhqXDAz1Nxq4oRyN8, boşta, bağlamı dolu) SendMessage ile kısa ek görev. Önce Fable okur, DÜZELTMELER eklenir. İş:
   - v2'de eski hub alanını (sur parçası döşemesinin ~15 m ötesinden itibaren) G21 şerit diliyle doldur:
     - bostan, bağ, meyve bahçesi, dağınık köy evi, harap kilise, kuyulu küçük meydan;
     - kapıdan saray yoluna (`IstSokak._saray_yolu`) giden gerçek bir yol, iki yanı bahçe ve ev;
     - hub düzlemesi (zemin yüksekliği) aynı kalır, yalnız üstü dolar.
   - Senaryo yerleri boş kalır: 6/7/10h/13/23/24'te sur parçasındaki bütün kişi ve tünek konumları + oyuncu yolları. Bölüm testleri bunu kanıtlar.
   - İç mahalle oyun alanı hub açısıyla dönük dikdörtgen olsun; köşe üçgenleri kalmasın.
   - Döşeme kenarı yumuşasın: bordür taşı, toprak geçişi, eşya. KUTU YASAĞI.
   - Eski dünyada mahalleye toprak yol: CityPlan'a dokunmadan, SiegeField/WallRear süslemesiyle. Küçükse yapılır, değilse rapora yazılır.
   - Kanıt: önce/sonra tam boy kareler (`v2_23/01`, `05_tepeden`, `v2_6/04`, uzak7/03-04, sahip_3, 43o drone).
   - Testler: hub bölümleri ×2, CITYCHECK 24/31o, STREETCHECK, ISTBOS %0, ZFIGHT, WALKCHECK/FLIGHTCHECK/MAPCHECK, sözleşme altılısı, yükleme süresi, menü dönüşü.
   - Standart yasaklar: oturum/zamanlayıcı/ajan araçları, pkill, ses, PR, main, liste dışı dosya, denetim susturma.
   - Bekçi: `$S/bekle_g22.sh` (rapor BİTTİ'yi bekler; "G22b" satırı için kalıp güncellenir), run_in_background.
3. **Bu arada ben: iki denetim satırının kökü** (f6adcdb1 üstünde, `--max-fps 20`, 4 paralel):
   - 26 (bütün çeşitler) ×4: Squad ile Duelist'in aynı yere düşmesi. Doğuş/yerleşim koşulu bulunup düzeltilir.
   - 22o (bütün çeşitler) ×4: kule dolgusu çarpıştırıcısının üstünde 0,58 m havada duran asker. Zemin örneklemesi (Person/zemin bulma) ile dolgu yüksekliği karşılaştırılır, düzeltilir.
   - Her düzeltmeden sonra ilgili çeşitler ×2 temiz.
4. **Birleştir:** `wip/saray22` (+G22b) → `wip/ist2-birlesik`; parse PASS; hedefli koşular (6, 7, 10h, 12b, 13, 23, 24, 31o, 26, 22o).
5. **Tam paket** `$S/tam129.sh` (setsid + `bekle_bitti.sh`). Kap yeniden başlarsa biten parçalar okunur, eksik parça yeniden koşulur.
6. **0.99.129 yayını** (G21 + G22 + G22b + 31o + iki denetim düzeltmesi):
   - VERSION; `qa129.md`'ye G22 dersleri (iki kök, düzleme alanının boş kalması, dönük oyun alanı, denetim kökleri);
   - ağaç `docs/_*` hariç, parent main 2a951cc6; main + `wip/0.99.129`;
   - `surum129.py` metni: saray ve kançılarya içeride; "sonraki sürüm" cümlesi çıkar; `--yaz`, site gönder;
   - CI; `bekle_yayin.sh 0.99.129`.
7. **Sahibine Türkçe rapor:**
   - kareler `kareler/0_99_129/` ve SendUserFile;
   - bilinen zayıflar; ElevenLabs anahtarı hatırlatması;
   - Faz 3 sorusu (eski dünya kutu kara surları, G23).
   - Devir: `PAZAR_LISTESI`, `plan.md`; mstrbought kaydet/gönder.

## Doğrulama
- G22b kareleri tam boy: sur ardında boş çayır yok, yol var, senaryo yerleri açık.
- 26 ve 22o çeşitleri ×4 denetim 0.
- Tam paket: fail 0, `^VISAUDIT ` 0, menü dönüşü 2/2.
- CI başarılı; `guncelleme.json` 0.99.129; site notu doğru.

# (Eski) DURUM 26 Kasım 02:45 UTC — KAP YENİDEN BAŞLADI; G22 AÇIK; 0.99.129 tam paketi yarım kaldı

## Context
- 0.99.129 adayı (G21 Lykos şeridi + harita) `wip/ist2-birlesik` 618521d7'de (kod 6dec6901 + G22 görev yazısı kaydı).
- Tam paket tam129 (22:04) makine yeniden başlamadan önce:
  - 3/4 parça bitti: 456'nın 456'sı AUTOTEST PASS; parça 2 ve 3 fail = 0.
  - Parça 1'de bir denetim satırı paketi düşürdü: `VISAUDIT personhidden key=D31O_AZ_03` (31o `=late`). Bir Person (`Chapter31o>Node3D>Person`, (−11,8; −70,8)) konuşan azabın önünde.
    - Önceden var olan seyrek kusur: bir eski tam pakette de çıkmış.
    - 0.99.127'de `Unclip.clear_line` eklenmişti (`chapter31o.gd:1354-1356`), yine de çıkıyor.
    - G21 şeritteki kalabalığı artırdığı için sıklaşmış olabilir.
  - Parça 0 son kontrollerde (MENURETURN PASS sonrası) kesildi.
- **G22 SARAY İÇERİ açıldı:** session_01RAjzxKhqXDAz1Nxq4oRyN8 → `wip/saray22`. Yazı `docs/_ajan/gorev/G22_saray.md` (+ Fable 26 düzeltme). Faz A–D, 16–24 sa; her faz `durum.md`'de `## Faz X: TAMAM`.
  - Bekçi yok (yeniden başlama hepsini sildi).

## Adımlar (sırayla)
1. **Ortam:** Godot `$S/godot/godot` yerinde, depolar yerinde (doğrulandı). Arka plan bekçilerini yeniden kur:
   - G22 bekçisi: `$S/bekle_g21.sh` kalıbıyla `bekle_g22.sh`; `wip/saray22:docs/_kanit_saray22/durum.md` BİTTİ ya da "Faz A: TAMAM".
2. **31o personhidden kökü:**
   - `--chapter=31o --autotest=late` ve öteki çeşitler, `--max-fps 20`, 4 aynı anda × 2 tur, tam günlük. Hangi Person (CityLife/IstHayatYakin yürüyeni mi, sahne kişisi mi), ne zaman araya giriyor.
   - Kökten düzelt. Seçenekler:
     - `Unclip.clear_line` yürüyenleri de kapsasın;
     - replik boyunca hattı tutsun;
     - kalabalık doğuşu konuşma çevresini dışlasın.
   - Sonra 31o bütün çeşitleri ×2 temiz.
3. **Tam paketi yeniden koş:** `$S/tam129.sh` (ısıtma + 4 parça; `VISAUDIT ` boşluklu sayım), setsid + bekçi.
   - Temizse **0.99.129**:
     - VERSION ve QA (`qa129.md`: G21 dersleri, harita, 37o/36b/ESYATEST/38o dersleri zaten 0.99.128'de);
     - ağaç `docs/_*` hariç, parent main 2a951cc6; main + `wip/0.99.129`;
     - site notu `surum129.py` (Lykos şeridi bostan/bağ/harap kilise; harita güncel; meydanın taşınması sonraki sürümde);
     - CI, `guncelleme.json` 0.99.129.
4. **G22 teslimlerinde:** Faz A geldiğinde 43o karelerini tam boy incele. İstenirse Faz A ayrı yayın (0.99.130); kalanlar sonra.
5. Sahibine Türkçe kısa rapor: 0.99.129 yayında, ne değişti, G22 durumu; ElevenLabs anahtarı hatırlatması.

## Doğrulama
- 31o `=late` ve bütün çeşitler ×2 (20 FPS) VISAUDIT 0.
- Tam paket: fail = 0, gerçek denetim 0, menüye dönüş 2/2.
- CI başarılı; `guncelleme.json` 0.99.129.

# (Eski) DURUM 25 Kasım 22:15 UTC — G21 BİRLEŞTİ (cc8cae88 → wip/ist2-birlesik; harita yeniden pişti 6dec6901, gönderildi).
#   Tam paket tam129 (setsid, 22:04; bekçi ba4kd8rmt) → temizse 0.99.129. G22 yazısı devir/gorev/prompt_G22_saray.txt,
#   Fable inceliyor → düzeltmeleri ekle → G22 aç (taban 6dec6901, dal wip/saray22).
# (Eski) DURUM 25 Kasım 19:55 UTC — G21 LYKOS AÇILDI: session_01RAjzxKE9tCRLMHXwBnsvLr → `wip/lykos21` (yazı devir/gorev/prompt_G21_lykos.txt
#   + Fable 27 düzeltme; tahmini 6–8 sa). Nöbetçi `$S/bekle_g21.sh 7000` (b2xcm0egw; süre dolarsa yeniden kur).
#   Teslimde: rapor + tam boy kareler (özellikle 43o drone), birleştir, doğrula, tam paket → 0.99.129; sonra G22 yazısı.

# PLAN (25 Kasım ≈18:00 UTC) — Meydanı böl: saray ve kançılarya içeri, Lykos şeridi bostan (0.99.129 / 0.99.130)

## Context
Sahibi 43o drone karesi gönderdi: "bu şehrin yeri doğru mu, çok garip duruyor, ne alaka surlar dibinde". Bulgular:
1. **Bizans meydanı** tek blok ve iç surun hemen ardında: ByzCity "walls", 84×70 m; cadde, Logothetes kançılaryası, saray avlusu + İmparator, Giustiniani, Romanos Kapısı. Romanos'ta savunmayı İmparator ve Giustiniani yönetti; burası doğru. Saray ve kançılarya ise orada değildi, sahne için toplanmışlar.
2. **Eski dünya bölümleri meydanı kutu surla pişiriyor.**
   - Hangileri: CampDay ordugâhları (6a, 9, 10, 10b, 10z, 13 ordugâh, 16, 24o, 25, 43o).
   - Nasıl: `ByzCity.far_hub` (`byz_city.gd:122`) `_build_walls`'u eski kipte çağırıyor; kutu iç sur, kuleler ve kemer kuruluyor.
   - Kara surları da `SiegeField` kutu modeli (`siege_field.gd`).
   - Sonuç: meydan "surlara yapışık, surlu bir kasaba" gibi görünüyor.
   - TAŞIMA 12 bunu yalnız v2'de (7, 11) düzeltti.
3. **Şehir surlara kadar sıra evle dolu.** Sebep 12 Kasım kalite notu 0/0b (`docs/_ajan/gorev/ist2_kalite_notlari.md`): sur dibi `sur_dibi` 0,75, `geo.gd:394`. 43o'da Sultan'ın seslendirilmiş repliği `D43O_F_VIEW3` ise "içeride bostanlar, harap kiliseler, boş meydanlar" diyor; görüntüyle çelişiyor.

**Sahibinin kararları (AskUserQuestion):**
- Saray ve kançılarya içeri (300–500 m).
- Lykos şeridi bostan: surun ardında ~150–250 m bostan, bağ, harap kilise, dağınık ev, boş meydan. Boş çayır yok; şehrin kalanı dolu kalır.

Birimler oyun (dünya) metresi; gerçek mesafe × 0,35 (`geo.gd:12`).

## Tasarım (varsayılanlar; onayda değişebilir)
- **İç mahallenin yeri.** Hub-yerel −x ≈ 360–420 (site A, Lykos terası).
  - v2: ≈ (−1290, 6–7, −170), eğim ≤ %7. Eski dünyada aynı ofset düz.
  - Tek ofset iki dünyada da çalışır; bölge dönüşümleri (`world1453.gd:106` byz_walls, `SurHub.hub_v2`) değişmez.
  - Kesin nokta `IstGeo.h` ile ölçülür: eğim ≤ %8; anıt, sarnıç (Mokios) ve Lykos çizgisiyle çakışma yok.
- **Surda kalanlar:** Giustiniani'nin iskelesi, Romanos kapısı, nöbetçiler, caddenin sur ucu, küçük bir nöbet/ikmal yeri (sandık, ocak, meşale).
- **İçeri gidenler:** saray avlusu + İmparator + divan, kançılarya (7 oda, 7 kâtip), meydan + çeşme + tezgâhlar, Niko ve kayığı, zindan hücresi (6/7), tabelalar.
  - ByzCity aynı bölüm çerçevesinde ikinci bir kök düğüm kurar (ofset P).
  - Kançılaryanın x'i sabite bağlanır (bugün x = 0'a gömülü: `byz_city.gd:1489`, `clerk_x` 1825).
- **Aradaki yol.** Kapıdan iç mahalleye gerçek sokak: v2'de `sokak.gd` açık yol, eski dünyada ROAD hattı (`city_plan.gd:51`). Serbest yürünür (≈ 2 dk).
- **Senaryolu gidiş-gelişler.** 10h kalıbı: kararma + yerleştirme (`chapter10h.gd:290, 420`); oyuncu isterse yürür.
  - 6b: martı kovalamacası iç meydanda. Tünek sayısı ve sabır süreleri aynı (denge aynı).
  - 6b: `D6B_T_CHASE_4` "Surlara gidiyor!" ile martı surlara uçar, kararma olur, son tünek Giustiniani'nin masası.
  - 10h: `D10H_L_04` "Bak, saray" kapıda değil, saraya varışta çalar.
  - Replik metni ve sesi değişmez; yeni replik yok.
- **Uzak görünüş.** `far_hub` (eski dünya) ve `hub_sehir` (v2, `sehir.gd:2216`) iki parça olur: sur parçası + iç mahalle.
  - Eski dünyada sur parçasının kutu iç suru SiegeField boşluğunu (`siege_field.gd:262-298`) doldurduğu için şimdilik kalır; Faz 3'e bakın.
- **Lykos şeridi.** Romanos–Pempton arası, surun iç yüzünden ~150–250 m.
  - v2: `IstGeo.mahalle`'de duvar bandından önce mozaik kuralı. 60–90 m hücrelerde bostan, bağ, harabe, seyrek (dağınık ev), manastır, mezarlık.
  - v2: `sokak.gd:1244` savunma yolu sıra ev zorlaması şeritte kapanır.
  - v2: boş meydan + kuyu; `_ogeler` dolgusu → ISTBOS %0.
  - v2: `hayat_yakin.gd:30` TARGET şeritte ayarlanır; CITYCHECK 24/31o ≥ 8 sivil kalır.
  - Eski dünya: `wall_rear.gd:17-25` bandı + SiegeField dolgusu bostan/harabe; CityLife "lykos" pazarı (`city_life.gd:348`, (0,−160)) iç mahalleye taşınır.

## Yürütme (yardımcılar sırayla, aynı anda değil: `sokak.gd` ve `siege_field.gd` ortak)
1. **G21 "LYKOS BOSTAN"** (Opus, dal `wip/lykos21`, taban `wip/ist2-birlesik`, ≈ 3–4 sa).
   - İş: şerit iki dünyada + kapıdan içeri yol iskeleti. Hedef: `IstSehir.oyun_alanlari()`'nda "saray" varsa o, yoksa hub-yerel (−380, 0).
   - Dosyalar: `geo.gd`, `sokak.gd`, `hayat_yakin.gd`, `wall_rear.gd`, `city_life.gd` (yalnız lykos pazarı), yeni `tests/_ist/lykos21_kare.*`.
   - Teslimde: doğrulama + tam paket → **0.99.129**. 43o'daki görüntü burada zaten düzelir: şerit bostan olur, meydanın ardı açılır.
2. **G22 "SARAY İÇERİ"** (Opus, G21'in üstünde, dal `wip/saray22`, ≈ 6–10 sa).
   - Dünya ve kurulum dosyaları:
     - `byz_city.gd`: bölünme, sabitler, `_RESERVED`, `Dressing.auto` alanları, `far_hub` iki pişirme.
     - `world1453.gd`: `FAR_REGIONS` iki dikdörtgen; sur parçası z −2,3'ü kesmeye devam eder.
     - `siege_field.gd`: dikdörtgen başına düz y.
     - `baglama.gd`: `YAMA`/`TEMIZ` dikdörtgen listesi, `hub_alan`.
     - `sehir.gd`: ikinci düzleme + öğe, `oyun_alanlari` "saray", `_make_hub` ikiye.
   - Bölümler:
     - `chapter6.gd`: z eşikleri 144/306/791/871, tünekler, otomatik test, byzyuru.
     - `chapter7.gd`: izler 239-260.
     - `chapter10h.gd`: `HALL` kopyası 16, geçişler.
     - `chapter12b.gd`: `city.emperor` düğümü yine kurulur.
     - `chapter13.gd` (Niko 220-223), `chapter23.gd` (`HALL`), `chapter24.gd` (yol arka planı).
   - Testler: `tasima12_kare`, `tasima10_kare`, `tur14_bolum_kare`, `city_audit`, `flight_check`.
   - Teslimde → **0.99.130**.
3. Görev yazıları önce Fable'a okutulur. Standart yasaklar geçerli: oturum/zamanlayıcı/ajan araçları, pkill, ses üretimi, PR, main, liste dışı dosya, denetim susturma, izin istemi doğuran komutlar. KUTU YASAĞI, havada duran yok, tek görsel dil; denge ve replik değişmez. Nöbetçi arka plan betiği; send_later yok.
4. **Faz 3 (ayrı, sonra; sahibine sorulur):** Osmanlı tarafının (eski dünya) kara surlarının tamamı hâlâ SiegeField kutu modeli. Yeni sur kalemine geçirmek ayrı bir görev (G23).

## Doğrulama
- **Tam boy kareler, önce/sonra:**
  - 43o drone, sahibinin karesindeki bakış (`WALLS_AT`) ve Sultan'ın VIEW1–3 anı.
  - Ordugâhtan surlara bakış (9, 27).
  - 6b/10h sur parçası ve iç mahalle göz hizasında (0,5–3 m).
  - Şerit göz hizasında ve 70 m tepeden; yol boyunca yürüyüş.
- **Testler:**
  - Hub bölümleri bütün çeşitleriyle ×2, `--max-fps 20`: 6 byz*, 7 byz*, 10h, 12b, 13=city, 23, 24.
  - CITYCHECK 24/31o (≥ 8 sivil), STREETCHECK, ISTBOS %0 (`gezi bos=1`), FLIGHTCHECK, WORLDCHECK, ZFIGHT.
  - YUKLEMEAUDIT KESIN 0, yükleme süresi ölçülür.
  - Sözleşme altılısı birebir: SURSOZLESME 13/8, SUROYUN 519/0/0/0, WALKTHRU 7/7, ESYATEST, HALICSONDA 661, MARMARASONDA 1837.
  - Tam paket fail = 0, menüye dönüş 2/2, CI başarılı.
- Ev sayısı 9 binin altına düşerse sahibine bildirilir (0b hedefi 9–12 bin).

# (Eski) DURUM 25 Kasım 17:25 UTC — 0.99.128 YAYINDA (CI #346 45651160219, main 2a951cc6; guncelleme.json 0.99.128). Sahibinin denemesi bekleniyor.
# (Eski) 16:10 — CI #346 koşuyordu (#344 38o devriye, #345 ESYATEST gömük + 36b overlap düzeltildi)
- Bekçi `$S/bekle_yayin.sh 0.99.128 7000` (b1fvn72pz) → guncelleme.json 0.99.128 olunca: releases/latest doğrula,
  sahibine Türkçe rapor (oyun içi güncelleyiciyle güncelle = ilk gerçek Windows denemesi; yüklemeleri dene; hangi
  bölümde ne gördüğünü yaz; ElevenLabs anahtarını yenile). CI düşerse: günlük → yerelde --max-fps 20 → kökten düzelt.
- Tam paket: 455/456, tek düşüş 37o =lose (bot yazı turası) → 54a7460b, 7/7. Açık işler PAZAR_LISTESI (9)–(11).

# (Eski) DURUM 25 Kasım 09:00 UTC — G19 BİRLEŞTİ (288ea111) + benim eklerim (kayıtsız); TAM PAKET tam128 KOŞUYOR (bekçi bcug8l6mq)
- Temizse: eklerimi kaydet, VERSION 0.99.128, QA (`$S/qa128.md`), ağaç docs/_* hariç parent main, main + wip/0.99.128,
  site `$S/surum128.py --yaz`, CI. Sonra sahibine rapor (güncelleyiciyle güncelle, yüklemeleri dene).

# (Eski) DURUM 25 Kasım ≈07:35 UTC — G19 SÜRÜYOR (session_01RAjzxKb4yV64iDSc3rLT7v → wip/yukleme19, son fabe2bf9)
- Bekçi (b81uiz0c7) 2 sa sınırında durdu; işçi süreci yeniden başladı. G19 ilerliyor: nabız + kapsam + YUKLEMEAUDIT,
  bölüm ortası perde (31o eyup/aya, 24 Ayasofya, 13 h3; 26 ve 13 tolga beyaz geçişte yalnız nabız), hub öğeleri atlama,
  çok girdili önbellek, büyük önbellek yazımı arka iş parçacığında; 8y soğuk en uzun boşluk 727 ms. Şu an bölüm testleri ×2.
- Sıradaki (onaydan sonra): bekçiyi yeniden kur (`setsid bash $S/bekle_g19.sh 7000`, run_in_background), başka iş yok;
  teslimde aşağıdaki PLAN'ın "Doğrulama" adımları → 0.99.128.

# PLAN (25 Kasım) — 0.99.128: "Yanıt vermiyor" bitsin, bölümler daha hızlı yüklensin

## Context
Sahibi: "oyunda genel bi yükleme sorunu var, yanıt vermiyor'a dönüyor ve zor yükleniyor bölümler". Windows bu uyarıyı, ana
iş parçacığı ~5 sn pencere iletilerini işlemeyince verir. İki inceleme (salt okuma) kökü gösterdi:
- **Bölüm dünyası tek seferde kuruluyor.** Bölüm `_ready`'sinde, ana iş parçacığında. Yükleme perdesi yalnız ~200 baytlık `.tscn`'yi arka planda yüklüyor (`game_state.gd:1082-1116 _change_with_loader`).
- **Pencereyi canlı tutan tek şey `LoadingScreen.pump()`** (`ui/loading_screen.gd:120-154`, 150 ms'de bir `DisplayServer.process_events()` + çizim). Tek çağıranı `Props._place` (`level/props.gd:425`). Perde yokken hiçbir şey yapmıyor.
- **İstanbul v2'nin ağır yolları hiç nabız atmıyor.** QA_DERSLER'de açık kayıt: `docs/QA_DERSLER.md:1193`.
  - `IstSehir.attach_v2` (`ist/sehir.gd:1429`): `_on_pisir` 6,7–7,9 sn; `_layers2/_merge_groups`; `_hat_far_*`.
  - `IstMahalleDoku` (`ist/mahalle_doku.gd:974`): 8 sn'ye kadar tek döngü.
  - `IstSokak.build`: soğukta 6,8 sn.
  - Ordugâh uzak hücreleri (`ist/ordugah_yonetici.gd:30-166`): 2,5–6,4 sn; v2'nin her bölgesinde var.
  - Kalabalık pişirme (`ist/hayat.gd:106`): soğukta 6,3 sn.
  - `World1453.bake` + `generate_lods` (`world1453.gd:436-540`).
- **Yükleme perdesi olmadan kurulanlar** (bunlarda nabız da yok):
  - Bölüm ortası yeniden kurulumlar: 31o Eyüp evresi (`chapter31o.gd:767`), 24 → Ayasofya (`chapter24.gd:378-391`), 26 → Ayasofya (`chapter26.gd:2421, 2998`), 13'ün dünyaları (`chapter13.gd:209-739`).
  - Oyunun açılışındaki ilk bölüm (`boot.gd:17`).
- **Kayıtlı süreler** (başsız/xvfb):
  - 8y/23/24 ≈ 55 sn; 12b/10h ≈ 48–50 sn; 31o ≈ 39 sn.
  - 11: soğukta 40 sn, ılıkta 20–27 sn.
  - SurSet bölümleri 3–5 sn.
- **Disk önbelleği her güncellemede soğuyor.** Anahtarda sürüm + betik md5'i var (`ist/sokak.gd:253`). Bölgeler arasında da birbirini siliyor olabilir (`sokak.gd:297-301`; doğrulanmadı).
- **İsraf:** Hub bölgelerinde şehir hub'ı `_on_pisir`'de üç kez (LOD 2/1/0) kurulup sonra `_temizle` ile siliniyor (`sehir.gd:2162`, `baglama.gd:510-531`).

## Yaklaşım: bir Opus yardımcı (G19, dal `wip/yukleme19`)
Görev yazısını önce danışman (Fable) okuyacak. Ben birleştirir, doğrular ve yayınlarım. İki kesme var:

**Kesme A — "Yanıt vermiyor" hiç olmasın (görüntü bit bit aynı, düşük risk)**
1. **Genel nabız:** `LoadingScreen.pump()` bir statik nabıza dönüşür (ör. `LoadingScreen.nabiz()`).
   - Perde olsun olmasın, ≥150 ms geçtiyse `DisplayServer.process_events()`; perde varsa ayrıca çizim (bugünkü gibi).
   - Ağır döngülere çağrı eklenir: `IstDunya._kur` parça döngüsü, `mahalle_doku` döngüleri (8 sn'lik dahil), `IstSokak.build`, `attach_v2` adımları ve öğe/hücre döngüleri, `_on_pisir` iş başına, `World1453.bake` ve `Props.bake_static` çağrı başına, ordugâh `_pisir/_ekle`, kalabalık pişirme, `SiegeField` adımları, `Scenery.solidify`, `SurOyun.kur` adımları.
   - Girdi, bugünkü gibi `gui_disable_input` ile kilitli kalır.
2. **Perdesiz kurulumlara perde:**
   - Bölüm ortası yeniden kurulumlar (31o Eyüp, 24/26 → Ayasofya, 13) kısa bir yükleme perdesiyle sarılır. `GameState._show_loader` ve `LoadingScreen` yeniden kullanılır.
   - Açılıştaki ilk bölüm de perdeyle ya da en azından nabızla yüklenir.
3. **Ölçüm denetimi:** nabız, iki çağrı arasındaki en uzun boşluğu tutar.
   - Kurulum bitince `YUKLEMEAUDIT scene=… toplam_ms=… en_uzun_bosluk_ms=… kaynak=<son nabız yeri>` basar. Otomatik testte de çalışır (perde olmasa da).
   - Önce ADAY olarak eklenir. Hedef başsızda her bölümde en uzun boşluk < 1000 ms (Windows eşiği ~5000).

**Kesme B — Yükleme süresi kısalsın (görüntü ve çarpışma aynı kalacak)**
4. **İsrafı at:**
   - Hub bölgelerinde silinecek v2 öğeleri (hub şehri, `_temizle` kapsamı) `_on_pisir`/`_place_v2`'de baştan kurulmaz.
   - Önerilip uygulanmamış "doku öğeleri `_on_pisir` dışı" da tartılır.
5. **Önbelleği sağlamlaştır:**
   - Bölgeler arası silme doğrulanır. Varsa tür başına birkaç anahtar saklanır, en eski silinir.
   - Anahtar yalnız ilgili kurucu betiklerin md5'ini içerir; oyun sürümü ve ilgisiz betikler çıkar. Böylece güncelleme önbelleği gereksiz yere soğutmaz. Yanlış eski veri riski için kurucu sürüm sabiti de eklenir.
6. **Uzak ordugâh hücreleri:** Açılışta yalnız yakın olanlar kurulur; uzaktakiler perde kalktıktan sonra kare bütçesiyle akar (`IstDunya` `butce_us`/`IstSehir._queue` kalıbı). Kalabalık soğuk pişirmesi de aynı kalıp.
7. Her adım `tests/load_time.gd` (`ready` ms) ve `YUKLEMEAUDIT` ile önce/sonra, soğuk (önbellek silinmiş) ve ılık ölçülür.

Kurallar: geometri, çarpışma ve sözleşme altılısı birebir aynı kalır. KUTU YASAĞI, havada duran yok, tek görsel dil, replik/denge değişmez; yasaklar standart.

PACE donuk bulguları (G20) ayrı iş, sahibinin onayını bekliyor.

## Doğrulama
- `YUKLEMEAUDIT`: bütün bölümler ve bölüm ortası kurulumlar; en uzun boşluk < 1000 ms (başsız).
- `tests/load_time.gd`: 8y, 10h, 11, 12b, 13, 23, 24, 26, 31o için soğuk/ılık önce|sonra.
- xvfb'de 31o ve 24 yüklenirken aralıklı kare: perdedeki dönen simge ve çubuk ilerliyor olmalı.
- Sözleşme altılısı + HALICSONDA/MARMARASONDA karmaları aynı; CITYCHECK/STREETCHECK; ZFIGHT 0.
- Tam paket `fail=0`, menüye dönüş 2/2.
- **0.99.128** yayınlanır. Sahibi oyun içi güncelleyiciyle (Windows'ta ilk gerçek deneme) günceller ve yüklemeleri dener.

# (Eski) PLAN (24 Kasım 14:10 UTC, kap yeniden başladı) — 0.99.127 yayınını bitir, sonra 0.99.128 açık işleri

## Context
0.99.127 (ilk oyun içi güncelleyici sürümü + G17 denetimleri + G18 + kapı geçidi eteği + 20/31o görüş) main'de
(4c703023), site notu yazıldı (ec22418). CI #343 (45408223153) 13:54'te başladı; kap yeniden başlayınca CI'ı bekleyen
uyandırma kayboldu. Ortam yerinde: depolar, `$S/` betikleri, Godot, `/root/is/`. Sahibinin bekleyen kararı: Meshy Pro
(görsel deneme). Açık işler `devir/PAZAR_LISTESI.md` "AÇIK İŞLER" bölümünde.

## Adımlar
1. **CI #343'ü izle** (arka planda `sleep` uyandırması; send_later yok). Testler ~15:05, yükleme ~15:20 UTC.
   - Başarılıysa:
     - `curl -L https://github.com/TradersEntertainment/nothistorygamedemo/releases/latest/download/guncelleme.json` 200 dönmeli; JSON'da `surum` 0.99.127, windows/linux `boyut` ve `sha256` olmalı.
     - `releases/latest` → v0.99.127 olmalı.
     - Sahibine Türkçe kısa rapor: 0.99.127'yi bir kez elle indir; 0.99.128'den itibaren oyun kendini günceller.
   - Düşerse:
     - Günlüğü indir (`get_job_logs` → `logs_url` → curl), satırı bul.
     - Yerelde CI koşuluyla (`--max-fps 20`) yeniden üret, kökünden düzelt.
     - Yayın ağacını yeniden kur (docs/_* hariç, parent main). Main'e gönder; VERSION değişmediyse `.github/release-mirrors.txt`'e `#` satırı ekle (etiket gönderimi 403).
2. **Devir:** PAZAR_LISTESI + plan; mstrbought kaydet/gönder.
3. **0.99.128 hazırlığı (sahibinin onayı olmadan yardımcı açılmaz; kota):**
   - Makine zamanıyla bütün bölümlerin PACE donuk taraması: `tests/_denetim17/pace_tarama.sh`, setsid, 6–8 sa. Sahibine söz verildi.
   - Meshy Pro alınırsa: anahtar `request_credential` ile (host api.meshy.ai). 8y kapı önü + ordugâh için 8–10 model, Forward+ denemesi, ayrı dal. Her üretimden önce kredi tahmini.

## Doğrulama
CI #343 başarılı; açık depoda v0.99.127, kurulum/zip/ham ikililer ve `guncelleme.json` var; site changelog 0.99.127.

# (Eski) DURUM 24 Kasım 13:55 UTC — 0.99.127 CI #343 KOŞUYOR
- main 4c703023, site ec22418. CI biterse: indirmeler + `guncelleme.json` açık depoda mı; sahibine rapor.
- Açık işler PAZAR_LISTESI'nde (0.99.128 adayları). Sahibinin kararı bekleniyor: Meshy Pro (görsel deneme).

# DURUM 24 Kasım 11:40 UTC — CI #342 paketliyor (testler geçti); 0.99.127 adayı tam pakette
- Birleşik 3d747148: G16 + G17 + G18 + etek (0e9989f6) + 20. Tam paket `$S/tam127.sh` (setsid) → `$S/tam127_ozet.txt`.
- #342 biterse: site/indirme doğrula, sahibine rapor. Tam paket temizse 0.99.127 (VERSION, QA `$S/qa126.md`+`qa127.md`,
  surum127.py, release.yml değişti: ilk güncelleyici sürümü → guncelleme.json yayında mı kontrol).

# DURUM 24 Kasım 10:20 UTC — CI #342 (0.99.126, 3. deneme) KOŞUYOR; G17 + G18 AÇIK
- #341 de 20'de düştü (D20_G_DONE). Düzeltme her iki replikte; 20 FPS'de 8/8. main d8d34273, CI #342 45373873762.
- Uyanınca: #342 sonucu; başarılıysa sahibine rapor (indirmeler); G17/G18 teslimleri.

# DURUM 24 Kasım 09:00 UTC — CI #341 KOŞUYOR; G17 + G18 AÇIK
- 0.99.126 yeniden: main 503b14e8 (6ec065b6 = cd7f4532 + chapter20 düzeltmesi; + mirrors açıklama satırı), CI #341 45359520591.
- G18 (göz kontrolü bulguları; yazı `devir/gorev/prompt_G18_goz.txt` + danışman DÜZELTMELER): session_01RAjzxKy6HZWoDH7rF8FX1J → `wip/goz18`.
- G17 sürüyor (`wip/denetim17`). Bekçi `bekle_teslim.sh 4500` (bq7nvj489).
- Uyanınca: CI #341 sonucu (başarılıysa indirmeler; değilse günlük `/root/is/ci`), teslimleri incele, birleştir, tam paket, 0.99.127.

# DURUM 24 Kasım 08:50 UTC — CI #341 (0.99.126 yeniden) KOŞUYOR; göz kontrolü son bölümlerde
- #340 testte düştü (20 VISAUDIT, seyrek). Düzeltme + mirrors açıklama satırı → main 503b14e8, CI #341 (45359520591).
- Göz kontrolü bulguları `devir/GOZ_KONTROLU_BULGULAR.md` (1: hub kapı geçidi arazi yırtığı, 7 bölüm; 5/6: kutu binalar).
- Sıradaki: #341 sonucu → sahibine rapor; G17 teslimi; bulgular için 0.99.127 görevi (G18) ya da kendim.

# DURUM 24 Kasım 06:40 UTC — 0.99.126 YAYINDA; G16 BİRLEŞTİ; G17 SÜRÜYOR; GÖZ KONTROLÜ KOŞUYOR
- 0.99.126: main 7f3814ce, wip/0.99.126, site a456e3d, CI #340 (45341370406) koşuyor. Tam paket temizdi.
- G16 güncelleyici kabul, `wip/ist2-birlesik` = e956ba36 (parse PASS 369, GUNCELLEMECHECK PASS, 8y PASS).
- Göz kontrolü: `tests/_ist/bakis_kare.gd` (yeni dosya, kayıtsız) → `$S/bakis.sh` (bzwwfkvm4) → /root/is/bakis/<bölüm>/,
  özet /root/is/bakis/ozet.txt. Bitince: kareleri tam boy incele, bulguları listele, düzelt ya da G17/0.99.127'ye aktar.
- G17 (`wip/denetim17`) teslimde: rapor + kareler, birleştir, tam paket, 0.99.127 (güncelleyicinin ilk sürümü).

# DURUM 24 Kasım 04:55 UTC — 0.99.126 TAM PAKET (2.) KOŞUYOR; G16 + G17 YARDIMCILAR AÇIK
- tam126 (ilk): 456/456; 26 nophoto VISAUDIT tek seferlik (3/3 temiz), FLIGHTCHECK 300 sn bekçisine takıldı (eski kodla da
  306 sn → bekçi 600, f957694c). Sahibi 8y oynadı (0.99.125): görünmez kapı rampası (`pis()` tek ağı siliyordu), havada keçiler
  (`Goat.zemin`), pazarda donuk bekleme (Hasan 2,8 + finale koşulu) → 192e1f8c, doğrulama C temiz (dog126c), kareler gönderildi.
- tam126b (bjxr55qd4) → temizse 0.99.126 yayını (surum126.py güncel: 8y düzeltmeleri eklendi; qa126.md iki ders eklendi).
- G16 güncelleyici: session_01RAjzxJBHTfCWnxwsvEBzhd → `wip/guncelleyici` (0.99.127 adayı).
- G17 denetim genişletmesi: session_01RAjzxL7KPVdpkuc7zxNRzC → `wip/denetim17`.
- Sahibinin görsel notları PAZAR_LISTESI L (ordugâh boş, çadır/kapı/top/birim → Blender MCP).

# DURUM 24 Kasım 01:15 UTC — İKİ TESLİM GELDİ → birleştir, doğrula, 0.99.126

## Context
Sahibi "31o ve 17o'yu hallet" dedi; iki Opus yardımcı teslim etti (kap yeniden başladı ama ortam duruyor: depolar,
Godot, `$S/` betikleri yerinde).
- **TAŞIMA 13** `wip/ist2-tasima13` 50445809: 31o yeni sette 8y kalıbıyla (SurHub "romanos" + `IstBaglama` bölge
  `fallen31o`), tek sur, cadde/sayılar aynı, kalabalık, evre geçişi temiz, `ESKI_VARSAYILAN = []`. Testler PASS (31o ×2,
  eski ×1, CITYCHECK 31o ×2, ZFIGHT 0, sözleşme altılısı aynı, ortak dosya bölümleri PASS). Zayıflar: kurulum 39 sn
  (başlık kartından sonra donuk ekran), ev evresi belleği 1,47 GB, tepeden cadde çevresi ~57 m seyrek (kök: `sehir.gd:~3159`
  oyun alanı tek daire), menu_return 31o varsayılanla FAIL (MR_AFTER=60 PASS, 24 ile aynı; önceden var olan v2 sızıntısı).
- **TUR 15** `wip/ist2-tur15` b2a2efab: `DENIZ_UZAK {"springs": INF}`, Eugenius yuvarlak kule, Galata surları yeni kalem
  (basamaklı). Öteki deniz bölümleri DENIZSET + görünüş karmasıyla birebir; 17o ×2 + eski PASS; ilkel −%0,8. Zayıflar: uzak
  sur gece çok koyu (tek görsel dil gereği bırakıldı), `in_world=false` ölü yolu eski (oynanmıyor).

## Adımlar (ben, sırayla)
1. Kareleri tam boy incele (iki dalın `kare/sahip_*` + ÖNCE/SONRA); sahibine `kareler/0_99_126/` (mstrbought), gönder.
2. `wip/ist2-birlesik`'e iki dalı birleştir (dosya kümeleri ayrık; çakışma beklenmiyor), parse PASS.
3. **31o donuk ekran**: 39 sn eşzamanlı kurulum başlık kartından sonra — 24/8y gibi bölüm açılışına (yükleme sırasında)
   alınabiliyorsa küçük düzeltme (`chapter31o.gd`); değilse sürüm notunda dürüstçe belirt. `sehir.gd` isteği 1 (uzun oyun
   alanını şerit boyunca küçük dairelere böl; kare alanlar eşik altında → 7b/13/23/24 bit bit aynı) küçük ve güvenliyse
   ben yaparım; aksi hâlde sonraki görsel tura.
4. Doğrula: sözleşme altılısı (SURSOZLESME 13/8, SUROYUN 0/0/0, WALKTHRU 7/7, ESYATEST, HALICSONDA 661, MARMARASONDA 1837),
   31o çeşitleri ×2 + `--eskisur=31o`, CITYCHECK 31o/24, ZFIGHT 31o/17o, 17o çeşitleri ×2, 8y/13/23/24, DENIZSET farkı;
   menu_return 31o (MR_AFTER=60) ve 26.
5. Tam paket `tam126.sh` (tam125 kalıbı; v2 önbellek yarışına karşı paralel koşuda ısıtılmış önbellek) → fail=0, denetim 0.
6. **0.99.126**: VERSION, QA dersleri, ağaç docs/_* hariç parent main 88ed3d3c, main + wip/0.99.126, site notu
   (`surum126.py`: eski surda kalan bölüm yok; 21o yeraltında; bilinen zayıflar), anahtar taraması 0, CI.
7. Devir + PAZAR_LISTESI E kapanır; sahibine Türkçe kısa rapor (+ ElevenLabs anahtarı hatırlatması).

## Doğrulama
Yukarıdaki hedefli koşular + tam paket fail=0, denetim 0; CI Release başarılı; site changelog'da 0.99.126.

# (Eski) DURUM 23 Kasım 18:22 UTC — İKİ YARDIMCI AÇILDI (Fable düzeltmeleri ekli; yazılar devir/gorev/prompt_T13_31o.txt, prompt_T15_17o.txt)
- TAŞIMA 13 (31o, 8y kalıbı SurHub + IstBaglama.build): session_01RAjzxMPM5qpCxPgidBDprx → `wip/ist2-tasima13`
- TUR 15 (17o, DENIZ_UZAK "springs" + galata_view): session_01RAjzxL8cmxzEWx9Nj2Dq2c → `wip/ist2-tur15`
- Nöbetçi: `$S/bekle_rapor.sh 7000` (rapor.md "hâlâ kötü" + durum.md BİTTİ/TESLİM). Teslimde: rapor + tam boy kare, birleştir,
  doğrula, tam126, 0.99.126.

# PLAN (23 Kasım ≈13:15 UTC): 31o ve 17o'yu bitir → 0.99.126 "İstanbul uyarlaması tamam (eksiksiz)"

## Context
0.99.125 yayında (main 88ed3d3c, CI başarılı). Sahibi: "31o ve 17o'yu hallet, şimdi başla". Kalan iki eksik:
- **31o**: yeni sette (`SurSetSahne`) ova `field.world = false` → surun ardında World1453 şehri, WorldWalk ve CityLife
  (yaşayan kalabalık) yok; bu yüzden 31o `SurSet.ESKI_VARSAYILAN = ["31o"]` ile eski sette. Yeni set kesimin gerçek
  dünya yerini biliyor (`sur.a.xf`: yerel → İstanbul v2; `SurSetSahne._harita` bunu kullanıyor) ve hub bölümleri
  (13/23/24) v2 şehrini (`IstSehir` + `IstHayat`/`IstHayatYakin`) `IstBaglama` (`scripts/world/ist/baglama.gd`) ile kuruyor.
- **17o**: karşı kıyıda eski kutu şehir surları: `chapter17o.gd:242 Scenery.city_walls(...)` ve `HornWorld` kıyı surları;
  HornWorld yeni deniz kalemini (`deniz_set.uzak_parca/uzak_kule`, `horn_world.gd:559 _deniz_yakin`) yalnız bölümün
  `keep` alanına ≤ 250 m kullanıyor, 17o'nun keep'i yok → hepsi eski kutu.

## Yaklaşım: iki Opus yardımcı aynı anda (taban `wip/ist2-birlesik` = f1f007c5), görev yazıları önce Fable'a okutulur
1. **TAŞIMA 13 — 31o surun ardı** (dal `wip/ist2-tasima13`). Varsayılan çözüm: v2 şehri `IstBaglama` kalıbıyla
   `sur.a.xf` üzerinden yeni setin arkasına oturt (hub'larla tek görsel dil); v2'nin kendi sur dilimi set kesiminde gizlenir
   (sur_set_hub kalıbı). Kalabalık 31o'nun dönemine uygun (eski `CityLife.opts_for(31o)` rolleri: fetih ertesi, devriye).
   Eski World1453'ü hizalamak ancak eski kutu sur görünmediği kanıtlanırsa. FallenCity caddesi, yanık ev, bölüm sayıları
   değişmez; aşama geçişlerinde (eyüp/aya) v2 dünyası temiz kalkar. Sonra `ESKI_VARSAYILAN`'dan 31o çıkar
   (`--eskisur=31o` çalışmaya devam). Dosyalar: `chapter31o.gd`, `sur_set.gd` (yalnız liste), `sur_set_sahne.gd`/`baglama.gd`
   (yalnız seçmeli bayrak, varsayılan kapalı), gerekirse `tests/city_check.gd` (ölçüt gevşetmeden), yeni `tests/_ist/tasima13_kare.*`.
2. **TUR 15 — 17o uzak surlar** (dal `wip/ist2-tur15`). 17o için HornWorld'e seçmeli "deniz kalemi her yerde/17o bölgesi"
   (ör. 17o'ya görüş alanını kapsayan keep ya da bayrak), `Scenery.city_walls` yeni kipte kurulmaz; öteki deniz bölümleri
   (4b, 17, 18b, 19, 19o, 29, 29o, 38o) bit bit aynı (DENIZSET satırları ve üçgen sayıları değişmez). `--eskisur=17o` eskiyi
   kurar. Dosyalar: `chapter17o.gd`, `horn_world.gd` (seçmeli), yeni `tests/_ist/tur15_kare.*`.
Her iki görev: KUTU YASAĞI, havada/gömük yok, tek görsel dil, yakın (0,5–3 m) ve oyuncunun gerçek bakışından TAM BOY
kareler (eski/yeni), rapor `docs/_kanit_ist2_<görev>/`; yasaklar (oturum/zamanlayıcı/ajan araçları, pkill, ses üretimi,
PR, main, liste dışı dosya, denetim susturma, izin istemi doğuran komutlar). Nöbetçi `bekle_sure.sh` (send_later yok).

## Teslimde (ben)
Rapor + tam boy kareler (sahibine `kareler/0_99_126/`), birleştir, sözleşme dörtlüsü + 31o çeşitleri ×2 + CITYCHECK/
STREETCHECK + ZFIGHT 31o/17o + 17o çeşitleri + HALICSONDA 661 / MARMARASONDA 1837; tam paket (`tam126.sh`, tam125
kalıbı); temizse **0.99.126** (VERSION, QA, ağaç docs/_* hariç, main + wip/0.99.126, site notu: "eski surda kalan bölüm
yok; 21o yeraltında"), CI. Devir ve PAZAR_LISTESI E maddesi kapanır.

## Doğrulama
Yardımcı kanıtları + benim hedefli koşularım; tam paket fail=0, denetim 0, menüye dönüş 2/2; anahtar taraması 0; CI başarılı.
Süre tahmini: yardımcılar 3–4 saat, birleştirme + tam paket + yayın ≈ 3 saat.

# (Eski) GÜNCEL (23 Kasım 11:40 UTC) — 0.99.125 YAYINDA
- main 88ed3d3c (parent 6c2fda8a), wip/0.99.125, birleşik f1f007c5, site 0578246. CI Release #339 (45166682565) koşuyor;
  nöbetçi bre05dzmp (3600 sn). Bitince: CI sonucu → sahibine kısa rapor. Sonra görsel program (PAZAR_LISTESI G/H/I + E).

# (Eski) GÜNCEL (23 Kasım ≈08:20 UTC)
- TAŞIMA 12 (0c92c915) ve TUR 14 (823c7d55) BİTTİ, raporlar okundu, kareler tam boy: kabul. `wip/ist2-birlesik` = 627ace1c
  (ikisi temiz birleşti, GÖNDERİLDİ). Sözleşme/sondalar aynı (SURSOZLESME 13/8, SUROYUN 0/0/0, yürüyüş 7/7, ESYATEST,
  HALICSONDA 661, MARMARASONDA 1837, T8DTEKME). TAM PAKET 0.99.125: `$S/tam125.sh` → `$S/tam125_ozet.txt` (buk6l2vvj).
  Temizse: VERSION 0.99.125 + `$S/qa125.md`, kayıt, ağaç (docs/_* hariç, parent origin/main 6c2fda8a), main, site
  `$S/surum125.py --yaz`, CI. Sahibine TUR 14 kareleri atıldı (`kareler/0_99_125/`). Fable ikinci göz koşuyor.
- Kalan zayıflar (sonraki görsel tur): 42b meydanı boş/çorak, 31o şehir evleri pastel kutu + soluk beyaz top "kayalar",
  17o karşı kıyı uzak surları eski, 10h =yuru test çeşidinde heyet üst üste (run_tests'te yok), bütçe bazı tepeden karelerde.

# (Eski) GÜNCEL (23 Kasım 05:30 UTC)
- AÇILDI: TAŞIMA 12 …NBTjprVSaRXXzeFrH → `wip/ist2-tasima12`; TUR 14 …NKHnUFcNtUwFXX7qC → `wip/ist2-tur14` (taban taban19).
- Ortam yeniden kuruldu: `/home/user/nothistorygame` (wip/ist2-birlesik de845619, import + PARSECHECK PASS 368),
  `/home/user/nothistorygamedemo`, Godot `$S/godot/godot`, betikler `$S/` (tam124.sh, birlesik17.sh, surum124.py),
  nöbetçi `$S/bekle_sure.sh 1800` (arka plan). Teslimlerde: rapor + tam boy kare, birleştir, doğrula, 0.99.125.

# DURUM (23 Kasım): moladan dönüş — "naptık, en son nerede kaldık"

## Context
17 Kasım'da sahibi kota azaldığı için Pazar'a (22 Kasım) kadar mola istedi. Molaya girmeden:
- **0.99.123** yayında: yeni surda 15 bölüm (26/26o, Blakherna dahil), eşya fiziği, Tolga'nın hareket hissi.
- **0.99.124** yayında (main 6c2fda8a, CI başarılı): +12 bölüm (6b, 7b, 10h, 12b; 4b, 17, 18b, 19, 19o, 29, 29o, 38o) →
  yeni surda 27 bölüm. Tam paket 456/456, denetim 0.
- Hâlâ eski sette: 8y (yeni hâli hazır, 18 cm havada asker kusuru yüzünden geçici eski sette), 13, 17o, 21o, 23, 24, 31o,
  41o, 42b.
- Mola sırasında konuşulanlar `devir/PAZAR_LISTESI.md`'de: karakterler önce (G), "gören oynamak istesin" görsel programı (H),
  500–1000 $ sanatçı bütçesi + MotionBricks (I), açık dünya yol haritası (J), Unreal'a geçmeme önerisi (sohbette).
Kap sıfırlanmış: oyun ve site depoları, Godot, geçici betikler ve plan dosyası gitti. Kalıcı olanlar: GitHub dalları
(`main` 6c2fda8a, `wip/ist2-birlesik` de845619, `wip/ist2-taban19` a38ad405) ve `/home/user/mstrbought/devir/`
(Pazar listesi, iki hazır görev yazısı, doğrulama/sürüm betikleri, plan).
Pazar geçti; Pazar işleri başlamadı (yardımcı açılmadı). Haftalık kota 22 Kasım'da yenilenmiş olmalı.

## Yapılacaklar (onaydan sonra, sırayla)
1. **Kurulum:** oyun deposunu (`TradersEntertainment/nothistorygame`, `wip/ist2-birlesik`) ve site deposunu klonla;
   Godot 4.4.1'i scratchpad'e indir; `devir/gorev/` betiklerini scratchpad'e geri koy; `--import`; ayrıştırma testi.
2. **İki Opus yardımcıyı aç** (görev yazıları hazır, Fable düzeltmeleri ekli, taban `wip/ist2-taban19` = a38ad405):
   - TAŞIMA 12 (`devir/gorev/prompt_C12_fon.txt`): 8y havada asker kök nedeni + 13, 23, 24, uzak hub, 31o, 41o, 42b; 17o/21o
     denetimi; 10h molozu.
   - TUR 14 (`devir/gorev/prompt_A14.txt`): Romanos kapı kemeri, harpuşta, döşeme, şehirde Haliç/Marmara kıyı surları,
     Blakherna kalanları.
3. Nöbetçi; teslimlerde rapor + tam boy kareler, birleştir, doğrula (`birlesik17.sh` kalıbı), sonra **0.99.125**
   ("İstanbul uyarlaması tamam"): tam paket (`tam124.sh` kalıbı), sürüm notu, main, site, CI.
4. Ardından karakter dilimi / görsel program (G, H, I): sanatçı ilanı + şartname (sahibi isterse hemen).

## Sahibinden beklenen kararlar (bloklamaz; varsayılanlarla ilerlerim)
10h gediği (varsayılan B: yerinde kalır, görünüşü düzelir), kapı kanatları açık mı kapalı mı (varsayılan: bugünkü gibi
açık), ek hesap, ElevenLabs anahtarı (yenilenmeli), sanatçı ilanını şimdi mi yazayım.

## Doğrulama
Kurulumda parse PASS ve sözleşme dörtlüsü; yardımcı teslimlerinde görev yazılarındaki kanıtlar; sürümde tam paket fail=0,
menüye dönüş 2/2, anahtar taraması 0, CI başarılı.
