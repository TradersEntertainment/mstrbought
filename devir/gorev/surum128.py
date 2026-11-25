#!/usr/bin/env python3
"""0.99.128 sürüm notunu site deposundaki data/changelog.json'un başına ekler (varsa günceller)."""
import json, sys
from collections import OrderedDict

P = "/home/user/nothistorygamedemo/data/changelog.json"
TR = "Bölüm yüklemeleri: büyük bölümler (8y, 10h, 11, 12b, 23, 24, 31o) kurulurken oyun yarım dakikadan uzun süre pencereye hiç cevap vermiyordu; Windows bu yüzden \"Yanıt vermiyor\" diyordu, yükleme ekranındaki çark ve çubuk da donuk kalıyordu. Artık kurulum boyunca pencere canlı (test makinesinde en uzun duraklama 1–2 saniye; Windows'un uyarı eşiği 5 saniye), çark dönüyor, çubuk ilerliyor. Bölüm ortasındaki büyük sahne değişimlerinde de pencere artık donmuyor; 31o'da Eyüp'e ve Ayasofya iskelesine, 24'te Ayasofya'ya, 13'te şehre ve ordugâha geçerken yükleme ekranı çıkıyor. Yüklemeler kısaldı: büyük bölümler test makinesinde ilk açılışta ~53 yerine ~40 saniye, sonraki açılışlarda ~37 yerine ~29 saniyede kuruluyor. Diskteki hazır şehir verisi artık bir bölgeden ötekine geçince (8y → 10h → 8y) silinmiyor; şehir evlerinin hazır verisi de her açılışta siliniyordu, artık saklanıyor. Güncellemeden sonraki ilk açılış yine biraz uzun sürer (hazır veri yeni sürüm için yeniden hazırlanır)."
EN = "Chapter loading: while the big chapters (8y, 10h, 11, 12b, 23, 24, 31o) were being built, the game did not answer the window for more than half a minute; that is why Windows said \"Not responding\", and the spinner and bar on the loading screen stood still. The window now stays alive during the whole build (the longest pause on the test machine is 1–2 seconds; Windows warns at 5 seconds), the spinner turns and the bar moves. The big scene changes in the middle of chapters no longer freeze the window either; a loading screen now appears when 31o moves to Eyüp and to the Hagia Sophia scaffold, when 24 moves to Hagia Sophia, and when 13 moves to the city and the camp. Loading is shorter: on the test machine the big chapters build in ~40 instead of ~53 seconds the first time and in ~29 instead of ~37 seconds afterwards. The prepared city data on disk is no longer deleted when you move from one area to another (8y → 10h → 8y), and the prepared data of the city houses, which used to be deleted on every start, is now kept. The first start after an update still takes a little longer (the prepared data is rebuilt for the new version)."


def main():
    d = json.load(open(P, encoding="utf-8"), object_pairs_hook=OrderedDict)
    yeni = OrderedDict([("0.99.128", OrderedDict([("tr", TR), ("en", EN)]))])
    for k, v in d.items():
        if k != "0.99.128":
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
