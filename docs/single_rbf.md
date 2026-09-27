# Single RBF: Hyper Duel and Magical Error wo Sagase

Status 2026-09-27: implemented and verified in Verilator (sim only).
Not yet built in Quartus or tested on hardware. Uncommitted.

## Design

One bitstream now runs both games on the same board model. The game is
picked at load time by the MRA, with the standard MiSTer-devel arcade
mod byte:

    <rom index="1">
        <part>01</part>
    </rom>

- `Arcade-Hyprduel.sv` latches the byte from any `ioctl_wr` with
  `ioctl_index[7:0] == 1` (address 0) into `mod`, then registers
  `game_me = (mod == 1)`. Power-on value 0, so an MRA with no index 1
  part (both Hyper Duel MRAs, unchanged) runs Hyper Duel.
- The byte arrives as its own download, and the shell already holds
  the core in reset for every download (`reset` includes
  `ioctl_download`). `hyprduel_sys` samples `i_game_me` into
  `game_me_r` only while `rst_n` is low, so the flag is static for the
  whole of play. Every per-game choice below reads `game_me_r`.
- `hyprduel_sys` has no `GAME_MAGERROR` parameter any more. The qsf
  never carried the macro (magerror builds appended it to a copied
  qsf), so the default Quartus build is now the unified one with no
  per-game setting.

## What changed

`rtl/hyprduel_sys.sv`

| Item | Before (compile time) | Now (runtime, `me = game_me_r`) |
|------|------------------------|---------------------------------|
| Sound chips | `gen_jt51` or `gen_opll` generate block | Both always instantiated, `u_ym` (jt51) and `u_opll` (IKAOPLL), directly under the core. jt51 CS is gated off for magerror; IKAOPLL only sees the magerror write stretcher, which only commits when `me`. |
| YM write stretch + DTACK guard | `gen_ym_stretch` only when magerror | Always present; commit gated by `me`, `ym_hold` gated by `me`, so for Hyper Duel the counters never leave 0. |
| Sub IPL1 | YM2151 IRQ or 968 Hz timer | `me_timer_irq OR !ym_irq_n`; the timer is held in reset when `!me`, and `ym_irq_n` is forced high when `me`. |
| VDP IRQ line mask | `P_IRQ_LINE_MASK` 0x02 / 0x01 | New `i4220_vdp` input `i_irq_line_mask`, ANDed with the parameter (now 0x03). Driven `{6'd0, ~me, me}` straight from the flop. |
| Main and sub address decodes | ternary on the parameter | same ternaries on `me` (VDP 0x4/0x8, control latch, shared1 size, YM and OKI windows) |
| Shared1 routing | BRAM for Hyper Duel, SDRAM for magerror | The 32 KB shared1 BRAM is always present with its write enables gated by `!me`; magerror shared1 and the vector shadow decode to the SDRAM sr3 port exactly as before. |
| Mix | per-build gain constants | Both gain paths computed, 2:1 mux on `me`. Magerror OKI x1.5 is now `(okim*768 >>> 8) >>> 1`, which is exact because `okim` is a multiple of 4 (one constant multiplier fewer). |
| `ym_cs_n` / `ym_wr_n` / `ym_a0` / `ym_din` / `ym_dout` / `ym_irq_n` | the one chip's signals | the active chip's view (testbench probes and the sub-bus read mux) |

SDRAM layout: unchanged and already compatible. Both games download the
same stream layout (main 512 KB at 0, GFX 4 MB at 0x080000, OKI 256 KB
at 0x480000). The sr3 port is 17 bits of words at `SR3_WBASE` 0x280000
(byte 0x500000, above the download): Hyper Duel shared3 uses words
0x10000 to 0x1DFFF, magerror shared1 uses words 0x00000 to 0x0FFFF, so
the magerror region is reserved regardless of game.

`Arcade-Hyprduel.sv`: mod byte latch, `.i_game_me(game_me)`, the
`ifdef GAME_MAGERROR` block removed.

`Arcade-Hyprduel.sdc`: the existing `*u_ym|*` and `*u_opll|*`
multicycles now both apply in the one build (instance names are
`emu|core|u_ym` and `emu|core|u_opll`, matched by the wildcards).
Added `set_false_path -from [get_registers {emu|core|*game_me_r}]`:
the flag only changes while the whole core is in reset.

`rtl/i4220_vdp.sv`: `i_irq_line_mask` input. `sim/tb/tb_vdp.sv` ties it
to 8'hFF.

`Arcade-Hyprduel.qsf`, `files.qip`: comments only (IKAOPLL was already
in the file list).

MRA: `Magical Error wo Sagase.mra` now sends the mod byte and names
`<rbf>hyprduel</rbf>`. After the verification below passed it moved
from `magerror_wip/` to `releases/`. It must not ship until a unified
RBF is in `releases/`: the current `Arcade-Hyprduel_20260719.rbf`
ignores the mod byte and would run Hyper Duel code on magerror ROMs.

Sim: `sim/tb/tb_system.sv` drives `i_game_me` from `+MAGERROR`; the
YM2413 audit is always compiled (YMAUDIT printed only with
`+MAGERROR`); the `AUDIOSPLIT` YM tap follows the active chip.
`sim/Makefile` builds one system model per pixel divider
(`build/obj_sys` at 16, `build/obj_sys12` at 12), both with jt51 and
IKAOPLL; `boot-magerror` and `ymtest` run `obj_sys12` with
`+MAGERROR`. `build/obj_sys_me` is gone.

## Verification

