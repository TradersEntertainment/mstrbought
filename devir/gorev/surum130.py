#!/usr/bin/env python3
"""0.99.130 sürüm notunu site deposundaki data/changelog.json'un başına ekler (varsa günceller)."""
import json, sys
from collections import OrderedDict

P = "/home/user/nothistorygamedemo/data/changelog.json"
TR = "Osmanlı ordugâhından görünen kara surları da artık yeni sur kalemiyle çiziliyor: kutu surlar kalktı; yerine tuğla hatıllı taş, sekizgen ve dört köşe gerçek kule biçimleri, mazgallar, sur yolu, hendek ve top yaraları geldi. Romanos, Pempton, Altın Kapı dahil yedi kara kapısı yeni kalemle ve hepsi bugünkü gibi açık. Bu, ordugâh bölümlerinde (6, 9, 10, 13, 16, 24o, 25, 43o), Blakherna (30), Haliç ve Galata bölümlerinde uzaktan görünen surlar ile 43o'da drone'un baktığı sur için geçerli; yeni surda oynanan bölümler değişmedi. Kuzeyde surun Blakherna köşe kulesine bağlandığı yerdeki boşluk kapandı. Harita yeni sur kesitiyle yeniden çizildi. Galata'da (27) bir yürüyenin bahçe duvarının yüksekliğinde havada yürümesi düzeldi. 37o'da kalas köprünün tahta aralıklarının altı artık boş değil. Bilinen: hendek eski dünyada dar (ova sınırı yüzünden) ve hendek rampaları yakından toprak kama gibi görünüyor; kapılarda kanat yok; Marmara ve Haliç deniz surları hâlâ eski kutu model (sıradaki iş)."
EN = "The land walls seen from the Ottoman camp are now drawn with the new wall pen as well: the box walls are gone, replaced by stone with brick bands, real octagonal and square towers, crenellations, wall walks, the moat and cannon scars. All seven land gates, including the Romanos, the Pempton and the Golden Gate, are drawn with the new pen and stay open as before. This applies to the walls seen from afar in the camp chapters (6, 9, 10, 13, 16, 24o, 25, 43o), Blachernae (30), the Golden Horn and Galata chapters, and to the wall the drone looks at in 43o; the chapters played on the new wall set did not change. In the north the gap where the land walls meet the Blachernae corner tower is closed. The map was redrawn with the new wall section. In Galata (27) a passer-by no longer walks in mid-air at the height of the garden wall. In 37o the gaps between the plank bridge boards are no longer open underneath. Known: in the old world the moat is narrower (it has to end before the plain) and the moat ramps look like earth wedges up close; the gates have no doors; the Marmara and Golden Horn sea walls are still the old box model (next job)."


def main():
    d = json.load(open(P, encoding="utf-8"), object_pairs_hook=OrderedDict)
    yeni = OrderedDict([("0.99.130", OrderedDict([("tr", TR), ("en", EN)]))])
    for k, v in d.items():
        if k != "0.99.130":
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
