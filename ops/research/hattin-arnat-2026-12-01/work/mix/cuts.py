# cuts.py f.mp4... — يكشف القطع الداخلي في مقطع مولَّد: فرق إطارين متتاليين (64×36 رمادي) فوق 6× الوسيط و> 6
import subprocess, sys, numpy as np
for f in sys.argv[1:]:
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', f, '-vf', 'scale=64:36,format=gray', '-f', 'rawvideo', '-'], capture_output=True).stdout
    a = np.frombuffer(r, np.uint8).reshape(-1, 36, 64).astype(float)
    d = np.abs(np.diff(a, axis=0)).mean(axis=(1, 2)); m = np.median(d) + 0.3
    c = [(round((i + 1) / 24, 2), round(v, 1)) for i, v in enumerate(d) if v > max(6, 6 * m)]
    print(f, 'CUT' if c else 'ok', c)
