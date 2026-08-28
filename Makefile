.PHONY: check_nix setup extract netlist test solve verify all clean

CIEL_VERSION ?= 7519dfb04400f224f140749cda44ee7de6f5e095
.DELETE_ON_ERROR:

check_nix:
	@[ -n "$$IN_NIX_SHELL" ] || { echo "Error: Not in nix shell. Run 'nix develop' first."; exit 1; }

# Step 0: Fetch and enable the SKY130 PDK via ciel
setup: check_nix
	git submodule update --init
	ciel fetch --pdk sky130A $(CIEL_VERSION)
	ciel enable --pdk sky130A $(CIEL_VERSION)

all: check_nix solve verify

# Step 2: Extract SPICE netlist from GDS using Magic
outputs/puzzle.spice: puzzle.gds scripts/run_extract.sh
	bash scripts/run_extract.sh puzzle.gds puzzle
	@test -s $@ || (echo "Error: extraction produced no output"; exit 1)

extract: check_nix outputs/puzzle.spice

# Step 3: Convert SPICE netlist to gate-level Verilog
outputs/puzzle_netlist.v: outputs/puzzle.spice scripts/spice_to_verilog.py
	python scripts/spice_to_verilog.py

netlist: check_nix outputs/puzzle_netlist.v

# Step 4: Run cocotb simulation tests
test: check_nix outputs/puzzle_netlist.v
	$(MAKE) -C tests MODULE=test_puzzle

# Step 5: Solve with Yosys SAT
outputs/solution.txt: outputs/puzzle_netlist.v scripts/run_sat_solve.sh scripts/gen_solve_ys.py scripts/extract_solution.py
	bash scripts/run_sat_solve.sh

solve: check_nix outputs/solution.txt

# Step 6: Verify the solution through cocotb
verify: check_nix outputs/solution.txt outputs/puzzle_netlist.v
	$(MAKE) -C tests MODULE=test_success

clean: check_nix
	$(MAKE) -C tests clean
	rm -rf outputs/puzzle.spice outputs/puzzle_netlist.v outputs/solution.txt
	rm -rf scripts/solve.ys logs/
