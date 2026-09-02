import fs from "node:fs";
import path from "node:path";

const basePath =
  "C:/Users/user/Documents/Codex/2026-07-14/i-w/outputs/fpga_space_uses_implementation_with_hdl_artifact.json";
const outputPath =
  "C:/Users/user/Documents/Codex/2026-07-14/i-w/outputs/fpga_3u_hosted_experiment_service_artifact.json";
const originalHdlDir =
  "C:/Users/user/Documents/Codex/2026-07-14/i-w/outputs/fpga_space_hdl_snippets";
const serviceHdlDir =
  "C:/Users/user/Documents/Codex/2026-07-14/i-w/outputs/fpga_3u_hosted_service_hdl";

const base = JSON.parse(fs.readFileSync(basePath, "utf8"));
const fence = "```";

const selectedGroups = [
  {
    id: "direct",
    title: "Direct hosted experiments use the three payload data streams",
    intro:
      "These nine roles can operate on camera pixels, ADS-B messages or bounded IQ windows, lightning RF windows/features, and operator-provided test vectors. Only one tenant configuration should run at a time in the first flight version.",
    uses: ["use_01", "use_02", "use_03", "use_04", "use_05", "use_16", "use_17", "use_28", "use_29"],
  },
  {
    id: "sandbox",
    title: "Four additional roles fit only as isolated recorded-data sandboxes",
    intro:
      "These functions are acceptable when they operate on virtual streams, dummy keys, or injected faults inside the experiment partition. They must never connect directly to the spacecraft network, mission cryptographic material, RF transmitter, or safety-critical control.",
    uses: ["use_09", "use_10", "use_22", "use_25"],
  },
  {
    id: "infrastructure",
    title: "Five roles belong to the trusted service shell, not tenant logic",
    intro:
      "Storage, time, fault recovery, protected memory, and reconfiguration make the hosted service possible. The spacecraft operator owns and qualifies these blocks; experimenters consume their bounded interfaces but cannot replace them.",
    uses: ["use_11", "use_19", "use_21", "use_23", "use_30"],
  },
];

const boundaryNotes = {
  use_01: "Tenant logic receives framed, timestamped samples from the trusted shell; it does not control sensor pins, clocks, ADC setup, or camera exposure.",
  use_02: "The service supplies cropped frames, tiles, or line streams. Full-rate raw imagery is available only within a declared storage and execution quota.",
  use_03: "Compression experiments may return compressed blocks and statistics, but only the shell writes flight storage or decides what baseline science data must be retained.",
  use_04: "SDR experiments are receive-only and operate on bounded IQ windows or replayed recordings. Tenant logic has no RF transmit path, synthesizer control, or direct antenna connection.",
  use_05: "Coding experiments process test or payload data streams. They cannot replace the spacecraft command/telemetry coding chain during flight.",
  use_09: "Network experiments run on a virtual packet fabric with synthetic addresses and quotas; the mission SpaceWire, SpaceFibre, CAN, or Ethernet control plane remains inaccessible.",
  use_10: "Protocol conversion is limited to operator-defined virtual endpoints. A tenant cannot become a bus master on the spacecraft avionics network.",
  use_11: "The shell owns ECC storage, DMA descriptors, partitioning, retention policy, and erase operations. Tenants receive logical objects or bounded streaming buffers.",
  use_16: "Inference experiments use signed model packages, bounded weights, and test vectors. The model may classify or rank data but does not command attitude, power, or RF transmission.",
  use_17: "Data-reduction experiments must preserve operator-defined background samples and raw event windows so false negatives can be measured on the ground.",
  use_19: "The shell distributes read-only mission time and PPS-derived timestamps. Tenant logic cannot discipline the spacecraft clock or change time correlation.",
  use_21: "Watchdogs, thermal trips, power trips, timeout enforcement, partition reset, and rollback stay in static trusted logic and an external supervisor.",
  use_22: "Fault-tolerance experiments may inject faults only into tenant state or operator-provided replicas. Fault injection into the shell, sensors, bus, or configuration controller is prohibited.",
  use_23: "The shell protects tenant buffers and bitstreams with ECC, integrity checks, and scrubbing. Tenants may study ECC using separate experimental memories.",
  use_25: "Cryptographic experiments use dummy keys and synthetic data. Mission keys, authentication roots, bitstream-signing keys, and command security are never exposed.",
  use_28: "Accelerators receive bounded buffers or streams and return results through the shell. Direct memory access is translated and range-checked by trusted DMA.",
  use_29: "A soft-core may run inside the partition with local BRAM and a small register window; it has no unrestricted external memory, configuration-port, or device-pin access.",
  use_30: "Only the trusted supervisor can load a signed image, isolate the partition, request reconfiguration, verify recovery, or select the golden image.",
};

