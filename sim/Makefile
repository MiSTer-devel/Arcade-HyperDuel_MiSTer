# M1/M2 verification loops: oracle vs SV, diffed per scene.
SCENES     := scene1 scene2 scene3 scene4
BLITSCENES := blit1 blit2
NBLITS     := 24
BUILD      := build
VERILATOR ?= verilator

.PHONY: all scenes model verify blit-verify clean

all: verify blit-verify

$(BUILD)/scenes.stamp: oracle/make_scene.py oracle/i4220_oracle.py
	mkdir -p $(BUILD)
	cd oracle && python3 make_scene.py ../$(BUILD)/scenes
	touch $@

scenes: $(BUILD)/scenes.stamp

$(BUILD)/obj_dir/Vi4220_model: tb/i4220_model.sv
	$(VERILATOR) --binary -Wall -Wno-UNUSEDSIGNAL -Wno-BLKSEQ \
		--Mdir $(BUILD)/obj_dir tb/i4220_model.sv --top-module i4220_model
model: $(BUILD)/obj_dir/Vi4220_model

verify: scenes model
	@fail=0; \
	for s in $(SCENES); do \
	  echo "=== $$s ==="; \
	  python3 oracle/i4220_oracle.py $(BUILD)/scenes/$$s $(BUILD)/$$s.oracle.ppm; \
	  $(BUILD)/obj_dir/Vi4220_model +SCENE=$(BUILD)/scenes/$$s +OUT=$(BUILD)/$$s.rtl.ppm; \
	  python3 diff_ppm.py $(BUILD)/$$s.oracle.ppm $(BUILD)/$$s.rtl.ppm || fail=1; \
	done; \
	exit $$fail

$(BUILD)/blitscenes.stamp: oracle/make_blit_scene.py
	mkdir -p $(BUILD)
	cd oracle && python3 make_blit_scene.py ../$(BUILD)/blitscenes
	touch $@

$(BUILD)/obj_blit/Vtb_blitter: tb/tb_blitter.sv ../rtl/i4220_blitter.sv
	$(VERILATOR) --binary --timing -Wall -Wno-UNUSEDSIGNAL --timescale 1ns/1ps \
		--Mdir $(BUILD)/obj_blit ../rtl/i4220_blitter.sv tb/tb_blitter.sv \
		--top-module tb_blitter

blit-verify: $(BUILD)/blitscenes.stamp $(BUILD)/obj_blit/Vtb_blitter
	@fail=0; \
	for s in $(BLITSCENES); do \
	  echo "=== $$s ==="; \
	  python3 oracle/i4220_blitter_oracle.py $(BUILD)/blitscenes/$$s; \
	  mkdir -p $(BUILD)/$$s.rtl; \
	  $(BUILD)/obj_blit/Vtb_blitter +SCENE=$(BUILD)/blitscenes/$$s \
	      +NBLITS=$(NBLITS) +OUTDIR=$(BUILD)/$$s.rtl; \
	  for l in 0 1 2; do \
	    python3 diff_hex.py $(BUILD)/blitscenes/$$s/vram$$l.out.hex \
	        $(BUILD)/$$s.rtl/vram$$l.out.hex || fail=1; \
	  done; \
	  if ! cmp -s $(BUILD)/blitscenes/$$s/irqs.out $(BUILD)/$$s.rtl/irqs.out; then \
	    echo "FAIL: IRQ count differs: oracle=$$(cat $(BUILD)/blitscenes/$$s/irqs.out) rtl=$$(cat $(BUILD)/$$s.rtl/irqs.out)"; fail=1; \
	  else echo "PASS: IRQ count $$(cat $(BUILD)/$$s.rtl/irqs.out)"; fi; \
	done; \
	exit $$fail

$(BUILD)/obj_render/Vtb_render: tb/tb_render.sv ../rtl/i4220_render.sv
	$(VERILATOR) --binary --timing -Wall -Wno-UNUSEDSIGNAL --timescale 1ns/1ps \
		--Mdir $(BUILD)/obj_render ../rtl/i4220_render.sv tb/tb_render.sv \
		--top-module tb_render

