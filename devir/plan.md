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
