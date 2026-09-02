import fs from "node:fs";
import path from "node:path";

const sourcePath =
  "C:/Users/user/Documents/Codex/2026-07-14/i-w/work/fpga_space_uses_implementation_base_artifact.json";
const outputPath =
  "C:/Users/user/Documents/Codex/2026-07-14/i-w/outputs/fpga_space_uses_implementation_with_hdl_artifact.json";
const snippetDir =
  "C:/Users/user/Documents/Codex/2026-07-14/i-w/outputs/fpga_space_hdl_snippets";

const snippets = [
  {
    id: "use_01",
    file: "01_payload_capture.sv",
    note: "A one-entry ready/valid capture stage with a free-running timestamp and a sticky overflow flag. Replace the input side with the device-specific ADC, camera, or SERDES interface.",
    code: String.raw`module payload_capture (
  input  logic        clk, rst_n,
  input  logic        sample_valid,
  input  logic [15:0] sample_data,
  output logic        sample_ready,
  output logic        out_valid,
  output logic [15:0] out_data,
  output logic [47:0] out_time,
  input  logic        out_ready,
  output logic        overflow
);
  logic [47:0] time_ctr;
  assign sample_ready = !out_valid || out_ready;

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      time_ctr <= '0; out_valid <= 1'b0; overflow <= 1'b0;
    end else begin
      time_ctr <= time_ctr + 1'b1;
      if (out_valid && out_ready) out_valid <= 1'b0;
      if (sample_valid) begin
        if (sample_ready) begin
          out_data <= sample_data; out_time <= time_ctr; out_valid <= 1'b1;
        end else overflow <= 1'b1;
      end
    end
  end
endmodule`,
  },
  {
    id: "use_02",
    file: "02_sobel_pixel_kernel.sv",
    note: "The arithmetic kernel for a 3x3 Sobel edge detector. Three line buffers and a window generator must supply the nine pixels; those storage blocks are intentionally outside this small example.",
    code: String.raw`module sobel_pixel_kernel (
  input  logic clk, rst_n, in_valid,
  input  logic [7:0] p00,p01,p02,p10,p11,p12,p20,p21,p22,
  output logic out_valid,
  output logic [12:0] magnitude
);
  logic signed [12:0] gx, gy;
  logic [12:0] ax, ay;
  always @* begin
    gx = $signed({1'b0,p02}) + ($signed({1'b0,p12}) <<< 1)
       + $signed({1'b0,p22}) - $signed({1'b0,p00})
       - ($signed({1'b0,p10}) <<< 1) - $signed({1'b0,p20});
    gy = $signed({1'b0,p20}) + ($signed({1'b0,p21}) <<< 1)
       + $signed({1'b0,p22}) - $signed({1'b0,p00})
       - ($signed({1'b0,p01}) <<< 1) - $signed({1'b0,p02});
    ax = gx[12] ? -gx : gx;
    ay = gy[12] ? -gy : gy;
  end
  always_ff @(posedge clk) begin
    if (!rst_n) begin out_valid <= 1'b0; magnitude <= '0; end
    else begin out_valid <= in_valid; if (in_valid) magnitude <= ax + ay; end
  end
endmodule`,
  },
  {
    id: "use_03",
    file: "03_delta_run_compressor.sv",
    note: "A compact lossless run-length front end. It emits a value and repetition count whenever the value changes; a flight compressor would add packet framing, bounded expansion handling, and often Rice or CCSDS compression.",
    code: String.raw`module delta_run_compressor (
  input  logic clk, rst_n, in_valid,
  input  logic [15:0] in_sample,
  output logic out_valid,
  output logic [15:0] out_value,
  output logic [7:0] out_run
);
  logic have_value;
  logic [15:0] previous;
  logic [7:0] run;
  always_ff @(posedge clk) begin
    if (!rst_n) begin have_value<=0; run<=0; out_valid<=0; end
    else begin
      out_valid <= 1'b0;
      if (in_valid) begin
        if (!have_value) begin previous<=in_sample; run<=8'd1; have_value<=1; end
        else if ((in_sample==previous) && (run!=8'hff)) run <= run + 1'b1;
        else begin
          out_value<=previous; out_run<=run; out_valid<=1;
          previous<=in_sample; run<=8'd1;
        end
      end
    end
  end
endmodule`,
  },
  {
    id: "use_04",
    file: "04_sdr_complex_mixer.sv",
    note: "The multiplier stage of a digital down-converter. A phase accumulator and sine/cosine lookup table supply the oscillator values; filters and decimation follow this block.",
    code: String.raw`module sdr_complex_mixer (
  input  logic clk, rst_n, in_valid,
  input  logic signed [15:0] sample,
  input  logic signed [15:0] nco_cos, nco_sin,
  output logic out_valid,
  output logic signed [31:0] i_mix, q_mix
);
  always_ff @(posedge clk) begin
    if (!rst_n) begin out_valid<=0; i_mix<='0; q_mix<='0; end
    else begin
      out_valid <= in_valid;
      if (in_valid) begin
        i_mix <= sample * nco_cos;
        q_mix <= -(sample * nco_sin);
      end
    end
  end
endmodule`,
  },
  {
    id: "use_05",
    file: "05_convolutional_encoder.sv",
    note: "A rate-1/2, constraint-length-7 convolutional encoder using the common 171/133 octal generator polynomials. A mission implementation must match the exact CCSDS profile, puncturing, interleaving, and frame conventions.",
    code: String.raw`module convolutional_encoder (
  input  logic clk, rst_n, bit_valid, bit_in,
  output logic code_valid,
  output logic [1:0] code_bits
);
  logic [5:0] state;
  logic [6:0] next_state;
  always_comb next_state = {bit_in, state};
  always_ff @(posedge clk) begin
    if (!rst_n) begin state<='0; code_valid<=0; code_bits<='0; end
    else begin
      code_valid <= bit_valid;
      if (bit_valid) begin
        code_bits[1] <= ^(next_state & 7'b1111001);
        code_bits[0] <= ^(next_state & 7'b1011011);
        state <= next_state[6:1];
      end
    end
  end
endmodule`,
  },
  {
    id: "use_06",
    file: "06_four_channel_beamformer.sv",
    note: "A four-channel complex weighted sum. Real designs pipeline the multipliers and adder tree, align channel timestamps, calibrate phase/gain, and normally obtain weights from a processor or calibration table.",
    code: String.raw`module four_channel_beamformer (
  input  logic clk, rst_n, in_valid,
  input  logic signed [15:0] x0i,x0q,x1i,x1q,x2i,x2q,x3i,x3q,
  input  logic signed [15:0] w0i,w0q,w1i,w1q,w2i,w2q,w3i,w3q,
  output logic out_valid,
  output logic signed [35:0] yi, yq
);
  logic signed [35:0] sum_i, sum_q;
  always_comb begin
    sum_i = x0i*w0i-x0q*w0q + x1i*w1i-x1q*w1q
          + x2i*w2i-x2q*w2q + x3i*w3i-x3q*w3q;
    sum_q = x0i*w0q+x0q*w0i + x1i*w1q+x1q*w1i
          + x2i*w2q+x2q*w2i + x3i*w3q+x3q*w3i;
  end
  always_ff @(posedge clk) begin
    if (!rst_n) begin out_valid<=0; yi<='0; yq<='0; end
    else begin out_valid<=in_valid; if(in_valid) begin yi<=sum_i; yq<=sum_q; end end
  end
endmodule`,
  },
  {
    id: "use_07",
    file: "07_complex_matched_filter_mac.sv",
    note: "One complex multiply-accumulate tap for a matched filter or correlator. A complete radar/SAR pipeline streams reference coefficients from ROM and uses a pipelined MAC tree or FFT engine.",
    code: String.raw`module complex_matched_filter_mac (
  input  logic clk, rst_n, start, tap_valid, last_tap,
  input  logic signed [15:0] xi, xq, hi, hq,
  output logic done,
  output logic signed [47:0] corr_i, corr_q
);
  always_ff @(posedge clk) begin
    if (!rst_n) begin corr_i<='0; corr_q<='0; done<=0; end
    else begin
      done <= 1'b0;
      if (start) begin corr_i<='0; corr_q<='0; end
      if (tap_valid) begin
        corr_i <= corr_i + xi*hi + xq*hq;
        corr_q <= corr_q + xq*hi - xi*hq;
        done <= last_tap;
      end
    end
  end
endmodule`,
  },
  {
    id: "use_08",
    file: "08_optical_link_framer.sv",
    note: "A simple fixed-length frame serializer that places a synchronization word before a payload. The actual laser/optical PHY, line code, FEC, clock recovery, and safety interlocks are separate qualified blocks.",
    code: String.raw`module optical_link_framer (
  input  logic clk, rst_n, payload_valid,
  input  logic [31:0] payload,
  output logic payload_ready, tx_bit, tx_valid
);
  logic [47:0] shifter;
  logic [5:0] bits_left;
  assign payload_ready = (bits_left==0);
  always_ff @(posedge clk) begin
    if (!rst_n) begin bits_left<=0; tx_valid<=0; tx_bit<=0; end
    else if (payload_valid && payload_ready) begin
      shifter <= {16'h1ACF,payload}; bits_left <= 6'd48; tx_valid <= 1'b1;
    end else if (bits_left!=0) begin
      tx_bit <= shifter[47]; shifter <= {shifter[46:0],1'b0};
      bits_left <= bits_left - 1'b1;
      if (bits_left==1) tx_valid <= 1'b0;
    end
  end
endmodule`,
  },
  {
    id: "use_09",
    file: "09_round_robin_arbiter.sv",
    note: "A four-port round-robin arbiter suitable for selecting the next packet source. Packet locking must hold the grant until end-of-packet so flits from different packets cannot interleave.",
    code: String.raw`module round_robin_arbiter (
  input  logic clk, rst_n,
  input  logic [3:0] request,
  input  logic grant_accepted,
  output logic [3:0] grant
);
  logic [1:0] pointer;
  integer k, index;
  logic found;
  always_comb begin
    grant='0; found=1'b0;
    for (k=0;k<4;k=k+1) begin
      index = pointer + k;
      if (index>=4) index=index-4;
      if (!found && request[index]) begin grant[index]=1'b1; found=1'b1; end
    end
  end
  always_ff @(posedge clk) begin
    if (!rst_n) pointer<=0;
    else if (grant_accepted && |grant)
      pointer <= grant[0]?2'd1:grant[1]?2'd2:grant[2]?2'd3:2'd0;
  end
endmodule`,
  },
  {
    id: "use_10",
    file: "10_ready_valid_to_req_ack.sv",
    note: "A protocol bridge that converts a ready/valid transfer into a level request held until acknowledge. Add clock-domain synchronizers if request and acknowledge cross clock domains.",
    code: String.raw`module ready_valid_to_req_ack (
  input  logic clk, rst_n,
  input  logic in_valid,
  input  logic [31:0] in_data,
  output logic in_ready,
  output logic req,
  output logic [31:0] req_data,
  input  logic ack
);
  assign in_ready = !req;
  always_ff @(posedge clk) begin
    if (!rst_n) begin req<=0; req_data<='0; end
    else begin
      if (req && ack) req <= 1'b0;
      if (in_valid && in_ready) begin req_data<=in_data; req<=1'b1; end
    end
  end
endmodule`,
  },
  {
    id: "use_11",
    file: "11_circular_dma_address.sv",
    note: "The address-generation part of a circular DMA writer. The storage controller still needs burst formation, descriptors, ECC status handling, backpressure, and power-loss-safe metadata.",
    code: String.raw`module circular_dma_address #(
  parameter logic [31:0] BASE=32'h1000_0000,
  parameter logic [31:0] LIMIT=32'h1001_0000
) (
  input  logic clk, rst_n, start, beat_accepted,
  output logic active,
  output logic [31:0] write_address
);
  always_ff @(posedge clk) begin
    if (!rst_n) begin write_address<=BASE; active<=0; end
    else begin
      if (start) active<=1'b1;
      if (active && beat_accepted)
        write_address <= (write_address+4>=LIMIT) ? BASE : write_address+4;
    end
  end
endmodule`,
  },
  {
    id: "use_12",
    file: "12_fixed_point_pid.sv",
    note: "A fixed-point PID control kernel. Saturation, anti-windup, sensor-valid gating, actuator limits, and independently verified scaling must be added for a real GNC loop.",
    code: String.raw`module fixed_point_pid #(
  parameter integer KP=16, KI=1, KD=4, SHIFT=4
) (
  input  logic clk, rst_n, sample_tick,
  input  logic signed [15:0] setpoint, measurement,
  output logic signed [31:0] control
);
  logic signed [16:0] error, previous_error;
  logic signed [31:0] integral;
  assign error = $signed(setpoint) - $signed(measurement);
  always_ff @(posedge clk) begin
    if (!rst_n) begin previous_error<='0; integral<='0; control<='0; end
    else if (sample_tick) begin
      integral <= integral + error;
      control <= (KP*error + KI*integral + KD*(error-previous_error)) >>> SHIFT;
      previous_error <= error;
    end
  end
endmodule`,
  },
  {
    id: "use_13",
    file: "13_star_centroid.sv",
    note: "A streaming threshold-and-centroid accumulator for one candidate star region. Division is shown for clarity; flight implementations usually schedule or pipeline a divider and separately handle connected-component labeling.",
    code: String.raw`module star_centroid (
  input  logic clk, rst_n, pixel_valid, region_end,
  input  logic [11:0] pixel,
  input  logic [10:0] x, y,
  input  logic [11:0] threshold,
  output logic centroid_valid,
  output logic [10:0] centroid_x, centroid_y
);
  logic [31:0] sum_x, sum_y;
  logic [20:0] count;
  always_ff @(posedge clk) begin
    if (!rst_n) begin sum_x<=0; sum_y<=0; count<=0; centroid_valid<=0; end
    else begin
      centroid_valid <= 1'b0;
      if (pixel_valid && pixel>threshold) begin
        sum_x<=sum_x+x; sum_y<=sum_y+y; count<=count+1'b1;
      end
      if (region_end) begin
        if (count!=0) begin centroid_x<=sum_x/count; centroid_y<=sum_y/count;
          centroid_valid<=1'b1; end
        sum_x<=0; sum_y<=0; count<=0;
      end
    end
  end
endmodule`,
  },
  {
    id: "use_14",
    file: "14_lidar_range_timer.sv",
    note: "A timestamp-difference range primitive. The result is in half-clock ticks; calibration converts ticks into physical distance and corrects fixed delays, clock drift, detector walk, and multi-return selection.",
    code: String.raw`module lidar_range_timer (
  input  logic clk, rst_n, tx_pulse, rx_pulse,
  output logic range_valid,
  output logic [47:0] half_round_trip_ticks
);
  logic [47:0] time_counter, transmit_time;
  logic waiting;
  always_ff @(posedge clk) begin
    if (!rst_n) begin time_counter<=0; waiting<=0; range_valid<=0; end
    else begin
      time_counter <= time_counter + 1'b1; range_valid <= 1'b0;
      if (tx_pulse) begin transmit_time<=time_counter; waiting<=1'b1; end
      if (rx_pulse && waiting) begin
        half_round_trip_ticks <= (time_counter-transmit_time) >> 1;
        range_valid<=1'b1; waiting<=1'b0;
      end
    end
  end
endmodule`,
  },
  {
    id: "use_15",
    file: "15_hazard_classifier.sv",
    note: "A deterministic terrain-cell classifier. The inputs would come from a lidar/camera map pipeline; actual landing systems combine confidence, neighborhood morphology, vehicle constraints, and a processor-level landing-site search.",
    code: String.raw`module hazard_classifier (
  input  logic clk, rst_n, cell_valid,
  input  logic [15:0] slope, roughness, clearance,
  input  logic [15:0] max_slope, max_roughness, min_clearance,
  output logic result_valid, safe_cell
);
  always_ff @(posedge clk) begin
    if (!rst_n) begin result_valid<=0; safe_cell<=0; end
    else begin
      result_valid <= cell_valid;
      if (cell_valid)
        safe_cell <= (slope<=max_slope) &&
                     (roughness<=max_roughness) &&
                     (clearance>=min_clearance);
    end
  end
endmodule`,
  },
  {
    id: "use_16",
    file: "16_quantized_neuron_mac.sv",
    note: "A signed 8-bit multiply-accumulate engine for quantized inference. A complete accelerator adds weight/activation memories, tiling, saturation, activation functions, layer control, and golden-model comparison.",
    code: String.raw`module quantized_neuron_mac (
  input  logic clk, rst_n, start, pair_valid, last_pair,
  input  logic signed [7:0] activation, weight,
  input  logic signed [31:0] bias,
  output logic result_valid,
  output logic signed [31:0] result
);
  logic signed [31:0] accumulator;
  always_ff @(posedge clk) begin
    if (!rst_n) begin accumulator<=0; result_valid<=0; result<=0; end
    else begin
      result_valid<=1'b0;
      if (start) accumulator<=bias;
      if (pair_valid) begin
        accumulator <= accumulator + activation*weight;
        if (last_pair) begin result<=accumulator+activation*weight;
          result_valid<=1'b1; end
      end
    end
  end
endmodule`,
  },
  {
    id: "use_17",
    file: "17_event_data_gate.sv",
    note: "A streaming event gate that forwards only samples inside a selected event window. Real intelligent reduction usually keeps a pre-trigger circular buffer and attaches the decision score and rejected-data counters to telemetry.",
    code: String.raw`module event_data_gate (
  input  logic clk, rst_n,
  input  logic event_start, event_end,
  input  logic in_valid,
  input  logic [31:0] in_data,
  output logic out_valid,
  output logic [31:0] out_data,
  output logic [31:0] rejected_count
);
  logic keep_window;
  always_ff @(posedge clk) begin
    if (!rst_n) begin keep_window<=0; out_valid<=0; rejected_count<=0; end
    else begin
      if (event_start) keep_window<=1'b1;
      if (event_end) keep_window<=1'b0;
      out_valid <= in_valid && (keep_window || event_start);
      if (in_valid && (keep_window || event_start)) out_data<=in_data;
      else if (in_valid) rejected_count<=rejected_count+1'b1;
    end
  end
endmodule`,
  },
  {
    id: "use_18",
    file: "18_instrument_sequencer.sv",
    note: "A deterministic power-and-trigger sequencer. Replace fixed counts with reviewed requirement constants, verify every transition, and include asynchronous hardware inhibits outside the FPGA for hazardous functions.",
    code: String.raw`module instrument_sequencer (
  input  logic clk, rst_n, start, abort,
  output logic bias_enable, adc_enable, trigger, done
);
  typedef enum logic [2:0] {IDLE,BIAS_WAIT,ADC_WAIT,PULSE,FINISH} state_t;
  state_t state;
  logic [15:0] timer;
  always_ff @(posedge clk) begin
    if (!rst_n || abort) begin state<=IDLE; timer<=0; end
    else case (state)
      IDLE:      if(start) begin state<=BIAS_WAIT; timer<=0; end
      BIAS_WAIT: if(timer==16'd999) begin state<=ADC_WAIT; timer<=0; end
                 else timer<=timer+1'b1;
      ADC_WAIT:  if(timer==16'd199) begin state<=PULSE; timer<=0; end
                 else timer<=timer+1'b1;
      PULSE:     state<=FINISH;
      FINISH:    state<=IDLE;
    endcase
  end
  always_comb begin
    bias_enable=(state!=IDLE); adc_enable=(state==ADC_WAIT||state==PULSE);
    trigger=(state==PULSE); done=(state==FINISH);
  end
endmodule`,
  },
  {
    id: "use_19",
    file: "19_pps_disciplined_clock.sv",
    note: "A simple one-pulse-per-second disciplining loop that corrects the local counter by at most one tick per PPS. Precision systems use a fractional accumulator, characterized oscillator model, and a formally bounded monotonic-time policy.",
    code: String.raw`module pps_disciplined_clock #(
  parameter integer TICKS_PER_SECOND=50_000_000
) (
  input  logic clk, rst_n, pps,
  output logic [63:0] mission_ticks,
  output logic signed [31:0] phase_error
);
  logic [31:0] local_ticks;
  always_ff @(posedge clk) begin
    if (!rst_n) begin local_ticks<=0; mission_ticks<=0; phase_error<=0; end
    else begin
      local_ticks<=local_ticks+1'b1; mission_ticks<=mission_ticks+1'b1;
      if (pps) begin
        phase_error <= $signed(local_ticks)-TICKS_PER_SECOND;
        if (local_ticks>TICKS_PER_SECOND) mission_ticks<=mission_ticks;
        else if (local_ticks<TICKS_PER_SECOND) mission_ticks<=mission_ticks+2;
        local_ticks<=0;
      end
    end
  end
endmodule`,
  },
  {
    id: "use_20",
    file: "20_command_decoder.sv",
    note: "A whitelist command decoder that acts only after an external frame checker asserts CRC validity. Commands that can cause hazardous state changes need authentication, range checking, interlocks, and explicit execution telemetry.",
    code: String.raw`module command_decoder (
  input  logic clk, rst_n, command_valid, crc_ok,
  input  logic [7:0] opcode,
  input  logic [23:0] argument,
  output logic set_mode, clear_faults,
  output logic [23:0] mode_argument,
  output logic rejected
);
  always_ff @(posedge clk) begin
    if (!rst_n) begin set_mode<=0; clear_faults<=0; rejected<=0; end
    else begin
      set_mode<=0; clear_faults<=0; rejected<=0;
      if (command_valid) begin
        if (!crc_ok) rejected<=1'b1;
        else case(opcode)
          8'h10: begin set_mode<=1'b1; mode_argument<=argument; end
          8'h21: clear_faults<=1'b1;
          default: rejected<=1'b1;
        endcase
      end
    end
  end
endmodule`,
  },
  {
    id: "use_21",
    file: "21_heartbeat_watchdog.sv",
    note: "A heartbeat watchdog with a latched safe-state request. In a spacecraft the final independent watchdog and power-cycle authority should not depend solely on the FPGA being monitored.",
    code: String.raw`module heartbeat_watchdog #(
  parameter integer TIMEOUT_TICKS=1_000_000
) (
  input  logic clk, rst_n, heartbeat, clear_fault,
  output logic safe_state_request,
  output logic [31:0] age
);
  always_ff @(posedge clk) begin
    if (!rst_n) begin age<=0; safe_state_request<=0; end
    else begin
      if (heartbeat) age<=0;
      else if (age<TIMEOUT_TICKS) age<=age+1'b1;
      if (age==TIMEOUT_TICKS-1) safe_state_request<=1'b1;
      if (clear_fault && heartbeat) safe_state_request<=1'b0;
    end
  end
endmodule`,
  },
  {
    id: "use_22",
    file: "22_tmr_voter.sv",
    note: "A bitwise majority voter with disagreement telemetry. TMR only helps when the three replicas, voters, clocks, resets, placement, and state repair strategy avoid common-mode failures.",
    code: String.raw`module tmr_voter #(
  parameter integer WIDTH=32
) (
  input  logic [WIDTH-1:0] a, b, c,
  output logic [WIDTH-1:0] voted,
  output logic disagreement
);
  always_comb begin
    voted = (a & b) | (a & c) | (b & c);
    disagreement = (a!=b) || (a!=c) || (b!=c);
  end
endmodule`,
  },
  {
    id: "use_23",
    file: "23_ecc_scrub_controller.sv",
    note: "A controller around a qualified ECC memory: it periodically reads every address and writes corrected data back after a correctable error. The ECC codec itself should normally be the characterized device or memory-controller implementation.",
    code: String.raw`module ecc_scrub_controller #(
  parameter integer ADDR_WIDTH=12, PERIOD=1024
) (
  input  logic clk, rst_n,
  output logic [ADDR_WIDTH-1:0] mem_addr,
  output logic mem_read, mem_write,
  input  logic read_valid, correctable_error, uncorrectable_error,
  input  logic [31:0] corrected_data,
  output logic [31:0] write_data,
  output logic fatal_error
);
  typedef enum logic [1:0] {IDLE,WAIT_READ,WRITE_BACK,ADVANCE} state_t;
  state_t state;
  logic [$clog2(PERIOD)-1:0] timer;
  always_ff @(posedge clk) begin
    if (!rst_n) begin
      state<=IDLE; timer<=0; mem_addr<=0; mem_read<=0; mem_write<=0; fatal_error<=0;
    end
    else begin
      mem_read<=0; mem_write<=0;
      case (state)
        IDLE: if (timer==PERIOD-1) begin
          timer<=0; mem_read<=1'b1; state<=WAIT_READ;
        end else timer<=timer+1'b1;
        WAIT_READ: if (read_valid) begin
          if (uncorrectable_error) fatal_error<=1'b1;
          if (correctable_error) begin write_data<=corrected_data; state<=WRITE_BACK; end
          else state<=ADVANCE;
        end
        WRITE_BACK: begin mem_write<=1'b1; state<=ADVANCE; end
        ADVANCE: begin mem_addr<=mem_addr+1'b1; state<=IDLE; end
      endcase
    end
  end
endmodule`,
  },
  {
    id: "use_24",
    file: "24_redundancy_manager.sv",
    note: "A simple A/B function selector that changes sides only when the active side has failed and the standby reports healthy. Real cross-strapping adds debounce, hysteresis, command authority, state synchronization, and independent hardware protection.",
    code: String.raw`module redundancy_manager (
  input  logic clk, rst_n, clear_fault,
  input  logic a_healthy, b_healthy,
  output logic select_b, no_healthy_side
);
  always_ff @(posedge clk) begin
    if (!rst_n) begin select_b<=0; no_healthy_side<=0; end
    else begin
      no_healthy_side <= !a_healthy && !b_healthy;
      if (!select_b && !a_healthy && b_healthy) select_b<=1'b1;
      else if (select_b && !b_healthy && a_healthy) select_b<=1'b0;
      if (clear_fault && a_healthy) select_b<=1'b0;
    end
  end
endmodule`,
  },
  {
    id: "use_25",
    file: "25_authenticated_link_wrapper.sv",
    note: "A security wrapper showing key loading, zeroization, and the interface to a vetted authenticated-encryption core. Do not create a new AES/GCM implementation from a short report snippet; use a reviewed, side-channel-assessed core and mission key-management design.",
    code: String.raw`module authenticated_link_wrapper (
  input  logic clk, rst_n, load_key, zeroize,
  input  logic [255:0] key_in,
  input  logic data_valid,
  input  logic [127:0] plaintext,
  output logic cipher_valid, auth_fail,
  output logic [127:0] ciphertext
);
  logic [255:0] key_reg;
  always_ff @(posedge clk) begin
    if (!rst_n || zeroize) key_reg<='0;
    else if (load_key) key_reg<=key_in;
  end
  qualified_aead_core core (
    .clk(clk), .rst_n(rst_n), .key(key_reg),
    .in_valid(data_valid), .plaintext(plaintext),
    .out_valid(cipher_valid), .ciphertext(ciphertext),
    .authentication_failure(auth_fail)
  );
endmodule`,
  },
  {
    id: "use_26",
    file: "26_actuator_pwm.sv",
    note: "A single-ended PWM command with enable and over-current interlocks. A real motor power stage needs dead-time generation, current-loop control, limit switches, watchdogs, and hardware shutdown independent of this logic.",
    code: String.raw`module actuator_pwm #(
  parameter integer PERIOD=4096
) (
  input  logic clk, rst_n, enable, over_current,
  input  logic [$clog2(PERIOD)-1:0] duty,
  input  logic direction_command,
  output logic pwm, direction, fault
);
  logic [$clog2(PERIOD)-1:0] counter;
  always_ff @(posedge clk) begin
    if (!rst_n) begin counter<=0; pwm<=0; direction<=0; fault<=0; end
    else begin
      counter <= (counter==PERIOD-1) ? '0 : counter+1'b1;
      if (over_current) fault<=1'b1;
      if (!enable || fault) pwm<=1'b0;
      else begin pwm <= (counter<duty); direction<=direction_command; end
    end
  end
endmodule`,
  },
  {
    id: "use_27",
    file: "27_power_window_supervisor.sv",
    note: "A digital voltage-window supervisor that requires consecutive bad samples before latching a trip. Analog comparators and power-controller hardware should enforce absolute safety limits even if the FPGA is unavailable.",
    code: String.raw`module power_window_supervisor #(
  parameter integer BAD_LIMIT=8
) (
  input  logic clk, rst_n, sample_valid, clear_trip,
  input  logic [15:0] voltage, minimum, maximum,
  output logic trip,
  output logic [$clog2(BAD_LIMIT+1)-1:0] bad_count
);
  always_ff @(posedge clk) begin
    if (!rst_n) begin bad_count<=0; trip<=0; end
    else begin
      if (sample_valid) begin
        if (voltage<minimum || voltage>maximum) begin
          if (bad_count<BAD_LIMIT) bad_count<=bad_count+1'b1;
          if (bad_count==BAD_LIMIT-1) trip<=1'b1;
        end else bad_count<=0;
      end
      if (clear_trip && voltage>=minimum && voltage<=maximum) trip<=1'b0;
    end
  end
endmodule`,
  },
  {
    id: "use_28",
    file: "28_stream_dot_accelerator.sv",
    note: "A streaming dot-product accelerator that returns one accumulated result at the final pair. Production accelerators add DMA, multiple MAC lanes, saturation/rounding, cache coherency rules, and timeout/error registers.",
    code: String.raw`module stream_dot_accelerator (
  input  logic clk, rst_n, start, pair_valid, last_pair,
  input  logic signed [15:0] a, b,
  output logic result_valid,
  output logic signed [47:0] result
);
  logic signed [47:0] accumulator;
  always_ff @(posedge clk) begin
    if (!rst_n) begin accumulator<=0; result<=0; result_valid<=0; end
    else begin
      result_valid<=1'b0;
      if (start) accumulator<=0;
      if (pair_valid) begin
        accumulator<=accumulator+a*b;
        if (last_pair) begin result<=accumulator+a*b; result_valid<=1'b1; end
      end
    end
  end
endmodule`,
  },
  {
    id: "use_29",
    file: "29_softcore_mmio_peripheral.sv",
    note: "A memory-mapped peripheral for a soft-core CPU: software writes a control register and reads telemetry. The bus adapter, access protection, CDC, timeout behavior, and register upset protection depend on the selected processor interconnect.",
    code: String.raw`module softcore_mmio_peripheral (
  input  logic clk, rst_n, write_strobe, read_strobe,
  input  logic [7:0] address,
  input  logic [31:0] write_data,
  input  logic [31:0] telemetry,
  output logic [31:0] read_data,
  output logic [31:0] control
);
  always_ff @(posedge clk) begin
    if (!rst_n) control<=0;
    else if (write_strobe && address==8'h00) control<=write_data;
  end
  always_comb begin
    read_data=32'h0;
    if (read_strobe) case(address)
      8'h00: read_data=control;
      8'h04: read_data=telemetry;
      default: read_data=32'hDEAD_BEEF;
    endcase
  end
endmodule`,
  },
  {
    id: "use_30",
    file: "30_reconfiguration_manager.sv",
    note: "A supervisory state machine that permits an update image only after validation and falls back to the golden image when the new design fails to produce a heartbeat. The actual configuration port is device-specific and must be controlled by an independent, recoverable path.",
    code: String.raw`module reconfiguration_manager #(
  parameter integer HEARTBEAT_TIMEOUT=1_000_000
) (
  input  logic clk, rst_n, request_update, image_valid, heartbeat,
  output logic select_update_image, reconfigure_go, fallback_event
);
  typedef enum logic [1:0] {GOLDEN,LOAD_UPDATE,MONITOR,LOAD_GOLDEN} state_t;
  state_t state;
  logic [31:0] age;
  always_ff @(posedge clk) begin
    if (!rst_n) begin
      state<=GOLDEN; age<=0; select_update_image<=0;
      reconfigure_go<=0; fallback_event<=0;
    end
    else begin
      reconfigure_go<=0;
      case(state)
        GOLDEN: if(request_update && image_valid) state<=LOAD_UPDATE;
        LOAD_UPDATE: begin select_update_image<=1; reconfigure_go<=1; age<=0; state<=MONITOR; end
        MONITOR: if(heartbeat) age<=0;
                 else if(age==HEARTBEAT_TIMEOUT-1) state<=LOAD_GOLDEN;
                 else age<=age+1'b1;
        LOAD_GOLDEN: begin select_update_image<=0; reconfigure_go<=1;
          fallback_event<=1; state<=GOLDEN; end
      endcase
    end
  end
endmodule`,
  },
];

