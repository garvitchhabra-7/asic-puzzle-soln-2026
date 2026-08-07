{
  description = "ASIC reverse engineering puzzle dev environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs, ... }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      python = pkgs.python313.withPackages (ps: with ps; [
        gdstk
        pyvcd
        numpy
        cocotb
      ]);
    in {
      devShells.${system}.default = pkgs.mkShell {
        packages = with pkgs; [
          # GDS viewing and layout exploration
          klayout
          magic-vlsi

          # Synthesis and netlist analysis
          yosys

          # Simulation
          iverilog
          verilator

          # Waveform viewing
          gtkwave
          surfer

          # LVS / netlist comparison
          netgen-vlsi

          # PDK management
          pdk-ciel

          # Python with libraries
          python
        ];

        shellHook = ''
          export SKY130_HD="$PWD/libs/sky130_fd_sc_hd"
          export PDK_ROOT="$HOME/.ciel"
          export PDK=sky130A

          if [ ! -d "$SKY130_HD/cells" ]; then
            echo "WARNING: sky130_fd_sc_hd submodule not initialized."
            echo "Run: git submodule update --init"
          fi

          if [ ! -e "$PDK_ROOT/$PDK" ]; then
            echo "WARNING: sky130A PDK not installed."
            echo "Run: ciel fetch --pdk sky130A <version> && ciel enable --pdk sky130A <version>"
            echo "Use: ciel ls-remote --pdk sky130A  to list available versions"
          fi
        '';
      };
    };
}
