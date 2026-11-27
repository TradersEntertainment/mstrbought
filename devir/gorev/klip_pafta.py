# klip_pafta.py ÇIKTI.png klip1.mp4 klip2.mp4 ... : her klipten %15/%50/%85 kareleri, satır başına bir klip
import subprocess, sys, os, tempfile
out, clips = sys.argv[1], sys.argv[2:]
tmp = tempfile.mkdtemp(dir="/root/is/web")
rows = []
for i, c in enumerate(clips):
    L = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", c], capture_output=True, text=True).stdout)
    fs = []
    for p in (0.15, 0.5, 0.85):
        f = os.path.join(tmp, "k%d_%d.png" % (i, int(p * 100)))
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "%.2f" % (L * p), "-i", c, "-vframes", "1", "-vf", "scale=640:360", f], check=True)
        fs.append(f)
    r = os.path.join(tmp, "r%d.png" % i)
    subprocess.run(["ffmpeg", "-v", "error", "-y"] + sum([["-i", f] for f in fs], []) + ["-filter_complex", "hstack=inputs=3", r], check=True)
    rows.append(r)
if len(rows) == 1:
    os.replace(rows[0], out)
else:
    subprocess.run(["ffmpeg", "-v", "error", "-y"] + sum([["-i", r] for r in rows], []) + ["-filter_complex", "vstack=inputs=%d" % len(rows), out], check=True)
print(out)