# real scanline RTL vs oracle on the synthetic scenes
render-verify: $(BUILD)/scenes.stamp $(BUILD)/obj_render/Vtb_render
	@fail=0; \
	for s in $(SCENES); do \
	  echo "=== render $$s ==="; \
	  [ -f $(BUILD)/$$s.oracle.ppm ] || python3 oracle/i4220_oracle.py $(BUILD)/scenes/$$s $(BUILD)/$$s.oracle.ppm; \
	  $(BUILD)/obj_render/Vtb_render +SCENE=$(BUILD)/scenes/$$s \
	      +OUT=$(BUILD)/$$s.render.ppm +GFXSIZE=524288; \
	  python3 diff_ppm.py $(BUILD)/$$s.oracle.ppm $(BUILD)/$$s.render.ppm || fail=1; \
	done; exit $$fail

MAME_FRAMES := 500 900 1500

# real scanline RTL vs real MAME snapshots
mame-verify: $(BUILD)/obj_render/Vtb_render
	@[ -f $(BUILD)/mame/gfxrom.hex ] || python3 -c "import pathlib; \
d=pathlib.Path('$(BUILD)/mame'); \
d.joinpath('gfxrom.hex').write_text('\n'.join('%02x'%b for b in d.joinpath('gfxrom.bin').read_bytes())+'\n')"
	@fail=0; \
	for f in $(MAME_FRAMES); do \
	  echo "=== mame frame $$f ==="; \
	  python3 mame/dump_to_hex.py $(BUILD)/mame/frame_$$f; \
	  ln -sf ../gfxrom.hex $(BUILD)/mame/frame_$$f/gfxrom.hex; \
	  $(BUILD)/obj_render/Vtb_render +SCENE=$(BUILD)/mame/frame_$$f \
	      +OUT=$(BUILD)/mame/frame_$$f/render.ppm +GFXSIZE=4194304; \
	  python3 diff_ppm.py $(BUILD)/mame/frame_$$f/snap.ppm \
	      $(BUILD)/mame/frame_$$f/render.ppm || fail=1; \
	done; exit $$fail

$(BUILD)/obj_vdp/Vtb_vdp: tb/tb_vdp.sv ../rtl/i4220_vdp.sv ../rtl/i4220_render.sv ../rtl/i4220_blitter.sv ../rtl/hd_dpram.sv ../rtl/hd_tdpram.sv
	$(VERILATOR) --binary --timing -Wall -Wno-UNUSEDSIGNAL -Wno-PINCONNECTEMPTY --timescale 1ns/1ps \
		--Mdir $(BUILD)/obj_vdp ../rtl/i4220_render.sv ../rtl/i4220_blitter.sv \
		../rtl/hd_dpram.sv ../rtl/hd_tdpram.sv \
		../rtl/i4220_vdp.sv tb/tb_vdp.sv --top-module tb_vdp

# full VDP top (bus-loaded, free-running timing, scan-out capture) vs MAME
vdp-verify: $(BUILD)/obj_vdp/Vtb_vdp
	@fail=0; \
	for f in $(MAME_FRAMES); do \
	  echo "=== vdp frame $$f ==="; \
	  $(BUILD)/obj_vdp/Vtb_vdp +SCENE=$(BUILD)/mame/frame_$$f \
	      +OUT=$(BUILD)/mame/frame_$$f/vdp.ppm +GFXSIZE=4194304; \
	  python3 diff_ppm.py $(BUILD)/mame/frame_$$f/snap.ppm \
	      $(BUILD)/mame/frame_$$f/vdp.ppm || fail=1; \
	done; exit $$fail

FX68K := ../rtl/vendor/fx68k

