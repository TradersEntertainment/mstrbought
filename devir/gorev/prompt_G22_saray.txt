**BU GÖREV ONAYLIDIR. Onay ya da soru beklemeden HEMEN başla, sonuna kadar kendi başına çalış, bitince rapor ver. Kimseye soru sorma; takılırsan bulduğunu rapora yaz ve en iyi kararla devam et. Dal oluşturmak, her adımda kaydetmek ve yalnız kendi dalına (`wip/saray22`) göndermek önceden onaylıdır.**

# G22 (Opus): Bizans meydanını böl — saray avlusu ve kançılarya ~430 m içeri, surda Giustiniani ve kapı kalır

Depo: `TradersEntertainment/nothistorygame` (yerelde klonla). Taban: `wip/ist2-birlesik` = **6dec6901** (0.99.128 + G21 Lykos şeridi + harita). Kendi dalın: `wip/saray22` (tabandan aç, yalnız buraya gönder).

## Neden (okuyarak doğrula)
Oyun sahibi 43o drone karesinde Romanos Kapısı'nın hemen ardındaki Bizans meydanını gördü ve sordu: "bu şehrin yeri doğru mu, çok garip duruyor, ne alaka surlar dibinde". Kararı: **saray avlusu ve kançılarya içeri taşınsın; surda yalnız Giustiniani'nin yeri ve kapı kalsın.**

Gerekçe:
- Romanos'ta (Mesoteikhion) savunmayı İmparator ve Giustiniani yönetti; bu doğru.
- Saray ve Logothetes kançılaryası orada değildi; sahne için toplanmışlar (GDD §9.4, `scripts/level/byz_city.gd:1-6`).
- Aşama 1 (G21, birleşti) surun ardını 150–250 m'lik bostan/bağ/harabe şeridine çevirdi ve yeni yeri hazırladı:
  - `SurHub.SARAY_OFS = Vector3(-400, 0, 130)` (hub yereli; `scripts/world/ist/sur_set_hub.gd:151-161`) ve `saray_v2()`.
  - v2 dünya ≈ (−1239,6; ~6,5; −295,7); alan 84 × 70 m, eğim ≤ %3; v2'de kapıdan oraya yol (`IstSokak._saray_yolu`, `sokak.gd:645`) ve alanda ev yok.
  - Rapor: `docs/_kanit_lykos21/rapor.md` (SARAY_OFS seçimi bölümü).

