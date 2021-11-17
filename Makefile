MOD_DIR ?= ..

CPP    = cpp-11
PYTHON = python3

###

INCLUDE_DIRS = papermario/include papermario/include/PR
TOOLS_DIR    = papermario/tools
SRC_DIRS     = $(MOD_DIR)/globals/patch $(MOD_DIR)/map $(MOD_DIR)/battle

CPPFLAGS = $(foreach dir,$(INCLUDE_DIRS),-I$(dir)) -D _LANGUAGE_C -ffreestanding -DF3DEX_GBI_2
CFLAGS   = -O2 -quiet -G 0 -mcpu=vr4300 -mfix4300 -mips3 -mgp32 -mfp32

C_FILES     = $(foreach dir,$(SRC_DIRS),$(shell find $(dir) -type f -name '*.c'))
PATCH_FILES = $(C_FILES:.c=.patch)

all: $(PATCH_FILES)

%.i: %.c
	bash -o pipefail -c ' \
		$(CPP) -w -Ipapermario/ver/us/build/include -Ipapermario/include -Ipapermario/src -Ipapermario/assets/us -D_LANGUAGE_C -D_FINALROM -DVERSION=us -DF3DEX_GBI_2 -D_MIPS_SZLONG=32 -nostdinc -DKMC_ASM -DVERSION_US $< -o - \
		| papermario/tools/iconv.py UTF-8 SHIFT-JIS > $@'

%.s: %.i
	papermario/tools/build/cc/gcc/gcc -c -G0 -O2 -fno-common -B papermario/tools/build/cc/gcc/  -Wuninitialized -Wmissing-braces -Wimplicit -fforce-addr -S $< -o $@

%.patch: %.s asm-to-patch.py
	bash -o pipefail -c 'cat $< | $(PYTHON) asm-to-patch.py $< > $@'

submodules:
	# note: no --recursive, we don't need n64splat etc
	git submodule update --init

setup: submodules
	cd papermario && ./install.sh

.PHONY: setup submodules
