.PHONY: extract netlist test solve verify all clean
.DELETE_ON_ERROR:

all: solve verify

# Step 2: Extract SPICE netlist from GDS using Magic
outputs/puzzle.spice: puzzle.gds scripts/run_extract.sh
	bash scripts/run_extract.sh puzzle.gds puzzle
	@test -s $@ || (echo "Error: extraction produced no output"; exit 1)

extract: outputs/puzzle.spice

# Step 3: Convert SPICE netlist to gate-level Verilog
outputs/puzzle_netlist.v: outputs/puzzle.spice scripts/spice_to_verilog.py
	python scripts/spice_to_verilog.py

netlist: outputs/puzzle_netlist.v

# Step 4: Run cocotb simulation tests
test: outputs/puzzle_netlist.v
	$(MAKE) -C tests MODULE=test_puzzle

# Step 5: Solve with Yosys SAT
outputs/solution.txt: outputs/puzzle_netlist.v scripts/run_sat_solve.sh scripts/gen_solve_ys.py scripts/extract_solution.py
	bash scripts/run_sat_solve.sh

solve: outputs/solution.txt

# Step 6: Verify the solution through cocotb
verify: outputs/solution.txt outputs/puzzle_netlist.v
	$(MAKE) -C tests MODULE=test_success

clean:
	$(MAKE) -C tests clean
	rm -rf outputs/puzzle.spice outputs/puzzle_netlist.v outputs/solution.txt
	rm -rf scripts/solve.ys logs/