const fileForUse = {
  use_01: "01_payload_capture.sv",
  use_02: "02_sobel_pixel_kernel.sv",
  use_03: "03_delta_run_compressor.sv",
  use_04: "04_sdr_complex_mixer.sv",
  use_05: "05_convolutional_encoder.sv",
  use_09: "09_round_robin_arbiter.sv",
  use_10: "10_ready_valid_to_req_ack.sv",
  use_11: "11_circular_dma_address.sv",
  use_16: "16_quantized_neuron_mac.sv",
  use_17: "17_event_data_gate.sv",
  use_19: "19_pps_disciplined_clock.sv",
  use_21: "21_heartbeat_watchdog.sv",
  use_22: "22_tmr_voter.sv",
  use_23: "23_ecc_scrub_controller.sv",
  use_25: "25_authenticated_link_wrapper.sv",
  use_28: "28_stream_dot_accelerator.sv",
  use_29: "29_softcore_mmio_peripheral.sv",
  use_30: "30_reconfiguration_manager.sv",
};

const serviceModules = [
  {
    file: "31_experiment_slot_controller.sv",
    note:
      "Trusted run-state controller. It holds the experiment in reset until an image is verified and armed, enforces total-runtime and heartbeat limits, and requests rollback on experiment, power, or thermal faults.",
    code: String.raw`module experiment_slot_controller #(
  parameter integer RUN_LIMIT=10_000_000,
  parameter integer HEARTBEAT_LIMIT=100_000,
  parameter integer DRAIN_CYCLES=64
) (
  input  logic clk, rst_n,
  input  logic image_verified, arm_cmd, start_cmd, stop_cmd,
  input  logic heartbeat, experiment_fault, power_fault, thermal_fault,
  output logic experiment_reset_n, stream_enable, capture_enable,
  output logic rollback_request,
  output logic [2:0] state_code
);
  typedef enum logic [2:0] {IDLE,ARMED,RUN,DRAIN,FAULT} state_t;
  state_t state;
  logic [31:0] run_age, heartbeat_age, drain_age;

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      state<=IDLE; run_age<=0; heartbeat_age<=0; drain_age<=0;
      experiment_reset_n<=0; stream_enable<=0; capture_enable<=0;
      rollback_request<=0;
    end else case (state)
      IDLE: begin
        experiment_reset_n<=0; stream_enable<=0; capture_enable<=0;
        rollback_request<=0;
        if (image_verified && arm_cmd) state<=ARMED;
      end
      ARMED: if (!arm_cmd) state<=IDLE;
        else if (start_cmd) begin
          experiment_reset_n<=1; stream_enable<=1; capture_enable<=1;
          run_age<=0; heartbeat_age<=0; state<=RUN;
        end
      RUN: begin
        run_age<=run_age+1'b1;
        if (heartbeat) heartbeat_age<=0; else heartbeat_age<=heartbeat_age+1'b1;
        if (stop_cmd) begin stream_enable<=0; drain_age<=0; state<=DRAIN; end
        else if (experiment_fault || power_fault || thermal_fault ||
                 run_age>=RUN_LIMIT-1 || heartbeat_age>=HEARTBEAT_LIMIT-1)
          state<=FAULT;
      end
      DRAIN: begin
        drain_age<=drain_age+1'b1;
        if (drain_age>=DRAIN_CYCLES-1) begin
          capture_enable<=0; experiment_reset_n<=0; state<=IDLE;
        end
      end
      FAULT: begin
        experiment_reset_n<=0; stream_enable<=0; capture_enable<=0;
        rollback_request<=1;
        if (!arm_cmd) state<=IDLE;
      end
    endcase
  end
  assign state_code=state;
endmodule`,
  },
  {
    file: "32_stream_quota_guard.sv",
    note:
      "Trusted ready/valid guard. It passes at most MAX_WORDS accepted output words during a run, blocks further output, and raises a sticky quota violation without trusting tenant backpressure behavior.",
    code: String.raw`module stream_quota_guard #(
  parameter integer WIDTH=32,
  parameter integer MAX_WORDS=4096
) (
  input  logic clk, rst_n, clear, enable,
  input  logic s_valid,
  input  logic [WIDTH-1:0] s_data,
  output logic s_ready,
  output logic m_valid,
  output logic [WIDTH-1:0] m_data,
  input  logic m_ready,
  output logic [31:0] accepted_words,
  output logic quota_violation
);
  logic quota_open;
  assign quota_open=(accepted_words<MAX_WORDS);
  assign m_valid=s_valid && enable && quota_open;
  assign m_data=s_data;
  assign s_ready=m_ready && enable && quota_open;

  always_ff @(posedge clk) begin
    if (!rst_n || clear) begin accepted_words<=0; quota_violation<=0; end
    else begin
      if (m_valid && m_ready) accepted_words<=accepted_words+1'b1;
      if (s_valid && enable && !quota_open) quota_violation<=1'b1;
    end
  end
endmodule`,
  },
  {
    file: "33_register_firewall.sv",
    note:
      "Trusted MMIO firewall. Only a small experiment register window is forwarded; every other request is blocked and reported.",
    code: String.raw`module register_firewall (
  input  logic clk, rst_n,
  input  logic bus_valid, bus_write,
  input  logic [15:0] bus_address,
  input  logic [31:0] bus_write_data,
  output logic tenant_valid, tenant_write,
  output logic [5:0] tenant_address,
  output logic [31:0] tenant_write_data,
  output logic blocked_request
);
  logic allowed;
  assign allowed=(bus_address>=16'h8000 && bus_address<=16'h803f);
  always_ff @(posedge clk) begin
    if (!rst_n) begin tenant_valid<=0; blocked_request<=0; end
    else begin
      tenant_valid<=bus_valid && allowed;
      tenant_write<=bus_write; tenant_address<=bus_address[5:0];
      tenant_write_data<=bus_write_data;
      if (bus_valid && !allowed) blocked_request<=1'b1;
    end
  end
endmodule`,
  },
  {
    file: "34_experiment_telemetry.sv",
    note:
      "Trusted per-run telemetry counters. The operator can compare intended work, stalls, output volume, heartbeats, and fault events before accepting experiment results.",
    code: String.raw`module experiment_telemetry (
  input  logic clk, rst_n, clear, run_active,
  input  logic input_accept, output_accept, output_stall,
  input  logic heartbeat, fault_event,
  output logic [31:0] active_cycles, inputs, outputs, stalls,
  output logic [31:0] heartbeats, faults
);
  always_ff @(posedge clk) begin
    if (!rst_n || clear) begin
      active_cycles<=0; inputs<=0; outputs<=0; stalls<=0;
      heartbeats<=0; faults<=0;
    end else begin
      if (run_active) active_cycles<=active_cycles+1'b1;
      if (input_accept) inputs<=inputs+1'b1;
      if (output_accept) outputs<=outputs+1'b1;
      if (output_stall) stalls<=stalls+1'b1;
      if (heartbeat) heartbeats<=heartbeats+1'b1;
      if (fault_event) faults<=faults+1'b1;
    end
  end
endmodule`,
  },
  {
    file: "35_thermal_power_guard.sv",
    note:
      "Trusted limit guard using digitized temperature and power telemetry. Analog hardware must still enforce absolute electrical limits outside the FPGA.",
    code: String.raw`module thermal_power_guard #(
  parameter integer GOOD_SAMPLES_TO_CLEAR=16
) (
  input  logic clk, rst_n, sample_valid, operator_clear,
  input  logic [15:0] temperature, maximum_temperature,
  input  logic [15:0] power, maximum_power,
  output logic trip,
  output logic [7:0] good_samples
);
  logic within_limits;
  assign within_limits=(temperature<=maximum_temperature) &&
                       (power<=maximum_power);
  always_ff @(posedge clk) begin
    if (!rst_n) begin trip<=0; good_samples<=0; end
    else if (sample_valid) begin
      if (!within_limits) begin trip<=1; good_samples<=0; end
      else if (good_samples<GOOD_SAMPLES_TO_CLEAR)
        good_samples<=good_samples+1'b1;
      if (operator_clear && within_limits &&
          good_samples>=GOOD_SAMPLES_TO_CLEAR-1) trip<=0;
    end
  end
endmodule`,
  },
];

