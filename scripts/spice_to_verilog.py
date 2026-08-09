#!/usr/bin/env python3
"""Convert puzzle.spice (extracted SPICE netlist) to a gate-level Verilog netlist."""

import re
import sys
from pathlib import Path

POWER_PINS = {"VGND", "VNB", "VPB", "VPWR"}
SKIP_CELLS = {"decap", "diode"}

def strip_drive_strength(cell_name):
    """sky130_fd_sc_hd__nor4_2 -> nor4"""
    base = cell_name.removeprefix("sky130_fd_sc_hd__")
    return re.sub(r'_\d+$', '', base)

def sanitize_net(name):
    """Make net names valid Verilog identifiers."""
    name = name.replace("/", "__")
    name = name.replace("[", "_").replace("]", "_")
    return name

def join_continuation_lines(lines):
    """Join SPICE continuation lines (starting with +) into single logical lines."""
    logical = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('+'):
            if logical:
                logical[-1] += ' ' + stripped[1:].strip()
        elif stripped:
            logical.append(stripped)
    return logical

def parse_spice(spice_path):
    """Parse puzzle.spice, return (cell_pin_orders, top_ports, instances)."""
    with open(spice_path) as f:
        raw_lines = f.readlines()

    logical_lines = join_continuation_lines(raw_lines)

    cell_pin_orders = {}
    top_ports = []
    instances = []
    in_puzzle = False

    for line in logical_lines:
        if line.startswith('*'):
            continue

        if line.startswith('.subckt'):
            tokens = line.split()
            name = tokens[1]
            pins = tokens[2:]
            if name == 'puzzle':
                top_ports = pins
                in_puzzle = True
            else:
                cell_pin_orders[name] = pins
            continue

        if line.startswith('.ends'):
            in_puzzle = False
            continue

        if not in_puzzle:
            continue

        if re.match(r'^C\d+\s', line):
            continue

        if line.startswith('X'):
            tokens = line.split()
            inst_name = tokens[0][1:]
            cell_type = tokens[-1]
            nets = tokens[1:-1]
            instances.append((inst_name, cell_type, nets))

    return cell_pin_orders, top_ports, instances

def convert(spice_path, output_path):
    cell_pin_orders, top_ports, instances = parse_spice(spice_path)

    const_hi_nets = set()
    const_lo_nets = set()

    processed = []
    all_internal_nets = set()

    top_signal_ports = [p for p in top_ports if p not in POWER_PINS]
    top_port_set = set(top_signal_ports)

    for inst_name, cell_type, nets in instances:
        base = strip_drive_strength(cell_type)

        if base in SKIP_CELLS:
            continue

        pin_order = cell_pin_orders.get(cell_type)
        if pin_order is None:
            print(f"WARNING: no pin order for {cell_type}", file=sys.stderr)
            continue

        if len(nets) != len(pin_order):
            print(f"WARNING: pin count mismatch for {inst_name}: "
                  f"{len(nets)} nets vs {len(pin_order)} pins", file=sys.stderr)
            continue

        port_map = {}
        for pin_name, net in zip(pin_order, nets):
            if pin_name in POWER_PINS:
                continue
            port_map[pin_name] = net

        if base == "conb":
            if "HI" in port_map:
                const_hi_nets.add(port_map["HI"])
            if "LO" in port_map:
                const_lo_nets.add(port_map["LO"])
            continue

        for net in port_map.values():
            if net not in top_port_set:
                all_internal_nets.add(net)

        processed.append((inst_name, cell_type, port_map))

    # Emit Verilog
    lines = []
    lines.append("module puzzle (")

    port_lines = []
    for p in top_signal_ports:
        port_lines.append(f"    {sanitize_net(p)}")
    lines.append(",\n".join(port_lines))
    lines.append(");")
    lines.append("")

    input_ports = []
    output_ports = []
    for p in top_signal_ports:
        sp = sanitize_net(p)
        if p.startswith("O[") or p == "success":
            output_ports.append(sp)
        else:
            input_ports.append(sp)

    if input_ports:
        lines.append(f"input {', '.join(input_ports)};")
    if output_ports:
        lines.append(f"output {', '.join(output_ports)};")
    lines.append("")

    declared_wires = set()
    sorted_nets = sorted(all_internal_nets)
    for net in sorted_nets:
        sn = sanitize_net(net)
        if sn not in declared_wires:
            lines.append(f"wire {sn};")
            declared_wires.add(sn)

    for net in sorted(const_hi_nets):
        sn = sanitize_net(net)
        if net not in top_port_set and sn not in declared_wires:
            lines.append(f"wire {sn};")
        lines.append(f"assign {sn} = 1'b1;")
    for net in sorted(const_lo_nets):
        sn = sanitize_net(net)
        if net not in top_port_set and sn not in declared_wires:
            lines.append(f"wire {sn};")
        lines.append(f"assign {sn} = 1'b0;")

    lines.append("")

    for inst_name, cell_type, port_map in processed:
        ports_str = ", ".join(
            f".{pin}({sanitize_net(net)})"
            for pin, net in sorted(port_map.items())
        )
        lines.append(f"{cell_type} {sanitize_net(inst_name)} ({ports_str});")

    lines.append("")
    lines.append("endmodule")

    with open(output_path, 'w') as f:
        f.write("\n".join(lines) + "\n")

    print(f"Wrote {len(processed)} cell instances to {output_path}")
    print(f"  Skipped cells: decap, diode, conb")
    print(f"  Internal nets: {len(all_internal_nets)}")
    print(f"  Constant hi nets: {len(const_hi_nets)}, lo nets: {len(const_lo_nets)}")

if __name__ == "__main__":
    import argparse

    project = Path(__file__).resolve().parent.parent

    parser = argparse.ArgumentParser(description="Convert SPICE netlist to gate-level Verilog.")
    parser.add_argument("spice", nargs="?", default=project / "outputs" / "puzzle.spice",
                        help="Path to input SPICE netlist (default: outputs/puzzle.spice)")
    parser.add_argument("-o", "--output", default=None,
                        help="Path to output Verilog file (default: <spice_stem>_netlist.v in same dir)")
    args = parser.parse_args()

    spice_path = Path(args.spice)
    output_path = Path(args.output) if args.output else spice_path.parent / f"{spice_path.stem}_netlist.v"

    convert(spice_path, output_path)
