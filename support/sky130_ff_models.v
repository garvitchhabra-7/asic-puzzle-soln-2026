module sky130_fd_sc_hd__dfrtp_2 (
    output reg Q,
    input CLK,
    input D,
    input RESET_B
);
    always @(posedge CLK or negedge RESET_B)
        if (!RESET_B) Q <= 0;
        else Q <= D;
endmodule

module sky130_fd_sc_hd__dfstp_2 (
    output reg Q,
    input CLK,
    input D,
    input SET_B
);
    always @(posedge CLK or negedge SET_B)
        if (!SET_B) Q <= 1;
        else Q <= D;
endmodule

module sky130_fd_sc_hd__dfxtp_2 (
    output reg Q,
    input CLK,
    input D
);
    always @(posedge CLK)
        Q <= D;
endmodule

module sky130_fd_sc_hd__mux2_1 (
    output X,
    input A0,
    input A1,
    input S
);
    assign X = S ? A1 : A0;
endmodule
