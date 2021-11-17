import sys
import re
import os

# opts
INDENT = os.environ.get("INDENT") or "\t"
PRETTY_SPACE_ARGS = True

IS_GLOBAL_PATCH = "globals/patch/" in sys.argv[1]

REGISTERS = {
    "$0": "R0",
    "$1": "AT",
    "$2": "V0",
    "$3": "V1",
    "$4": "A0",
    "$5": "A1",
    "$6": "A2",
    "$7": "A3",
    "$8": "T0",
    "$9": "T1",
    "$10": "T2",
    "$11": "T3",
    "$12": "T4",
    "$13": "T5",
    "$14": "T6",
    "$15": "T7",
    "$16": "S0",
    "$17": "S1",
    "$18": "S2",
    "$19": "S3",
    "$20": "S4",
    "$21": "S5",
    "$22": "S6",
    "$23": "S7",
    "$24": "T8",
    "$25": "T9",
    "$26": "K0",
    "$27": "K1",
    "$28": "GP",
    "$29": "SP", "$sp": "SP",
    "$30": "S8", "$fp": "S8",
    "$31": "RA",
}
for i in range(0, 32):
    REGISTERS[f"$f{i}"] = f"F{i}"

LOAD_STORES = [
    "SB", "SBU", "LB", "LBU",
    "SH", "SHU", "LH", "LHU",
    "SW", "SHU", "LW", "LWU",
    "SF",        "LF",
    "SD",        "LD",
]

GLOBAL_SYMBOLS = {}
with open("papermario/ver/us/symbol_addrs.txt", "r") as f:
    for line in f.readlines():
        if match := re.match(r"^(\w+)\s*=\s*0x([0-9a-fA-F]+);", line): # .globl
            symbol = match[1]
            address = int(match[2], 16)
            GLOBAL_SYMBOLS[symbol] = address

def eprint(message):
    print(message, file=sys.stderr)

# state
globls = []
in_function = False
function_directive_written = False
label = None
values = {}
reorder_delay_slot = True

after_fn_buffer = ""
def print_after_fn(text):
    global after_fn_buffer
    if in_function:
        after_fn_buffer += text + "\n"
    else:
        print(text)
def end_function():
    global in_function, function_directive_written, after_fn_buffer
    if in_function and function_directive_written:
        print("}")
        in_function = False

    if len(after_fn_buffer) > 0:
        print(after_fn_buffer, end=None)
        after_fn_buffer = ""

