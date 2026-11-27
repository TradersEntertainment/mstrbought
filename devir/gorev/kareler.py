# Günlükteki "MONTAGE buro an=N frame=F" ve "kesme" satırlarından her anın/kesmenin +0,9 sn ve satır ortası karelerini çıkarır
import re, subprocess, sys, os
avi, log, out = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(out, exist_ok=True)
picks = []
for raw in open(log, encoding="utf-8", errors="replace"):
    m = re.match(r"MONTAGE buro an=(\d+) frame=(\d+)", raw)
    if m: picks.append(("an%02d_a" % int(m.group(1)), int(m.group(2)) + 27))
    m = re.match(r"MONTAGE buro kesme an=(\d+) frame=(\d+)", raw)
    if m: picks.append(("an%02d_k%d" % (int(m.group(1)), int(m.group(2))), int(m.group(2)) + 20))
    m = re.match(r"MONTAGE buro an=(\d+) son frame=(\d+)", raw)
    if m: picks.append(("an%02d_z" % int(m.group(1)), int(m.group(2)) - 25))
sel = "+".join("eq(n\\,%d)" % f for _, f in picks)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", avi, "-vf", "select='%s'" % sel, "-vsync", "0", os.path.join(out, "tmp_%03d.png")], check=True)
fs = sorted(x for x in os.listdir(out) if x.startswith("tmp_"))
for (name, f), fn in zip(sorted(picks, key=lambda x: x[1]), fs):
    os.replace(os.path.join(out, fn), os.path.join(out, "%s_%05d.png" % (name, f)))
print("\n".join(sorted(os.listdir(out))))
