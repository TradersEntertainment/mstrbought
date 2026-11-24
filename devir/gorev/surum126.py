#!/usr/bin/env python3
"""0.99.126 sürüm notunu site deposundaki data/changelog.json'un başına ekler (varsa günceller)."""
import json, sys
from collections import OrderedDict

P = "/home/user/nothistorygamedemo/data/changelog.json"
TR = "İstanbul uyarlaması tamamlandı: surun göründüğü bütün bölümler artık yeni surlarda, eski surda kalan bölüm yok (21o yeraltında geçiyor, orada sur yok). Bu sürümle son iki yer de geçti. 31o (fetihten sonra Romanos iç kapısı): caddenin sonunda artık yeni surun gerçek iç kapısı ve kuleleri var, kapının ardında 13, 23 ve 24'teki aynı yaşayan şehir ve kalabalığı başlıyor; yanık ev, cadde ve bölümün akışı aynı. Şehir bölüm açılırken yükleme ekranında kurulduğu için 31o'nun açılışı biraz daha uzun sürebilir. 17o: Haliç'in karşı kıyısından uzakta görünen bütün şehir surları (iki uç, buruna ve Marmara'ya dönen kısım, Eugenius kulesi) ve oyuncunun kendi kıyısındaki Galata surları artık öteki deniz bölümlerindeki taş deniz suruyla aynı görünüşte; düz kutu surlar kalmadı. 8y (beyaz havlu) düzeltmeleri: dış kapıdan köprüye inen toprak rampa artık görünüyor (önceki sürümde yalnız üstünde yürünüyordu, görüntüsü yoktu; kapı eşiği havada duruyor gibiydi), keçiler artık havada değil, yerde yürüyor, ve siperden sonra pazarda Hasan'ı donup bekleme kalktı (Hasan senin hızına yakın yürüyor, beklerken serbestsin)."
EN = "The Istanbul update is complete: every chapter where the walls are visible now uses the new walls, and no chapter is left on the old ones (21o takes place underground, with no walls). This version moves the last two places. 31o (the Romanus inner gate after the conquest): the end of the street now shows the real inner gate and towers of the new walls, and beyond the gate begins the same living city and crowds as in 13, 23 and 24; the burnt house, the street and the flow of the chapter are unchanged. The city is built on the loading screen when the chapter opens, so 31o may take a little longer to start. 17o: all the city walls seen far across the Golden Horn (both ends, the stretch turning toward the point and the Marmara, and the Tower of Eugenius) and the Galata walls on your own shore now have the same stone sea-wall look as the other sea chapters; no flat box walls are left. 8y (the white towel) fixes: the earth ramp from the outer gate down to the bridge is now visible (in the previous version you could walk on it but it was not drawn, so the gate threshold seemed to float), the goats walk on the ground instead of in the air, and you no longer stand frozen at the market waiting for Hasan after the trench (he walks close to your pace and you can move while he arrives)."


def main():
    d = json.load(open(P, encoding="utf-8"), object_pairs_hook=OrderedDict)
    yeni = OrderedDict([("0.99.126", OrderedDict([("tr", TR), ("en", EN)]))])
    for k, v in d.items():
        if k != "0.99.126":
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
