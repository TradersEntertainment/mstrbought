#!/usr/bin/env python3
"""0.99.125 sürüm notunu site deposundaki data/changelog.json'un başına ekler (varsa günceller)."""
import json, sys
from collections import OrderedDict

P = "/home/user/nothistorygamedemo/data/changelog.json"
TR = "İstanbul uyarlamasının son büyük parçası: surun göründüğü bölümlerin neredeyse hepsi artık yeni surlarda. Bu sürümle 8y (Beyaz Havlu: Romanos kapısından ovaya), 13, 23 ve 24 (şehir meydanı), 41o ve 42b (talim meydanları) de yeni surda; şehirden uzaktan görünen meydan da yeni surun yanında. Yakından görünüş: Romanos kapısının kemeri artık gerçek ölçüde tuğla ve taş, kapı kanatlarında tahta damarı, demir kuşak ve çiviler var; mazgal dişlerinin taş başlıkları açık renkli ve kaba yontu; sur yolu ve rıhtım döşemesi gerçek taş; şehirde Haliç ve Marmara kıyısındaki deniz surları da yeni görünüşte; büyük kalkanlar (pavez) deri kaplı. 10h'de gedik molozu köşeli taş ve tuğla kırığı. Düzeltme: 10'da Ağa sizi attırınca nöbetçiler artık kapıdaki yerlerine dönüyor (ikinci denemede Ağa'nın önünde dikiliyorlardı). Henüz eski surda olanlar: 31o (fetihten sonra Romanos iç kapısı; yeni surun ardında şehir ve kalabalık henüz kurulmadığı için bu sürümde eski hâlinde, yeni hâli hazır) ve 17o'da Haliç'in karşı kıyısından uzakta görünen şehir surları (21o yeraltında geçiyor, orada sur yok)."
EN = 'The last big part of the Istanbul update: almost every chapter where the walls are visible now uses the new walls. This version adds 8y (the White Towel: from the Gate of St. Romanus out onto the plain), 13, 23 and 24 (the city square), and 41o and 42b (the drill grounds); the square seen from afar in the city now sits by the new walls too. Up close: the arch of the Romanus gate is now real-scale brick and stone, the gate leaves have wood grain, iron bands and nails; the merlon caps are light, rough-hewn stone; the wall walk and quays are paved with real stone; the sea walls along the Golden Horn and the Marmara in the city have the new look; and the big pavise shields are covered in hide. In 10h the breach rubble is angular stone and broken brick. Fix: in 10, when the Agha has you thrown out, the guards now return to their posts by the gate (on the second try they used to stand right in front of the Agha). Still on the old walls: 31o (the Romanus inner gate after the conquest; the city and its crowds behind the new walls are not built yet, so it stays as before in this version, the new version is ready) and the city walls seen far across the Golden Horn in 17o (21o takes place underground, with no walls).'


def main():
    d = json.load(open(P, encoding="utf-8"), object_pairs_hook=OrderedDict)
    yeni = OrderedDict([("0.99.125", OrderedDict([("tr", TR), ("en", EN)]))])
    for k, v in d.items():
        if k != "0.99.125":
            yeni[k] = v
    raw = open(P, encoding="utf-8").read()
    girinti = 1 if "\n \"" in raw[:40] else (2 if "\n  \"" in raw[:40] else None)
    with open(P, "w", encoding="utf-8") as f:
        json.dump(yeni, f, ensure_ascii=False, indent=girinti)
        if raw.endswith("\n"):
            f.write("\n")
    print("yazıldı:", list(yeni.keys())[:3], "TR", len(TR), "EN", len(EN))


if __name__ == "__main__":
    if "--yaz" in sys.argv:
        main()
    else:
        print("TR", len(TR), "EN", len(EN), "(yazmak için --yaz)")
