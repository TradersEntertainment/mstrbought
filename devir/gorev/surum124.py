#!/usr/bin/env python3
"""0.99.124 sürüm notunu site deposundaki data/changelog.json'un başına ekler (varsa günceller)."""
import json, sys
from collections import OrderedDict

P = "/home/user/nothistorygamedemo/data/changelog.json"
TR = "İstanbul güncellemesinin üçüncü parçası: 12 bölüm daha yeni surda. Şehir içi ve kapı bölümleri 6b, 7b, 10h ve 12b artık yeni surun Romanos kapısı kesiminde oynanıyor (12b'de İmparator'la gerçek sur yolunda, kule geçidinde); Haliç ve deniz kıyısı bölümleri 4b, 17, 18b, 19, 19o, 29, 29o ve 38o yeni deniz surlarında (taş örgü, kuleler, rıhtım, deniz kapıları; 38o'da merdivenin tepesinden sur yoluna takılmadan çıkılıyor). Böylece 27 bölüm yeni surda: 0, 4b, 6b, 7b, 10h, 12b, 17, 18b, 19, 19o, 20, 20o, 21, 22, 22o, 25, 26, 26o, 28o, 29, 29o, 30, 30o, 32o, 36b, 37o, 38o. Hâlâ eski sette olanlar: 8y (yeni hâli hazır, bir görünüş kusuru düzelince gelecek) ve surun yalnız uzaktan göründüğü 13, 17o, 21o, 23, 24, 31o, 41o, 42b."
EN = 'The third part of the Istanbul update: 12 more chapters on the new walls. The city and gate chapters 6b, 7b, 10h and 12b now play at the Gate of St. Romanus section of the new walls (in 12b you walk with the Emperor along the real wall walk and through the tower passage); the Golden Horn and sea-wall chapters 4b, 17, 18b, 19, 19o, 29, 29o and 38o are on the new sea walls (coursed stone, towers, quays, sea gates; in 38o you step off the top of the ladder onto the wall walk without getting stuck). That makes 27 chapters on the new walls: 0, 4b, 6b, 7b, 10h, 12b, 17, 18b, 19, 19o, 20, 20o, 21, 22, 22o, 25, 26, 26o, 28o, 29, 29o, 30, 30o, 32o, 36b, 37o, 38o. Still on the old set: 8y (its new version is ready and will come once a visual glitch is fixed) and 13, 17o, 21o, 23, 24, 31o, 41o, 42b, where the walls are only seen from afar.'


def main():
    d = json.load(open(P, encoding="utf-8"), object_pairs_hook=OrderedDict)
    yeni = OrderedDict([("0.99.124", OrderedDict([("tr", TR), ("en", EN)]))])
    for k, v in d.items():
        if k != "0.99.124":
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