const artifact = JSON.parse(fs.readFileSync(sourcePath, "utf8"));

const newTitle =
  "How FPGAs Are Used in Space: 30 Implementation Recipes with HDL Examples";
artifact.manifest.title = newTitle;
artifact.manifest.description =
  "Thirty detailed spacecraft FPGA implementation recipes, each with a synthesizable SystemVerilog kernel or qualified-IP wrapper example.";
artifact.manifest.generatedAt = "2026-07-17T00:00:00Z";
artifact.snapshot.generatedAt = "2026-07-17T00:00:00Z";

const titleBlock = artifact.manifest.blocks.find((block) => block.id === "title");
titleBlock.body = `# ${newTitle}`;

const summaryBlock = artifact.manifest.blocks.find(
  (block) => block.id === "technical_summary",
);
summaryBlock.body +=
  "\n\n**Every recipe now includes an HDL example.** The examples use SystemVerilog and demonstrate the smallest useful synthesizable kernel, interface wrapper, or supervisory state machine for the function. They are teaching and architecture examples, not flight-qualified IP.";

const scopeBlock = artifact.manifest.blocks.find((block) => block.id === "scope");
scopeBlock.body +=
  "\n\n### How to use the HDL examples\n\nThe snippets target modern SystemVerilog synthesis. They intentionally omit device pin constraints, clock-generation primitives, CDC wrappers, vendor transceivers, memories, configuration ports, and complete protocol stacks. Treat widths, latencies, reset polarity, thresholds, and constants as placeholders derived from requirements. For cryptography, high-speed PHYs, ECC codecs, FEC, and configuration access, instantiate a characterized or qualified core and use the snippet as the control/data wrapper. Before hardware use, add a self-checking testbench, assertions, lint, CDC/RDC checks, timing constraints, fault injection, and mission-device synthesis.\n\n**Compiler status.** All 30 distributed snippets were compiled successfully with Icarus Verilog 12.0 in SystemVerilog-2012 mode (`-g2012 -t null -i`). This proves parser and elaboration acceptance only; it does not replace testbenches, synthesis, timing closure, or target-device verification.";

