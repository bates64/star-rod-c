# Star Rod C

Star Rod C is a tool that lets you compile C code to patch files using tools and headers from the [Paper Mario decompilation](https://github.com/ethteck/papermario). [Star Rod](https://github.com/nanaian/star-rod) is used as the assembler and linker.

Currently supports Linux (Ubuntu, Arch) only, but the output is portable. You can also use WSL2 or a Linux VM.

### Installation

You'll need:
* A [Star Rod](https://github.com/nanaian/star-rod) mod folder
* git

`cd` to your mod folder and run the following commands:
```sh
$ git init
$ git submodule add https://github.com/nanaian/star-rod-c.git
$ git submodule add https://github.com/pmret/papermario.git
$ make -C star-rod-c setup
```

### Usage

Create a `globals/patch/foo.c` file in your mod folder:

```c
#include "common.h"

ApiStatus ExampleFunction(ScriptInstance* script, s32 isInitialCall) {
    // Increment *Var[0] by 10
    script->varTable[0] += 10;

    return ApiStatus_DONE2;
}
```

Run Star Rod C: `make -C star-rod-c`

This should produce a `globals/patch/foo.patch` file. All functions are `#export`ed unless their name begins with `_`.

You can then use the global patch as usual, in any script. For example:
```starrod
% kmr_20.mpat

#new:Script {
    Set *Var[0] 5
    Call $ExampleFunction ()

    % *Var[0] == 15`

    Return
    End
}
```

Running `make -C star-rod-c` will compile all `globals/patch/*.c` files to a `*.patch` file in the same directory. `make` won't recompile files that haven't been modified since the last time it was run.

### Known issues

* You may not name a function `main`.
