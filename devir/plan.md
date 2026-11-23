# GÜNCEL (23 Kasım ≈08:20 UTC)
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
