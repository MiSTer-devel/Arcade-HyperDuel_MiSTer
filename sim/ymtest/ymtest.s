| Synthetic magerror-map stimulus for the YM2413 write-path test
| (docs/magerror_audio_fix.md). No game ROM needed.
|
| Main CPU: copies the sub program to shared1 (0xC00000), releases the
| sub CPU (write 0x00 to the sub control latch at 0x400000), then idles.
| Sub CPU: boots from the shared1 vector shadow, writes a YM2413 register
| sequence to 0x800000 (address port, A0=0) / 0x800002 (data port, A0=1):
|   phase A: spec-compliant spacing (software waits after every write)
|   phase B: back-to-back writes with NO software wait (stress / guard)
|   phase C: re-key three melodic channels with spacing, then idle
| The testbench counts CPU-side port writes vs writes IKAOPLL accepts.

        .text
        .globl  _start
_start:
        .long   0x00FE3F00              | main SSP (shared2 BRAM)
        .long   main_entry              | main PC
        .fill   62,4,0x00000100         | other vectors -> harmless

        .org    0x100
main_entry:
        move.w  #0x2700,%sr
        lea     sub_image,%a0
        lea     0x00C00000,%a1
        move.w  #((sub_image_end-sub_image)/2)-1,%d0
1:      move.w  (%a0)+,(%a1)+
        dbra    %d0,1b
        move.w  #0x0000,0x00400000      | release sub CPU
2:      bra.s   2b

        .balign 2
| ---- sub CPU image: position-independent, runs at sub address 0 ----
sub_image:
        .long   0x00FE3E00              | sub SSP
        .long   sub_entry-sub_image     | sub PC (offset in image)
        .fill   62,4,0x00000100

        .org    sub_image+0x100
sub_entry:
        move.w  #0x2700,%sr
        | ---------------- phase A: spaced writes ----------------
        lea     seq_a-sub_image,%a0
        move.w  #((seq_a_end-seq_a)/2)-1,%d7
3:      move.b  (%a0)+,0x00800001       | address port
        move.w  #20,%d1
4:      dbra    %d1,4b                  | ~5 us address wait
        move.b  (%a0)+,0x00800003       | data port
        move.w  #120,%d1
5:      dbra    %d1,5b                  | ~30 us data wait
        dbra    %d7,3b
        | ---------------- phase B: back-to-back ------------------
        lea     seq_b-sub_image,%a0
        move.w  #((seq_b_end-seq_b)/2)-1,%d7
6:      move.b  (%a0)+,0x00800001
        move.b  (%a0)+,0x00800003
        dbra    %d7,6b
        | long pause so phase B notes sound
        move.w  #3,%d2
7:      move.w  #0xFFFF,%d1
8:      dbra    %d1,8b
        dbra    %d2,7b
        | ---------------- phase C: spaced re-key -----------------
        lea     seq_c-sub_image,%a0
        move.w  #((seq_c_end-seq_c)/2)-1,%d7
9:      move.b  (%a0)+,0x00800001
        move.w  #20,%d1
10:     dbra    %d1,10b
        move.b  (%a0)+,0x00800003
        move.w  #120,%d1
11:     dbra    %d1,11b
        dbra    %d7,9b
idle_trap:
12:     bra.s   12b

| (reg, value) pairs
seq_a:
        .byte   0x0E,0x00               | rhythm off
        .byte   0x30,0x10               | ch0 inst 1 (violin) vol 0
        .byte   0x31,0x30               | ch1 inst 3 (piano)  vol 0
        .byte   0x32,0x50               | ch2 inst 5 (flute)  vol 0
        .byte   0x10,0xAD               | ch0 fnum lo
        .byte   0x11,0x6C               | ch1 fnum lo
        .byte   0x12,0x20               | ch2 fnum lo
        .byte   0x20,0x19               | ch0 key on, block 4, fnum8
        .byte   0x21,0x19               | ch1 key on, block 4, fnum8
        .byte   0x22,0x1B               | ch2 key on, block 5, fnum8
seq_a_end:
seq_b:
        .byte   0x33,0x70               | ch3 inst 7 (trumpet) vol 0
        .byte   0x13,0x57
        .byte   0x23,0x19               | ch3 key on
        .byte   0x34,0x20               | ch4 inst 2 (guitar) vol 0
        .byte   0x14,0xC3
        .byte   0x24,0x17               | ch4 key on block 3
seq_b_end:
seq_c:
        .byte   0x20,0x09               | ch0 key off
        .byte   0x21,0x09               | ch1 key off
        .byte   0x22,0x0B               | ch2 key off
        .byte   0x10,0x6C
        .byte   0x20,0x1B               | ch0 key on, different pitch
seq_c_end:
        .balign 2
sub_image_end:
