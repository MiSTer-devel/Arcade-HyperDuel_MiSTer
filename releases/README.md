# Releases

Released bitstreams and MRA files, in the MiSTer-devel arcade layout.

Copy `Arcade-Hyprduel_YYYYMMDD.rbf` to `/media/fat/_Arcade/cores/`, the
MRA files to `/media/fat/_Arcade/`, and the ROM set (MAME 0.288 naming,
`hyprduel.zip`) to `/media/fat/games/mame/`.

Alternative versions live in `_alternatives/_Hyper Duel/` and are copied
to `/media/fat/_Arcade/_alternatives/_Hyper Duel/`.

| File | md5 | Notes |
|------|-----|-------|
| `Arcade-Hyprduel_20260719.rbf` | `87b6ee7d275b96c4b01a635fac204335` | Hyper Duel v1.0. Hiscore SDRAM-snoop address fix, verified saving on hardware. |

Every released RBF passed, in order: the full Verilator parity suite,
the always-on integrity gates over a 2,200-frame SDRAM-model soak with
the hardware DIP configuration, a clean Quartus timing summary (all
clocks non-negative, report timestamps matched to the bitstream), an
md5-verified deploy, and on-hardware verification on a CRT.

## Magical Error wo Sagase

Not shipped here. The magerror build is held in `../magerror_wip/`
pending a fix to its YM2413 music, which is silent on hardware (OKI
M6295 sound effects play correctly). See `../magerror_wip/README.md`.
