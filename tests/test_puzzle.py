import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles

VCD_RUN0 = "001010100000001011000010100110000000001000000111011000010010110000111001100000001011000000101110000000001000001100111000"
VCD_RUN1 = "110101100001001111000000000100000100001100001110111000010000110000100101100000010111000011001110000000001000000000010000"

def read_output_byte(dut):
    byte = 0
    for i in range(8):
        bit = getattr(dut, f"O_{i}_").value
        if bit:
            byte |= (1 << i)
    return byte

async def run_input_bits(dut, bits, label, num_output_cycles=9):
    """Reset, feed input bits, read output."""
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
    for cycle in range(num_output_cycles):
        await RisingEdge(dut.clk)
        byte = read_output_byte(dut)
        success = int(dut.success.value)
        ch = chr(byte) if 32 <= byte < 127 else '.'
        dut._log.info(f"[{label}] Cycle +{cycle}: O=0x{byte:02x} '{ch}' success={success}")
        if byte != 0:
            output_chars.append(chr(byte))

    result = ''.join(output_chars)
    dut._log.info(f"[{label}] Output: '{result}'")
    return result

@cocotb.test()
async def test_120_zeros(dut):
    """Send 120 zero bits, then read output for 9 cycles."""
    result = await run_input_bits(dut, "0" * 120, "zeros")
    assert result == "EMPTY SKY", f"Expected 'EMPTY SKY', got '{result}'"

@cocotb.test()
async def test_vcd_run0(dut):
    """Replay first input sequence from example_inputs.vcd."""
    result = await run_input_bits(dut, VCD_RUN0, "vcd_run0")
    assert result == "TRY AGAIN", f"Expected 'TRY AGAIN', got '{result}'"

@cocotb.test()
async def test_vcd_run1(dut):
    """Replay second input sequence from example_inputs.vcd."""
    result = await run_input_bits(dut, VCD_RUN1, "vcd_run1")
    assert result == "TRY AGAIN", f"Expected 'TRY AGAIN', got '{result}'"