## Bugünkü yapı (doğrula; ayrıntılı kod haritası aşağıda)
- **ByzCity "walls"** (`byz_city.gd`) tek, 84 × 70 m'lik blok. Hub yereli: +x surlar/ova, −x şehrin içi, +z Haliç yönü; iç sur x 32,5 (yeni) / 34 (eski).
- **Sabitler** (`:10-20`): START (0,0,12), GIUST_POS (26,0,−14), EMPEROR_POS (−27,0,−14), EXIT_POS (33,0,5,5), NIKO_POS (1,5,0,−27), HALL_Z0 −30, ROOM_Z0/Z1 −32,5/−40.
- **Kurucular:**
  - `_build_ground` 383-394, `_build_street` 523-601 (çeşme (0,−16), tezgâhlar, tabelalar 598);
  - `_build_chancery` 1488-1581: x = 0'a gömülü (`x0/x1 = ∓3,5·ROOM_W`, `clerk_x` 1825);
  - `_build_walls`/`_build_walls_yeni` 1594-1687, `_build_giust_yeri` 1653-1666, `_build_gate` 1694-1770;
  - `_build_palace` 1775-1822: EMPEROR_POS'a göre;
  - `_build_hub_people` 191-229 (Niko + kayık NIKO_POS'ta, `_build_council` 258-282, `_build_cell` 234-255);
  - `_build_small_skyline` 746-773, `_RESERVED` 1047-1060, `_build_fill` 1142-1290, `_walls_edge` 177-180;
  - `Dressing.auto` 99-115.
- **Hub dünyaya yerleştirme:**
  - Eski dünya: `World1453.REGIONS["byz_walls"]` (`world1453.gd:106-108`: `world.x = 5,5 − yerel.z`, `world.z = −36,3 + yerel.x`) ve `FAR_REGIONS` (`:118`).
  - Eski dünya uzak kopyası: `ByzCity.far_hub` (`byz_city.gd:122-172`).
  - Eski dünyada `SiegeField`, hub alanında kendi iç surunu ve kapısını kurmaz (`siege_field.gd:262-298`); uzak hub'ın kutu iç suru o boşluğu doldurur.
  - v2: `SurHub.hub_v2()` (`sur_set_hub.gd:76`; köken (−1660,16; 14,09; −296,24), yaw 161,9°).
  - v2 bağlama: `IstBaglama.build` (`baglama.gd:354-491`; `YAMA` `:46`, `TEMIZ` `:49`, `hub_alan` `:454-462`, `_temizle`/`silinecek_mi` `:535-581`).
  - v2 şehir: `IstSehir` (`sehir.gd`: hub düzlemesi `:2044`, `hub_sehir` öğesi `:2048`, `_make_hub` `:2216-2247`, `oyun_alanlari` `:2544-2556`, `hub_xf` `:2565-2581`).
- **Yükseklik:** SARAY'ın v2 arazisi ~6,5; hub kökeni 14,09. Yani iç mahalle hub yerelinde **y ≈ −7,6**. Arazi düzlemesi o yükseklikte olmalı.
- **Eski dünya karşılığı** (byz_walls): (−124,5; ?; −436,3). Eski dünyada `SiegeField` tek bir ortak düz y kullanıyor (`siege_field.gd:164-188`); dikdörtgen başına yükseklik gerekecek.

## Bölümler (kim neyi kullanıyor; doğrula)
| Bölüm | Kullandığı | Bugünkü gidiş-geliş |
|---|---|---|
| **6 (6b; `=byz*`)** | kançılarya (kâtipler, Theodoros = oda Η), martı kovalamacası (kançılarya → surlar, PERCHES `:29-31`, tünek başına 14–16 sn sabır), Giustiniani, İmparator (saray), kapıdan çıkış, divan/mangal/kayık yan olayları, çatı tırmanışı, hücre (başarısızlıkta) | 3 yürüyüş (kovalamaca, surlar→saray 53 m, saray→kapı 63 m) |
| **7 (7b; `=byz*`, `=tea`, `=lost`, `=form`, `=wall*`, `=fez`)** | Nihat serbest gezer/uçar. İzler: kançılarya `(−2,2,0,−26,5)` gömülü (`chapter7.gd:258`), surlar GIUST_POS+…, saray EMPEROR_POS+(3,2,0,2,5), hücre, dışarı EXIT_POS+… (`:239-262`). Rapor kapısı START+(0,0,2,6) (`:268`). Tanıklar: Niko, Theodoros, Giustiniani, İmparator. | süre eylem başına (mesafe değil) |
| **10h** | kapıdan giriş (EXIT_POS−3), sarayda huzur (`HALL` EMPEROR_POS'un **kopyası**, `chapter10h.gd:16`), gece işleri (gedik BREACH (32,4,0,−26), Giustiniani, kançılarya önünde Niko, çıkış) | kapı→saray ve saray→START KARARMA (`:290`, `:420`); gece yürür |
| **12b** | yalnız sur yolu; `city.emperor` düğümü sura taşınır (`chapter12b.gd`, ~22 kullanım) | 0 |
| **13 `=city`** | START+(0,0,−4)'te doğar, 35 m ötedeki Niko'ya bakar (`chapter13.gd:220-223`) | 0 |
| **23** | bütünüyle saray avlusu (`HALL := ByzCity.EMPEROR_POS`, `chapter23.gd:14`, 73-130) | 0 |
| **24 (ilk yarı)** | ana caddede alay: ROUTE_A (0,0,−24) kançılarya önü → ROUTE_B (0,0,6), çeşmeyi dolanır (`chapter24.gd:15-25, 481-487`); ikinci yarı "aya" parçası | 0 |
| 8y, 25, 26, 31o, 44b | ByzCity "walls" kullanmıyor | — |

Testler `tests/run_tests.sh:113-147` (çeşitler); kare testleri `tests/_ist/tasima12_kare.gd:97`, `tasima10_kare.gd:115-122`, `tur14_bolum_kare.gd:117-124`; `tests/city_audit.gd:49-52`; `flight_check.gd`.

## Hedef
### 1. Bölünme (tek bölüm çerçevesi, iki kök düğüm)
- **Surda kalan** (hub kökeni, bugünkü yerinde):
  - iç sur (yeni `SurHub.kur` / eski kutu), Romanos kapısı, Giustiniani'nin iskelesi ve masası, nöbetçiler ve meşaleler;
  - kapı önünde küçük bir nöbet/ikmal yeri (sandık, ocak, su fıçısı; tek görsel dil, kutu değil);
  - caddenin sur ucu → G21'in iç yoluna (`oyun_bag` ucu) bağlanır.
  - Gedik (10h BREACH) ve 12b sur yolu yerinde.
- **İçeri giden** (SARAY_OFS'ta, hub yerelinde y ≈ −7,6; G21'in alanı):
  - saray avlusu + İmparator + divan + mangal;
  - kançılarya (7 oda, 7 kâtip, Nihat cameo);
  - meydan + çeşme + tezgâhlar + tabelalar (`ΚΑΓΚΕΛΛΑΡΙΑ`, `ΠΑΛΑΤΙΟΝ`; `ΤΕΙΧΗ` surları gösterir);
  - Niko ve kayığı, zindan hücresi (6/7), çatıları tırmanılan cadde evleri.
  - İç düzenin kendisi bugünkü gibi (kançılarya, cadde, meydan, saray ilişkisi aynı); yalnız bütün grup taşınır.
- **Uygulama:**
  - ByzCity'de iç grubu ayrı bir `Node3D` kökünde kur (`saray_kok`, konum SARAY_OFS + y).
  - Sabitleri iki gruba ayır: `SARAY_*` iç grubun yereli + dünya konumu için yardımcı (ör. `ByzCity.saray_konum(v)`).
  - Kançılaryanın x'i sabite bağlanır.
  - `_RESERVED`, `Dressing.auto` alanları, `_build_fill` ve `_walls_edge` her iki alan için.
  - Tek dünya ızgarası; kök düğüm döndürülmez (hub ekseni aynı yönde).

### 2. Dünya (iki dünyada)
- **v2:**
  - `IstSehir.oyun_alanlari()`'na ikinci alan "saray" (G21 yalnız sokak tarafında damgaladı; şimdi resmi oyun alanı).
  - `IstBaglama`: `YAMA`/`TEMIZ` dikdörtgen listesi; SARAY'da arazi düzlemesi kendi yüksekliğinde, kenarı yumuşak.
  - `hub_alan`/`_oyun` iki alan; `_temizle` iki alanı temizler.
  - `hub_sehir` öğesi iki öğe olur: sur parçası + `hub_saray` (`_make_hub` ikiye).
  - Hub bölümleri bu iki öğeyi `_temizle` ile kaldırır; uçuş bölümleri (7a, 11) ikisini de görür.
- **Eski dünya:**
  - `FAR_REGIONS` iki dikdörtgen. Sur parçası z −2,3'ü kesmeye DEVAM eder (yoksa SiegeField ikinci bir iç sur kurar); alan surdaki parçaya küçülür.
  - `far_hub` iki pişirme: sur parçası (eski kutu iç sur bu görevde KALIR; Osmanlı tarafı surlarının tamamı kutu, ayrı iş) + iç mahalle.
  - `siege_field.gd`: dikdörtgen başına düz y (`flat_rects`/`flat_y`, `:150-300`); SARAY alanı kendi arazi yüksekliğinde.
  - Eski dünya yolu: ROAD (`city_plan.gd:51`) SARAY'ın ~86 m doğusunda. **`CityPlan.PLAZAS`/`MAIN`'e DOKUNMA** (rng kayar, harita eskir); kısa bağlantı ancak son-süzgeç gibi rng'yi kaydırmadan.
- **Kalabalık AZALMAZ:**
  - İç mahallede bugünkü hub halkı (`_build_life`, Dressing yürüyenleri).
  - Surdaki parçada nöbetçiler ve işçiler.
  - CITYCHECK 24 ve 31o (≥ 8 sivil, `tests/city_check.gd`) gevşetilmeden geçer.

### 3. Bölüm akışları (içerik, replik, denge AYNI)
- **Senaryolu gidiş-gelişler: 10h kalıbı** kararma + yerleştirme (`hud.fade_to(1)` → konumla → `fade_to(0)`).
  - Hedef işareti öteki alanı gösterir; oyuncu isterse yolu yürür.
  - Kararma, hedef öteki alandaysa senaryonun bugün "yürü" dediği yerde. Ör. 6b'de Giustiniani izin verince "İmparator'a git" → kararma → saray avlusu.
  - 10h'nin iki kararması bugünkü gibi; START ve hedefler yeni yerlere.
- **6b:**
  - Martı kovalamacası iç meydanda: kançılaryadan çıkıp meydanın tüneklerinde; tünek sayısı ve sabır süreleri aynı (DENGE AYNI).
  - Son tünekten sonra `D6B_T_CHASE_4` "Surlara gidiyor!" ile martı surlara uçar → kararma → martı Giustiniani'nin masasında (son tünek).
  - z eşikleri (`chapter6.gd:144, 306, 791, 871`), otomatik test (`:1237-1261`), `byzyuru` botu (`:115-127`), `VISTAS`/`ROOF_BOUNDS` (`:19-25`), hücre (`:734-736, 1076-1084`) iç gruba göre.
- **10h:** `D10H_L_04` "Bak, saray. Kaftanını düzelt." kapıda değil, saraya varışta (kararmadan sonra) çalar. Gece işlerinde Niko kançılarya önünde (içeride); gidiş kararmayla.
- **7b:** iz ve tanık konumları ve rapor kapısı iç gruba göre. Uçuşta iki alan arası serbest.
- **12b:** saray kurulmasa da `city.emperor` düğümü kurulur.
- **13 `=city`:** iç meydanda doğar, Niko'ya bakar.
- **23:** yalnız iç grup + gerekirse sur parçası arka planda.
- **24 ilk yarı:** iç caddede; ROUTE_A/B iç gruba göre.
- **Ortak kurallar:**
  - Var olan replik metni ve sesi, denge, gizli süre, sayaç, sabır DEĞİŞMEZ. Yeni replik yok.
  - Bir repliğin ÇALDIĞI AN yerleşim gereği değişebilir (`D10H_L_04` gibi); rapora yaz.
  - Seslendirilmiş "Surlara gidiyor!", "Önce izin, sonra surlar, sonra İmparator", "Casus! Buraya. Önce kançılarya." anlam olarak tutarlı kalır.

### 4. Uzak görünüş ve 43o
- **43o drone** (eski dünya, iki yol; G21 raporunda açıklandı: taze süreç ve önce v2 bölümü kurulmuş süreç):
  - Romanos'un ardında artık yalnız Giustiniani'nin yeri ve kapı.
  - Saray mahallesi ~430 m içeride, bostan şeridinin ötesinde.
  - Kare: `--chapter=43o --shots=<klasör>` (`c43o_05_feed_walls.png`, `chapter43o.gd:1000-1004`) ve G21'in `tests/_ist/lykos21_kare.*` sahnesi.
- **v2 uçuşları (7a, 11):** iki parça doğru yerde ve yönde.

## Kurallar (kesin)
Türkçe çalış, Türkçe yaz. Godot 4.4.1, gl_compatibility, prosedürel GDScript.
- **Sahibinin kuralları:** KUTU YASAĞI; HAVADA DURAN HİÇBİR ŞEY OLMAZ (gömük de yok; iç mahalle arazisine oturur; kenarlarda basamak/şev); TEK GÖRSEL DİL.
- **Sur sözleşmesi DEĞİŞMEZ.** Her kayıttan önce aynı çıkmalı:
  - `tests/_ist/sur_sozlesme.tscn` → `SURSOZLESME PASS kalem=13 kesim=8`
  - `tests/_ist/sur_oyun_denetim.tscn` → `SUROYUN nokta=519 havada=0 gomuk=0 katida=0`
  - `tests/_ist/sur_oyun_yuru.tscn` → `WALKTHRU OZET yol=7 tamam=7 takilma=0 dusme=0`
  - `tests/_ist/esya_fizik.tscn` → `ESYATEST PASS`
  - `tests/_ist/tasima11_halic_sonda.tscn` → `HALICSONDA OZET carp=661 karma=3854034809`
  - `tests/_ist/tur14_marmara_sonda.tscn` → `MARMARASONDA OZET carp=1837 karma=2250736444`
- **Eski dünyanın rng sırası kaymaz:** `CityPlan` meydan/ana yol listeleri, `WallRear.depth/in_band` aynı. WORLDCHECK (`byz_walls` çerçevesi) aynı.
- **Yükleme:** `YUKLEMEAUDIT_KESIN` çıkmaz. Yükleme süresi önce|sonra (`res://tests/load_time.tscn -- --only=chapter24`, ayrı koşularla 23, 10h, 6) raporlanır; belirgin artış olmasın.
- Harita (`assets/ui/map1453.png`) eski dünyada değişen bir şey olursa `godot --headless --path . res://tools/map_bake.tscn` ile yeniden pişirilir; MAPCHECK PASS.

## Doğrulama (çıktılar `docs/_kanit_saray22/testler/`)
1. Ayrıştırma PASS; sözleşme altılısı aynı.
2. **Bölüm testleri** (`--max-fps 20`, `godot --headless --max-fps 20 --path . -- --chapter=X --autotest[=v]`, `run_tests.sh` süzgeciyle):
   - hub bölümlerinin BÜTÜN çeşitleri ×2: 6 `=byz*`, 7 `=byz*`/`=tea`/`=lost`/`=form`/`=wall*`/`=fez`, 10h, 12b, 13 `=city`, 23 (+ `=osm`), 24;
   - kalan dünya bölümleri ×1: 6, 7, 8y, 9, 10, 10b, 10z, 11, 13, 16, 24o, 25 (osm), 31o, 43o.
   - Hepsinde `AUTOTEST PASS`; VISAUDIT, WALKTHRU, HELDAUDIT, ARMAUDIT, GORUNMEZZEMIN, ALETAUDIT, DONUKAUDIT, ESYAAUDIT (dusme/havada/gomuk/tikama/sinir), JOURNEY, YUKLEMEAUDIT_KESIN, SCRIPT ERROR satırı 0.
3. **Ayrı koşular:** CITYCHECK `CITYCHECK_CH=24` ve `=31o` PASS; STREETCHECK, FLIGHTCHECK, WORLDCHECK, WALKCHECK, MAPCHECK PASS; ZFIGHT 0 (değişen bölümler); `tests/menu_return.tscn -- --chapter=26` ve `20o` PASS.
4. **Kare testleri** (`tasima12_kare`, `tasima10_kare`, `tur14_bolum_kare`, `city_audit`) yeni konumlara göre güncel ve çalışır.
5. **Kareler** (TAM BOY, `kare/`, önce|sonra, gündüz):
   - 43o drone sahibinin bakışı (Romanos'a ~70 m'den, dışarıdan içeri) iki yoldan;
   - 7a ya da 11 uçuşunda iki parça;
   - iç mahalle göz hizasında: saray avlusu + İmparator, kançılarya kapısı, meydan + çeşme, Niko;
   - surdaki parça: Giustiniani'nin yeri, kapı, nöbet yeri;
   - 6b'de martı kovalamacası ve sura kararma; 10h'de saraya varış;
   - sahibine en iyi 3 kanıt `kare/sahip_*.jpg`.
   - Kareler DALA KAYDEDİLİR.

## Kanıt → `docs/_kanit_saray22/`
- `rapor.md`:
  - her hedef maddesi TAMAM / KISMEN / YAPILMADI;
  - bölüm başına değişen akış (kararma noktaları, repliğin çaldığı an);
  - değişen dosya:satır listesi;
  - yükleme süresi önce|sonra;
  - "hâlâ kötü olanlar" (dürüst).
- `durum.md`: her kayıtta güncel; iş bitince ilk satırı `# G22 durum: BİTTİ`.

## Dosya sahipliği
Aynı anda başka yardımcı yok.
- **SEN:**
  - `scripts/level/byz_city.gd`, `scripts/world/world1453.gd` (ya da bulunduğu yol; yalnız `FAR_REGIONS`/bölge/keep/`far` kurulumu), `scripts/level/siege_field.gd` (yalnız `flat_rects`/`flat_y`/`ground`/`city_ground` ve hub boşluğu), `scripts/world/ist/baglama.gd`;
  - `scripts/world/ist/sehir.gd` (yalnız `_make_hub`, hub düzlemesi/öğesi, `oyun_alanlari`, `hub_xf`, dışlama listeleri);
  - `scripts/world/ist/sur_set_hub.gd` (yalnız yardımcı ekleme; var olan satır değişmez);
  - `scripts/world/ist/sokak.gd` (yalnız `_saray_yolu` ve saray alanı damgası, gerekiyorsa);
  - bölümler: `chapter6.gd`, `chapter7.gd`, `chapter10h.gd`, `chapter12b.gd`, `chapter13.gd`, `chapter23.gd`, `chapter24.gd` (yalnız yerleşim ve geçişler);
  - testler: `tests/_ist/tasima12_kare.gd`, `tasima10_kare.gd`, `tur14_bolum_kare.gd`, `tests/city_audit.gd`, `tests/flight_check.gd` (yalnız konumlar), yeni `tests/_ist/saray22_*`;
  - `assets/ui/map1453.png` (yalnız yeniden pişirme).
- **Kimsenin değiştirmediği:**
  - `scripts/world/ist/geo.gd`, `hayat_yakin.gd`, `wall_rear.gd`, `city_plan.gd` (G21'in şeridi aynı kalır), `chapter43o.gd`;
  - `project.godot`, sözleşme ve sonda testleri, `VERSION`, `.github/*`, `i18n/*`, ses dosyaları.

## KESME SIRASI
Hedef 8–12 saat.
1. Ölç (önce): kareler, yükleme, bölüm testleri tabanı.
2. ByzCity bölünmesi + v2 (oyun alanı, düzleme, temizleme, uzak öğeler) → 23 ve 24 (en basitler) geçer → kaydet.
3. 10h, 12b, 13 → kaydet.
4. 6b (kovalamaca + kararmalar) ve 7b → kaydet.
5. Eski dünya (FAR_REGIONS, far_hub, SiegeField yükseklik) + 43o kareleri → kaydet.
6. Testler + kareler + rapor.

Her adımın sonunda bütün hub bölümleri en azından tek çeşitle koşar; bozuk ara kayıt bırakma (geçmeyen adım ayrı dalda değil, aynı dalda "SÜRÜYOR" notuyla).

## Dayanıklılık ve yasaklar
- **Kayıt:**
  - Her adımın sonunda ve en geç 20 dakikada bir kaydet + gönder (yarım da olsa; kareler dahil).
  - `durum.md` her kayıtta güncel.
  - İlk 40 dakikada ara kayıt.
  - Kayıt iletisine model adı yazma.
- **Süreçler:**
  - Arka plan işleri ≤ 10 dakika; aynı anda en çok 4 süreç.
  - Bitti bildirimi gelmezse çıktı dosyasını kendin oku.
  - Testleri çalışma ağacının bir eşinden koş (`~/is/kopya`).
- **Önbellek:** v2 önbelleği (`user://ist_onbellek`) bütün kopyalarda ortak. Değişiklikten sonra önce TEK süreçle ısıt, sonra paralel. Soğuk: `-- --onbellek=yaz`; kapalı: `--onbellek=yok`.
- **Kurulum:**
  - Godot 4.4.1 linux x86_64 resmi sürümü `~/is/godot/godot` (indir).
  - `timeout 900 ~/is/godot/godot --headless --path . --import`.
  - Pencereli kare: `xvfb-run -a -s "-screen 0 1280x720x24" ~/is/godot/godot --path . --rendering-driver opengl3 --resolution 1280x720 …`.
  - xvfb yoksa `sudo apt-get install -y xvfb` (sudo YALNIZ apt-get için).
  - Bölümlerin kare kipi: `--shots=<klasör>`.
- **Yasak araçlar ve işler:**
  - Oturum/tetikleyici/zamanlama/bildirim/ajan başlatma araçlarını KULLANMA.
  - PR açma. Yalnız kendi dalına gönder; geçmişi yeniden yazma, zorla gönderme yok; main'e dokunma.
  - `pkill`/`killall` yok (yalnız `kill <pid>`).
  - Ses üretme. Denetim susturma, eşik gevşetme yok.
- **İzin kutusu çıkarabilecek komut yok:**
  - `rm -rf`/`rm -r`/`mv`/`cp -r` hedefinde kabuk değişkeni kullanma (tam yolu elle yaz); silmeyi heredoc zincirine gömme.
  - `bash -c '…'` ya da `until/while … sleep` bekleme döngüsü yazma.
  - Geçici dosyalar yalnız `~/is/` altında.
  - `.git/` içine ve `.gitignore`'a yazma; `git config` ve `git clean` kullanma.
- **Kayda eklenmeyenler:** Godot'nun ürettiği `.import`/`.translation` yan dosyaları ve ilgisiz `.uid`'ler kayda girmez. Yeni `.gd` dosyalarının `.uid`'si eklenir.
- **Dal ve disk:**
  - Dalda duran öteki `docs/_*` klasörlerine dokunma.
  - Disk payı sınırlı: ham kare yığınlarını iş bitince sil.

## DÜZELTMELER (danışman incelemesi, kod okumasıyla; yukarıdakiyle çelişirse BU BÖLÜM geçerli)

Yol düzeltmesi: bölümler `scripts/chapter6.gd` vb. (`scripts/chapters/` yok). Aşağıdakiler yalnız kod okumasıdır; "doğrula" yazanları ilk iş ölç.

**A. Yükseklik ve çerçeve (en çok saat kazandıracak karar)**
1. y sabit DEĞİL.
   - v2'de −7,6 doğru (G21 raporu: arazi 6,56, hub kökeni 14,09).
   - Eski dünyada işaret ters: `SiegeField.city_ground(−124,5; −436,3)` ≈ **+5,65**, alan içinde 5,0–9,6 m, eğim ~%5 (`siege_field.gd:184-196`).
   - Tek statik yardımcı yaz (`ByzCity.saray_ofs()`): v2'de `IstGeo.h_ham(saray_v2) − hub_v2().origin.y`, eski dünyada city_ground formülü. Bölümlerde y yazma.
2. İç grubun yerelini bugünkü hub yereliyle AYNI tut (START, EMPEROR_POS, HALL_Z0, `clerk_x` yeniden adlandırılmaz).
   - `saray_kok.position = SARAY_OFS + (0, dy, 0)`.
   - Kurucularda `self` yerine "geçerli kök" üyesi (`_k`) kullan: bütün `Props.*(self, …)`, `add_child`, `_house` (`:401-403`), `_fbox`, `_trunk`, `_wall`, `_chi_rho` buna geçer.
3. Önerilen yol: iç ağırlıklı bölümlerde (6b, 7b, 13, 23, 24) ByzCity kökünü `_ready`'nin SONUNDA `−(SARAY_OFS + dy)` kadar ötele; iç grup sahne kökenine gelir.
   - Kazanç: ~300 `Vector3` sabiti, `ROOF_BOUNDS`/`VISTAS`/`ROOF_PAGES` (`chapter6.gd:19-25`), `PERCHES[0..3]`, `ROUTE_A/B`, z eşikleri, `Dressing.auto` ve `player.global_position = ByzCity.X` satırları aynen çalışır.
   - Yalnız sur tarafı (GIUST_POS, EXIT_POS, `PERCHES[4..5]`) `city.to_global(...)` ister; kare testleri bu kalıbı zaten kullanıyor (`tasima10_kare.gd:115`).
   - 10h ve 12b ötelemesiz (sur çerçevesi); iç başvurular (`chapter10h.gd:16, 246-255`) `saray_kok.to_global` ile.
   - Öteleme kurulumdan ÖNCE yapılamaz: v2 kurulumu birim dönüşüm ister (`baglama.gd:476-479`).
   - WorldWalk, CityLife ve IstDunya izleyiciyi göreli okuyor (`world_walk.gd:80,297`, `dunya.gd:136-138`); sorun beklenmez, yine de ilk iş 23'te dene.
   - `ByzCity.new()`'yi doğrudan kuranlar (`city_audit.gd:49`, `flight_check.gd:17,31`, `tools/trailer/trailer.gd:782`) varsayılan olarak ötelemesiz ve eksiksiz kurulmalı.
4. `.position` atanan kişiler ebeveyne göre yanlış yere düşer.
   - Niko: `chapter6.gd:736, 1081, 1161, 1211, 1780`; 1211 kapıda, yani sur çerçevesinde.
   - İmparator 12b'de sura taşınır ve `position` tween'i var (`chapter12b.gd:76, 459, 705`). 12b'de `emperor` doğrudan `city` altında kurulsun.
   - Öteki yerlerde `global_position` kullan.
5. `Dressing.auto` genel koordinatla ışın atar ve sonucu `level`'in yereline koyar; ışın `y_max + 0,5 → −3` mutlak (`dressing.gd:1044-1060, 1229-1231`).
   - Kökeni kaymış grupta hiçbir şey kurmaz ya da yanlış yere kurar.
   - `auto`'ya öteleme seçeneği gerekir; **`scripts/level/dressing.gd` sahiplik listesine eklendi** (yalnız bu seçenek).
   - `_plant_cypresses` (`byz_city.gd:1065-1090`) `to_global/to_local`'i `self` ile yapıyor; köke göre düzelt.
6. Bölme çizgisini sen yaz, brifte yok.
   - Öneri: yerel x ≈ 14 (6b'nin sur ortam sesi eşiği `p.x > 14`, `chapter6.gd:797`). Sur parçası: x 14…HUB_IC_X, z −48…22.
   - `_build_fill` ızgarasında rng, koşuldan önce `cx, cz` çeker; koşul tutmazsa kalan çekimler atlanır (`:1163-1170`). Hücre atlarsan iç evlerin hepsi değişir: **çek, sonra at**.
   - Sur parçasına dolgu ev koyma (G21: sur dibinde sıra ev yok).
7. Brifte olmayan iki yapı içeri taşınırsa şehrin ortasında 70 m'lik kutu sur olur.
   - Yapılar: "Deniz kapısı" bloğu (`_build_street :524-531`, 22×9 m); z 19,4'teki Haliç suru ve 15 m'lik dört kule (`_build_fill :1269-1280`).
   - İki parçada da KURMA. Yerine sokak ağzı: iç grupta G21 yoluna, sur parçasında `oyun_bag` ucuna.
   - START'ın arkası açık kalır; `D6B_T_01_NIGHT` ("Niko'nun kapı odası") bununla çelişmez.

**B. v2 (IstBaglama / IstSehir / IstSokak)**
8. İkinci YAMA gerekmez, riskli de.
   - `_yama_uygula` ilk eşleşen yamada döner (`geo.gd:246-259`). Hub yaması dış yarıçap 260, merkezler arası ~421 m; ikinci yamanın dış yarıçapı > 160 olursa dikiş çıkar. `geo.gd` zaten yasak.
   - Saray için yalnız `IstGeo.duzle` kullan (`sehir.gd:2044` kalıbı): merkez `hub_xf · (SARAY_OFS + (−4, 0, −13))`, r ≥ 58 (84×70'in yarı köşegeni 54,7), geçiş ~14, y = taban − 0,12. Hub ve uzak bölümlerde aynı arazi olur, önbellek tutarlı kalır.
   - Mevcut hub düzlemesi r 48, merkez (0, 0, −10); sur parçası küçülünce onu da küçült ve kaydır.
9. Hub dikdörtgeninin elle yazılmış kopyaları hepsi sur parçasına küçülmeli; yoksa Giustiniani'nin ardında 60×70 m boş döşeme kalır.
   - `byz_city.gd`: `:66,68` (keep), `:104-106` (drect), `:384-385` (zemin levhası), `:1148-1150` (fr).
   - `baglama.gd`: `:46` (YAMA 62/260, merkez (−4, −13)), `:49` (TEMIZ), `:454` (hub_alan).
   - `sehir.gd:2043-2044, 2554`; `world1453.gd:118`.
10. `baglama.gd:386-388` keep dikdörtgenlerini `merge` ediyor: iki alan 430 m'lik tek dikdörtgen olur, yamanın −0,35 bölgesi büyür. Sur dikdörtgenini ayrı ver.
11. `_oyun` üç yerde dolar: `sehir.gd:2544-2556` ve `baglama.gd:458-461`'in iki dalı (31o dahil). Sarayı SONA ekle: `hub_xf` `ar[0]`'ı hub sayıyor (`sehir.gd:2573-2576`).
12. `sokak.gd` değişikliği ZORUNLU ("gerekiyorsa" değil).
    - `_saray_yolu` hub'ı "T'ye en yakın oyun alanı" diye seçiyor (`:652-659`); saray oyun alanı olunca kendini seçer, yol bozulur. Hub'ı dizinle al.
    - Yol alanın MERKEZİNE gidiyor (`:669-677`): kançılaryanın içinden geçer. Alan kenarındaki sokak ağzında bitir.
    - G21 alanın içine meydan döşemesi, `zemin_ek` (r 24), 7 ağaç kümesi ve bir kuyu koydu (`:679-697`). Bunlar IstSehir öğesi değil, `_temizle` silmez; yapıların içinden çıkar. Kaldır ya da alan dışına al.
    - Oyun alanı olunca çevre yolu ve 4 bağlantı kendiliğinden gelir (`:619-634`).
13. `_make_hub` (`sehir.gd:2216-2247`): TEK ByzCity örneğini aynı kurucu sırasıyla kur, çocukları iki tutucuya dağıt.
    - Genel RNG tüketimi değişirse sonraki içerik kayar (`baglama.gd:552-555`).
    - `hub_saray`'ı `KURULUM_ATLAMA_YOK`'a ekle.
    - `_hub_dondur` yalnız `hub_sehir`'i çeviriyor (`:503-514`); `silinecek_mi` tek `_sil_alan` ve `_sil_hub` biliyor (`:547-549`). İkisi de iki öğeye genişlemeli.
14. Kararma sonrası v2 arazi çarpışması 320 m'lik pencere (`dunya.gd:45-46`); 430 m ışınlanınca döşemenin dışında zemin yok.
    - Her yerleştirmeden sonra `IstBaglama.dunya.carpisma_yenile(IstBaglama.kok.to_local(p))` (`flight_check.gd:150` kalıbı).
    - Sonra kalabalık ve akış için ~1 sn karanlıkta bekle.
    - Zemin yakalayıcı yalnız 7'de bağlı (`baglama.gd:714-719`).
15. Önbellek imzası oyun alanlarını ve öğeleri içerir (`sokak.gd:440-450`): her dikdörtgen değişikliği soğuk kurulum demek. Dikdörtgenleri bir kez kesinleştir, sonra TEK süreçle ısıt.

**C. Eski dünya**
16. `World1453.REGIONS`'a yeni bölge EKLEME (WORLDCHECK bütün bölgeleri dolaşır, sayıyı basar). `FAR_REGIONS`'ı yalnız `world1453.gd:265-275, 304-307` okuyor: değeri dikdörtgen listesi yap.
17. Uzak hub bugün hiç düzlenmiyor: `flat_rects` yalnız bölümün kendi keep'i (`world1453.gd:255`); hub y ≈ 0'da durduğu için gerekmiyordu.
    - Saray için sabit, dikdörtgen başına y'li ek liste gerek; yalnız `city_ground`'a (`siege_field.gd:184-196`).
    - Görünen arazi ve yürüme çarpışması 25 m'lik ızgara (`:207-210, 231`; `world_walk.gd:192`): düz dikdörtgeni **26 m büyüt**, yoksa kenarda döşeme ±2 m havada ya da gömük kalır.
    - `--eski-dunya`'da saray keep'i tek `flat_y = −0,03`'e düşer (`world1453.gd:255-257`): 6–9 m çukur.
    - Liste sabit olursa `CityPlan` imzası (`city_plan.gd:288`) ve `_exit_tree` sıfırlaması (`siege_field.gd:583-588`) dokunulmadan kalır.
18. "rng kaymaz" tam tutmaz; rapora dürüst yaz.
    - Keep değişince SiegeField servi döngüsü (`siege_field.gd:634-641`) ve `WallRear._ok` (`wall_rear.gd:164-169`) sonraki çekimleri kaydırır. CityPlan etkilenmez (keep okumaz).
    - Sur parçasının keep'i z −2,3'ü kesmeye devam ederse iç sur boşluğu aynı kalır (`siege_field.gd:295-297, 363-365`).
    - Harita yeniden pişirilir.
19. G21 raporu kaçırmış: `CityPlan.MARKETS`'ta (−120, −400) var (`city_plan.gd:73-74`), saray dikdörtgeninin (dünya x −146,5…−76,5; z −482…−398) içinde. Pazar kümesi ve ara sokaklar alana düşer: 43o karesinde bak, gerekirse son süzgeçle çıkar.

**D. Bölüm akışları**
20. 6b kovalamaca: brifteki tarif tünek sayısını değiştiriyor; doğrusu 6 tünek aynen kalır.
    - `D6B_T_CHASE_4` "Surlara gidiyor!" i = 4'e (fıçı) uçarken çalar, `CHASE_5` "Masaya gidiyor!" i = 5'te (`chapter6.gd:903-906`).
    - Kararma 3→4 geçişinde, yakalasa da kaçırsa da. Martı da ışınlanır (hız 7 ile 430 m = 61 sn).
    - Oyuncuyu fıçıya ~11 m'ye koy (bugünkü tabela→fıçı uzaklığı); sabır konunca başlar (`:907`), denge aynı kalır.
    - Güncellenecekler: `_auto_chase_step` (`:981-986`), `_gull_leave` hedefleri (`:1008, 1040`), `byzyuru` bacakları (`:117-126`, iki alana bölünür).
21. Fıçı tüneği (16,5; 1,27; −11) kodda açıkça kurulmuyor; büyük olasılıkla `Dressing.auto` (tohum 453) ürünü, **doğrula**. Dressing dikdörtgeni değişince yeri kayar, martı havada durur. Nöbet yerine sabit bir su fıçısı kur, `PERCHES[4]`'ü onun tepesine bağla.
22. 6b'de brifte olmayan geçişler:
    - Leblebiyle yakalama (`_gull_lure` → `_gull_caught(false)`, `:989-1024`) iç meydanda biter, hedef Giustiniani 430 m ötede: `_permit_done`'dan sonra da kararma.
    - `_process_space` (`:791-798`) ve kançılarya çıkış eşiği (`:144`) çerçeveye göre.
    - `VISTA_3` "Kara surları" bakış hedefi (90, 6, −14) (`:22`) gerçek sura çevrilmeli; 430 m'den sis içinde okunuyor mu, karesine bak.
    - `D6B_N_E_04` "kapı şu tarafta" kararmayla tutarlı; metin değişmez.
23. 10h: Niko'yu içeride bırakma. Seslendirilmiş replikler onu SURA koyuyor: `D10H_N_1` "Gece gece surda ne arıyorsun?", `D10H_N_K` "(Surun üstünden)".
    - Gece Niko kapının nöbet yerinde; gece başlangıcı (`chapter10h.gd:425`) sur parçasında. Üç iş ve çıkış aynı alanda, ek kararma yok.
    - Kaftan verme (`:279-288`) kapıda kalır; `D10H_L_04` avlu kenarında.
24. 12b: iç grup kurulmayacaksa `hub_saray` uzak öğesini SİLME (surun üstünden boş düzlük görünür). En basiti her hub bölümünde iki grubu da kurmak; yükleme farkını ölç.

**E. Testler, sıra, süre**
25. `city_audit.gd:49` "hub" dikdörtgeni (−140, −330, 320, 326) sarayı (−124, −436) kapsamıyor: ek dikdörtgen.
    - CITYCHECK 24 ve STREETCHECK (e) oyuncunun durduğu yerde ölçer (`city_check.gd:143-200`, `street_check.gd:559`); artık saray.
    - `hayat_yakin.gd` yasak, eşik gevşetilemez. ≥ 8 sivili 2. adımda ölç; tutmuyorsa çevre yolu ve bağlantılarla çöz.
26. Süre: 8–12 saat gerçekçi değil, 16–24 saat say. Fazlara böl, her faz yeşil ve kayıtlı bitsin; geçişi `ByzCity`'de bölüm başına bir anahtarla yap (bölünmemiş yol çalışır kalsın).
    - **Faz A:** ByzCity kurucu bölünmesi + eski dünya uzak hub + 43o kareleri. Sahibin şikâyeti bu karedir ve bölüm akışlarından bağımsızdır. Ara kayıtta hub bölümleri eski yerde oynar; rapora yaz.
    - **Faz B:** v2 (uzak öğeler, oyun alanı, sokak) + 23, 24, 13, 12b, 10h.
    - **Faz C:** 6b, 7b.
    - **Faz D:** `--eski-dunya` hub yolu (bölüm başına tek çeşit), kare testleri, rapor.
    - Her faz bitince `durum.md`'ye `## Faz X: TAMAM (kayıt <hash>)` yaz: yönetici Faz A'yı ayrıca yayınlayabilir.