function markdown(id, body) {
  return { id, type: "markdown", body };
}

function selectedUseBlock(useId, displayNumber) {
  const source = base.manifest.blocks.find((block) => block.id === useId);
  if (!source) throw new Error(`Missing ${useId}`);
  const clone = structuredClone(source);
  const originalNumber = Number(useId.slice(-2));
  clone.id = `hosted_${useId}`;
  clone.body = clone.body.replace(
    /^##\s+\d+\.\s+(.+)$/m,
    `## Hosted role ${displayNumber}. $1`,
  );
  clone.body = clone.body.replace(
    /\n\n\*\*What it does\.\*\*/,
    `\n\n**Hosted-service boundary.** ${boundaryNotes[useId]}\n\n**What it does.**`,
  );
  clone.body += `\n\n*Original catalog reference: use ${originalNumber}.*`;
  return clone;
}

const title = "3U CubeSat Hosted FPGA Experiment Service";
const blocks = [
  markdown("title", `# ${title}`),
  markdown(
    "technical_summary",
    `## Technical summary\n\n**The concept is feasible only as a time-shared, operator-controlled experiment service.** The camera, ADS-B receiver, lightning RF receiver, configuration controller, storage, time service, power/thermal protection, and spacecraft interfaces remain in a trusted static shell. Qualified users receive one bounded reconfigurable partition or a software/model slot; they never upload an arbitrary bitstream directly to the spacecraft.\n\nA 3U implementation is conditional on the existing bus providing enough payload volume, power, thermal rejection, nadir aperture, antenna accommodation, storage, and downlink. The report uses provisional design-screen assumptions because the actual bus interface-control document is not available. If those assumptions fail, reduce the service to model/parameter uploads or move the payload to 6U.\n\n**Recommended operational split:** run lightweight detection, classification, compression, and event selection onboard; run lightning forecasting, model training, multi-source weather fusion, and final scientific analysis on the ground.`,
  ),
  markdown(
    "fit_assumptions",
    `## A 3U service needs a deliberately narrow accommodation envelope\n\nThe CubeSat standard defines the external spacecraft envelope, not free payload volume. This report assumes an already-integrated 3U bus and screens a custom combined payload—not separate commercial modules. [CubeSat Design Specification Rev. 14.1](https://www.nasa.gov/wp-content/uploads/2018/01/cubesatdesignspecificationrev14_12022-02-09.pdf)\n\n**Provisional design-screen targets, not confirmed allocations:**\n\n| Item | Screening target |\n|---|---|\n| Remaining payload volume | Prefer at least 1.0–1.3U with a usable nadir aperture |\n| Payload average power | Approximately 5–8 W during routine collection |\n| Payload peak power | Approximately 12–15 W during FPGA experiments |\n| Heat rejection | A characterized conductive path for roughly 8–12 W peak dissipation |\n| External interfaces | Nadir optical aperture plus ADS-B and lightning-RF antenna accommodation |\n| Operation | One tenant configuration at a time; receive-only experimental RF |\n\nThese values are engineering placeholders for an early go/no-go review. Replace them with the actual bus dimensions, rail limits, battery/eclipse energy, allowable heat load, pointing performance, storage, and downlink. NASA notes that high-power SmallSat payloads such as multispectral imaging place materially higher demands on power management. [NASA SmallSat power systems](https://www.nasa.gov/smallsat-institute/sst-soa/power-subsystems/)`,
  ),
  markdown(
    "role_chart_intro",
    `## Eighteen retained roles divide into experiments, sandboxes, and trusted infrastructure\n\nThe chart counts logical roles, not simultaneously instantiated hardware. Nine roles directly process payload data, four are optional isolated sandboxes, and five are operator-owned infrastructure. Dynamic reconfiguration or sequential scheduling allows these roles to share one FPGA footprint.`,
  ),
  { id: "hosted_role_chart_block", type: "chart", chartId: "hosted_role_chart" },
  markdown(
    "service_architecture",
    `## A static shell must remain in control of every experiment\n\nThe service boundary should be fixed before selecting the FPGA:\n\n\`\`\`text\nCamera head ───────┐\nADS-B 1090 MHz ────┼─> trusted ingress, timestamp and ring buffers ─┐\nLightning RF ──────┘                                                │\n                                                                    v\nExternal supervisor <─> signed-image store <─> static FPGA shell <─> tenant partition\n        │                                      │                    │\n        └─ golden recovery                     ├─ quota/firewall     ├─ stream input\n                                               ├─ watchdog           ├─ stream output\n                                               ├─ ECC/scrubbing      ├─ small MMIO window\n                                               └─ storage/downlink   └─ heartbeat/fault\n\`\`\`\n\nThe tenant partition receives fixed clocks, synchronized reset, ready/valid streams, bounded buffers, read-only time, and a small register window. It has no direct access to device pins, PLLs, transceivers, configuration ports, spacecraft buses, mission storage descriptors, command decoding, mission keys, attitude control, power switching, or RF transmission.`,
  ),
  markdown(
    "data_products",
    `## The service should publish bounded data products, not unrestricted sensors\n\nA qualified experiment selects one or more operator-defined inputs:\n\n- **Optical:** cropped frames, tiles, line streams, background-subtracted pixels, or short raw event windows.\n- **ADS-B:** decoded 1090ES messages, pulse features, or tightly bounded IQ windows. The FAA identifies 1090 MHz as the common international ADS-B link. [FAA ADS-B guidance](https://www.faa.gov/air_traffic/publications/atpubs/aim_html/chap4_section_5.html)\n- **Lightning RF:** bounded VHF windows, spectra, pulse descriptors, or optical/RF coincidence records. The exact band and antenna remain a payload science decision; space-based VHF detection has demonstrated the importance of propagation and interference characterization. [NASA VHF lightning study](https://ntrs.nasa.gov/api/citations/20240005740/downloads/FINAL_VERSION.pdf)\n- **Playback:** operator-curated archived data and synthetic vectors for repeatable comparisons.\n\nContinuous raw camera or wideband-IQ access is incompatible with a small spacecraft’s storage and downlink. NOAA’s much larger GLM uses a 777.4 nm band and 2 ms frames, illustrating why onboard event extraction is essential even though a CubeSat implementation will be much smaller. [NOAA GLM](https://goes-r.noaa.gov/spacesegment/glm.html)`,
  ),
  markdown(
    "configuration_modes",
    `## Four configuration modes provide a sensible path from low to high risk\n\n1. **Model and parameter service — recommended first flight.** Users upload signed neural-network weights, filter coefficients, thresholds, or soft-core software into a prequalified accelerator. The FPGA bitstream does not change.\n\n2. **Prequalified accelerator catalog.** The operator builds and qualifies a library of image, compression, DSP, AI, and fault-tolerance modules. Users select a module and provide data or parameters.\n\n3. **Partial reconfiguration service.** A trusted static shell remains active while one signed reconfigurable module is loaded into a fixed partition. AMD calls this Dynamic Function eXchange: static logic remains in place while the reconfigurable region changes. [AMD DFX](https://docs.amd.com/r/2024.2-English/ug909-vivado-partial-reconfiguration/Introduction)\n\n4. **Full payload-image replacement.** An external supervisor isolates the payload FPGA, loads a complete signed image, verifies startup, and returns to a golden image on failure. Microchip documents external-controller-based in-flight reprogramming for RTG4 and RT PolarFire. [Microchip in-flight reprogramming](https://www.microchip.com/en-us/development-tool/fpga-in-flight-reprogramming)\n\nStart with modes 1 and 2. Add mode 3 only after the static shell, partition boundaries, power behavior, and ground qualification pipeline are mature. Mode 4 is a recovery and operator-maintenance mechanism before it is offered as a tenant service.`,
  ),
  markdown(
    "qualification_pipeline",
    `## Qualified users still submit experiments through an operator-owned build pipeline\n\nA user should submit RTL or HLS source, testbench, expected outputs, resource request, clock requirement, runtime limit, data-product request, model or coefficient files, and a signed experiment manifest. The operator—not the user—builds the flight image.\n\nThe acceptance pipeline should require:\n\n1. Identity, organization, experiment purpose, data rights, and applicable regulatory/program-policy review.\n2. Reproducible toolchain container and immutable source/dependency hashes.\n3. Lint, synthesizability, forbidden-primitive checks, CDC/RDC analysis, and assertions.\n4. Static-shell interface conformance; no extra clocks, pins, configuration access, unrestricted memory masters, or combinational paths across the boundary.\n5. Resource, timing, clock, toggle-rate, and conservative power checks against the booked quota.\n6. Self-checking simulation with nominal, malformed, backpressure, reset, timeout, and maximum-rate cases.\n7. Hardware-in-the-loop execution on an engineering model with the same shell and memory map.\n8. Power/thermal soak, watchdog tests, forced stalls, fault injection, and golden-image rollback demonstration.\n9. Operator-generated bitstream, compatibility verification, mission signature, version/expiry metadata, and encrypted storage where supported.\n10. Human flight-operations approval and a rehearsed rollback procedure.\n\nECSS-E-ST-20-40C provides a current engineering framework for FPGA and IP-core development; the project would tailor it to the hosted-experiment criticality. [ECSS FPGA engineering](https://ecss.nl/standard/ecss-e-st-20-40c-asic-fpga-and-ip-core-engineering-11-october-2023/)`,
  ),
  markdown(
    "runtime_lifecycle",
    `## Every flight run should be a bounded transaction\n\nThe flight lifecycle is: upload to inactive storage → verify length/hash/signature/compatibility → wait for power, temperature, attitude and communications conditions → isolate and reset the partition → configure → run known-answer self-test → enable a bounded input → capture output and health telemetry → stop and drain → reset → archive results → return to blank or golden configuration.\n\nA run ends immediately on heartbeat loss, timeout, output quota, illegal register access, malformed stream behavior, ECC escalation, configuration error, over-temperature, over-power, spacecraft safe mode, or operator abort. The external supervisor must be able to reset or depower the payload even when the FPGA is non-responsive.`,
  ),
  markdown(
    "resource_contract",
    `## The booking contract must reserve physical resources and operational budgets\n\nEach experiment manifest should state maximum LUTs, flip-flops, DSPs, BRAM/URAM, clock frequency, input/output words, external-memory bytes, expected and worst-case runtime, maximum output, predicted dynamic power, allowed data products, and required telemetry. The first version should expose one fixed clock and one reconfigurable partition sized for the largest accepted experiment; unused resources stay unavailable rather than being dynamically lent between tenants.\n\nRun one tenant at a time. This simplifies isolation, attribution, thermal analysis, recovery, and scientific comparison. Concurrent tenants can be considered only after the single-tenant service has flight evidence.`,
  ),
  markdown(
    "service_hdl",
    `## Trusted HDL enforces runtime and data quotas around the tenant partition\n\nThe complete package contains five new shell examples. The two central patterns are shown below.\n\n### Experiment slot controller\n\n${serviceModules[0].note}\n\n${fence}systemverilog\n${serviceModules[0].code}\n${fence}\n\n### Stream quota guard\n\n${serviceModules[1].note}\n\n${fence}systemverilog\n${serviceModules[1].code}\n${fence}\n\nThese examples are architecture kernels, not a complete security boundary. Device-specific isolation primitives, partial-reconfiguration decouplers, authenticated boot, bitstream verification, analog power protection, and the external supervisor must complete the design.`,
  ),
];

