# Magical Error: silent YM2413 music (write-strobe fix)

Status 2026-09-27: root cause confirmed in simulation with the real game
ROM; fix and a MAME-parity mix gain are in the working tree (uncommitted).
Music now matches MAME 0.288 in content and level. NOT yet verified by
STA or on hardware.

## Symptom

On the MiSTer, OKI M6295 effects play but YM2413 (IKAOPLL) music is
silent.

## Root cause

`rtl/hyprduel_sys.sv` drove the sound chip strobe as a 1-sys-clock pulse
on the sub-bus SB_IDLE commit cycle. That suits jt51 (Hyper Duel), which
samples every clock. IKAOPLL is instantiated with `FULLY_SYNCHRONOUS=1`,
and its `IKAOPLL_rw_synchronizer` samples the write request only on the
phiM clock enable (3.579545 MHz, 1 in about 22.35 sys clocks at 80 MHz).
A 1-clock pulse is therefore seen only when it happens to coincide with
that enable, so about 95% of register writes are silently dropped. The
few that land usually hit the wrong register, because the address write
before them was dropped.

The standalone smoke test (`make opll-smoke`) passed because its
testbench holds CS low for 4 phiM periods; the integration never did.

## Evidence

Synthetic stimulus, no game ROM needed (`sim/ymtest/ymtest.s`): the main
CPU copies a sub program to shared1 and releases the sub CPU; the sub CPU
(real fx68k, real sub-bus FSM, magerror map, 10 MHz as on the PCB) writes
42 YM2413 port writes: 20 with datasheet spacing, 12 back-to-back with no
software wait, 10 more with spacing. The testbench counts CPU-side
writes to 0x800000-3 against rising edges of IKAOPLL's internal
`addrreg_wrrq` / `datareg_wrrq`, logging the byte the chip latched.

| RTL | CPU writes | accepted by IKAOPLL | order/data match |
|-----|-----------:|--------------------:|------------------|
| before fix | 42 | 2 (0 address, 2 data) | FAIL (2/42) |
| after fix  | 42 | 42 (21 address, 21 data) | PASS, 0 torn |

An independent cycle model of the synchroniser (Python, all 800
combinations of commit phase against the phiM enable and phi1 ring)
agrees: a 1-clock pulse is accepted 32/800 = 4.0% of the time; a
40-clock hold is accepted 800/800. Worst-case request rise is 156 clocks
after commit and fall 245 clocks (the sim measured 154 and 244).

Before the fix the OPLL output is a flat +342 (the idle level). After the
fix, native-rate spectrum of the OPLL output (`+OPLLDUMP`):

| window | RMS | strongest peaks (Hz) | expected |
|--------|----:|----------------------|----------|
| 0.01-0.26 s | 479 | 552, 340, 872, 520, 1040, 1560 | ch1 552, ch4 342, ch2 874, ch3 520 (+harmonics) |
| 0.28-0.66 s | 319 | 521, 342, 1040, 1560, 2082, 2603 | ch3 520 + harmonics, ch4 342 |

Output range -1406..+1778, bipolar, about 480 RMS with five channels
at full volume.

## A second hazard found while testing

With the strobe stretched, a data write followed immediately by the next
address write still went wrong (a stray 196 Hz tone in place of the 342
and 520 Hz notes). Writes to registers 0x10-0x38 are queued inside the
chip until that channel's slot comes round (up to one 72-phiM sample
period). A new address write before then redirects the queued data.
This is the reason for the real YM2413's 84-phiM wait after data writes.
The fix therefore holds off a following YM write until the previous one
has been consumed.

## The fix (rtl/hyprduel_sys.sv, magerror only)

New `gen_ym_stretch` block, active only for magerror (originally a
`GAME_MAGERROR=1` generate block; since the single-RBF change it is
always present and gated by the runtime game flag, docs/single_rbf.md):

- On the commit cycle, latch A0 and D, then drive CS_n/WR_n low for
  `YMW_HOLD = 40` sys clocks. That always covers at least one phiM enable
  and never more than two. The request cannot re-trigger, because it
  only drops at least 156 clocks after it was sampled.
- A further YM write gets no DTACK until `YMW_BUSY_A = 288` clocks after
  an address write, or `YMW_BUSY_D = 1920` clocks after a data write.
  The datasheet minimums are 12 phiM (268 clocks) and 84 phiM (1878
  clocks). Software that honours them never waits; software that does
  not is serialised correctly, as in MAME, and the sub CPU loses at most
  24 us.
