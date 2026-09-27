#!/usr/bin/env python3
"""Compare the CPU-side and chip-side YM2413 write streams from +YMLOG.
Usage: ymcheck.py <ymlog.txt>. Exit 0 only if every CPU write was
accepted exactly once, in order, with the same A0 and data byte."""
import sys
cpu, acc = [], []
for ln in open(sys.argv[1]):
    f = ln.split()
    if f[0] not in ("C", "A"):
        continue
    (cpu if f[0] == "C" else acc).append((int(f[1]), f[2].lower()))
print(f"cpu_writes={len(cpu)} accepted={len(acc)} "
      f"(addr {sum(1 for a,_ in acc if a==0)}, data {sum(1 for a,_ in acc if a==1)})")
ok = cpu == acc
if not ok:
    # how many CPU writes appear in the accepted stream as an in-order subsequence
    j = 0
    for w in cpu:
        if j < len(acc) and acc[j] == w:
            j += 1
    print(f"MISMATCH: in-order matched {j}/{len(cpu)}")
    for i in range(min(12, max(len(cpu), len(acc)))):
        c = cpu[i] if i < len(cpu) else None
        a = acc[i] if i < len(acc) else None
        print(f"  {i:3d} cpu={c} acc={a}")
print("PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
