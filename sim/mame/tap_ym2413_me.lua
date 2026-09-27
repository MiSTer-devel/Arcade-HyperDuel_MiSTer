-- magerror YM2413 oracle tap (docs/magerror_audio_fix.md).
-- Logs every sub-CPU write to the YM2413 ports (0x800000-0x800003) as
-- "<emu_seconds> <a0> <data>" to TAP_OUT. With MUTE_YM=1 it also keys
-- every melodic channel off and disables rhythm (write-only chip, so
-- CPU flow is unchanged), giving an OKI-only -wavwrite; mix minus that
-- run isolates the YM2413 music.
--
--   SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy mame magerror \
--     -rompath "../roms;<dir with ym2413/ym2413_instruments.bin>" \
--     -video none -sound none -nothrottle -seconds_to_run 20 \
--     -wavwrite out.wav -autoboot_script mame/tap_ym2413_me.lua
local outpath = os.getenv("TAP_OUT") or "build/mame_me/ym2413_tap.txt"
local mute = os.getenv("MUTE_YM") == "1"
local fh = io.open(outpath, "w")
local sub = manager.machine.devices[":sub"].spaces["program"]
local cur = -1
_G.me_ym_tap = sub:install_write_tap(0x800000, 0x800003, "me_ym_tap",
  function(offset, data, mask)
    local a0 = (offset >= 0x800002) and 1 or 0
    local v = data & 0xff
    fh:write(string.format("%.9f %d %02x\n", manager.machine.time:as_double(), a0, v))
    if a0 == 0 then
      cur = v
    elseif mute then
      if cur >= 0x20 and cur <= 0x28 then return data & ~0x10 end
      if cur == 0x0e then return data & ~0x20 end
    end
  end)
_G.me_ym_fh = fh
emu.add_machine_stop_notifier(function() fh:close() end)
