import os
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles

def load_solution():
    project = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(project, "outputs", "solution.txt")
    with open(path) as f:
        return f.read().strip()

def read_output_byte(dut):
    byte = 0
    for i in range(8):
        bit = getattr(dut, f"O_{i}_").value
        if bit:
            byte |= (1 << i)
    return byte

@cocotb.test()
async def test_success(dut):
    """Send solution bits, then read output for 15 cycles."""
    bits = load_solution()
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    dut.rst_n.value = 0
    dut.enable.value = 0
    dut.I.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
    dut.enable.value = 1
    await RisingEdge(dut.clk)

    for b in bits:
        dut.I.value = int(b)
        await RisingEdge(dut.clk)

    dut.enable.value = 0
    dut.I.value = 0

    output_chars = []
    await RisingEdge(dut.clk)
    for cycle in range(15):
        await RisingEdge(dut.clk)
        byte = read_output_byte(dut)
        success = int(dut.success.value)
        ch = chr(byte) if 32 <= byte < 127 else '.'
        dut._log.info(f"Cycle +{cycle}: O=0x{byte:02x} '{ch}' success={success}")
        if byte != 0:
            output_chars.append(chr(byte))

    dut._log.info(f"Output: '{''.join(output_chars)}'")