# ONE full-system model runs both games (docs/single_rbf.md): Hyper Duel
# by default, Magical Error wo Sagase with +MAGERROR (the runtime game
# select the MRA mod byte drives on hardware). Both sound chips (jt51 and
# IKAOPLL) are always built in. Two pixel dividers are kept as separate
# model dirs so switching never reuses a stale build:
#   build/obj_sys    P_PIXDIV 16 (sim default, legacy Hyper Duel baselines)
#   build/obj_sys12  P_PIXDIV 12 (hardware value; magerror runs use this)
OPLL := ../rtl/vendor/ikaopll
SYS_DEPS := tb/tb_system.sv tb/sdram_model.sv ../rtl/hyprduel_sys.sv ../rtl/hyprduel_sdram.sv ../rtl/i4220_vdp.sv ../rtl/i4220_render.sv ../rtl/i4220_blitter.sv ../rtl/hd_dpram.sv ../rtl/hd_tdpram.sv $(FX68K)/fx68k.sv $(FX68K)/fx68kAlu.sv $(OPLL)/IKAOPLL.v
SYS_SRCS = $(FX68K)/fx68k.sv $(FX68K)/fx68kAlu.sv $(FX68K)/uaddrPla.sv \
		$(wildcard ../rtl/vendor/jt51/hdl/jt51*.v) \
		$(wildcard ../rtl/vendor/jt6295/hdl/*.v) \
		$(OPLL)/IKAOPLL.v $(wildcard $(OPLL)/IKAOPLL_modules/*.v) \
		../rtl/i4220_render.sv ../rtl/i4220_blitter.sv ../rtl/i4220_vdp.sv \
		../rtl/hd_dpram.sv ../rtl/hd_tdpram.sv \
		../rtl/hyprduel_sys.sv ../rtl/hyprduel_sdram.sv tb/sdram_model.sv \
		tb/tb_system.sv

$(BUILD)/obj_sys/Vtb_system: $(SYS_DEPS)
	cp -f $(FX68K)/microrom.mem $(FX68K)/nanorom.mem .
	$(VERILATOR) --binary --timing -Wno-fatal --timescale 1ns/1ps \
		--Mdir $(BUILD)/obj_sys -I../rtl/vendor/jt51/hdl \
		$(SYS_SRCS) --top-module tb_system

$(BUILD)/obj_sys12/Vtb_system: $(SYS_DEPS)
	cp -f $(FX68K)/microrom.mem $(FX68K)/nanorom.mem .
	$(VERILATOR) --binary --timing -Wno-fatal --timescale 1ns/1ps \
		+define+PIXDIV12 \
		--Mdir $(BUILD)/obj_sys12 -I../rtl/vendor/jt51/hdl \
		$(SYS_SRCS) --top-module tb_system

SYSMODEL := $(BUILD)/obj_sys$(if $(PIXDIV12),12)/Vtb_system
SYSMODEL12 := $(BUILD)/obj_sys12/Vtb_system

$(BUILD)/mame/mainrom.hex: ../tools/build_mainrom.py
	python3 ../tools/build_mainrom.py ../roms/hyprduel.zip $@

# full-system boot run (background-friendly): dumps PPMs into build/boot
boot: $(SYSMODEL) $(BUILD)/mame/mainrom.hex
	mkdir -p $(BUILD)/boot$(if $(SDRAM),_sdram)
	$(SYSMODEL) +MAINROM=$(BUILD)/mame/mainrom.hex \
		+GFXROM=$(BUILD)/mame/gfxrom.hex +GFXSIZE=4194304 \
		+OKIROM=$(BUILD)/mame/okirom.hex \
		+OUTDIR=$(BUILD)/boot$(if $(SDRAM),_sdram) \
		+FRAMES=$(or $(FRAMES),240) +DUMPEVERY=30 \
		$(if $(AUDIODUMP),+AUDIODUMP=$(AUDIODUMP)) \
		$(if $(AUDIOSPLIT),+AUDIOSPLIT=$(AUDIOSPLIT)) \
		$(if $(SDRAM),+SDRAM=$(SDRAM)) $(PLUSARGS)

# lockstep attract parity: run MAME + sim, diff screenshots frame by frame
attract-mame:
	DUMP_DIR=$(BUILD)/mame/attract DUMP_EVERY=30 DUMP_TOTAL=$(or $(FRAMES),620) \
	  mame hyprduel -rompath ../roms -video none -sound none -nothrottle \
	  -autoboot_script mame/dump_attract.lua

attract-diff:
	python3 diff_attract.py $(BUILD)/mame/attract $(BUILD)/boot_sdram \
	  --every 30 --max-frame $(or $(FRAMES),620)

$(BUILD)/obj_dl/Vtb_download: tb/tb_download.sv tb/sdram_model.sv ../rtl/hyprduel_sdram.sv
	$(VERILATOR) --binary --timing -Wno-fatal --timescale 1ns/1ps \
		--Mdir $(BUILD)/obj_dl \
		../rtl/hyprduel_sdram.sv tb/sdram_model.sv \
		tb/tb_download.sv --top-module tb_download

download: $(BUILD)/obj_dl/Vtb_download
	$(BUILD)/obj_dl/Vtb_download

.PHONY: download

clean:
	rm -rf $(BUILD)

# magerror branch: IKAOPLL (YM2413) standalone smoke at the
# integration shape (80 MHz clk + fractional 3.579545 MHz cen)
$(BUILD)/obj_opll/Vtb_opll_smoke: tb/tb_opll_smoke.sv ../rtl/vendor/ikaopll/IKAOPLL.v
	$(VERILATOR) --binary --timing -Wno-UNUSEDSIGNAL -Wno-WIDTHEXPAND \
		-Wno-WIDTHTRUNC --timescale 1ns/1ps --Mdir $(BUILD)/obj_opll \
		../rtl/vendor/ikaopll/IKAOPLL.v ../rtl/vendor/ikaopll/IKAOPLL_modules/*.v \
		tb/tb_opll_smoke.sv --top-module tb_opll_smoke

.PHONY: opll-smoke
opll-smoke: $(BUILD)/obj_opll/Vtb_opll_smoke
	$(BUILD)/obj_opll/Vtb_opll_smoke | grep OPLL

# magerror ROM images from ../roms/magerror.zip (local, gitignored)
$(BUILD)/magerror_mainrom.hex: ../tools/build_mainrom.py
	python3 ../tools/build_mainrom.py ../roms/magerror.zip $@
$(BUILD)/magerror_gfxrom.hex: ../tools/build_gfxrom_magerror.py
	python3 ../tools/build_gfxrom_magerror.py ../roms/magerror.zip $(BUILD)/magerror_gfxrom.bin
	python3 -c "import pathlib; b=pathlib.Path('$(BUILD)/magerror_gfxrom.bin').read_bytes(); \
pathlib.Path('$@').write_text('\n'.join('%02x'%x for x in b)+'\n')"
$(BUILD)/magerror_okirom.hex:
	python3 -c "import zipfile, pathlib; b=zipfile.ZipFile('../roms/magerror.zip').read('97.u97'); \
pathlib.Path('$@').write_text('\n'.join('%02x'%x for x in b)+'\n')"

.PHONY: boot-magerror
# same model as `boot`, run as magerror; always the hardware pixel divider
boot-magerror: $(SYSMODEL12) $(BUILD)/magerror_mainrom.hex $(BUILD)/magerror_gfxrom.hex $(BUILD)/magerror_okirom.hex
	mkdir -p $(BUILD)/boot_magerror$(if $(SDRAM),_sdram)
	$(SYSMODEL12) +MAGERROR +MAINROM=$(BUILD)/magerror_mainrom.hex \
		+GFXROM=$(BUILD)/magerror_gfxrom.hex +GFXSIZE=4194304 \
		+OKIROM=$(BUILD)/magerror_okirom.hex \
		+OUTDIR=$(BUILD)/boot_magerror$(if $(SDRAM),_sdram) \
		+FRAMES=$(or $(FRAMES),600) +DUMPEVERY=30 \
		$(if $(AUDIODUMP),+AUDIODUMP=$(AUDIODUMP)) \
		$(if $(AUDIOSPLIT),+AUDIOSPLIT=$(AUDIOSPLIT)) \
		$(if $(SDRAM),+SDRAM=$(SDRAM)) $(PLUSARGS)

# magerror YM2413 write-path audit on a synthetic sub-CPU program (no
# game ROM needed): counts CPU writes to 0x800000-3 vs writes IKAOPLL
# accepts. docs/magerror_audio_fix.md
YMT := $(BUILD)/ymtest
$(YMT)/ymtest.bin: ymtest/ymtest.s
	mkdir -p $(YMT)
	m68k-elf-as -m68000 -o $(YMT)/ymtest.o ymtest/ymtest.s
	m68k-elf-ld -Ttext=0 -e _start -o $(YMT)/ymtest.elf $(YMT)/ymtest.o
	m68k-elf-objcopy -O binary $(YMT)/ymtest.elf $@

.PHONY: ymtest
ymtest: $(SYSMODEL12) $(YMT)/ymtest.bin
	python3 ymtest/mkhex.py $(YMT)/ymtest.bin $(YMT)/main.hex $(YMT)/gfx.hex
	$(SYSMODEL12) +MAGERROR +MAINROM=$(YMT)/main.hex \
		+GFXROM=$(YMT)/gfx.hex +GFXSIZE=4194304 +OUTDIR=$(YMT) \
		+FRAMES=$(or $(FRAMES),20) +DUMPEVERY=1000 \
		+YMLOG=$(YMT)/ymlog.txt +AUDIOSPLIT=$(YMT)/aud \
		+AUDIODUMP=$(YMT)/mix.raw +OPLLDUMP=$(YMT)/opll.raw $(PLUSARGS) | grep -E "YMAUDIT|frames simulated"
	python3 ymtest/ymcheck.py $(YMT)/ymlog.txt
