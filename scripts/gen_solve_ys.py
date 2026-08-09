#!/usr/bin/env python3
"""Generate a Yosys script to solve the puzzle using SAT.

Usage:
    python3 scripts/gen_solve_ys.py [--validate | --sim]

Modes:
    solve (default): free 120 input bits, assert success=1
    --validate:      all-zero input, assert first output byte = 'E' (0x45)
    --sim:           all-zero input, no output assertions (just show outputs)

Key insight: clk2fflogic converts FFs into edge-detection logic that checks
clk vs $past(clk). We MUST toggle clk in the SAT constraints, which means
2 SAT steps per real clock cycle (clk=0 then clk=1 = posedge).
"""

import glob
import re
import os
import sys

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(PROJECT, "libs", "sky130_fd_sc_hd")

validate_mode = "--validate" in sys.argv
sim_mode = "--sim" in sys.argv
success_step = None
for arg in sys.argv[1:]:
    if arg.startswith("--success-at="):
        success_step = int(arg.split("=")[1])

with open(os.path.join(PROJECT, "outputs", "puzzle_netlist.v")) as f:
    netlist = f.read()

cell_types = set(re.findall(r'(sky130_fd_sc_hd__\S+)\s+\w+\s*\(', netlist))
skip_cells = {'sky130_fd_sc_hd__dfrtp_2', 'sky130_fd_sc_hd__dfstp_2',
              'sky130_fd_sc_hd__dfxtp_2', 'sky130_fd_sc_hd__mux2_1'}

func_files = []
for ct in sorted(cell_types - skip_cells):
    base = re.sub(r'^sky130_fd_sc_hd__', '', ct)
    base_no_drive = re.sub(r'_\d+$', '', base)
    pattern = os.path.join(LIB, "cells", base_no_drive, f"{ct}.functional.v")
    matches = glob.glob(pattern)
    if matches:
        func_files.append(matches[0])

# Real clock cycles (matching cocotb test):
#   cycle 1-3:     reset (rst_n=0, enable=0, I=0)
#   cycle 4:       release reset (rst_n=1, enable=0, I=0)
#   cycle 5:       enable activation (rst_n=1, enable=1, I=0)
#   cycle 6-125:   120 input bits (rst_n=1, enable=1, I=free/zero)
#   cycle 126:     wait cycle (rst_n=1, enable=0, I=0)
#   cycle 127-135: output phase (rst_n=1, enable=0, I=0)
#
# clk2fflogic needs 2 SAT steps per clock cycle:
#   step 2C-1: clk=0 (setup inputs)
#   step 2C:   clk=1 (posedge — FF captures D from step 2C-1)
#
# So clock cycle C maps to SAT steps (2C-1, 2C).

TOTAL_CYCLES = 135
TOTAL_SAT_STEPS = TOTAL_CYCLES * 2

def cycle_to_posedge(c):
    """SAT step where posedge occurs for clock cycle c (1-based)."""
    return 2 * c

def set_cycle(sat_parts, cycle, rst_n, enable, I, I_free=False):
    """Set inputs for both phases of a clock cycle."""
    lo = 2 * cycle - 1  # clk=0 phase
    hi = 2 * cycle       # clk=1 phase (posedge)
    for step in (lo, hi):
        clk_val = 0 if step == lo else 1
        parts = f"-set-at {step} clk {clk_val} -set-at {step} rst_n {rst_n} -set-at {step} enable {enable}"
        if not I_free:
            parts += f" -set-at {step} I {I}"
        sat_parts.append(parts)

lines = []
mode_name = "sim" if sim_mode else ("validate" if validate_mode else "solve")
lines.append("# Auto-generated Yosys solve script")
lines.append(f"# Mode: {mode_name}")
lines.append(f"# {TOTAL_CYCLES} clock cycles = {TOTAL_SAT_STEPS} SAT steps (2 per cycle for clk toggling)")
lines.append("")

lines.append("read_verilog support/sky130_ff_models.v")
for f in func_files:
    lines.append(f"read_verilog -DFUNCTIONAL {os.path.relpath(f, PROJECT)}")
lines.append("read_verilog outputs/puzzle_netlist.v")
lines.append("")

lines.append("hierarchy -top puzzle")
lines.append("proc")
lines.append("flatten")
lines.append("clk2fflogic")
lines.append("opt_clean")
lines.append("")

sat_parts = [f"sat -seq {TOTAL_SAT_STEPS}"]
sat_parts.append("-set-init-zero")
sat_parts.append("-show clk -show I -show success -show O_0_ -show O_1_ -show O_2_ -show O_3_ -show O_4_ -show O_5_ -show O_6_ -show O_7_")

# Reset phase: cycles 1-3
for c in range(1, 4):
    set_cycle(sat_parts, c, rst_n=0, enable=0, I=0)

# Release reset: cycle 4
set_cycle(sat_parts, 4, rst_n=1, enable=0, I=0)

# Enable activation: cycle 5 (always I=0)
set_cycle(sat_parts, 5, rst_n=1, enable=1, I=0)

# Input phase: cycles 6-125 (120 bits)
for c in range(6, 126):
    if validate_mode or sim_mode:
        set_cycle(sat_parts, c, rst_n=1, enable=1, I=0)
    else:
        set_cycle(sat_parts, c, rst_n=1, enable=1, I=0, I_free=True)

# Wait + output phase: cycles 126-135
for c in range(126, 136):
    set_cycle(sat_parts, c, rst_n=1, enable=0, I=0)

# Assertions — output appears at cycle 126 (when enable drops), SAT step 252
OUTPUT_CYCLE = 126
if sim_mode:
    pass
elif validate_mode:
    out_step = cycle_to_posedge(OUTPUT_CYCLE)
    e_bits = [int(b) for b in f"{0x45:08b}"[::-1]]  # LSB first
    for i, b in enumerate(e_bits):
        sat_parts.append(f"-set-at {out_step} O_{i}_ {b}")
    sat_parts.append(f"-set-at {out_step} success 0")
else:
    target_cycle = success_step if success_step is not None else OUTPUT_CYCLE
    s = cycle_to_posedge(target_cycle)
    sat_parts.append(f"-set-at {s} success 1")

lines.append(" \\\n    ".join(sat_parts))

script = "\n".join(lines) + "\n"
out_path = os.path.join(PROJECT, "scripts", "solve.ys")
with open(out_path, "w") as f:
    f.write(script)

if sim_mode:
    mode_str = "SIM (all-zero input, no assertions — just show outputs)"
elif validate_mode:
    mode_str = "VALIDATE (all-zero input, expect 'E' at cycle 127)"
else:
    mode_str = "SOLVE (free input, assert success=1)"
print(f"Written {out_path}")
print(f"Mode: {mode_str}")
print(f"Clock cycles: {TOTAL_CYCLES}, SAT steps: {TOTAL_SAT_STEPS} (2 steps per cycle for clk edge detection)")
