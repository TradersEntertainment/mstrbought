# KUM HAVUZU PLANI — varlık dünyası, serbest kurma, büyük savaş, bütün bölümler sabit haritada

Hazırlandı 26 Kasım 2026; Fable (üst akıl) iki kez inceledi (iki tur), düzeltmeler işlendi. Başlangıç: **Pazar 29 Kasım 20:00 (TR)** (sahibi 26 Kasım: "20:00de"; kota yenilenmesiyle aynı saat).

## Hedef (sahibinin isteği)

1. **Varlık dünyası:** oyundaki her şey tek bir katalogda "koyulabilir varlık" olur: sur parçası, kule, kapı, ev, çadır,
   asker, sivil, at, top, gemi, fıçı, ağaç…
2. **Kum havuzu kipi:** bu varlıkları koyar, taşır, kaydeder, yükleriz. Kip oyuncuya açıktır; biz de içeriği onunla kurarız.
3. **Canlanır:** askerler dövüşür, toplar atar, sur yıkılır.
4. **Büyük savaş:** Fatih olarak 1453 kuşatması. Gerçek zamanlı akar, duraklatıp emir verilir.
5. **Bütün bölümler bu sistemle, SABİT BİR HARİTA üstünde kurulur.**
   - Bölüm = kum sahnesi (yerleşim) + senaryo betiği (replik, tetik, akış).
   - Akış GDScript'te kalır; yalnız yerler ve yerleşim veriye (`.kum`) geçer.

## Sahibinin kararları

- **26 Kasım:**
  - Kum havuzu: ikisi birden (oyuncuya açık + bizim aracımız).
  - İlk savaş: Fatih olarak 1453 kuşatması.
  - Komuta: gerçek zamanlı + duraklat.
  - Görsellik: önce prosedürel; model desteği hazır kurulur.
- **26 Kasım, ek:** bütün bölümler kum havuzuyla, sabit haritada kurulacak.
- **26 Kasım, ek:** Blender'la şık ve az poligonlu modeller. **GÖRSEL İNDİRİM YASAK:** her model bugünkü karşılığından
  açıkça iyi olmadan oyuna girmez.

## Elimizde ne var (kodla doğrulandı)

- ~160 bin satır prosedürel GDScript; 63 bölüm dosyası (73.856 satır) ve ortak bir taban sınıf yok.
  - Bölümler sabit koordinatlı eşyordam betikleri: 6404 `Vector3(` sabiti, 6267 `await`, 1409 `autotest` başvurusu.
- Katalog zemini var: `scripts/world/ist/` altında 21 modül `catalog()` + `build_<id>(host, k, lod, tohum)` düzeninde
  (`evler.gd:102-200`); `IstSehir.catalog_all()` (`sehir.gd:146`); önizleme sahneleri `tests/_ist/*_onizleme.tscn`.
- `Props` ilkel kitaplıktır (box/cyl/mat/bake_static), varlık değildir. `Dressing` ve `Scenery` toplu/serpme kurucudur:
  parçaları 24 m'lik tek ağa birleştirir (`dressing.gd:140-165`), tek tek seçilemez.
- Büyük kalabalık katmanı var: `Crowd`, `PoseCrew`, `NightArmy` (pişmiş asker + MultiMesh).
- Dövüş ve top sistemleri oyuncu merkezli; birlikler arası savaşa olduğu gibi uymaz:
  - `Melee` bir `Player` ister (`melee.gd:38`, `max_on_player 2`);
  - `CannonCrew` oyuncunun mini oyunu;
  - `Gunner` yalnız oyuncuya nişan alır.
- Kuşatma için hazır arayüz: `SurOyun.kur("mesoteikhion")` yol, dayama, batarya, gedik, doğma noktası verir.
- Taşıma kalıbı kanıtlı: `SurSet` bağdaştırıcısı + donmuş sözleşme + `--eskisur` geri dönüşü (kara suru taşıması 36 dosya,
  0.99.122 → G23).
- Blender 4.2 LTS bu ortamda ekransız çalışıyor (anahtar gerekmez): script → `.glb` boru hattı denendi.
  Görsel olarak HEDEF DEĞİL, yalnız boru hattı kanıtı (`kareler/kum_havuzu/blender_deneme_kule.png`).