let hostedNumber = 1;
for (const group of selectedGroups) {
  blocks.push(markdown(`group_${group.id}`, `## ${group.title}\n\n${group.intro}`));
  for (const useId of group.uses) blocks.push(selectedUseBlock(useId, hostedNumber++));
}

blocks.push(
  markdown(
    "excluded_uses",
    `## Safety-critical and high-aperture uses are intentionally excluded\n\nThe hosted service does not expose direct GNC, star-tracker control, autonomous landing, actuator/motor control, power switching, primary C&DH, spacecraft command decoding, mission cryptography, RF transmission, optical communications, radar/SAR transmission, or unrestricted beamforming. These functions either require hardware the 3U payload does not carry or could jeopardize the spacecraft if tenant logic failed.\n\nResearchers may still evaluate such algorithms against recorded or synthetic data when the result remains a passive data product. For example, a navigation filter may process archived imagery, but it cannot feed the flight ADCS.`,
  ),
  markdown(
    "onboard_ground_split",
    `## Onboard experiments should detect and reduce data; the ground should forecast\n\nFor the lightning mission, the onboard service is well suited to optical/RF coincidence, pulse classification, event scoring, compression, and retention of pre/post-trigger windows. A full predictive weather model belongs on the ground because it benefits from radar, meteorological satellites, numerical weather prediction, and historical context unavailable to one 3U spacecraft.\n\nEvery onboard model should retain operator-defined background samples and uncertain events. Ground analysts need those negatives to measure selection bias, false dismissals, radiation-induced errors, and model drift.`,
  ),
  markdown(
    "limitations",
    `## The concept remains conditional until the existing bus is measured\n\nThis document does not prove accommodation, radiation tolerance, regulatory compliance, link closure, thermal closure, or business/service viability. The decisive missing inputs are the bus payload bay dimensions, mass allocation, rail limits, battery/eclipse energy, conductive thermal interface, pointing and jitter, orbit, antenna locations, RF coexistence plan, storage, downlink, FPGA device, configuration technology, and acceptable mission risk.\n\nPartial reconfiguration is device- and tool-flow-specific. A flash-based space FPGA with full-image reprogramming produces a different service architecture from an SRAM FPGA with dynamic partial reconfiguration and scrubbing. Select the service mode only after the device trade.`,
  ),
  markdown(
    "next_steps",
    `## Recommended next steps\n\n1. Obtain the existing 3U bus payload accommodation and interface-control documents.\n2. Freeze the lightning RF band, antenna concept, camera channels/frame windows, and ADS-B data product.\n3. Build a measured volume, mass, orbit-average/peak power, thermal, storage, and downlink budget with at least 20% development margin where the program can support it.\n4. Select the FPGA/configuration technology and decide whether the first flight supports parameters only, a curated catalog, partial modules, or full images.\n5. Implement the static shell on an engineering model and demonstrate isolation, quotas, watchdog reset, power trip, image verification, and golden recovery.\n6. Run a pilot service with recorded sensor data on the ground before accepting a flight experiment.\n7. Define experiment eligibility, data rights, cybersecurity, export/regulatory review, pricing or allocation, support, publication, and incident-response policy with qualified counsel and mission authorities.`,
  ),
  markdown(
    "further_questions",
    `## Questions that determine the final architecture\n\n- How much payload volume, mass, average power, peak power, and heat rejection does the existing bus actually provide?\n- Which FPGA family and configuration technology are already selected?\n- Is the hosted service a primary mission objective or a secondary payload used only when lightning collection is idle?\n- Will users submit RTL/HLS source, model weights, soft-core software, or all three?\n- Must experiments access live sensors, archived data, or both?\n- What downlink allocation and turnaround time can the service promise?\n- Which organization owns qualification, bitstream signing, operations approval, customer support, and liability decisions?`,
  ),
);

