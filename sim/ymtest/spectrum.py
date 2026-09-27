#!/usr/bin/env python3
"""Peak/RMS report for a native-rate OPLL dump (s16le mono, 3579545/72 Hz).
Usage: spectrum.py <opll.raw> [t0 t1 ...]  (window edges in seconds)"""
import sys
import numpy as np
fs = 3579545 / 72
x = np.fromfile(sys.argv[1], dtype="<i2").astype(float)
edges = [float(v) for v in sys.argv[2:]] or [0, len(x) / fs]
print(f"{len(x)} samples {len(x)/fs:.3f}s min={x.min():.0f} max={x.max():.0f} "
      f"mean={x.mean():.1f} rms_ac={x.std():.1f}")
for lo, hi in zip(edges, edges[1:]):
    seg = x[int(lo * fs):int(hi * fs)]
    if len(seg) < 2048:
        continue
    seg = seg - seg.mean()
    sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
    f = np.fft.rfftfreq(len(seg), 1 / fs)
    peaks = []
    for i in np.argsort(sp)[::-1]:
        if f[i] < 40:
            continue
        if all(abs(f[i] - q) > 20 for q in peaks):
            peaks.append(f[i])
        if len(peaks) == 6:
            break
    print(f"  {lo:.3f}-{hi:.3f}s rms={seg.std():7.1f} peaks_Hz={[round(q, 1) for q in peaks]}")