- Only the SB_IDLE entry condition changes (`&& !ym_hold`), and
  `ym_hold` stays 0 when Hyper Duel is selected.
- As a side effect, the SDC's multicycle-2 on internal `u_opll` paths
  (which includes the CS/D sync chain) is now safe, because the inputs
  stay static for 40 clocks.

Reads of 0x800000-3 no longer assert CS. MAME maps them `nopr`.

## Real game ROM (roms/magerror.zip, CRCs match the driver)

`make boot-magerror PIXDIV12=1 FRAMES=900` with `+YMLOG` and `+OPLLDUMP`
(default DSW 0xFFBF = the MRA default, demo sounds on). Music starts at
frame 480 (design time 7.98 s; MAME 7.95 s).

| RTL | CPU writes | accepted | torn | stall_clocks |
|-----|-----------:|---------:|-----:|-------------:|
| before fix | 2930 | 132 (4.5%) | 0 | n/a |
| after fix  | 2930 | 2930 (1465 address, 1465 data), order and data exact | 0 | 0 |

- The game's writes are 432 sys clocks (5.4 us) apart at the closest,
  above the 268-clock address minimum. The guard never stalls the real
  game.
- The 2930-write CPU stream is byte-identical, in order, to MAME 0.288's
  first 2930 YM2413 writes (tap below), and its timing matches MAME
  (the sim's 6.90 s span of design time equals MAME's).
