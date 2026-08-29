# Magical Error wo Sagase - held back

The magerror build is **not** part of the MiSTer-devel submission and is
not distributed from `releases/`.

## Why

Confirmed on hardware 2026-08-29: **OKI M6295 sound effects play, but the
YM2413 music is silent.**

That isolates the fault to the IKAOPLL integration. OKI audio reaches the
output through the same shared mix and shell audio path, so both of those
are exonerated.

The likely seam: IKAOPLL was verified only by a standalone smoke test (an
FFT on a preset patch, proving the write -> PG -> OP -> EG -> DAC pipeline).
Its ACC output is near-unipolar impulse form with 5-bit signed slot volumes,
and the mixing polarity and scale were deferred to "settle against MAME
parity at integration". No system-level audio parity run against MAME was
ever done for this build.

## Next step

Run a system-level audio parity check against MAME 0.288 `magerror`,
focused on the OPLL ACC to mix polarity and scale.

Once fixed, this becomes its own `Arcade-Magerror_MiSTer` repository. The
MiSTer-devel contribution guide requires every game shipped in `releases/`
to be fully playable, which is why it is not included here.

## Contents

| File | md5 |
|------|-----|
| `Magerror_20260719.rbf` | `33f7c0de13501a51f48bdffea92d60de` |
| `Magical Error wo Sagase.mra` | - |

The RTL supports this build via the `GAME_MAGERROR` Verilog macro; the
source is unchanged and still present in `rtl/`.
