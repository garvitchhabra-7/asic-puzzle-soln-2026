#!/bin/bash
# Usage: run_extract.sh <filename> <cellname>
# where <filename> is a GDS layout file and <cellname> is the top-level cell to extract.
echo ${PDK_ROOT:=~/.ciel} > /dev/null
echo ${PDK:=sky130A} > /dev/null
mkdir -p outputs logs
export PDKPATH=${PDK_ROOT}/${PDK}
magic -dnull -noconsole -rcfile ${PDK_ROOT}/${PDK}/libs.tech/magic/${PDK}.magicrc -T ${PDK_ROOT}/${PDK}/libs.tech/magic/${PDK}.tech > logs/magic.log << EOF
drc off
locking disable
crashbackups stop
box 0 0 0 0
gds noduplicates true
gds read $1
load $2
select top cell
extract path extfiles
extract all
ext2spice hierarchy on
ext2spice subcircuit top on
ext2spice -o outputs/$2.spice -p extfiles
quit -noprompt
EOF
rm -rf extfiles
echo "Done!"
exit 0
