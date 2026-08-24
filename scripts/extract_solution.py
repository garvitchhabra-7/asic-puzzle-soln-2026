#!/usr/bin/env python3
"""Extract the 121-bit solution from a Yosys SAT solve log.

Input bits are at clock cycles 5-125, which map to SAT steps 9-250
(2 steps per cycle). We read I at the clk=0 phase (odd steps: 9,11,...,249).

Usage:
    python3 scripts/extract_solution.py yosys_solve_log.txt
"""

import os
import re
import sys

log_path = sys.argv[1] if len(sys.argv) > 1 else "yosys_solve_log.txt"

with open(log_path) as f:
    log = f.read()

# Parse lines like: "   11 \I    ... 1         1             1"
# Format: <step> \I <spaces> <dec> <spaces> <dec> <spaces> <dec>
i_values = {}
for m in re.finditer(r'^\s+(\d+)\s+\\I\s+(\d+)\s+(\d+)\s+(\d+)', log, re.MULTILINE):
    step = int(m.group(1))
    val = int(m.group(2))
    i_values[step] = val

# Input phase: clock cycles 5-125, clk=0 steps are odd: 2*c-1
bits = []
for cycle in range(5, 126):
    step = 2 * cycle - 1  # clk=0 phase
    if step in i_values:
        bits.append(i_values[step])
    else:
        step = 2 * cycle  # try clk=1 phase
        if step in i_values:
            bits.append(i_values[step])
        else:
            print(f"WARNING: no I value at cycle {cycle} (steps {2*cycle-1}, {2*cycle})")
            bits.append(0)

bitstring = ''.join(str(b) for b in bits)
print(f"121-bit solution: {bitstring}")
print(f"Length: {len(bits)}")

# Format for cocotb test
print(f"\nFor test_puzzle.py:")
print(f'SOLUTION_BITS = "{bitstring}"')

# Write to outputs/solution.txt
project = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out_path = os.path.join(project, "outputs", "solution.txt")
with open(out_path, "w") as f:
    f.write(bitstring + "\n")
print(f"\nWritten to {out_path}")
