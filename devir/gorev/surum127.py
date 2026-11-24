#!/usr/bin/env python3
"""0.99.127 sürüm notunu site deposundaki data/changelog.json'un başına ekler (varsa günceller)."""
import json, sys
from collections import OrderedDict

P = "/home/user/nothistorygamedemo/data/changelog.json"
TR = "Oyun artık kendini internetten güncelleyebiliyor (Windows ve Linux): yeni sürüm çıkınca ana menünün sağ üstünde \"Yeni sürüm var\" bandı çıkar; \"Güncelle\" ile yeni sürüm (≈1,2 GB) arka planda iner, sen oynamaya devam edebilirsin; boyutu ve parmak izi doğrulanır, \"Yeniden başlat ve güncelle\" ile oyun yeni sürümle açılır, kayıtların ve ayarların yerinde kalır. Bir adım tutmazsa eski sürüm yerinde kalır ve indirme sayfası açılır. \"Ne değişti?\" sürüm notunu gösterir, ayarlardan kapatılabilir. Bu özellik bu sürümle geldiği için 0.99.127'yi bir kez elle indirmen gerekiyor; sonrakiler oyunun içinden gelir. Sur kapıları: kapıyı iki yandan tutan kulelerin dibindeki toprak etek kapı geçidinin içine taşıyordu; 8y'de ve şehir meydanından çıkılan kapıda geçidin ortasında çatlak bir toprak tümseği vardı. Artık geçit düz taş döşeme. Şehir meydanında (10h, 12b, 13, 23, 24, 6 ve 7'nin Bizans tarafı) peribolos toprağı da döşemenin altına indi. 8y: hendek köprüsünün görünen ayakları yıkık, yürünen köprü sağlamdı; köprüye inip çıkarken havada yürünüyordu, artık iki yakada tam boy taş ayaklar var. Ordugâh girişindeki aşçı konuşmalardan sonra kazanı karıştırmaya geri dönüyor (önceden kepçeyle havayı karıştırıyordu). Ordugâhta ve 2. bölümde öküzler artık toprağa gömük değil. 18b: Haliç surunun yanındaki penceresiz pembe kutu bina (Blakherna Sarayı) artık pencereli ve kapılı; 25: Ayasofya çevresindeki pastel kutu evler tam ev. 20: zor zorlukta bir dost asker Giustiniani'nin önünde kalıp onu kapatabiliyordu; artık kenara çekilemezse komutan yanına gelip konuşuyor. Testlere yeni denetimler eklendi: görünmez zemin, kazanın dışında kalan alet, sebepsiz donup bekleme, havada/gömük hayvan."
EN = "The game can now update itself from the internet (Windows and Linux): when a new version is out, a \"New version available\" banner appears at the top right of the main menu; \"Update\" downloads it (≈1.2 GB) in the background while you keep playing; its size and fingerprint are checked, and \"Restart and update\" reopens the game on the new version with your saves and settings kept. If any step fails, the old version stays in place and the download page opens. \"What changed?\" shows the release notes, and the check can be turned off in the settings. Since the feature arrives with this version, 0.99.127 has to be downloaded by hand once; later versions come from inside the game. Wall gates: the earth skirt at the foot of the towers flanking a gate spilled into the gate passage; in 8y and at the gate out of the city square there was a cracked mound of earth in the middle of the passage. The passage is now flat paving. In the city square (10h, 12b, 13, 23, 24 and the Byzantine side of 6 and 7) the peribolos ground also sits under the paving now. 8y: the visible piers of the moat bridge were the ruined ones while the walkable bridge was intact, so you walked in the air going on and off the bridge; there are now full stone piers on both banks. The cook at the camp entrance goes back to stirring the pot after conversations (he used to stir the air). The oxen in the camp and in chapter 2 are no longer sunk into the ground. 18b: the windowless pink box building next to the Golden Horn walls (the Blachernae Palace) now has windows and doors; 25: the pastel box houses around Hagia Sophia are now proper houses. 20: on hard difficulty a friendly soldier could stand in front of Giustiniani and hide him; now, if the soldier cannot step aside, the commander comes to your side to speak. New automated checks were added to the tests: invisible ground, a tool left outside its pot, standing frozen for no reason, and animals floating or sunk."


def main():
    d = json.load(open(P, encoding="utf-8"), object_pairs_hook=OrderedDict)
    yeni = OrderedDict([("0.99.127", OrderedDict([("tr", TR), ("en", EN)]))])
    for k, v in d.items():
        if k != "0.99.127":
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
