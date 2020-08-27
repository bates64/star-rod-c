MOD_DIR ?= ..

INCLUDE_DIRS = papermario/include papermario/include/PR
TOOLS_DIR    = papermario/tools
SRC_DIRS     = $(MOD_DIR)/globals/patch $(MOD_DIR)/map $(MOD_DIR)/battle

CC     = $(TOOLS_DIR)/cc1
PYTHON = python3.8

CPPFLAGS = $(foreach dir,$(INCLUDE_DIRS),-I$(dir)) -D _LANGUAGE_C -ffreestanding -DF3DEX_GBI_2
CFLAGS   = -O2 -quiet -G 0 -mcpu=vr4300 -mfix4300 -mips3 -mgp32 -mfp32

C_FILES     = $(foreach dir,$(SRC_DIRS),$(shell find $(dir) -type f -name '*.c'))
PATCH_FILES = $(C_FILES:.c=.patch)

all: $(PATCH_FILES)

%.patch: %.c asm-to-patch.py
	cpp $(CPPFLAGS) $< | $(CC) $(CFLAGS) -o - | $(PYTHON) asm-to-patch.py $< > $@

submodules:
	# note: no --recursive, we don't need n64splat etc
	git submodule update --init

setup: submodules
	./papermario/install.sh --extra

.PHONY: setup submodules
