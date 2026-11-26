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
