# options (use env variables)
TARGET = papermario
ifndef MOD_DIR
MOD_DIR = .
endif

INCLUDE_DIRS = decomp/include decomp/include/PR
TOOLS_DIR    = decomp/tools
SRC_DIRS     = $(MOD_DIR)/global/patch

ifndef STARROD
STARROD = cd .. && java -jar -mx2G StarRod.jar
endif
CC = $(TOOLS_DIR)/cc1

CPPFLAGS = $(foreach dir,$(INCLUDE_DIRS),-I$(dir)) -D _LANGUAGE_C -ffreestanding -DF3DEX_GBI_2
CFLAGS   = -O2 -quiet -G 0 -mcpu=vr4300 -mfix4300 -mips3 -mgp32 -mfp32

C_FILES = $(foreach dir,$(SRC_DIRS),$(wildcard $(dir)/*.c))
PATCH_FILES=$(C_FILES:.c=.patch)

all: $(PATCH_FILES)

$(MOD_DIR)/%.patch: $(MOD_DIR)/%.c
	cpp $(CPPFLAGS) $(MOD_DIR)/$< | $(CC) $(CFLAGS) -o - | python3 asm-to-patch.py > $(MOD_DIR)/$@

submodules:
	git submodule update --init --recursive

setup: submodules
	./decomp/install.sh --extra

.PHONY: setup submodules

$(MOD_DIR)/$(TARGET).z64:
	$(STARROD) -CompileMod