for line in sys.stdin.readlines():
    line = re.sub(r"#.*$", '', line.strip()).strip()
    if len(line) == 0:
        continue

    if match := re.match(r"^.globl\s*(.*)", line): # .globl
        end_function()
        globls.append(match.group(1))
    elif re.match(r"^.set\s*noreorder", line): # .set noreorder
        reorder_delay_slot = False
    elif re.match(r"^.set\s*reorder", line): # .set reorder
        reorder_delay_slot = True
    elif re.match(r"^.end\s", line): # .end
        end_function()
    elif match := re.match(r"^.ascii\s*(.*)", line): # .ascii
        # star rod inserts null terminator
        s = match.group(1)[1:-5]
        print_after_fn(f'\n#new:ASCII {label} {{ "{s}" }}')
    elif match := re.match(r"^.(byte|half|word)\s*(.*)", line): # .word, .byte, etc
        # TODO: .word 0,1,2
        word = eval(match[2])
        print(f'#new:{"Data" if IS_GLOBAL_PATCH else "IntTable"} ${label} {{ {word:X} }}')
    elif match := re.match(r"^.frame", line): # .frame
        # only to detect a function
        if not function_directive_written:
            print(f"#export:Function ${label} {{")
            function_directive_written = True
    elif re.match(r"^\.[a-z]", line): # .*
        continue
    elif match := re.match(r"^(.*):$", line): # label:
        label = match.group(1)

        if label in globls:
            if in_function and function_directive_written:
                eprint(f"warning: found function {label} within another function")
                continue
            in_function = True

            values[label] = f"${label}"
            function_directive_written = False

            #if label[0] != "_" and IS_GLOBAL_PATCH:
            #    after_fn_buffer += f"#export ${label}"
        elif in_function and function_directive_written:
            print(f"{INDENT}.{label[1:]}")
    elif in_function: # asm
        if not function_directive_written:
            print(f"#export:Function ${label} {{")
            function_directive_written = True

        line_parts = line.split(None, 1)
        mnemonic = line_parts[0].upper()
        args = line_parts[1] if len(line_parts) > 1 else ""

        has_register = False
        has_immediate = False
        replaced = False
        if args:
            match = re.match(r"^([^,]+)(?:,([^(,]+))?(?:[(,]([^)]+)\)?)?$", args)
            if not match:
                eprint("error: unable to parse asm:")
                eprint(line)
                exit(1)

            offset = 0
            for i in range(1, 4):
                text = match.group(i)
                if not text:
                    break
                old_text = text

                if text in values:
                    text = values[text]
                elif text in REGISTERS:
                    text = REGISTERS[text]
                    has_register = True
                else:
                    # dec (dec -> hex, dec if operand 3)
                    text = re.sub(r"^(-?[0-9]+)$", lambda m: f"{int(m[0]):X}" if i < 3 else f"{int(m[0])}`", text)

                    # hex (0xabc -> ABC)
                    text = re.sub(r"^-?0x[0-9a-fA-F]+$", lambda m: f"{int(m[0], 16):X}", text)

                    # float
                    text = re.sub(r"^(-?[0-9]+\.[0-9e-]+)", lambda m: f"{float(m[0]):f}", text)

                    # label ($LX -> .LX)
                    text = re.sub(r"^\$(L[0-9]+)$", r".\1", text)

                    if text != old_text:
                        has_immediate = True

                    # global symbol (symbol+offset -> address)
                    def handle_symbol(m):
                        if m[1] in GLOBAL_SYMBOLS:
                            address = GLOBAL_SYMBOLS[m[1]]
                            offset = int(m[3]) if m[2] else 0
                            return f"{address + offset:X}"
                        return m[0]
                    text = re.sub(r"^(\w+)(\+([0-9]+))?$", handle_symbol, text)

                if text != old_text:
                    # replace match with updated text
                    start, end = match.span(i)
                    args = args[:start + offset] + text + args[end + offset:]
                    offset += len(text) - len(old_text)
                    replaced = True

        if mnemonic == "MOVE":
            mnemonic = "COPY"

        # TODO(Star Rod 0.4.0): add option not to perform LI transformations
        if mnemonic == "LI":
            mnemonic = "LIO"
            if m := re.search(r",(-?[0-9A-F]+)", args):
                if (int(m[1], 16) & 0xFFFF0000) == 0:
                    # halfword-sized
                    mnemonic = "ORI"
                    args = re.sub(r",", ",R0,", args)
        if mnemonic == "LA":
            mnemonic = "LIA"
            if m := re.search(r",(-?[0-9A-F]+)", args):
                if (int(m[1], 16) & 0xFFFF0000) == 0:
                    # halfword-sized
                    mnemonic = "ADDIU"
                    args = re.sub(r",", ",R0,", args)

        if mnemonic == "LI.S": mnemonic = "LIF"
        if mnemonic == "LI.D": mnemonic = "LIF"

        if mnemonic == "L.S": mnemonic = "LWC1" if "(" in args else "LAF"
        if mnemonic == "L.D": mnemonic = "LDC1" if "(" in args else "LAF"
        if mnemonic == "S.S": mnemonic = "SWC1" if "(" in args else "SAF"
        if mnemonic == "S.D": mnemonic = "SDC1" if "(" in args else "SAF"

        if mnemonic == "J" and has_register:
            mnemonic = "JR"

        if mnemonic == "J" and "." in args:
            # star rod limitation
            mnemonic = "BEQ"
            args = f"R0,R0,{args}"

        if mnemonic == "JAL":
            if not replaced:
                args = f"~Func:{args}"
            elif m := re.match(r"(..),(..)$", args):
                mnemonic = "JALR"
                args = f"{m[2]},{m[1]}"

        if (mnemonic in LOAD_STORES) and not "(" in args:
            mnemonic = mnemonic[0] + "A" + mnemonic[1]

        # immediate instruction variants
        if has_immediate:
            if mnemonic == "ADD": mnemonic = "ADDI"
            elif mnemonic == "ADDU": mnemonic = "ADDIU"

            elif mnemonic == "SUBU":
                args = re.sub(r",([0-9A-F]+)", lambda m: f",-{m[1]}", args)
                mnemonic = "ADDIU"

            elif mnemonic == "SLT": mnemonic = "SLTI"
            elif mnemonic == "SLTU": mnemonic = "SLTIU"

        if PRETTY_SPACE_ARGS:
            args = args.replace(",", ", ")
            args = args.replace("(", " (")

        if args:
            print(f"{INDENT}{mnemonic:<9} {args}")
        else:
            print(f"{INDENT}{mnemonic}")

        if reorder_delay_slot and (mnemonic[0] == "J" or mnemonic[0] == "B"):
            print(f"{INDENT}NOP")
