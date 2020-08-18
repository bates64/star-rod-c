import sys
import re
import os

# opts
INDENT = os.environ.get("INDENT") or "\t"
PRINT_ORIGINAL_ASM = False

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
    "$30": "S8",
    "$31": "RA",
}
for i in range(0, 32):
    REGISTERS[f"$f{i}"] = f"F{i}"

def eprint(message):
    print(message, file=sys.stderr)

# state
globls = []
in_function = False
label = None
values = {}
reorder_delay_slot = True

after_fn_buffer = ""
def print_after_fn(text):
    if in_function:
        after_fn_buffer += text + "\n"
    else:
        print(text)

for line in sys.stdin.readlines():
    line = re.sub(r"#.*$", '', line.strip()).strip()

    if len(line) == 0:
        continue

    if match := re.match(r"^.globl\s*(.*)", line): # .globl
        globls.append(match.group(1))
    elif re.match(r"^.set\s*noreorder", line): # .set noreorder
        reorder_delay_slot = False
    elif re.match(r"^.set\s*reorder", line): # .set reorder
        reorder_delay_slot = True
    elif re.match(r"^.end\s", line): # .end
        if in_function:
            print("}\n")
            in_function = False

            if len(after_fn_buffer) > 0:
                print(after_fn_buffer, end=None)
                after_fn_buffer = ""
        else:
            error("warning: found end of function but not in one")
    elif match := re.match(r"^.ascii\s*(.*)", line): # .ascii
        # star rod inserts null terminator
        s = match.group(1)[1:-5]
        print_after_fn(f'#new:ASCII {label} {{ "{s}" }}\n')
    elif re.match(r"^\.[a-z]", line): # .*
        continue
    elif match := re.match(r"^(.*):$", line): # label:
        label = match.group(1)

        if label in globls:
            if in_function:
                eprint(f"warning: found function {label} within another function")
                continue
            in_function = True

            values[label] = f"${label}"
            print(f"#new:Function ${label} {{")

            if label[0] != "_":
                after_fn_buffer += f"#export ${label}\n"
        elif in_function:
            print(f"{INDENT}.{label[1:]}")
    elif in_function: # asm
        mnemonic, args = line.split(None, 1)

        if mnemonic == "li": mnemonic = "LIO" # TODO(Star Rod 0.4.0): remove this
        if mnemonic == "la": mnemonic = "LIA" # "
        if mnemonic == "li.s": mnemonic = "LIF" # "
        if mnemonic == "li.w": mnemonic = "LIF" # "
        if mnemonic == "move": mnemonic = "COPY"
        mnemonic = mnemonic.upper()

        match = re.match(r"^([^,]+)(?:,([^(,]+))?(?:[(,]([^)]+)\)?)?$", args)
        if not match:
            eprint("error: unable to parse asm:")
            eprint(line)
            exit(1)
        
        if PRINT_ORIGINAL_ASM:
            print(f"{INDENT}% {line}")

        has_register = False
        replaced = False
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
                # hex
                text = re.sub(r"^0x[0-9a-fA-F]+$", lambda m: f"{int(m[0], 16):X}", text)

                # dec
                text = re.sub(r"^([0-9]+)$", r"\1`", text)

                # float
                text = re.sub(r"^([0-9]+\.[0-9e]+)", lambda m: f"{float(m[0]):f}", text)

                # label ($LX -> .LX)
                text = re.sub(r"^\$(L[0-9]+)$", r".\1", text)

            if text != old_text:
                # replace match with updated text
                start, end = match.span(i)
                args = args[:start + offset] + text + args[end + offset:]
                offset += len(text) - len(old_text)
                replaced = True

        if mnemonic == "J" and has_register:
            mnemonic = "JR"
        
        if mnemonic == "JAL" and not replaced:
            args = f"~Func:{args}"

        print(f"{INDENT}{mnemonic:<7} {args}")

        if reorder_delay_slot and (mnemonic[0] == "J" or mnemonic[0] == "B"):
            print(f"{INDENT}NOP")