const hostedRoles = [
  {
    role: "Direct payload experiments",
    count: 9,
    examples: "Acquisition, image/DSP, compression, AI, reduction and acceleration",
  },
  {
    role: "Isolated recorded-data sandboxes",
    count: 4,
    examples: "Virtual networking/protocols, TMR and dummy-key cryptography",
  },
  {
    role: "Trusted service infrastructure",
    count: 5,
    examples: "Storage, time, recovery, ECC/scrubbing and reconfiguration",
  },
];

const addedSources = [
  {
    id: "hosted_roles_sql",
    label: "Hosted-service role taxonomy",
    query: {
      engine: "portable-sql",
      language: "sql",
      sql: "SELECT * FROM (VALUES ('Direct payload experiments', 9, 'Acquisition, image/DSP, compression, AI, reduction and acceleration'), ('Isolated recorded-data sandboxes', 4, 'Virtual networking/protocols, TMR and dummy-key cryptography'), ('Trusted service infrastructure', 5, 'Storage, time, recovery, ECC/scrubbing and reconfiguration')) AS t(role, count, examples)",
      description:
        "Materializes the design taxonomy of retained FPGA roles for the 3U hosted experiment service.",
      executed_at: "2026-07-17T00:00:00Z",
    },
  },
  {
    id: "cubesat_spec",
    label: "CubeSat Design Specification Rev. 14.1",
    href: "https://www.nasa.gov/wp-content/uploads/2018/01/cubesatdesignspecificationrev14_12022-02-09.pdf",
  },
  {
    id: "nasa_smallsat_power",
    label: "NASA 2026 SmallSat power systems",
    href: "https://www.nasa.gov/smallsat-institute/sst-soa/power-subsystems/",
  },
  {
    id: "nasa_smallsat_avionics",
    label: "NASA 2026 SmallSat avionics",
    href: "https://www.nasa.gov/smallsat-institute/sst-soa/small-spacecraft-avionics/",
  },
  {
    id: "amd_dfx",
    label: "AMD Dynamic Function eXchange",
    href: "https://docs.amd.com/r/2024.2-English/ug909-vivado-partial-reconfiguration/Introduction",
  },
  {
    id: "noaa_glm",
    label: "NOAA Geostationary Lightning Mapper",
    href: "https://goes-r.noaa.gov/spacesegment/glm.html",
  },
  {
    id: "faa_adsb",
    label: "FAA ADS-B guidance",
    href: "https://www.faa.gov/air_traffic/publications/atpubs/aim_html/chap4_section_5.html",
  },
  {
    id: "nasa_vhf_lightning",
    label: "NASA VHF lightning detection study",
    href: "https://ntrs.nasa.gov/api/citations/20240005740/downloads/FINAL_VERSION.pdf",
  },
];

