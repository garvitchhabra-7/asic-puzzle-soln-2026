SIM ?= icarus
TOPLEVEL_LANG ?= verilog
TOPLEVEL = puzzle
MODULE = test_puzzle

PROJ_DIR = $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))/..
SKY130_HD = $(PROJ_DIR)/libs/sky130_fd_sc_hd

VERILOG_SOURCES = $(PROJ_DIR)/outputs/puzzle_netlist.v
VERILOG_SOURCES += $(PROJ_DIR)/support/sky130_ff_models.v

CELL_TYPES := $(shell grep -oP '^sky130_fd_sc_hd__\S+' $(PROJ_DIR)/outputs/puzzle_netlist.v | sort -u)
SKIP_CELLS := dfrtp dfstp dfxtp mux2
VERILOG_SOURCES += $(foreach cell,$(CELL_TYPES),$(if $(filter $(foreach s,$(SKIP_CELLS),sky130_fd_sc_hd__$(s)_%),$(cell)),,$(wildcard $(SKY130_HD)/cells/$(shell echo $(cell) | sed 's/sky130_fd_sc_hd__//;s/_[0-9]*$$//')/$(cell).functional.v)))

COMPILE_ARGS += -DFUNCTIONAL '-DUNIT_DELAY=\#1'
COMPILE_ARGS += $(foreach d,$(wildcard $(SKY130_HD)/cells/*/),-I$(d))

include $(shell cocotb-config --makefiles)/Makefile.sim
