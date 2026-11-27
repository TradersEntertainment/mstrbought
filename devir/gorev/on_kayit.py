# Genel fragman ön kaydı: biten çekimleri kesip sayfanın "ön kayıt" bölümünü yazar (index.html'de işaretler arası)
import json, os, re, subprocess, sys
S = "/tmp/claude-0/-home-user-mstrbought/30127caa-76dd-5459-81fb-4bbd5156d7e0/scratchpad"
KAYIT = [(S + "/fragman2/kayit/p_aksiyon_a.avi", S + "/fragman2/kayit/p_aksiyon_a.log"),
         (S + "/fragman2/kayit/p_aksiyon_b.avi", S + "/fragman2/kayit/p_aksiyon_b.log")]
KIMLIK = ["ok_yagmuru", "ladder_arrows", "pole", "wall_duel", "tower_gunner", "cannon", "duel", "matchlock", "wounded",
          "giust_carry", "kizak_kayis", "sahi_hey", "fren_ipi", "dokum", "rowing", "fici", "havlu_ok2", "flight", "arena"]
D = S + "/fragman_sayfa"
ADLAR = [("Ok yağmurunda gediğe koşu", "0"), ("Merdiveni taşı, oklar yağıyor", "30o"), ("Merdiveni surdan it", "30"),
    ("Surda ilk rakip", "30o"), ("Tüfek dolu, yana atla", "30o"), ("Topu kendin doldur, nişanla", "20o"),
    ("Kılıç: yönü oku, savuştur", "20"), ("Fitilli tüfek", "20"), ("Yaralıyı omzuna al", "30o"),
    ("Komutanı taşı, sarsma", "26"), ("Yağlı kızakta kay", "2"), ("Şahi'yi çek", "28o"), ("İpi bırakma", "35o"),
    ("Topu dök", "10b"), ("Haliç'te kürek çek", "38o"), ("Fıçıyı yuvarla", "18"), ("İki ordunun arasında", "8y"),
    ("Uç, görünmez ol", "7"), ("Sonsuz kuşatma", "arena")]
NOT = json.load(open("/root/is/web/on_notlar.json", encoding="utf-8")) if os.path.exists("/root/is/web/on_notlar.json") else {}
segs, fail = [], []
for AVI, LOG in KAYIT:
    if not os.path.exists(LOG):
        continue
    ids, ins = {}, {}
    for raw in open(LOG, encoding="utf-8", errors="replace"):
        m = re.match(r"MONTAGE seg=(\d+) .* ok=(\w+) .*id=(\S*)", raw)
        if m:
            ids[int(m.group(1))] = m.group(3)
            if m.group(2) != "true": fail.append(m.group(3))
        m = re.match(r"MONTAGE (in|out) seg=(\d+) frame=(\d+)", raw)
        if m:
            k, f = int(m.group(2)), int(m.group(3))
            if m.group(1) == "in": ins[k] = f
            elif k in ins and ids.get(k) in KIMLIK:
                segs.append((KIMLIK.index(ids[k]), ins.pop(k), f, AVI))
segs.sort()
yeni = []
kartlar = []
for n, a, b, AVI in segs:
    ad = "s%02d_%s" % (n, KIMLIK[n])
    mp4, jpg = "on/%s.mp4" % ad, "on/%s.jpg" % ad
    t0, dur = a / 30.0 + 0.034, (b - a) / 30.0 - 0.034
    if not os.path.exists(os.path.join(D, mp4)):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % t0, "-t", "%.3f" % dur, "-i", AVI, "-c:v", "libx264",
            "-preset", "medium", "-crf", "23", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart",
            os.path.join(D, mp4)], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % (t0 + dur * 0.45), "-i", AVI, "-vframes", "1", "-q:v", "4",
            os.path.join(D, jpg)], check=True)
        yeni += [mp4, jpg]
    nt = NOT.get(str(n), ["bakılıyor", ""])
    sinif = {"seçildi": "yeni", "zayıf": "eski", "bakılıyor": "bekle"}.get(nt[0], "bekle")
    kartlar.append(f'''      <article class="dosya kucuk">
        <div class="cerceve"><video controls preload="none" playsinline poster="{jpg}" src="{mp4}"></video></div>
        <div class="bas"><h3>{ADLAR[n][0]}</h3><span class="etiket {sinif}">{nt[0]}</span></div>
        <div class="kunye"><span>Çekim {n + 1:02d}</span><span>Bölüm {ADLAR[n][1]}</span><span>{dur:.1f} sn</span></div>
        {f"<p>{nt[1]}</p>" if nt[1] else ""}
      </article>''')
bitti = len(kartlar)
var = {n for n, *_ in segs}
kalan = [ADLAR[i][0] for i in range(len(ADLAR)) if i not in var]
blok = f'''<!--ON-BASLA-->
  <div class="bolum-baslik" id="on-kayit">Genel fragman · ön kayıt çekimleri ({bitti}/{len(ADLAR)})</div>
  <p class="giris">Seçim için alınan düşük çözünürlüklü (640×360) ham çekimler, oyunun kendi sesiyle; müzik ve kurgu yok. Kayıt sürdükçe buraya ekleniyor. Fragmana girecekler 1080p'de yeniden çekilecek.</p>
  <section class="izgara uc">
{chr(10).join(kartlar)}
  </section>
  {f'<p class="kalan">Sırada: {", ".join(kalan)}.</p>' if kalan else ''}
<!--ON-BITIR-->'''
h = open(os.path.join(D, "index.html"), encoding="utf-8").read()
h = re.sub(r"<!--ON-BASLA-->.*?<!--ON-BITIR-->", lambda m: blok, h, flags=re.S)
open(os.path.join(D, "index.html"), "w", encoding="utf-8").write(h)
print("biten", bitti, "yeni dosya", len(yeni), "başarısız", fail)
print(json.dumps(yeni))
