MOD_DIR ?= ..

INCLUDE_DIRS = papermario/include papermario/include/PR
TOOLS_DIR    = papermario/tools
SRC_DIRS     = $(MOD_DIR)/global/patch

CC = $(TOOLS_DIR)/cc1

CPPFLAGS = $(foreach dir,$(INCLUDE_DIRS),-I$(dir)) -D _LANGUAGE_C -ffreestanding -DF3DEX_GBI_2
CFLAGS   = -O2 -quiet -G 0 -mcpu=vr4300 -mfix4300 -mips3 -mgp32 -mfp32

C_FILES = $(foreach dir,$(SRC_DIRS),$(wildcard $(dir)/*.c))
PATCH_FILES=$(C_FILES:.c=.patch)

all: $(PATCH_FILES)

$(MOD_DIR)/%.patch: $(MOD_DIR)/%.c
	cpp $(CPPFLAGS) $(MOD_DIR)/$< | $(CC) $(CFLAGS) -o - | python3 asm-to-patch.py > $(MOD_DIR)/$@

submodules:
	# note: no --recursive, we don't n64splat etc
	git submodule update --init

setup: submodules
	./papermario/install.sh --extra

.PHONY: setup submodules
