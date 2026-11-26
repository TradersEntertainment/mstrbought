#!/usr/bin/env python3
"""0.99.129 sürüm notunu site deposundaki data/changelog.json'un başına ekler (varsa günceller)."""
import json, sys
from collections import OrderedDict

P = "/home/user/nothistorygamedemo/data/changelog.json"
TR = "Lykos vadisinde (Romanos ile Pempton kapıları arası) surların ardı artık 1453'teki gibi: surun iç yüzüne yaslı sıra evler kalktı, yerinde bostanlar, bağlar, meyve bahçeleri, harap kiliseler, kuyulu boş meydanlar ve dağınık köy evleri var; 43o'da Sultan'ın drone'dan baktığında söylediği gibi (\"içeride bostanlar, harap kiliseler, boş meydanlar\"). Şehrin geri kalanı dolu; kalabalık azalmadı (bostanda çalışanlar, keşişler, nöbetçiler). Romanos Kapısı'ndan şehrin içine yeni bir yol açıldı. Harita (M ve köşedeki küçük harita) bugünkü şehirle yeniden çizildi. 31o'da azap konuşurken derviş artık önüne geçmiyor. Saray avlusu (İmparator ve divanı) ile Logothetes kançılaryası surların dibinden alındı, ~400 m içeride kendi mahallesinde; Romanos Kapısı'nda yalnız Giustiniani'nin karargâhı, nöbet yeri ve kapı kaldı. Kapıdan saraya yürünebilen bir yol var; senaryolu gidiş gelişler kararmayla. Eski meydanın yeri de boş kalmadı: kapı önünde nöbet ve onarım yeri, sığınmacı çadırları; yol boyunca evler, bostanlar, bağlar, bir harabe ve kuyulu bir meydan. 26'da toplu dövüşten sonra dost askerler artık yedek bölüğün içine ya da gedik setinin içine girmiyor; 22o'da hendekteki asker dolgunun üstünde havada durmuyor. Bilinen: Bölüm 7'nin uçuşunda uzaktan bakınca surun dibi hâlâ yeşil görünüyor (uzak arazi katmanı); bir bölgeye ilk girildiğinde birkaç saniye surdan önce merdivenleri görünebiliyor."
EN = "In the Lycus valley (between the Romanos and Pempton gates) the land behind the walls now looks the way it did in 1453: the row houses leaning against the inner wall are gone, replaced by vegetable plots, vineyards, orchards, ruined churches, empty squares with wells and scattered village houses, just as the Sultan says when he looks through the drone in 43o (\"vegetable plots, ruined churches, empty squares\"). The rest of the city is still full, and the crowd was not thinned out (gardeners, monks, watchmen). A new road leads from the Romanos Gate into the city. The map (M and the small corner map) was redrawn from the current city. In 31o the dervish no longer steps in front of the azap while he talks. The palace courtyard (the Emperor and his council) and the chancery of the Logothetes have moved away from the walls to their own quarter about 400 m inside the city; only Giustiniani's headquarters, the guard post and the gate remain at the Romanos Gate. A road you can walk leads from the gate to the palace; scripted trips between them use a fade. The old square did not stay empty either: in front of the gate there is a guard and repair post with refugee tents, and along the road houses, vegetable plots, vineyards, a ruin and a small square with a well. In 26 friendly soldiers no longer end up inside the reserve squad or inside the breach rampart after the big fight; in 22o the soldier in the moat no longer floats above the earth fill. Known: during the Chapter 7 flight the foot of the walls still looks green from far away (distant terrain layer), and when you first enter an area the wall stairs can appear a few seconds before the wall itself."


def main():
    d = json.load(open(P, encoding="utf-8"), object_pairs_hook=OrderedDict)
    yeni = OrderedDict([("0.99.129", OrderedDict([("tr", TR), ("en", EN)]))])
    for k, v in d.items():
        if k != "0.99.129":
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
