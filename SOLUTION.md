# Solution Procedure

## Pipeline Overview

```
nix develop          Enter the Nix dev shell
     │
make setup           Fetch submodule + PDK (one-time)
     │
make extract         GDS → SPICE netlist  (Magic)                ┐
     │                                                           │
make netlist         SPICE → Verilog      (spice_to_verilog.py)  ├─ make all
     │                                                           │
make solve           SAT solve            (Yosys)                │
     │                                                           │
make verify          Confirm solution     (cocotb)               ┘
```

## Prerequisites

This project uses a Nix flake to manage its toolchain. You need **Nix** installed with **flakes enabled**. If you don't have Nix yet, look up how to install Nix and enable the `nix-command` and `flakes` experimental features.

After cloning the repository, enter the Nix shell and run `make setup` to initialize the submodule and fetch the PDK:

```bash
nix develop
make setup
```

This pulls the `sky130_fd_sc_hd` standard cell library into `libs/` (so you can browse the Verilog cell definitions locally) and fetches the full SKY130 PDK into `.ciel/` via ciel.

## Step 1: Set Up the Dev Environment

Enter the Nix development shell to get all the required tools:

```bash
nix develop
```

This provisions the following toolchain:

| Category | Tools |
|---|---|
| GDS viewing & layout exploration | KLayout, Magic |
| Synthesis & netlist analysis | Yosys, xdot |
| Simulation | Icarus Verilog, Verilator |
| Waveform viewing | GTKWave |
| LVS / netlist comparison | Netgen |
| PDK management | pdk-ciel |
| Python (3.13) | gdstk, pyvcd, numpy, cocotb |

The shell also configures environment variables for the SkyWater SKY130 PDK. If you haven't run `make setup` yet (see [Prerequisites](#prerequisites)), do that first — it fetches the PDK into `.ciel/` inside the project directory so everything can be cleaned up by deleting the repo.

> **Want to skip ahead?** If you just want to run the full pipeline without walking through each step, see [Makefile](#makefile) at the bottom.

## Step 2: Extract a SPICE Netlist from the GDS

Use Magic to extract a SPICE netlist from the puzzle layout:

```bash
bash scripts/run_extract.sh puzzle.gds puzzle
```

- `puzzle.gds` — the GDS file to extract
- `puzzle` — the name of the top-level cell

**Why ciel is required:** Magic needs a process technology file (`sky130A.tech`) to understand the GDS layer stack and perform extraction. This file is not included in the `sky130_fd_sc_hd` cell library — it is only available through the full SKY130 PDK, which is built by `open_pdks`. Ciel (formerly volare) is a version manager that downloads pre-built PDK releases, avoiding the need to build `open_pdks` from source. The extraction script uses the tech file from `.ciel/sky130A/libs.tech/magic/`.

The following warnings are known and do not impact the output:

```
Error while reading cell "INTERNAL_7" (byte position 120): Unknown layer/datatype in boundary, layer=200 type=0
Error while reading cell "INTERNAL_3" (byte position 230): Unknown layer/datatype in boundary, layer=200 type=0
```

These occur because the GDS contains layers that Magic doesn't recognize (layer 200), but they are not part of the actual circuit geometry.

The extracted netlist will be written to the `outputs/` directory.

## Step 3: Convert the SPICE Netlist to Gate-Level Verilog

Convert the extracted SPICE netlist into a simulatable Verilog netlist:

```bash
python scripts/spice_to_verilog.py
```

This reads `outputs/puzzle.spice` by default and writes `outputs/puzzle_netlist.v`. You can also specify a different input or output:

```bash
python scripts/spice_to_verilog.py path/to/other.spice -o path/to/output.v
```

The script:
- Parses `.subckt` definitions and instance lines from the SPICE netlist
- Filters out power pins (`VGND`, `VNB`, `VPB`, `VPWR`) and non-logic cells (`decap`, `diode`)
- Converts `conb` (constant) cells into `assign` statements
- Emits a structural Verilog module with named port connections

The output netlist references `sky130_fd_sc_hd` cells by their full names (e.g. `sky130_fd_sc_hd__nor4_2`). To simulate it, you need the cell definitions — see Step 4.

## Step 4: Simulate with cocotb

Run the cocotb test suite from the `tests/` directory:

```bash
cd tests && make
```

The test suite (`test_puzzle.py`) includes three cases:
- **test_121_zeros** — feeds 121 zero bits, expects output `EMPTY SKY`
- **test_vcd_run0** — replays the first input sequence from `example_inputs.vcd`, expects `TRY AGAIN`
- **test_vcd_run1** — replays the second input sequence from `example_inputs.vcd`, expects `TRY AGAIN`

### Behavioral cell models

The SKY130 library's functional Verilog uses Verilog UDP primitives for sequential cells and muxes. UDPs work in Icarus Verilog but not in Yosys. To use the same cell definitions across both tools, `support/sky130_ff_models.v` provides pure behavioral (`always`/`assign`) replacements for the four affected cells: `dfrtp_2`, `dfstp_2`, `dfxtp_2`, and `mux2_1`. All other cells in the netlist are combinational and use only built-in Verilog primitives, so they work everywhere without modification.

## Step 5: Solve with Yosys SAT

Run the SAT solver to find the 121-bit input that makes `success=1`:

```bash
bash scripts/run_sat_solve.sh
```

This wrapper script generates the Yosys SAT script, runs the solver (with live output), and extracts the solution — all in one command. The log is saved to `logs/yosys_solve.log` and the solution is written to `outputs/solution.txt`.

You can also pass flags through to the generator:

```bash
bash scripts/run_sat_solve.sh --validate   # all-zero input, assert first byte = 'E'
bash scripts/run_sat_solve.sh --sim         # all-zero input, no assertions (skip extraction)
```

The generated script uses `clk2fflogic` to convert flip-flops into combinational edge-detection logic, then runs `sat -seq` over 270 SAT steps (2 per clock cycle — one for clk=0 setup, one for the clk=1 posedge). The input phase covers 121 bits: bit 0 is always 0, bits 1-120 are free in solve mode.

## Step 6: Verify the Solution

Run the solution through cocotb to confirm the output and `success` signal:

```bash
cd tests && make MODULE=test_success
```

This reads the 121-bit solution from `outputs/solution.txt` (written by Step 5) and feeds it into the puzzle, logging the output bytes and `success` flag for 15 cycles.

## Makefile

Steps 2–6 are wrapped in a top-level `Makefile` with dependency tracking. After entering the Nix shell (Step 1), you can run the entire pipeline with:

```bash
make          # runs: extract → netlist → solve → verify
```

Or run individual steps:

```bash
make setup    # fetch submodule + PDK (one-time)
make extract  # Step 2: GDS → SPICE netlist
make netlist  # Step 3: SPICE → Verilog
make test     # Step 4: cocotb simulation tests
make solve    # Step 5: Yosys SAT solver
make verify   # Step 6: verify the solution
make clean    # remove all generated outputs
```

Each target tracks file dependencies, so `make solve` will automatically run `extract` and `netlist` first if their outputs don't exist yet. If an output already exists and its inputs haven't changed, Make skips the step. To force a re-run, use `make -B <target>`.