## Sabit harita

- **Temel: İstanbul v2.** Gerçek koordinatlı ve sözleşmesi donmuş. Eski 1/4,5 ölçekli dünya (World1453) temel alınmaz.
- **Sabit olan geometridir.** Tarihe bağlı durum (gedik aşaması, sağlam sur, gece/gündüz, düşmüş şehir) senaryonun durum
  katmanıdır.
- **Bölgeler:** v2 üstünde adlı bölge çapaları (World1453 `REGIONS` fikrinin v2 karşılığı).
- **Deniz:** v2'nin Haliç ve deniz modülleri; gemi, hareketli çerçeve varlığıdır.
- **Haritaya gömülmeyenler:** iç mekânlar ve başka yerler (Büro, 1977/2026 sokakları, Edirne, otağ içi, sarnıç). Bunlar
  kendi orijinli ayrı set `.kum`'larıdır, kapı işaretiyle bağlanır.

## Mimari

1. **Varlık Kataloğu** (`scripts/kum/`): her varlık bir kayıt.
   - Alanlar: `id`, ad (tr/en), kategori, etiketler, kurucu (mevcut fonksiyonu sarar), ayak izi, yerleşme kuralı,
     çarpışma, LOD, ayarlar (taraf, renk, boy, hasar durumu), simge.
   - Kural: bir varlık = bir kök düğüm + kendi çarpışması. Seçim AABB ile. Birleştirme/pişirme yalnız "Oynat"ta ya da
     bölüm yüklenirken, parça parça.
   - Kurucular dört sınıfa ayrılır: tekil / serpme (fırça aracı olur) / coğrafyaya bağlı anıt / bağlama bağımlı.
   - Model desteği: aynı kayıt prosedürel kurucu ya da `.glb` model taşıyabilir.
2. **`.kum` belgesi:**
   - JSON; `surum`, `harita` ya da `set` alanları;
   - taban harita + bölüm bindirmesi; set'e göre yerel koordinat;
   - kimlik göç tablosu; varlık başına `tohum`; yalnız JSON türleri (`str_to_var` yasak).
   - Belirlenim tanımı: aynı belge → aynı statik ağaç (karma testi). Benzetimin sonucu kapsam dışı.
