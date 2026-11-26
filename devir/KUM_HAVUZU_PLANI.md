# KUM HAVUZU PLANI — varlık dünyası, serbest kurma, büyük savaş

Hazırlandı: 26 Kasım 2026. Başlangıç: **Pazar 29 Kasım 08:00 (TR)**.

## Hedef (sahibinin isteği)

Oyunu bir kum havuzu olarak bitirmek:
1. **Varlık dünyası:** oyundaki her şey (sur parçası, kule, kapı, ev, çadır, asker, sivil, at, top, gemi, fıçı, ağaç…)
   tek bir katalogda "koyulabilir varlık" olur.
2. **Kum havuzu kipi:** bir haritada bunları serbestçe koyar, taşır, çoğaltır, kaydeder, yükleriz.
3. **Canlanır:** koyduğumuz askerler dövüşür, toplar atar, sur yıkılır.
4. **Büyük savaş ve ordu yönetimi:** üstüne "Fatih'in yerine geç" kuşatma senaryosu ve ileride başka oyunlar/senaryolar
   aynı varlık dünyasıyla kurulur.

## Elimizde ne var (kod, 26 Kasım)

- ~160 bin satır prosedürel GDScript. Varlıklar fonksiyon olarak kuruluyor; tek bir katalog yok:
  - `Props` (28 statik kurucu), `Scenery` (31), `Dressing` (17);
  - yeni sur kalemi `IstSurlar` (dilim, kule, kapı, hendek) ve sözleşmesi;
  - evler, mahalle dokusu, harabe, bostan (`scripts/world/ist/`), ordugâh ve çadırlar.
- Canlılar: `Person`, `Soldier`, `Horse`, `Ox`, `Goat`, `Cat`, `Chicken`, kalabalık (`IstHayat`, `CityLife`, `Crowd`).
- Savaş: `Duelist` + `Melee`, `Assault`, `WaveRunner`, `Garrison` (bölükler), `CannonCrew`, `Gunner`, `BattleExtras`,
  `SiegeTower`, `Ladder`, `SeaBattle`. Hepsi bölüm betikleriyle sahnelenmiş; serbest emir yok.
- 28 hazır `.glb` model (top, fıçı, kazan, kadırga, Fatih, imparator…).
- Kayıt: yalnız oyun ilerlemesi (`GameState`). Sahne kaydı yok.
- Denetim altyapısı güçlü: VISAUDIT, ESYAAUDIT, ZFIGHT, WALKTHRU, otomatik testler, tam paket. Kum havuzu buna bağlanır.

## Mimari

1. **Varlık Kataloğu (`VarlikKatalog`)**: her varlık bir kayıt.
   - Alanlar: `id`, ad (tr/en), kategori, etiketler, kurucu (mevcut fonksiyonu sarar; yeniden yazmak yok), ayak izi,
     yerleşme kuralı (zemine otur / duvara yaslan / suya / sur yoluna), çarpışma, LOD, ayarlar (taraf, renk, boy, hasar),
     simge (otomatik pişirilen önizleme).
   - Kural: kataloğa giren her varlık otomatik denetimden geçer: havada/gömük yok, çarpışma = görünen, ZFIGHT 0, KUTU YASAĞI.
2. **Kum sahnesi belgesi (`.kum`, JSON)**: dünya seçimi (boş ova / 1453 eski dünya / İstanbul v2) + varlık listesi
   (id, konum, dönüş, ayarlar) + birlikler + kurallar. Kaydet/yükle aynı sonucu verir (karma ile test).
3. **Editör kipi** (ana menüde "Kum Havuzu"):
   - kamera: RTS (yukarıdan), serbest uçuş, göz hizası (yürü);
   - araçlar: koy, taşı, döndür, çoğalt, sil, fırça (çadır/ağaç/kalabalık serpme), hat çiz (sur, çit, asker sırası);
   - zemine oturtma, ızgara, çoklu seçim, geri al/yinele;
   - katalog paneli (arama, kategori, simge), özellik paneli.