All runs 2026-09-27, Verilator 5.050. References were built first from
a snapshot of the pre-unification working tree (magerror fix, final
magerror gains and video options included) and kept in the session
scratchpad (`su/pre`, runs `R*`). Post runs (`P*`) use the unified
models. "Identical" = `cmp` byte-identical on every PPM dump and every
raw audio file, and the testbench log identical apart from Verilator's
wall-time footer.

| Check | Model | Result |
|-------|-------|--------|
| Hyper Duel boot, 720 frames, PIXDIV 16 | `obj_sys` | PASS: 12 frame dumps + audio identical to the pre build and to the earlier `hdlong_post` run; audio md5 `021983dc...`, 83,306 transitions; log identical; all integrity gates PASS |
| Hyper Duel boot, 720 frames, PIXDIV 12 | `obj_sys12` | PASS: 12 frames + audio identical to pre (audio is silent before about frame 757 at this divider, so see next row) |
| Hyper Duel boot, 1200 frames, PIXDIV 12 | `obj_sys12` | PASS: 20 frames + audio identical to pre; audio md5 `b70bf9ef...`, 356,168 transitions, music from about frame 757 |
| Hyper Duel, SDRAM model, 240 frames, PIXDIV 12 | `obj_sys12` | PASS: frames, audio, log identical to pre |
| Magical Error boot, 900 frames, PIXDIV 12, `+MAGERROR` | `obj_sys12` | PASS: 30 frames, mix audio, YM and OKI split taps, OPLL native dump all identical to the pre magerror build; `+YMLOG` identical; log identical; audio md5 `d96f0e1e...`, 350,260 transitions |
| ymcheck on that run | | PASS: 2930/2930 accepted (1465 address, 1465 data), torn 0, stall_clocks 0 |
| Magical Error, SDRAM model, 240 frames | `obj_sys12` | PASS: frames, audio, split taps, log identical to pre |
| `make ymtest` (synthetic YM2413 stimulus) | `obj_sys12` | PASS: 42/42 accepted |
| `make verify` | | PASS: 4/4 scenes pixel-exact |
| `make blit-verify` | | PASS: 2 scenes, all VRAM words, IRQ count 22 |
| `make download` | | PASS: 0 errors |
| `make opll-smoke` | | PASS |
| `tb_vdp` build (new VDP port) | | builds (`vdp-verify` itself needs MAME frame dumps that are not present) |
| Verilator lint of the Quartus top (`emu` + `lint_stubs.sv` + `sys/video_freak.sv` + `sys/math.sv`, `-Wall`) | | 0 errors before and after. New non-vendor warnings: 2 x PROCASSINIT on the shell's `mod` / `game_me` power-on initialisers (the usual MiSTer idiom, same class as `hiscore.v`). The rest of the delta is IKAOPLL's own vendor warnings, now elaborated in every build. |
| System-model Verilator warnings in `rtl/` | | none, before or after |

The same `obj_sys12` binary ran both games; the game came only from
the `+MAGERROR` plusarg. The final `obj_sys12` was regenerated after the
last source edit and its generated C++ is identical to the binary used
for the final runs.

`make render-verify` still fails to build on the pre-existing
`tb_render.sv:59` PINMISSING (unchanged, noted in
docs/magerror_audio_fix.md).

Reproduce (from `sim/`):

    make boot FRAMES=720 AUDIODUMP=build/hd.raw           # Hyper Duel, PIXDIV 16
    make boot PIXDIV12=1 FRAMES=1200 AUDIODUMP=build/hd12.raw
    make boot-magerror FRAMES=900 AUDIODUMP=build/me.raw AUDIOSPLIT=build/me_aud \
      PLUSARGS="+YMLOG=build/me_ymlog.txt +OPLLDUMP=build/me_opll.raw"
    python3 ymtest/ymcheck.py build/me_ymlog.txt

## Risks and open items

- Resources: the Hyper Duel image now also carries IKAOPLL, and the
  magerror image also carries jt51 and the 32 KB shared1 BRAM. Last
  fits: Hyper Duel (video options build) ALMs 70%, block memory bits
  77%; magerror ALMs 69%, block memory 73%. The unified build should
  land at roughly the Hyper Duel figures plus one IKAOPLL. Not
  measured: needs the Quartus fit.
- Timing: the flag adds one LUT input to the CPU address decodes
  (`m_sel_vdp` feeds `m_din` and `m_dtackn` combinationally; the
  fx68k to VDP interface was once near-critical). `ym_hold` is now a
  live term in the sub-bus SB_IDLE entry for Hyper Duel too (it was
  constant 0 in the Hyper Duel build; the magerror build closed with
  it). The mix gains a 2:1 mux on its combinational path to AUDIO_L.
  The false path on `game_me_r` removes the flag's own fan-out from
  analysis. Check the STA for the paths above and confirm in the
  Quartus report that `u_ym`, `u_opll` and `game_me_r` matched their
  SDC patterns (no "ignored" warnings for these constraints).
- Load behaviour: Hyper Duel relies on the mod register's power-on 0.
  MiSTer reloads the bitstream on every MRA load, so a Hyper Duel MRA
  after a magerror session starts from 0. If an MRA were ever loaded
  without an FPGA reload, a Hyper Duel MRA with no mod byte would keep
  the previous value. Adding `<rom index="1"><part>00</part></rom>` to
  the Hyper Duel MRAs would remove that dependency; left unchanged
  here so existing MRAs keep working as they are.
- `hyperduel_db.json` still lists the old separate magerror RBF. The
  magerror MRA now points at `hyprduel`, so the separate magerror RBF
  is no longer needed by it.
- Hardware: both games need a boot and listen test on the MiSTer with
  the unified RBF (Hyper Duel music and effects, magerror music and
  effects, DIPs, hiscore on Hyper Duel).
