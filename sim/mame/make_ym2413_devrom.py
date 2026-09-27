#!/usr/bin/env python3
"""Build MAME 0.288's required ym2413 device ROM (ym2413_instruments.bin,
144 bytes, CRC 6f582d01) from the die-shot patch table already vendored in
IKAOPLL, and verify it by CRC + SHA1 before writing. MAME refuses to run
magerror without it. Usage: make_ym2413_devrom.py <outdir>
(writes <outdir>/ym2413/ym2413_instruments.bin; add <outdir> to -rompath)."""
import hashlib, re, sys, zlib
from pathlib import Path

src = (Path(__file__).resolve().parents[2] /
       "rtl/vendor/ikaopll/IKAOPLL_modules/IKAOPLL_reg.v").read_text()
blk = src[src.index("INSTROM_STYLE == 0"):src.index("ROM STYLE 1")]
rows = {int(m.group(1), 16): m.group(2).split("_") for m in
        re.finditer(r"6'h([0-9A-F]{2}): mem_q <= 63'b([01_]+);", blk)}


def fields(r):
    b = lambda s: int(s, 2)
    TL, DC, DM, FB, AM, PM, ET, KSR, MUL, KSL, AR, DR, SL, RR = r
    return dict(TL=b(TL), DC=b(DC), DM=b(DM), FB=b(FB),
                AMm=b(AM[0]), AMc=b(AM[1]), PMm=b(PM[0]), PMc=b(PM[1]),
                ETm=b(ET[0]), ETc=b(ET[1]), KSm=b(KSR[0]), KSc=b(KSR[1]),
                MULm=b(MUL[:4]), MULc=b(MUL[4:]), KSLm=b(KSL[:2]), KSLc=b(KSL[2:]),
                ARm=b(AR[:4]), ARc=b(AR[4:]), DRm=b(DR[:4]), DRc=b(DR[4:]),
                SLm=b(SL[:4]), SLc=b(SL[4:]), RRm=b(RR[:4]), RRc=b(RR[4:]))


def regs(d):
    return [d["AMm"] << 7 | d["PMm"] << 6 | d["ETm"] << 5 | d["KSm"] << 4 | d["MULm"],
            d["AMc"] << 7 | d["PMc"] << 6 | d["ETc"] << 5 | d["KSc"] << 4 | d["MULc"],
            d["KSLm"] << 6 | d["TL"], d["KSLc"] << 6 | d["DC"] << 4 | d["DM"] << 3 | d["FB"],
            d["ARm"] << 4 | d["DRm"], d["ARc"] << 4 | d["DRc"],
            d["SLm"] << 4 | d["RRm"], d["SLc"] << 4 | d["RRc"]]


def merge(a, b):
    return {k: fields(rows[a])[k] | fields(rows[b])[k] for k in fields(rows[a])}


tab = [regs(fields(rows[i])) for i in range(1, 16)]
tab += [regs(merge(0x10, 0x13)), regs(merge(0x11, 0x14)), regs(merge(0x12, 0x15))]
data = bytes(sum(tab, []))
assert len(data) == 144 and zlib.crc32(data) == 0x6F582D01
assert hashlib.sha1(data).hexdigest() == "bb5537717e0b34849456b5ca7d405403dc3f8fda"
out = Path(sys.argv[1]) / "ym2413"
out.mkdir(parents=True, exist_ok=True)
(out / "ym2413_instruments.bin").write_bytes(data)
print(f"{out}/ym2413_instruments.bin: 144 bytes, CRC 6f582d01, SHA1 verified")