3. **Editör** (`Player`'sız ayrı sahne):
   - v1: RTS kamera + fare; koy / taşı / döndür / sil / kaydet / yükle / geri al.
   - Senaryo araçları:
     - adlı nokta (başlangıç, konuşmacı yeri, bakış hedefi, doğma);
     - yol;
     - tetik hacmi (`sahne.tetik("ad")`);
     - adlı kamera (oyuncu gözü önizlemesi);
     - kadro yuvası; etkileşim kimliği; evre katmanı; bölge sınırı;
     - bot yol noktaları.
   - v2: fırça, hat çizme, çoklu seçim, göz hizası, oyun kolu, öteki dünyalar.
4. **Birlik katmanı** (eski S3 ve S4 birleşti):
   - Veri odaklı: dizilerde asker, sabit adım (10 Hz karar), kendi tohumlu.
   - Çizim gölgesiz ve dış hatsız MultiMesh (PoseCrew yöntemi, hücreli).
   - Tam `Person` yalnız kameraya en yakın N askerde; N, Pazar sondasından gelir. `Duelist` yalnız oyuncu göz hizasında
     savaşırken devreye girer.
   - Birlikler arası çarpışma ve top atışı için yeni, istatistiksel çözücü: temas hattı, moral, bozgun; topta balistik ve görsel etki.
5. **Sur:**
   - v1 = `IstSurlar.build_run` düz dilim + kule + kapı.
   - Hasar = tanımlı gedik yuvasında aşama değişimi.
   - Serbest yıkım, köşe ve eğim kapsam dışı. `SUR_SOZLESME` sayılarına dokunulmaz.
6. **Çapa sözleşmesi:**
   - Adlı noktalar ve bölge çapaları donmuş bir tabloda; testi `SURSOZLESME` gibi.
   - `check_kum_refs.py` betiklerdeki nokta/tetik adlarını denetler.
   - Olmayan bir ada başvuran betik yüksek sesle hata verir.

## Görsel kalite: Blender hattı (İNDİRİM YASAK)

- **Ölçü oyunun içi.** Her model, oyunun kendi ışığında ve aynı kamerayla bugünkü karşılığıyla önce/sonra karşılaştırılır
  (göz hizası 0,5–3 m, 50 m, 150 m). Açıkça iyi değilse girmez. Blender önizlemesi karar ölçüsü değildir.
- **Az poligonla şıklık:**
  - siluet elle düşünülür; kenarlar pahlanır;
  - taş/tuğla/hatıl ortak doku atlasından gelir (bugünkü sur dokusu `sur_doku` dahil);
  - çok poligonludan düşük poligonluya normal ve ortam gölgesi pişirilir;
  - renk tek palete bağlanır;
  - oyunun dış hat gölgelendiricisiyle uyum, LOD kademeleri.
- **Üçgen bütçeleri:** asker 1,5–3 bin, ev 0,5–2 bin, kule 1–3 bin, top 0,5–1 bin. Ölçüm testle.
- **Önce örnek:** ilk 3–5 parça (kule, ev, çadır, top, asker) sahibine önce/sonra kareleriyle gösterilir; onaysız seri üretim yok.
- **Teknik:** Blender script'leri depoda (`tools/blender/`), tekrar üretilebilir; `.glb` + içe aktarma ayarları + katalog kaydı.

## Aşamalar (her biri ayrı sürüm; tam paket + CI kuralı aynı)

| Sıra | İş | Sahibi neyi tıklar | Tahmin |
|---|---|---|---|
| **D0** (Pazar 20:00, ben; kota yenilenince) | Dört sınıflı varlık envanteri; bölüm × dünya matrisi (63 dosya, L0/L1/L2 adayı); 1000 asker başarım sondası (tam `Person` / Crowd MultiMesh / poz değiştiren MultiMesh) | Gizli "yarat" menüsünde ölçüm sahnesi: kendi makinende FPS, çizim, üçgen | 1 gün |
| **D1** (D0 biter bitmez, yardımcı A) | Mini editör: düz ova, ~15 varlık + adlı nokta + tetik hacmi; `.kum` v1 | "Kum Havuzu (deneme)": koy, döndür, sil, F5/F9 kaydet-yükle | 2–3 gün |
| **D2** (paralel, yardımcı B) | Birlik çekirdeği: veri odaklı 100'e 100, MultiMesh, tıkla-emir, duraklat | Ovada iki ordu, bölük seç, git/saldır | 3–4 gün |
| **D3** | D1 + D2: editörde birlik koy, "Oynat" | Kendi kurduğun savaşı oynat | 2–3 gün |
| **D4** | Fatih dilimi: v2 Mesoteikhion kesimi, 3–4 bölük, top bataryası, gedik aşaması, tek hedef; `.kum` + betikle yazılan ilk bölüm | Fatih olarak gedikten gir | 4–6 gün |
| **D5** | Pilot taşıma (L1): zaten yeni sette olan, suru fon olan bir bölüm (aday 28o); çapa sözleşmesi, ESKİ \| YENİ süre tablosu, geri dönüş bayrağı | Aynı bölüm, yeni sistemde | 3–5 gün |
| **G-model** (D1'le paralel başlayabilir) | Blender hattı + ilk 3–5 örnek model, önce/sonra kareleri | Onay ya da ret | 2–3 gün |
| **D6** | Katalog ~100 varlığa; fırça, hat; 1000+ asker ölçümü | Büyük savaş | 4–6 gün |
| **D7 →** | Aile aile taşıma: v2 sur bölümleri → şehir hub'ı → Galata/Haliç → deniz → ordugâh → iç mekân setleri | Her ailede bölümler yeni sistemde | tarihsiz, aylar ölçeği |

- D4 ile D5 birlikte, aynı aracın hem yeni bölüm yazdığını hem eski bölüm taşıdığını kanıtlar. Kanıt gelmeden toplu
  taşıma başlamaz.
- Kum havuzu ana menüye D3'ten sonra çıkar. Ondan önce gizli "yarat" menüsünden açılır.

## Taşıma kuralları (her bölüm için)

- **Düzeyler:**
  - L0: dokunulmamış.
  - L1: dünya sabit haritadan gelir; betik sabit sayı yerine adlı noktadan okur.
  - L2: dekor ve kadro da `.kum`'da.
- **Her taşımada:**
  - bağdaştırıcı + `--eskidunya` geri dönüşü;
  - ESKİ | YENİ süre tablosu (hendek geçişi 8,7 → 46 sn gibi sessiz denge kaymaları yakalanır);
  - üç sabit satır: çapa sözleşmesi, havada/gömük nokta 0, bot yürüyüşü;
  - bütün `--autotest` yolları yeşil;
  - sahibine kalan kararlar listesi.
- Sürüm notunda "hâlâ eski dünyada olanlar" listesi.
- Yeni bölüm yalnız yeni sistemde yazılır.
- Eski dünyadaki (1/4,5 ölçek) bölümlerde mesafe ve süre büyür. Replik ve denge için bölüm başına sahibine karar sorulur.

## Kurallar

- Kum çekirdeği (`scripts/kum/`: yükleyici, katalog, nokta arayüzü) çekirdek koddur. Şema v1 ve çapa sözleşmesi donmadan
  hiçbir bölüm taşınmaz.
- `Person`, `Duelist`, `Melee`, `Props` değiştirilmez; gerekirse yeni sınıf yazılır. Bölümler arası geçiş tam sahne
  yenilemesiyle (statik sızıntı testi).
- KUTU YASAĞI, HAVADA DURAN HİÇBİR ŞEY OLMAZ, TEK GÖRSEL DİL, GÖRSEL İNDİRİM YOK.
- Denge ve replik kuralları hikâye bölümlerinde aynen geçerli.

## Test

- Varlık denetimi, tek başına düz zeminde:
  - havada/gömük;
  - çarpışma ile görsel AABB uyumu;
  - üçgen, çizim ve kurma süresi bütçesi;
  - ZFIGHT.
- Altın `.kum` gidiş-dönüş karması; tohumlu rastgele yerleştirme.
- Ekransız 100'e 100 savaş: süre sınırı, asker sayısı korunumu, NaN yok.
- Başarım kapısı (`perf_run.sh`).
- Çapa sözleşmesi + `check_kum_refs.py`.
- Ayrı test parçası olarak koşar. Ara teslimde QUICK, sürümde tam paket.

## Kota

- Haftalık kota uyarı düzeyinde; yenilenme Pazar 29 Kasım 20:00 (TR).
- Başlangıç Pazar 20:00 (TR), kota yenilenmesiyle aynı saat. D0'ı ben yaparım; D1 ve D2 yardımcıları D0'ın envanteri ve başarım sondası bitince açılır.
- Tahminler gerçekçi tutuldu (birlik ve Fatih dilimi iki katı sayıldı); bölüm taşıma aylar ölçeğinde ve tarihsiz.

## Sahibine sorulacak açık kararlar (D0'da)

1. Sabit harita İstanbul v2 mi? (Öneri: evet.)
2. İç mekânlar (Büro, sokaklar, Edirne, otağ) ayrı set olarak mı kalsın? (Öneri: evet, kapıyla bağlı.)
3. İlk pilot taşıma bölümü? (Öneri: 28o.)
4. Kum havuzu ana menüye D3'ten sonra mı çıksın? (Öneri: evet.)
5. Model örnekleri için ilk beş parça: kule, ev, çadır, top, asker mi?

## EK: YAPAY ZEKÂLI ASKERLER VE DOĞAL DAVRANIŞ: YAPILACAKLAR (27 Kasım; sahibinin sorusu)

### Context
- 0.99.130 yayında (CI #348 başarılı; guncelleme.json 0.99.130).
- Sahibi sordu: "Kum havuzunun çalışması için neler yapılması gerekecek? Yapay zekâlı askerler, doğal davranışlar; hepsine çalışmak gerekecek."
- Bu bölüm, `devir/KUM_HAVUZU_PLANI.md`'deki aşamaların (D0–D7) içini askerler ve canlılık açısından açar. Başlangıç Pazar 29 Kasım 20:00 TR.
- Bugün elimizde olanlar (kodla):
  - Davranışlar bölüme bağlı küçük döngüler:
    - `reserve_loop` (147 satır): bakınma, ok yağmurunda kalkan altı, çavuş bağırır;
    - `archer_loop` (87): yay germe, ok bırakma;
    - `spear_loop` (199): siperden bakma, merdivendekini dürtme;
    - `Rout` (211): dağınık geri çekilme;
    - `Walker` (376) ve `RectNav` (102): yürüyüş ve dolanma;
    - `IstHayatYakin` (1672): oyuncunun çevresinde yaşayan şehir.
  - Kitle görselleri: `Crowd` (donmuş kopya + MultiMesh), `PoseCrew` (uzakta poz değiştiren asker), `NightArmy` (dört karelik koşu).
  - Ordu ve dövüş: `Assault` (1695 satır), `WaveRunner` (312), `Duelist` + `Melee` (oyuncu merkezli).
  - `Rig`'de ~23 hazır poz/iş: aim, carry, cheer, chop, crouch, dead, dig, eat, hammer, lie, point, push, sit, sleep, sweep, wave…
- Eksik olan: emir alan, kendi karar veren, birbiriyle savaşan bir ordu katmanı. Bugünkü askerler sahnelenmiş; serbest kum havuzunda kendi başlarına hiçbir şey yapamıyorlar.

### Yapılacaklar (katmanlar)

### 1. Benzetim çekirdeği (her şeyin altı)
- Asker kaydı veri dizilerinde (sahne düğümü değil):
  - konum, hız, yön, taraf, birlik;
  - rol: mızraklı, okçu, tüfekçi, topçu, süvari, işçi, sancaktar, çavuş;
  - can, moral, yorgunluk, durum, hedef.
- Sabit adım: kararlar 10 Hz, konum her kare ara değerle. Tohumlu rastgele (aynı kayıt → aynı savaş).
- Uzamsal ızgara: komşu ve düşman araması, iç içe girmeyi önleme (bugünkü `Unclip` ızgara fikri).

### 2. Hareket ve yol bulma
- Akış alanı (flow field): birlik hedefine giden yol haritası. Maliyet haritası sahnedeki çarpışmalardan çıkar: sur, hendek, kapı, gedik, merdiven.
- Düzen tutma: saf, kare, dağınık, kama.
  - Askerler düzendeki yerine doğru gider, komşusundan ayrışır.
  - Dönüşte ve engelde düzen bozulup yeniden kurulur.
- Sur geçişleri: `SurOyun`'un yol, dayama ve doğma noktaları. Merdiven (`Ladder`), kule (`SiegeTower`), gedik.

### 3. Karar (askerin ve birliğin beyni)
- Birlik durumları: bekle, ilerle, saldır, siper al, tut, geri çekil, bozgun, toplan.
  - Geçişler fayda puanıyla (utility AI): tehdit, moral, kayıp, emir.
- Asker:
  - hedef seçer (en yakın, en zayıf, emir hedefi);
  - temasa girer, menzildekine atar;
  - moralini komşularından ve sancaktan alır.
- Komuta:
  - Fatih olarak oyuncunun emirleri;
  - karşı tarafın basit generali: gediği tut, sur yolunu savun, karşı hücum, ihtiyatı sür.

### 4. Savaş çözücüleri (bugünküler oyuncu merkezli, yenileri gerekir)
- Yakın dövüş: temas hattında istatistiksel çözüm (saldırı, savunma, yorgunluk, moral). Görünüşü vuruş pozları + toz/kıvılcım.
  - Oyuncu göz hizasında savaşırsa en yakın birkaç asker `Duelist` olur.
- Ok ve tüfek: balistik ok/kurşun yağmuru (bugünkü ok ağı), siper ve kalkan etkisi.
- Top:
  - doldur–ateş döngüsü, balistik gülle;
  - sur hasarı = gedik yuvasında aşama (kara surunun 4 aşaması), ahşap perde ve siper kırılması.
- Kuşatma araçları: merdiven dayama, tırmanma, kuleden atlama, kızgın yağ ve taş (bugünkü parçalar).

### 5. Doğal davranış (canlılık)
- Boşta: bakınma, sohbet, silah ve kalkan düzeltme, oturma, ateş başı, nöbet değişimi.
  - `reserve_loop`/`archer_loop`/`spear_loop` genelleşip her role takılır.
- Tepkiler:
  - ok yağmurunda kalkan altına çömelme;
  - yakına gülle düşünce irkilme ve yere atılma;
  - arkadaşı düşünce dönüp bakma;
  - zaferde sevinç; bozgunda dağınık kaçış (`Rout`).
- Yaralı ve ölü: düşme, yerde yatma, yaralı taşıma, ceset sınırı ve görüş dışında silinme (bugünkü kural).
- Ordugâh ve lojistik: su/barut/taş taşıyan, kazan başı, at sırası, yürüyen devriye (`carry`, `dig`, `hammer` işleri).
- Ses: savaş narası, davul (`drum_beat`), çarpışma, top efekti. Mevcut efektlerle; yeni seslendirme sahibinin onayıyla.

### 6. Görünüş ve başarım (1000+ asker)
- Üç kat:
  - yakında tam `Person` + `Rig` (poz ve iş veriden);
  - ortada poz başına MultiMesh (`PoseCrew` yöntemi; koşu `NightArmy`'nin dört karesi);
  - uzakta `Crowd` donmuş kopya.
- Katlar arası geçiş sıçramasız: aynı yer, eşlenen poz. Orta ve uzak kat gölgesiz ve dış hatsız; hücreli MultiMesh.
- Bütçe Pazar sondasıyla belirlenir; hedef 1000+ asker, 30+ FPS, sahibinin makinesinde.

### 7. Komuta arayüzü (Fatih)
- Seçim: tıkla ya da kutu çiz; birlik kartları.
- Emir: sağ tık git/saldır; düzen menüsü; Boşluk = duraklat; zaman hızı.
- Mini harita.
- Kamera: RTS (yukarıdan) + istenince Fatih'in gözü (otağdan, atla).

### 8. Test ve denetim
- Ekransız savaş testleri:
  - 100'e 100 ve 500'e 500;
  - süre sınırı, asker sayısı korunumu, NaN yok, takılan birlik yok;
  - aynı tohum → aynı sonuç.
- Mevcut denetimler orta katmana da: havada/gömük (VISAUDIT), iç içe (overlap), surdan geçme (WALKTHRU), donuk bekleme (DONUKAUDIT).
- Başarım kapısı (`perf_run.sh`).
- "Doğallık" kanıtı: göz hizası ve tepeden kısa kare dizileri sahibine (görsel indirim yasak kuralıyla).

### Sıra (KUM_HAVUZU_PLANI'ndaki aşamalara oturuş)

| Aşama | Askerler için ne gelir | Sahibi ne görür |
|---|---|---|
| D0 (Pazar 20:00, ben) | 1000 asker başarım sondası (tam / donmuş / poz değiştiren), mevcut davranış envanteri | Kendi makinende üç kipte FPS |
| D2 (yardımcı B) | 1 + 2 + 3'ün çekirdeği: veri kaydı, akış alanı, düzen, birlik durumları, yakın dövüş çözücüsü, MultiMesh orta kat; tıkla-emir, duraklat | Ovada 100'e 100, bölük seç, git/saldır |
| D3 | D1 editörüyle birleşir: birlik koy, Oynat. Tepkilerin ilk takımı (kalkan altı, irkilme, düşme, bozgun) | Kendi kurduğun savaşı oynat |
| D4 | Kuşatma: ok ve top çözücüleri, sur hasarı (gedik aşamaları), merdiven/gedik geçişi, karşı general | Fatih olarak gedikten gir |
| D5–D6 | Boşta davranışlar ve ordugâh lojistiği, ses, 1000+ asker ve LOD geçişleri, ikinci kat tepkiler (yaralı taşıma, sancak, moral zinciri) | Büyük, canlı bir kuşatma |
| sürekli | Denetimler, savaş testleri, kare dizileri | Her sürümde önce/sonra |

### Gerçekçi süre
- Oynanabilir ilk savaş (D2 + D3): 1–1,5 hafta.
- Fatih kuşatma dilimi (D4): +1 hafta.
- Canlılık ve 1000+ asker (D5–D6): +1–2 hafta.
- Doğal davranış işi bitmeyen bir cila; her turda sahibinin karelerine göre artar.

### Doğrulama
- D0 sondası sahibinin makinesinde ölçülür.
- Her aşama: ekransız savaş testleri yeşil, denetimler 0, başarım kapısı geçer, tam paket yeşil (hikâye bölümleri bozulmaz), sahibine kare dizisi.
