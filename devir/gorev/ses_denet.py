# Her replik penceresinde (line on → off) ham kaydın ortalama ses düzeyi: sessiz replik (≈ -35 dB) yakalanır
import re, subprocess, sys
avi, log = sys.argv[1], sys.argv[2]
on = None
rows = []
for raw in open(log, encoding="utf-8", errors="replace"):
    m = re.match(r"MONTAGE line on frame=(\d+) key=(\S+) .*spk=(.*?) text=", raw)
    if m: on = (int(m.group(1)), m.group(2), m.group(3)); continue
    m = re.match(r"MONTAGE line off frame=(\d+)", raw)
    if m and on:
        rows.append((on[0], int(m.group(1)), on[1], on[2])); on = None
for f0, f1, k, spk in rows:
    t0, d = f0 / 30.0, max((f1 - f0) / 30.0, 0.2)
    out = subprocess.run(["ffmpeg", "-nostats", "-ss", "%.3f" % t0, "-t", "%.3f" % d, "-i", avi, "-vn", "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
    mv = re.search(r"mean_volume: (\S+)", out); xv = re.search(r"max_volume: (\S+)", out)
    flag = "  <-- SESSİZ?" if mv and float(mv.group(1)) < -30 else ""
    print("%-18s %-22s %6.2f-%6.2f  ort %s  tepe %s%s" % (k, spk[:22], t0, t0 + d, mv.group(1) if mv else "?", xv.group(1) if xv else "?", flag))