- Before the fix, the YM output after music start is sparse garbage
  (peak 1329, 72 RMS, and only 1x gain against the OKI's 12x), which
  fits "silent" on hardware.

### Against MAME 0.288

MAME was run headless on this machine. It refuses to run magerror
without the `ym2413` device ROM `ym2413_instruments.bin` (144 bytes,
CRC 6f582d01). That table is the chip's patch ROM, which IKAOPLL
already carries from the die shot. `sim/mame/make_ym2413_devrom.py`
rebuilds it from the vendored IKAOPLL source; it matches MAME's CRC and
SHA1 exactly, so nothing was downloaded. Two runs with
`sim/mame/tap_ym2413_me.lua` (25 s, `-wavwrite`, 48 kHz): one normal,
one with every YM key-on and rhythm bit masked (`MUTE_YM=1`). The chip
is write-only, so CPU flow is unchanged; the two tap logs are identical.
Normal minus muted gives MAME's YM-only stream; the muted run gives
MAME's OKI-only stream.

Music, sim OPLL vs MAME YM-only, first 6.9 s after the first write:

- Level: MAME = 7.03 x IKAOPLL ACC overall. In 13 consecutive 0.5 s
  windows the ratio stays between 6.36 and 7.61.
- Pitch: the dominant pitch class agrees with MAME in 60/60 windows of
  0.21 s (pre-fix 24/60; the null test with MAME offset by 2.3 s gives
  65%). The median log-spectrum correlation is 0.77 (null 0.57).

Effects, sim pre-gain OKI tap (`oki_snd << 2`) vs MAME OKI-only,
8.5-11.0 s: MAME = 2.13 x the tap. Our OKI clock is 2.000 MHz against
MAME's 2.0625 MHz, so short windows scatter (1.84-2.32).

## Mix gain (applied, marked)

The mix applies x3 to the OKI tap. To reproduce MAME's music:effects
balance, the YM gain is 7.03 x 3 / 2.13 = 9.90, applied as
`(ymm * 2534) >>> 8` for magerror only (the RTL comment carries the
derivation). The previous unscaled mix had the music 9.9x (20 dB) too
quiet relative to MAME. I dropped the earlier x16 estimate.

- Headroom: over the 900-frame run the mixed output peaks at 21495 with
  0 clipped samples. The worst-case ACC with every slot at full volume
  is about 8.4k, x2534 < 2^25, so the 26-bit intermediate cannot wrap.
- Caveat: this is MAME parity, not PCB parity. On Hyper Duel, PCB video
  showed MAME's OKI route is about 3.5x (11 dB) too quiet against the FM.
  If the same holds for magerror's board mix, the PCB value is nearer
  x2.8. There is no magerror PCB recording to settle this.
- Not addressed: IKAOPLL idles at +342 (+38 per silent channel), so
  there is a DC step of about 3.4k at reset and about 376 per channel as
  channels start or stop. MAME idles at 0. A DC-blocking high-pass
  (the shell probably AC-couples anyway) would remove it; left for
  hardware listening.

## Hyper Duel is unaffected

- Verilator C++ generated for the Hyper Duel build (`GAME_MAGERROR=0`,
  PIXDIV12) with the final RTL (fix and gain) is identical to the
  original, apart from testbench line numbers in assertion strings.
- `make boot`-equivalent runs with `roms/hyprduel.zip` (PIXDIV 16, the
  `make boot` default), original RTL vs fixed RTL, 240 and 720 frames:
  all PPM dumps and the audio capture are byte-identical (720-frame audio
  md5 021983dc..., 83306 audio transitions, 40812 YM writes). The log is
  identical and every gate PASSes (in-flight exposure 0, scroll snapshot
  0/162512, ladder 0). These binaries were built before the gain edit,
  which the C++ diff above covers.
- `make verify` (4/4 scenes pixel-exact), `make blit-verify` (2 scenes,
  all VRAM words plus IRQ counts), `make download` (0 errors) and
  `make opll-smoke` all PASS.
- `make render-verify` fails to build with `PINMISSING` on
  `tb/tb_render.sv:59` (`o_dbg_used_sx2_*`). This is a pre-existing
  testbench issue; `i4220_render.sv` and `tb_render.sv` are untouched.
- `mame-verify` / `vdp-verify` were not run: their MAME frame dumps
  (`build/mame/frame_*`) do not exist, and neither suite instantiates
  `hyprduel_sys.sv`.

## Still open

1. STA (Quartus not run here). The new logic is a small counter and
   byte latch on the sub-bus side.
2. Hardware listening test, including the final gain choice (x9.90 MAME
   parity vs about x2.8 if the Hyper Duel PCB offset carries over) and
   whether the idle DC step is audible.

## Reproduce

    cd sim
    make ymtest FRAMES=40        # prints YMAUDIT line, then PASS/FAIL
    python3 ymtest/spectrum.py build/ymtest/opll.raw 0.01 0.26 0.28 0.66

Real ROM and MAME (roms/ in place):

    cd sim
    make boot-magerror PIXDIV12=1 FRAMES=900 AUDIOSPLIT=build/me_aud \
      PLUSARGS="+YMLOG=build/me_ymlog.txt +OPLLDUMP=build/me_opll.raw"
    python3 ymtest/ymcheck.py build/me_ymlog.txt
    python3 mame/make_ym2413_devrom.py build/mame_me/devroms
    for m in 0 1; do MUTE_YM=$m TAP_OUT=build/mame_me/tap_mute$m.txt \
      SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy mame magerror \
      -rompath "../roms;build/mame_me/devroms" -video none -sound none \
      -nothrottle -skip_gameinfo -seconds_to_run 25 -samplerate 48000 \
      -wavwrite build/mame_me/mix_mute$m.wav \
      -autoboot_script mame/tap_ym2413_me.lua; done

(`boot-magerror` builds its ROM hex files from `../roms/magerror.zip`.
Since the single-RBF change (docs/single_rbf.md) there is no separate
magerror model: `boot-magerror` and `ymtest` run the unified
`build/obj_sys12` model with `+MAGERROR`. The 900-frame run takes about
30 minutes.)

Needs `m68k-elf-as` / `m68k-elf-ld` / `m68k-elf-objcopy` (Homebrew
`m68k-elf-binutils`). The pre-fix result is reproduced by building
against `git show HEAD:rtl/hyprduel_sys.sv`.

Files: `rtl/hyprduel_sys.sv` (fix + x9.90 magerror YM gain), `sim/tb/tb_system.sv`
(YMAUDIT counters, `+YMLOG`, `+OPLLDUMP`; the existing YM write counter
is now edge-counted, which gives identical Hyper Duel counts), `sim/Makefile`
(`ymtest` target, magerror ROM hex rules, AUDIODUMP/AUDIOSPLIT passthrough
on `boot-magerror`), `sim/ymtest/` (stimulus, hex builder, checker,
spectrum), `sim/mame/tap_ym2413_me.lua` (MAME YM tap + mute),
`sim/mame/make_ym2413_devrom.py` (MAME device ROM from IKAOPLL).
