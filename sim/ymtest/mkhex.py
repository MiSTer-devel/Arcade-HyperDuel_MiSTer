#!/usr/bin/env python3
"""Binary 68000 image -> tb_system +MAINROM hex (256K big-endian words),
plus a 1-line dummy GFX hex. Usage: mkhex.py <in.bin> <mainrom.hex> <gfx.hex>"""
import sys
b = open(sys.argv[1], "rb").read()
b += b"\0" * (0x80000 - len(b))
open(sys.argv[2], "w").write("\n".join("%04x" % ((b[i] << 8) | b[i + 1]) for i in range(0, 0x80000, 2)) + "\n")
open(sys.argv[3], "w").write("00\n")
