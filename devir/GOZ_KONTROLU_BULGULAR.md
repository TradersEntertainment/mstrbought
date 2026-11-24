# Göz kontrolü bulguları (0.99.126 sonrası, bakis_kare)

1. **10h (ve hub'ı kullanan bütün bölümler: 12b, 13, 23, 24, 6/7 Bizans): kapı geçidinin zemini yırtık.** Hub'dan çıkış
   kapısına bakınca geçidin içinde arazi yamuk bir parça olarak döşemenin üstüne çıkıyor, ortada mavimsi bir boşluk var
   (`10h_kapi_gecidi.jpg`, göz 31,1.6,5.9 → +x). Sonda (`bakis_kare sonda=30,58,5.9`): set zemin çarpışması y 0,00, görünen
   arazi (`IstGeo.h`) peribolosta +0,12, dış surun ötesinde −3,43. 8y'de aynı kapıda arazi −0,08 (doğru). Kök: hub
   çerçevesinde sur seti (SurHub "romanos") gerçek yerinin 0,20 m altına oturuyor; v2 surunun peribolos düzlük kayıtları
   (`sur_oturtma.gd:~135`, son kayıt kazanır) araziyi gerçek peribolos yüksekliğinde tutuyor. Hub'ın kendi düzlemesi
   (`sehir.gd:1997`, r 48 + 10) peribolosu kapsamıyor/eziliyor. Düzeltme yolu: set ayak izinde (hub x ≈ 34–55) düzlük
   kayıtlarını setin zeminine göre (−0,08) yeniden yaz ya da hub_v2 düşey yerini setle tutarlı kıl; arazi ağı kayıttan sonra.
2. **26o: top kızağı yakın planda düz turuncu kutular** (KUTU YASAĞI; sahibinin "top" notu L ile aynı iş, Blender turu).
3. **26o: merdivende gökte köşeli yarı saydam şekiller** (büyük olasılıkla uzak top dumanı; incelenecek).
4. **8y: gün doğumunda sur gölgesi koyu lacivert, su gibi okunuyor** (ışık/gölge rengi).
5. **18b: sur yolunun (Haliç surları) hemen yanında penceresiz pembe kutu bina** (beyaz kat çizgili, 3–4 kat; `18b_00`
   sol üst ve sağ alt, göz 1,4/11,2/61,8). Uzak LOD'un yakında kalması ya da sadeleştirilmiş şehir bloğu olabilir. KUTU YASAĞI.
6. **25: başlangıcın 30 m çevresinde penceresiz pastel kutu evler + koyu boş meydan** (`25_02h1`, göz −47,9/1,6/−71,1).
   31o'daki "pastel kutu ev" notuyla aynı aile (eski dünya blokları?). Oyuncunun oraya erişip erişmediği kontrol edilecek.
7. Gün batımı/doğumunda gölgeler keskin koyu lacivert (8y, 12b): su gibi okunuyor. Işık ayarı (görsel program).
8. 26o/29: duman parçacıkları yarı saydam köşeli altıgenler (hata değil; görsel program).
9. Top kızakları düz kutu: 26o, 17o, 18b, 8y (Blender turu, L).
10. **36b (aday, düşük): hendek dibinde açık gri, düz, kalınlıksız düzlemler** (köşeli alt kenar = mazgal gölgesi;
    `36b_02h1`, göz −37,2/−7,9/30,0). Büyük olasılıkla kesim ucundaki hendek kapağı; oyuncu yolundan görünüp görünmediği
    doğrulanacak.
11. **CI 0.99.126 (#340) düştü: 20 `--difficulty=2` VISAUDIT personhidden D20_G_REPELLED** (dost düellocu, moloz
    yamacında yana yer yok). Yerelde 0/8 yeniden üretilemedi. Düzeltme `chapter20.gd _see_giust`: hat hâlâ doluysa komutan
    oyuncunun 1,7–2,2 m yanında hattı açık bir yere gelir.
12. **42b: talim meydanının ötesi ufka kadar boş düz ova** (`42b_00` sağ üst/sol alt; göz −16/1,6/−32,5). Surun iç
    yanında şehir yok gibi; bilinen "42b meydanı boş/çorak" notunun daha ağır hâli (görsel program ya da v2 şehir bağlaması).
13. 38o: Haliç surunun ardında çıplak, düz gri şehir tepesi (`38o_05`): doku/çimen yok (görsel program).

## Kapanış (24 Kasım 09:10 UTC)
34 bölüm (0, 4, 4b, 6/7 Bizans, 8y, 10h, 12b, 13, 17, 17o, 18b, 19, 19o, 20, 20o, 21, 22, 22o, 23, 24, 25, 26, 26o, 28o, 29,
29o, 31o, 32o, 36b, 37o, 38o, 41o, 42b) çekildi; her bölümde 1–4 kare tam boy incelendi. Gerçek hata: 1 (hub kapı geçidi,
7 bölüm). Kutu/boşluk: 5, 6, 12. Aday: 10. Görsel program: 2/9, 7, 8, 13. Havada duran ya da gömük bir şey, görünmez
zemin ya da kırık geometri başka yerde görülmedi. Araç notları: halka noktası denizde dibe, kalabalığın içine ya da
hendek dibine düşebiliyor (kare aracın yanılgısı); dövüşte dünyayı durdurmak testin sayaçlarını bozabiliyor (41o
finishers 2/3, 6/4b beklenen sonuç farkı: araç kurulumu, oyun hatası değil).