const keepSourceIds = new Set([
  "spacecube",
  "spacecube3",
  "esaOdp",
  "spacewire",
  "spacefibre",
  "ccsds",
  "ecss",
  "ecssEngineering",
  "nasaSee",
  "amdSem",
  "microchipReconfig",
  "microchipRtg4",
  "amdXqr",
  "esaSecurity",
]);
const sources = [
  ...base.sources.filter((source) => keepSourceIds.has(source.id)),
  ...addedSources,
];

const artifact = {
  surface: "report",
  manifest: {
    version: 1,
    surface: "report",
    title,
    description:
      "A conditional 3U CubeSat architecture for a safe, time-shared hosted FPGA experiment service using multispectral, ADS-B and lightning-RF data.",
    generatedAt: "2026-07-17T00:00:00Z",
    charts: [
      {
        id: "hosted_role_chart",
        title: "Retained FPGA roles by service boundary",
        subtitle:
          "Eighteen logical roles share one physical FPGA over time; counts do not imply simultaneous hardware.",
        showDescription: true,
        type: "bar",
        dataset: "hosted_roles",
        sourceId: "hosted_roles_sql",
        encodings: {
          x: { field: "role", type: "nominal", label: "Service boundary" },
          y: {
            field: "count",
            type: "quantitative",
            label: "Retained roles",
            unit: "roles",
          },
          tooltip: [
            { field: "role", type: "text", label: "Boundary" },
            { field: "count", type: "quantitative", label: "Roles" },
            { field: "examples", type: "text", label: "Examples" },
          ],
        },
        valueFormat: "number",
        unit: "roles",
        layout: "full",
      },
    ],
    sources,
    blocks,
  },
  snapshot: {
    version: 1,
    generatedAt: "2026-07-17T00:00:00Z",
    status: "ready",
    datasets: { hosted_roles: hostedRoles },
  },
  sources,
};

fs.mkdirSync(serviceHdlDir, { recursive: true });
for (const useId of Object.keys(fileForUse)) {
  fs.copyFileSync(
    path.join(originalHdlDir, fileForUse[useId]),
    path.join(serviceHdlDir, fileForUse[useId]),
  );
}
for (const module of serviceModules) {
  fs.writeFileSync(
    path.join(serviceHdlDir, module.file),
    `// ${module.note}\n// Educational architecture example; not flight-qualified IP.\n\n${module.code}\n`,
    "utf8",
  );
}

fs.writeFileSync(outputPath, JSON.stringify(artifact, null, 2), "utf8");
console.log(
  JSON.stringify({
    outputPath,
    blocks: blocks.length,
    retainedUses: selectedGroups.flatMap((group) => group.uses).length,
    serviceModules: serviceModules.length,
    hdlFiles: fs.readdirSync(serviceHdlDir).filter((file) => file.endsWith(".sv")).length,
    sources: sources.length,
  }),
);