4. **Canlandırma ("Oynat")**: birlik sistemi.
   - Birlik = N asker + düzen (saf, kare, dağınık) + emir (git, saldır, bekle, siper al, kaç).
   - Mevcut `Melee`/`Duelist` yakın dövüş, `CannonCrew`/`Gunner` atış, sur hasarı (gedik), `Ladder`/`SiegeTower` yeniden kullanılır.
   - Basit moral ve bozgun.
5. **Büyük ordu başarımı**: üç katman.
   - Yakın: tam `Person`.
   - Orta: sade, toplu canlandırılan gövde.
   - Uzak: MultiMesh.
   - Yol bulma akış alanıyla (flow field), birlik başına.
   - Hedef sahibinin makinesinde ölçülür (öneri: 1000+ asker, 30+ FPS).

## Aşamalar (her biri ayrı sürüm; tam paket + CI kuralı aynı)

| Aşama | İş | Tahmin |
|---|---|---|
| **S0** (Pazar sabahı) | Envanter: kurucuların listesi ve katalog şeması. Ölçütler, 1000 asker başarım ölçümü (bugünkü sistemle taban). Sahibine kategori listesi | 2–3 sa |
| **S1** | Katalog v1: ~100 varlık (sur parçaları, kule, kapı, 6–8 ev türü, çadırlar, top, fıçı/sandık, ağaçlar, asker/sivil türleri, at). Simgeler, katalog denetim testi | 1–2 gün |
| **S2** | Editör v1: 3 dünya seçimi, koy/taşı/döndür/sil/çoğalt, kaydet/yükle, geri al. Ana menüye "Kum Havuzu" | 2–3 gün |
| **S3** | Canlandırma: birlik + emir + dövüş + top atışı + sur hasarı; Oynat/Durdur | 3–4 gün |
| **S4** | Büyük savaş başarımı (LOD/MultiMesh, akış alanı); 1000+ asker ölçümü | 2–3 gün |
| **S5** | "Fatih'in yerine geç" prototipi: 1453 kuşatma haritası, bölük seçip emir verme, hedefler, bir görev | 3–5 gün |
| **S6** | Yeni oyun/senaryo şablonu: bir senaryo = kum sahnesi + kural betiği. Mevcut bölümler isteğe bağlı, yavaş geçiş | sonra |

Yardımcı düzeni:
- S1 ve S2 aynı anda iki yardımcıyla yürür (dosyaları ayrık: katalog / editör).
- S3 ve S4 sırayla (ikisi de birlik sistemi).
- Her görev yazısı önce danışmana (Fable) okutulur; teslimde tam boy kareler + testler + tam paket.

## Kurallar

- Mevcut 100+ bölüm bozulmaz: kum havuzu ayrı kip, ortak dosyalara seçmeli bayrakla dokunur; tam paket her sürümde.
- KUTU YASAĞI, HAVADA DURAN HİÇBİR ŞEY OLMAZ, TEK GÖRSEL DİL. Katalogdaki her varlık aynı kalemle.
- Kayıtlar deterministik (aynı dosya → aynı sahne). Başarım bütçeleri yazılı ve testli.
- Denge/replik kuralları hikâye bölümleri için aynen geçerli.

## Kota

- Haftalık kota şu an uyarı düzeyinde; yenilenme Pazar 29 Kasım 20:00 (TR).
- Pazar sabahı S0'ı ben yaparım (yardımcısız, düşük kota).
- S1 ve S2 yardımcıları kota yenilenince açılır (Pazar akşamı).

## Sahibinin kararları (26 Kasım, AskUserQuestion)

1. Kum havuzu: **ikisi birden.** Oyuncuya ana menüden açık; biz de yeni senaryoları onunla kurarız.
2. İlk büyük savaş: **Fatih olarak 1453 kuşatması.**
3. Ordu yönetimi: **gerçek zamanlı + duraklatıp emir verme.**
4. Görsellik: **önce prosedürel; katalog model (Meshy/sanatçı) desteğine hazır kurulur.**