fs.mkdirSync(snippetDir, { recursive: true });

for (const snippet of snippets) {
  const block = artifact.manifest.blocks.find((candidate) => candidate.id === snippet.id);
  if (!block) throw new Error(`Missing report block ${snippet.id}`);
  if (block.body.includes("### Illustrative HDL kernel")) {
    throw new Error(`Report block ${snippet.id} already contains an HDL snippet`);
  }

  const fence = "```";
  const section =
    `\n\n### Illustrative HDL kernel (SystemVerilog)\n\n${snippet.note}` +
    `\n\n${fence}systemverilog\n${snippet.code}\n${fence}\n`;
  block.body = block.body.replace("\n\n### Verification", `${section}\n### Verification`);

  const fileText =
    `// ${snippet.note}\n` +
    "// Educational architecture snippet; not flight-qualified IP.\n\n" +
    snippet.code +
    "\n";
  fs.writeFileSync(path.join(snippetDir, snippet.file), fileText, "utf8");
}

fs.writeFileSync(outputPath, JSON.stringify(artifact, null, 2), "utf8");

console.log(
  JSON.stringify({
    outputPath,
    snippetDir,
    snippets: snippets.length,
    recipeBlocks: artifact.manifest.blocks.filter((block) => /^use_\d+$/.test(block.id))
      .length,
    blocks: artifact.manifest.blocks.length,
  }),
);
