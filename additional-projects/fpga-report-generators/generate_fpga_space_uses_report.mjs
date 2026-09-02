import fs from "node:fs";

const outputPath = "C:/Users/user/Documents/Codex/2026-07-14/i-w/outputs/fpga_space_uses_implementation_artifact.json";

const referenceCatalog = {
  spacecube: ["NASA SpaceCube", "https://technology.nasa.gov/patent/GSC-TOPS-35"],
  spacecube3: ["NASA SpaceCube 3.0 Mini", "https://technology.nasa.gov/patent/GSC-TOPS-293"],
  esaOdp: ["ESA On-board Data Processing", "https://www.esa.int/Enabling_Support/Space_Engineering_Technology/Onboard_Data_Processing"],
  spacewire: ["ESA SpaceWire", "https://www.esa.int/Enabling_Support/Space_Engineering_Technology/Onboard_Computers_and_Data_Handling/SpaceWire"],
  spacefibre: ["ESA SpaceFibre", "https://www.esa.int/Enabling_Support/Space_Engineering_Technology/Onboard_Data_Processing/SpaceFibre"],
  ccsds: ["CCSDS active publications", "https://ccsds.org/publications/allpubs/"],
  gnc: ["NASA Small Spacecraft GNC", "https://www.nasa.gov/smallsat-institute/sst-soa/guidance-navigation-and-control/"],
  trn: ["NASA Terrain Relative Navigation", "https://www.nasa.gov/space-technology-mission-directorate/tdm/terrain-relative-navigation-trn/"],
  splice: ["NASA SPLICE", "https://www.nasa.gov/safe-and-precise-landing-integrated-capabilities-evolution-splice/"],
  ecss: ["ECSS FPGA radiation-mitigation handbook", "https://ecss.nl/home/ecss-e-hb-20-40a-engineering-techniques-for-radiation-effects-mitigation-in-asics-and-fpgas-handbook/"],
  ecssEngineering: ["ECSS-E-ST-20-40C FPGA engineering", "https://ecss.nl/standard/ecss-e-st-20-40c-asic-fpga-and-ip-core-engineering-11-october-2023/"],
  nasaSee: ["NASA FPGA SEE test-guideline update", "https://ntrs.nasa.gov/citations/20180001945"],
  amdSem: ["AMD UltraScale SEM design checklist", "https://docs.amd.com/r/en-US/pg187-ultrascale-sem/IP-Design-Checklist"],
  microchipReconfig: ["Microchip in-flight FPGA reprogramming", "https://www.microchip.com/en-us/development-tool/SPACE-RATED-FPGA-IN-FLIGHT-REPROGRAMMING"],
  microchipRtg4: ["Microchip RTG4 documentation", "https://www.microchip.com/en-us/products/fpgas-and-plds/radiation-tolerant-fpgas/rtg4-radiation-tolerant-fpgas"],
  amdXqr: ["AMD Kintex UltraScale XQR", "https://www.amd.com/en/products/adaptive-socs-and-fpgas/fpga/kintex-ultrascale-xqr.html"],
  esaSecurity: ["ESA AegisSat secure SoC-FPGA paper", "https://security4space.esa.int/2025/papers/46/"]
};

const uses = [
  {
    n: 1,
    title: "Payload data acquisition",
    purpose: `Capture detector or instrument samples without losing ordering, timing, or calibration context. The FPGA sits beside the ADC, camera, spectrometer, radar receiver, or particle detector because it can accept many synchronous lanes at deterministic rates.`,
    path: `Sensor or analog front end → ADC or digital PHY → input delay and deserializer → word alignment → timestamp → elastic FIFO → calibration/quality flags → memory or downstream processing.`,
    steps: [
      `Freeze the electrical interface: lane count, voltage standard, bit rate, sample clock, framing, valid markers, and startup sequence.`,
      `Instantiate the device I/O primitives, differential buffers, input delays, SERDES blocks, and clock buffers required by the interface.`,
      `Train the link with a known pattern; sweep delay taps, identify the valid eye, choose its center, and store alignment status.`,
      `Convert lane data into framed samples, attach a counter or mission timestamp, and mark missing, duplicated, saturated, or out-of-range samples.`,
      `Cross into the processing clock through an elastic or asynchronous FIFO and define overflow behavior before it occurs.`,
      `Feed a packetizer, DMA engine, compressor, or real-time processing pipeline and expose counters for every loss or resynchronization event.`
    ],
    resources: `ISERDES/IDELAY or equivalent I/O primitives, PLL/MMCM, frame detector, timestamp counter, BRAM FIFO, CRC/parity checker, AXI-stream or vendor-neutral ready/valid interfaces.`,
    verification: `Use a behavioral instrument model that introduces skew, clock drift, bit slips, missing frames, illegal codes, and bursts at maximum rate. Compare every received sample and timestamp with a scoreboard, then repeat using an FPGA-generated pattern at temperature and voltage corners.`,
    space: `Synchronize resets per clock domain, protect FIFOs with ECC or parity, triplicate only the control state that warrants it, and make loss visible in telemetry. A hidden dropped sample is normally worse than an explicitly invalid sample.`,
    refs: ["spacecube3", "ecss"]
  },
  {
    n: 2,
    title: "Image and video processing",
    purpose: `Transform raw focal-plane pixels into corrected, registered, filtered, or feature-ready imagery before storage or downlink. FPGA pipelines are effective because each pixel can pass through a new arithmetic stage every clock.`,
    path: `Pixel stream → frame/line parser → bad-pixel and dark-current correction → gain/offset calibration → neighborhood filters → geometric or spectral processing → metadata insertion → frame buffer/compressor.`,
    steps: [
      `Define pixel format, frame dimensions, blanking, bands, calibration coefficients, dynamic range, and required throughput.`,
      `Build a streaming parser that produces pixel, line-start, frame-start, valid, band, and timestamp signals.`,
      `Apply per-pixel calibration with fixed-point subtract/multiply/saturate stages and double-buffer coefficients so updates cannot split a frame.`,
      `Use BRAM line buffers and shift registers to form 3×3 or larger neighborhoods for convolution, morphology, edge detection, or denoising.`,
      `Pipeline every arithmetic dependency until timing closes; maintain sideband alignment by delaying metadata by the same number of cycles.`,
      `Write results to memory or a compressor with explicit backpressure and a defined policy for frame drop or truncation.`
    ],
    resources: `Line buffers, dual-port BRAM, DSP multipliers, fixed-point adders, coefficient memories, stream crossbars, optional external DDR controller, and DMA.`,
    verification: `Use a bit-accurate software reference and compare complete frames, including boundaries, saturation, coefficient changes, and invalid pixels. Test synthetic impulses, ramps, checkerboards, and archived sensor scenes.`,
    space: `Protect coefficient and frame memories, detect stale or corrupt calibration tables with CRCs, and ensure one corrupted frame cannot poison later state. For partial-frame failures, mark the product invalid instead of silently presenting it as complete.`,
    refs: ["spacecube", "esaOdp", "ecss"]
  },
  {
    n: 3,
    title: "Data compression",
    purpose: `Reduce the number of bits stored or transmitted while preserving the scientific information required by the mission. Lossless methods preserve exact samples; controlled lossy methods trade fidelity for a stronger reduction.`,
    path: `Calibrated samples → predictor or transform → residual/quantization → entropy coder → packet framing → output FIFO and mass memory/downlink.`,
    steps: [
      `Choose the mission-approved algorithm and define whether exact reconstruction, bounded error, or visual quality is required.`,
      `Implement the predictor or transform as a streaming fixed-point pipeline and document rounding, saturation, and coefficient precision.`,
      `Buffer only the lines, blocks, or bands the algorithm actually needs; size buffers for worst-case backpressure rather than average compression.`,
      `Implement variable-length coding with a bit packer that can emit zero, one, or many words per input symbol.`,
      `Frame compressed data into independently decodable units with uncompressed length, algorithm mode, sequence count, and CRC.`,
      `Monitor compression ratio and output occupancy; switch to a safe raw or lower-complexity mode before overflow.`
    ],
    resources: `DSP blocks for transforms, BRAM for block/line storage, leading-zero/count logic, variable-length coder, bit reservoir, CRC, and packetizer.`,
    verification: `For lossless compression, decompress and compare every sample. For lossy compression, use mission-defined error metrics and science-product tests. Exercise incompressible data because it creates the largest output and buffer pressure.`,
    space: `Use restart markers or independent packets so one upset does not corrupt the remainder of an observation. Protect tables and coder state, and retain a bypass mode for anomaly recovery.`,
    refs: ["spacecube", "ccsds", "ecss"]
  },
  {
    n: 4,
    title: "Software-defined radio",
    purpose: `Move radio functions from fixed analog hardware into reprogrammable digital logic so the same payload can change bandwidth, waveform, channel plan, modulation, or mission mode.`,
    path: `ADC samples → digital down-converter → channel filter/decimator → synchronization → demodulator/decoder; transmit performs encoder/modulator → interpolator → digital up-converter → DAC.`,
    steps: [
      `Specify sample rates, occupied bandwidth, carrier uncertainty, modulation, coding, spectral mask, and acquisition time.`,
      `Implement a numerically controlled oscillator and mixer; use a phase accumulator plus LUT/CORDIC or DSP-based complex multiply.`,
      `Apply CIC and FIR decimation/interpolation in stages so each filter runs only as fast as necessary.`,
      `Add automatic gain, carrier recovery, timing recovery, frame synchronization, and soft-decision metrics.`,
      `Connect the demodulator to the channel decoder and packet layer through rate-matched FIFOs.`,
      `Store waveform parameters in checked configuration registers and change modes only at a defined frame boundary.`
    ],
    resources: `DSP slices, complex mixers, NCO/CORDIC, FIR/CIC filters, correlators, numerically controlled gain, BRAM delay lines, high-speed ADC/DAC interfaces, and transceivers.`,
    verification: `Generate vectors in MATLAB/Python or another golden model; sweep SNR, Doppler, clock offset, interference, quantization, and burst timing. Measure BER/PER, acquisition time, EVM, and spectral compliance.`,
    space: `Separate an immutable safe waveform from reconfigurable modes, authenticate parameter/bitstream updates, and bound any automatic gain or tracking loop so radiation-induced state changes cannot drive it unstable.`,
    refs: ["esaOdp", "ccsds", "ecss"]
  },
  {
    n: 5,
    title: "Communication coding",
    purpose: `Add synchronization and forward-error correction so the receiver can recover data corrupted by noise, fading, or interference. The selected code and framing must match the mission’s space-link standard.`,
    path: `Packets → transfer frames → optional randomizer → CRC → FEC encoder/interleaver → attached synchronization marker → modulator; receive reverses the chain and reports decoder quality.`,
    steps: [
      `Select the exact CCSDS or mission profile, code rate, frame length, interleaving, puncturing, and synchronization marker.`,
      `Implement frame assembly first and verify field placement, counters, idle frames, CRC, and byte/bit order.`,
      `Add the encoder as a streaming block; for LDPC or turbo codes, partition parity operations across BRAM banks and parallel processing units.`,
      `On receive, correlate for frame sync, de-randomize, decode soft metrics, check CRC, and classify corrected versus rejected frames.`,
      `Use elastic buffers between modem, decoder, and packet layers because their rates and burst behavior differ.`,
      `Expose syndrome, iteration, correction, sync-loss, and rejected-frame counters to operations.`
    ],
    resources: `XOR networks, shift registers, BRAM parity matrices, soft-metric RAM, parallel check-node/variable-node engines, correlators, CRC, and bit interleavers.`,
    verification: `Use official or independently generated conformance vectors, then inject bit errors and soft-metric noise. Verify known BER/FER points, maximum decoder iterations, false synchronization rate, and continuous operation across frame boundaries.`,
    space: `Protect code/configuration tables and counters, reset a stuck iterative decoder with a watchdog, and ensure a rejected frame cannot be mistaken for valid command or telemetry data.`,
    refs: ["ccsds", "ecss"]
  },
  {
    n: 6,
    title: "Digital beamforming",
    purpose: `Combine samples from multiple antenna elements with controlled delay and complex weight so the array points, nulls interference, or forms several simultaneous beams.`,
    path: `Per-element ADC streams → calibration/delay alignment → channelization → complex weighting → adder tree → beam streams → detector, demodulator, or recorder.`,
    steps: [
      `Define array geometry, element count, sample rate, bandwidth, beam count, steering update rate, and acceptable sidelobes.`,
      `Calibrate element gain, phase, cable delay, and ADC timing; apply integer delays in RAM and fractional delays in FIR filters.`,
      `Optionally channelize with a polyphase filter bank/FFT so weights can vary by frequency bin.`,
      `Multiply every element by its complex weight and sum through a pipelined tree with enough guard bits.`,
      `Normalize, round, and saturate the result; attach beam ID, time, pointing state, and calibration version.`,
      `Load new weights into a shadow bank, verify CRC, and switch banks synchronously.`
    ],
    resources: `Many DSP multipliers, BRAM delay lines, polyphase FIRs, FFT cores, pipelined adder trees, coefficient RAM, and high-bandwidth serial I/O.`,
    verification: `Inject coherent tones and simulated sources across angle/frequency; measure beam peak, null depth, phase error, sidelobes, gain, overflow, and behavior during weight-bank switching.`,
    space: `Protect weight memories and calibration state, detect a failed element, support element masking, and ensure coefficient corruption cannot command excessive transmit power or invalidate pointing.`,
    refs: ["spacecube", "esaOdp", "ecss"]
  },
  {
    n: 7,
    title: "Radar and synthetic-aperture radar processing",
    purpose: `Convert sampled echoes into range, Doppler, or image products quickly enough to reduce storage and downlink load or support time-critical sensing.`,
    path: `ADC I/Q → pulse/window correction → matched filter/range FFT → pulse compression → Doppler FFT → detection or SAR focusing → product formatter.`,
    steps: [
      `Define waveform, bandwidth, pulse repetition frequency, aperture length, range cells, Doppler bins, and product latency.`,
      `Capture and calibrate I/Q samples; align each pulse with transmit timing and platform navigation metadata.`,
      `Implement matched filtering by FIR or FFT convolution and preserve sufficient precision through accumulation.`,
      `Buffer a coherent processing interval, transpose memory access if needed, and perform Doppler processing across pulses.`,
      `Apply magnitude detection, thresholding/CFAR, or forward selected data to a processor for higher-level SAR focusing.`,
      `Packetize products with geometry, calibration, timing, and processing-mode metadata.`
    ],
    resources: `High-rate ADC interfaces, FFT engines, complex DSP multipliers, corner-turn memory, DMA, CFAR comparators, external DDR, and transceivers.`,
    verification: `Use a signal simulator with known targets, delays, Dopplers, clutter, and noise. Compare range/Doppler peaks and SAR point-spread functions with a floating-point reference, including quantization and saturation.`,
    space: `Protect large memories with ECC, use checksums on navigation/calibration inputs, bound accumulation, and mark any product affected by timing loss, memory correction overflow, or dropped pulses.`,
    refs: ["spacecube", "spacecube3", "ecss"]
  },
  {
    n: 8,
    title: "Optical and laser communications",
    purpose: `Process high-rate optical-link data and tightly timed acquisition/tracking signals while the optical front end handles photons, detectors, modulators, and pointing hardware.`,
    path: `Detector/ADC → clock and frame recovery → deinterleaver/FEC decoder → packet output; transmit performs packet/FEC/framing → serializer/modulator drive, alongside pointing/acquisition telemetry.`,
    steps: [
      `Specify detector interface, line rate, modulation, coding, acquisition sequence, allowable jitter, and link-interruption behavior.`,
      `Use dedicated transceivers or SERDES for clock/data recovery and gearbox functions.`,
      `Implement frame correlation, deinterleaving, FEC, CRC, and packet buffering with measured latency.`,
      `Create deterministic trigger and timestamp paths for pointing, acquisition, and tracking sensors.`,
      `Separate the safety/control channel from the high-rate payload channel so link overload cannot block pointing or shutdown.`,
      `Record signal level, lock state, corrected errors, decoder margin, and reacquisition time.`
    ],
    resources: `Multi-gigabit transceivers, PLLs, FEC engines, elastic buffers, high-resolution counters, LVDS/CMOS control I/O, and DMA to memory or processor.`,
    verification: `Use optical-front-end emulation and electrical loopback; inject burst loss, jitter, fades, bit errors, false sync, and clock discontinuities. Verify reacquisition and data-integrity boundaries.`,
    space: `Provide a bounded safe state for laser enable, redundant inhibit paths where required, authenticated configuration, and independent monitoring so corrupt FPGA state cannot leave an unsafe transmitter condition.`,
    refs: ["spacecube", "ccsds", "ecss"]
  },
  {
    n: 9,
    title: "Onboard networking",
    purpose: `Move commands, telemetry, payload data, time codes, and memory transactions among instruments, processors, mass memory, and radios.`,
    path: `Physical link codec → receive FIFO → packet parser → routing/virtual-channel decision → arbitration and flow control → transmit FIFO → physical link codec.`,
    steps: [
      `Choose the network standard and topology from bandwidth, latency, determinism, redundancy, and harness constraints.`,
      `Instantiate or implement the PHY/codec and prove link initialization, disconnect handling, parity/CRC, and flow control.`,
      `Parse headers into a normalized internal descriptor containing source, destination, priority, length, and time.`,
      `Route through a crossbar or wormhole switch; arbitrate with explicit priority and starvation limits.`,
      `Provide virtual channels or separate queues so bulk payload traffic cannot block commands, time codes, or fault messages.`,
      `Count link resets, errors, retries, congestion, dropped packets, and maximum queue depth.`
    ],
    resources: `SpaceWire codecs, SpaceFibre lanes, Ethernet/CAN cores, packet FIFOs, crossbars, routing tables, arbiters, CRC, and transceivers.`,
    verification: `Run protocol-conformance tests, then saturate every ingress simultaneously. Check ordering, fairness, deadlock freedom, flow-control recovery, redundant-path switchover, and deterministic latency for critical traffic.`,
    space: `Protect routing tables and queue pointers, isolate faulty links, use end-to-end CRC beyond link-local checks, and keep a management path available under congestion.`,
    refs: ["spacewire", "spacefibre", "ecss"]
  },
  {
    n: 10,
    title: "Protocol conversion",
    purpose: `Bridge devices that disagree about electrical signalling, clock rate, framing, word size, byte order, addressing, or transaction semantics.`,
    path: `Protocol-A PHY/parser → normalized transaction or stream → buffering/rate adaptation → mapping/state machine → Protocol-B formatter/PHY.`,
    steps: [
      `Write a mapping table for every field, command, response, timeout, error, and unsupported operation.`,
      `Terminate each protocol independently; never let one side’s timing assumptions leak directly into the other.`,
      `Translate into an internal ready/valid stream or request/response record with explicit length and status.`,
      `Use FIFOs for rate and clock-domain adaptation; calculate worst-case occupancy for burst conversion.`,
      `Implement timeout, retry, duplicate suppression, and partial-transaction cleanup.`,
      `Expose raw and translated error counters so integration teams can identify which side violated the contract.`
    ],
    resources: `UART/SPI/I2C/CAN/1553/Ethernet/SpaceWire cores, asynchronous FIFOs, packet parsers, register maps, transaction state machines, timers, and CRC.`,
    verification: `Use independent bus-functional models for both sides and randomize stalls, resets, malformed messages, clock ratios, and backpressure. Prove that each accepted source transaction produces exactly one permitted destination outcome.`,
    space: `Reset the two interfaces independently, protect state and routing registers, reject illegal commands by default, and ensure conversion failure cannot hold a shared bus or safety-critical control line indefinitely.`,
    refs: ["spacewire", "ccsds", "ecss"]
  },
  {
    n: 11,
    title: "High-speed data storage control",
    purpose: `Buffer large payload bursts and move data reliably into DDR, SDRAM, NAND flash, MRAM, or mass-memory modules despite different rates and access granularities.`,
    path: `Input streams → per-source FIFO → DMA descriptors → memory controller/ECC → circular file or packet store → read scheduler → downlink or processor.`,
    steps: [
      `Define capacity, sustained and burst bandwidth, retention, erase/write endurance, latency, and acceptable data loss.`,
      `Use the vendor memory PHY/controller for training and low-level timing, then wrap it with mission-specific ECC, scrubbing, and address protection.`,
      `Implement DMA descriptors with base, length, source, timestamp, CRC, and ownership; validate descriptors before use.`,
      `Schedule reads and writes with bounded priority so recording cannot permanently starve downlink or housekeeping.`,
      `Create a journal or commit marker so power loss cannot make partially written data appear complete.`,
      `Track corrected/uncorrectable errors, bad blocks, retries, occupancy, bandwidth, and wear.`
    ],
    resources: `DDR/flash PHY and controller, DMA engines, ECC, address generators, descriptor RAM, large FIFOs, scrub controller, CRC, and high-speed fabric interfaces.`,
    verification: `Stress simultaneous peak-rate producers and consumers; inject read/write errors, power interruption, refresh pressure, bad blocks, descriptor corruption, and reset during transactions. Reconstruct stored data and metadata exactly.`,
    space: `Interleave ECC words to reduce correlated multi-bit events, scrub volatile memory, protect address/control state more strongly than payload data, and provide a read-only recovery area.`,
    refs: ["spacecube3", "ecss", "nasaSee"]
  },
  {
    n: 12,
    title: "Guidance, navigation, and control support",
    purpose: `Provide deterministic sensor capture and acceleration for filters or control-law arithmetic while a flight processor retains mission-level sequencing and safety authority.`,
    path: `IMU/star tracker/GNSS/lidar inputs → timestamp and calibration → sensor validation → filter/control accelerator → bounded command output → flight computer and actuator interface.`,
    steps: [
      `Allocate functions between FPGA and flight software based on rate, latency, determinism, updateability, and assurance.`,
      `Capture every sensor against a common timebase and carry validity, age, saturation, and source ID with each measurement.`,
      `Implement fixed-point filters, matrix operations, coordinate transforms, or control loops with explicit scaling and overflow handling.`,
      `Compare commands against range, slew-rate, freshness, and mode constraints before presenting them to an actuator path.`,
      `Support processor bypass, safe hold, and commanded reset; never make the FPGA accelerator the only route to safe mode unless qualified for it.`,
      `Log latency, missed deadlines, stale inputs, rejected commands, and divergence monitors.`
    ],
    resources: `Timestamp units, SPI/UART/SpaceWire interfaces, DSP pipelines, matrix engines, CORDIC, BRAM coefficient/state memory, watchdogs, and redundant I/O.`,
    verification: `Use closed-loop simulation, Monte Carlo cases, sensor dropouts, bias/drift, timing jitter, extreme states, and hardware-in-the-loop. Compare fixed-point results against the flight algorithm’s high-precision model.`,
    space: `Triplicate or compare only the critical control state, protect coefficients, detect stale data, and force outputs to a bounded safe value after reset, clock loss, or invalid mode transition.`,
    refs: ["gnc", "splice", "ecss"]
  },
  {
    n: 13,
    title: "Star-tracker processing",
    purpose: `Turn a star-field image into centroids and, when required, candidate star IDs or an attitude solution. Many systems use the FPGA for front-end image work and a processor for catalog matching and estimation.`,
    path: `Image sensor → pixel correction → threshold/background estimation → connected components → centroid/intensity list → catalog matcher → quaternion and quality.`,
    steps: [
      `Capture the sensor stream and correct fixed-pattern noise, dark offset, bad pixels, and exposure-dependent gain.`,
      `Estimate background and threshold pixels; reject saturated regions, cosmic-ray streaks, hot pixels, and known exclusion zones.`,
      `Group neighboring bright pixels into blobs using line buffers and labels or a run-length method.`,
      `Accumulate sum of intensity, x·intensity, and y·intensity; divide to produce subpixel centroids and brightness.`,
      `Send a bounded centroid list to a CPU or implement geometric pattern matching if latency and resources require it.`,
      `Attach exposure time, sensor temperature, timing, quality, and exclusion flags to every attitude result.`
    ],
    resources: `Camera interface, line buffers, threshold/label logic, accumulators, reciprocal/divide unit, centroid FIFO, catalog memory or processor interface, and timestamping.`,
    verification: `Use synthetic star fields and recorded images with blur, smear, glare, hot pixels, cosmic rays, lost-in-space cases, and varying angular rates. Measure centroid error, false/ missed stars, acquisition time, and attitude residual.`,
    space: `Protect calibration/catalog data, bound blob counts and accumulators, reject implausible solutions, and combine with an IMU/estimator so temporary star loss does not immediately remove attitude knowledge.`,
    refs: ["gnc", "spacecube", "ecss"]
  },
  {
    n: 14,
    title: "Radar, lidar, and navigation-sensor preprocessing",
    purpose: `Convert raw range-sensor waveforms or point returns into validated range, velocity, intensity, or point-cloud measurements before the flight computer consumes them.`,
    path: `ADC/TDC returns → baseline correction → matched filtering/correlation → peak detection → range/Doppler calculation → quality gating → measurement packets.`,
    steps: [
      `Calibrate timing, channel delay, amplitude, temperature dependence, and sensor geometry.`,
      `Capture returns with transmit-event timestamps and reject samples taken during invalid or saturated intervals.`,
      `Apply matched filtering, accumulation, FFT, or correlation to improve detection signal-to-noise ratio.`,
      `Detect peaks with adaptive thresholds; estimate sub-bin range or Doppler and report ambiguity and quality.`,
      `Transform measurements into the required coordinate frame using current alignment coefficients.`,
      `Package measurements with acquisition time, calibration version, covariance/quality, and fault flags.`
    ],
    resources: `Fast ADC/TDC interfaces, correlators, FFTs, accumulators, CORDIC, timestamp units, coefficient RAM, and high-rate output FIFOs.`,
    verification: `Use return-waveform simulators with multiple targets, noise, saturation, false returns, changing reflectivity, clock error, and motion. Compare estimated range/velocity with truth and verify latency.`,
    space: `Prevent one extreme return from overflowing later processing, protect timing/calibration state, monitor detector noise and stuck channels, and output an explicit invalid measurement rather than stale range.`,
    refs: ["spacecube3", "splice", "ecss"]
  },
  {
    n: 15,
    title: "Autonomous landing and hazard detection",
    purpose: `Process camera or lidar data quickly enough to localize the vehicle, build a terrain model, identify hazards, and provide safe-site candidates during a short descent.`,
    path: `Camera/lidar/IMU → synchronized sensor products → feature or elevation extraction → map correlation/hazard metrics → safe-site candidates → navigation and guidance computer.`,
    steps: [
      `Define the decision timeline, sensor fields of view, map formats, hazard sizes, vehicle footprint, divert capability, and required confidence.`,
      `Time-align imagery, lidar ranges, and inertial state; reject data outside the allowed age or geometry.`,
      `Accelerate image rectification, feature descriptors, correlation, point-cloud gridding, slope/roughness, or rock/crater detection.`,
      `Produce candidate sites with coordinates, size, slope, roughness, uncertainty, and reachability—not a single unqualified answer.`,
      `Let the navigation/guidance function fuse the measurement and select/command the divert under independent constraints.`,
      `Freeze or degrade gracefully when confidence falls below threshold and log the reason.`
    ],
    resources: `Image/lidar front ends, line/frame buffers, pyramids, correlation engines, FFT/DSP blocks, external memory, coordinate transforms, and low-latency processor links.`,
    verification: `Use high-fidelity Monte Carlo, recorded field data, hardware-in-the-loop, sensor occlusion, lighting extremes, dust, map error, motion blur, dropped frames, and deadline overruns. Evaluate false-safe and false-hazard rates separately.`,
    space: `Keep guidance authority outside an unmonitored accelerator, validate every candidate against physical constraints, protect maps and calibration, and include a deterministic timeout path when processing misses its deadline.`,
    refs: ["trn", "splice", "spacecube", "ecss"]
  },
  {
    n: 16,
    title: "Onboard artificial intelligence",
    purpose: `Run inference near the sensor to classify scenes, detect events, segment imagery, estimate state, or prioritize data without downlinking every raw observation.`,
    path: `Corrected sensor data → resize/normalize → quantized neural-network layers → post-processing/NMS → confidence and product metadata → autonomy or storage policy.`,
    steps: [
      `Define the operational decision and error costs before choosing a model; specify confidence, latency, power, and memory limits.`,
      `Train and validate on mission-representative data, then quantize weights/activations and measure accuracy loss.`,
      `Map convolutions or matrix operations onto DSP arrays with tiled BRAM buffers and deterministic scheduling.`,
      `Store weights in checked memory, load them through an authenticated path, and identify the model version in every result.`,
      `Implement post-processing such as thresholds, non-maximum suppression, temporal voting, or rule-based plausibility checks.`,
      `Retain a bypass/raw-sample path and treat inference as advisory unless its assurance case supports control authority.`
    ],
    resources: `DSP arrays, systolic MAC engines, BRAM/URAM weight and activation buffers, DMA, quantizers, soft-core or hard processor for orchestration, and high-speed memory.`,
    verification: `Use held-out mission data, edge cases, corrupted inputs, distribution shifts, quantization comparisons, timing/power measurements, and bit-flip injection in weights and activations. Report false positives and false negatives by scenario.`,
    space: `Authenticate model updates, CRC/ECC-protect weights, monitor confidence and data validity, support rollback, and prevent a model or accelerator fault from bypassing hard safety constraints.`,
    refs: ["spacecube", "amdXqr", "esaSecurity", "ecss"]
  },
  {
    n: 17,
    title: "Intelligent data reduction",
    purpose: `Decide what to keep, summarize, or downlink when instruments generate more data than the spacecraft can store or transmit.`,
    path: `Sensor products → quality/event features → scoring or rules → keep/discard/priority decision → metadata audit trail → storage/downlink queues.`,
    steps: [
      `Define the science value function, false-discard cost, quotas, protected observation types, and ground-audit requirements.`,
      `Compute simple deterministic features first: cloud fraction, saturation, motion, novelty, energy, geographic mask, or event trigger.`,
      `Apply thresholds, a lightweight model, or a processor-assisted policy to assign priority and retention duration.`,
      `Preserve thumbnails, features, decision reason, algorithm version, and representative rejected samples for validation.`,
      `Use separate queues and quotas so one event type cannot consume all storage or downlink capacity.`,
      `Allow ground commands to disable reduction, adjust thresholds, or request raw capture for calibration.`
    ],
    resources: `Streaming feature extractors, histogram/reduction trees, small neural or rule engines, priority queues, metadata packetizer, and mass-memory/DMA interfaces.`,
    verification: `Replay labeled mission-like datasets and calculate science recall, false discard, storage saved, queue behavior, and results under corrupted metadata or model state. Include long quiet periods and event storms.`,
    space: `Default to a conservative keep policy after uncertainty or reset, protect thresholds and geographic masks, and never silently discard data without a telemetered reason and count.`,
    refs: ["spacecube", "esaOdp", "ecss"]
  },
  {
    n: 18,
    title: "Instrument control",
    purpose: `Generate precise clocks, triggers, biases, readout phases, calibration sequences, and detector modes while collecting status and enforcing electrical or thermal limits.`,
    path: `Command/registers → validated mode sequencer → clock/trigger waveform generators → instrument electronics; status ADC/GPIO → debounce/filter → interlocks and telemetry.`,
    steps: [
      `Translate the instrument timing diagram into states, counters, allowable transitions, and abort conditions.`,
      `Generate clocks and pulses from dedicated clock resources and synchronous counters, not combinational delay chains.`,
      `Implement shadow registers so multi-field settings become active together at a safe boundary.`,
      `Read interlocks and status through synchronized inputs; require stable conditions before enabling high voltage, heaters, shutters, or lasers.`,
      `Create calibration and self-test sequences with explicit completion, timeout, and safe-abort paths.`,
      `Record command acceptance, mode, sequence step, limits, timeouts, and first-fault cause.`
    ],
    resources: `Clock managers, synchronous sequencers, PWM/pulse generators, SPI/I2C/DAC/ADC interfaces, watchdog timers, interlock logic, and protected register banks.`,
    verification: `Use a cycle-accurate instrument model and check every output edge, setup/hold interval, mode transition, timeout, and abort. Then test with logic analyzers and representative loads over temperature.`,
    space: `Use fail-safe output polarity, independent hardware inhibits for hazardous energy, protected state machines, synchronized reset release, and a power-up state that is safe without software.`,
    refs: ["spacecube3", "ecssEngineering", "ecss"]
  },
  {
    n: 19,
    title: "Spacecraft timing and synchronization",
    purpose: `Give distributed instruments and processors a common concept of time and deterministic event markers so measurements can be correlated.`,
    path: `GNSS/oscillator/time-code source → clock cleanup and counter → disciplined time estimator → event capture/distribution → local timestamps and network time messages.`,
    steps: [
      `Define the mission time scale, epoch, resolution, drift, accuracy, holdover, leap/event handling, and reset behavior.`,
      `Drive a wide free-running counter from a characterized oscillator and capture external time references synchronously.`,
      `Estimate offset/frequency error in a bounded control loop; slew time when discontinuities would break users.`,
      `Distribute clocks through dedicated resources and time messages through SpaceWire/SpaceFibre or custom links.`,
      `Timestamp events at the I/O boundary before variable-latency buffering.`,
      `Expose lock, offset, drift, missing-reference, holdover duration, and clock-switch events.`
    ],
    resources: `Low-jitter PLLs, global clocks, wide counters, capture/compare units, digital PLL control, network time-code interfaces, and redundant oscillator muxing.`,
    verification: `Measure absolute and relative timestamp error, jitter, drift, holdover, source switching, counter rollover, reset, and network latency. Inject missing pulses and phase steps.`,
    space: `Protect counter and control state, avoid single-event clock glitches with qualified clock switching/filtering, retain monotonic time where required, and make loss of synchronization explicit in every affected product.`,
    refs: ["spacefibre", "spacewire", "ecss"]
  },
  {
    n: 20,
    title: "Command and data handling",
    purpose: `Decode spacecraft commands, collect housekeeping, assemble telemetry, and move data among subsystems while the primary flight software handles mission logic.`,
    path: `Uplink/network command → frame/CRC/authentication → command decoder/register or processor queue; housekeeping sources → scheduler → telemetry packets/frames → downlink.`,
    steps: [
      `Define command and telemetry dictionaries, APIDs or equivalent identifiers, sequence rules, time tags, and acknowledgements.`,
      `Terminate the link layer, verify CRC/authentication, and reject malformed lengths or illegal destinations before execution.`,
      `Dispatch simple register operations in hardware or queue complex commands to the flight processor.`,
      `Schedule housekeeping collection, timestamp values, apply validity flags, and construct packets with bounded lengths.`,
      `Prioritize emergency and health traffic over payload data and ensure congestion cannot block commanding.`,
      `Maintain acceptance, rejection, sequence, timeout, queue, and packet-generation counters.`
    ],
    resources: `CCSDS frame/packet engines, CRC/authentication cores, packet FIFOs, schedulers, register files, processor mailbox, time service, and network interfaces.`,
    verification: `Use command/telemetry conformance vectors and fuzz malformed frames, duplicates, reordering, time-tag boundaries, queue overflow, and resets. Trace every accepted command to one execution result and acknowledgement.`,
    space: `Keep safe-mode commanding small and independent, protect critical registers, authenticate destructive commands, and design the default response to corruption as rejection rather than partial execution.`,
    refs: ["ccsds", "spacewire", "ecss"]
  },
  {
    n: 21,
    title: "Fault detection and recovery",
    purpose: `Observe whether subsystems are alive and correct, classify failures, contain them, and execute bounded recovery without waiting for ground contact.`,
    path: `Health inputs/counters → debounce and plausibility → fault latches/timers → recovery state machine → reset, isolate, reconfigure, power-cycle, or safe-mode request → event telemetry.`,
    steps: [
      `Derive monitors from the FMEA: progress counters, heartbeats, voltage/current/temperature limits, protocol errors, memory errors, and output disagreement.`,
      `Filter transient indications with persistence or voting while preserving immediate action for hazardous limits.`,
      `Latch first-fault time and context before recovery changes the evidence.`,
      `Execute an escalation ladder: retry → local reset → interface isolation → reconfiguration → power cycle → spacecraft safe-mode request.`,
      `Limit retries and cool-down intervals to prevent reset or power-cycle loops.`,
      `Provide ground override, inhibit, event history, action count, and current recovery state.`
    ],
    resources: `Watchdogs, window comparators, timers, event latches, recovery FSM, reset/power-control interfaces, redundant cross-checks, and nonvolatile or protected logs.`,
    verification: `Inject every monitor condition singly and in combination; verify detection coverage, false trips, first-fault capture, recovery latency, retry limits, and behavior when the recovery hardware itself fails.`,
    space: `Place the highest-level supervisor outside the device it may need to recover, protect recovery state, avoid common clocks/power where independence is claimed, and test radiation-like faults rather than only software exceptions.`,
    refs: ["spacecube", "ecss", "nasaSee", "amdSem"]
  },
  {
    n: 22,
    title: "Triple modular redundancy",
    purpose: `Mask one faulty logic replica by running three copies and voting their outputs or state. TMR is a selective design technique, not a blanket substitute for radiation analysis.`,
    path: `Input → three separated logic domains A/B/C → majority voter → output; optional disagreement monitor identifies the minority replica and triggers repair.`,
    steps: [
      `Identify the state and outputs whose upset consequence justifies roughly triple logic plus voter overhead.`,
      `Triplicate registers, combinational logic, and relevant clocks/resets; do not merely triplicate the final register.`,
      `Insert voters at outputs and, for long stateful paths, feedback or partition boundaries so one bad replica does not persist uncontrolled.`,
      `Physically separate replicas and avoid shared routing, BRAM, clock, reset, enable, or voter resources that defeat independence.`,
      `Detect disagreement and count it; combine with configuration scrubbing or reset so masked faults do not accumulate.`,
      `Review synthesis and placement reports to confirm the tools did not merge equivalent replicas.`
    ],
    resources: `Triplicated registers/LUTs, majority or minority voters, disagreement counters, placement constraints, separate BRAM banks where needed, and scrub/recovery control.`,
    verification: `Force faults into each replica, voter input, shared input, reset, and configuration location. Confirm correct output for one fault, known behavior for two faults, and detection of latent disagreement.`,
    space: `TMR does not repair SRAM configuration, prevent SEFIs, or protect a common voter/supply/clock. Use it with scrubbing, ECC, fault containment, and a quantified upset-rate model.`,
    refs: ["ecss", "nasaSee", "amdSem"]
  },
  {
    n: 23,
    title: "Memory error correction and scrubbing",
    purpose: `Detect and correct bit errors in user memories and, for SRAM FPGAs, detect/repair configuration-memory upsets before they accumulate. These are two different scrubbing functions.`,
    path: `User memory write → ECC encode → stored codeword → read/scrub → syndrome/correction → data and counters; configuration path performs frame readback/check/correction through the device configuration port.`,
    steps: [
      `Select an ECC code from word width and expected error multiplicity; SECDED is common but not sufficient for every multi-bit pattern.`,
      `Encode on write and decode on read; report corrected and uncorrectable addresses without exposing corrupt data as valid.`,
      `Background-scan every memory address within the allowed accumulation time and rewrite corrected codewords.`,
      `Interleave physical bits so one particle or device fault is less likely to hit several bits in one codeword.`,
      `For SRAM configuration, integrate the vendor SEM/readback solution and define actions for correctable, essential, uncorrectable, and functional-interrupt events.`,
      `Use an independent watchdog/supervisor for the scrubber and retain error-rate telemetry.`
    ],
    resources: `ECC encoder/decoder, syndrome logic, scrub address generator, BRAM/DDR controller, configuration access port, vendor SEM core, event FIFO, and supervisor interface.`,
    verification: `Inject single and multiple data-bit errors, address/control errors, configuration bit flips, scrub interruption, counter overflow, and reset. Measure detection and repair latency and prove uncorrectable data is contained.`,
    space: `Configuration scrubbing does not correct user flip-flops or BRAM; memory ECC does not repair routing. Allocate each protected state class explicitly and calculate whether scrub period is short enough for the mission upset rate.`,
    refs: ["ecss", "nasaSee", "amdSem"]
  },
  {
    n: 24,
    title: "Redundancy management",
    purpose: `Select and cross-check primary/backup sensors, processors, links, memories, clocks, or power channels without creating a new single point of failure in the selector.`,
    path: `Redundant inputs → validity/freshness/plausibility and cross-comparison → selection policy → glitch-free mux or command → active-channel telemetry and fallback.`,
    steps: [
      `Define independence assumptions and failure modes for each redundant channel, including common power, clock, harness, environment, and software.`,
      `Validate each channel separately for freshness, range, self-test, error counters, and protocol health.`,
      `Compare channels using thresholds and time persistence appropriate to the measurement.`,
      `Apply a deterministic selection policy with hysteresis, inhibit conditions, and a manual command override.`,
      `Switch only at a safe boundary: packet, frame, zero crossing, disabled actuator interval, or qualified clock-mux event.`,
      `Log cause, old/new channel, disagreement, failed attempts, and dwell time.`
    ],
    resources: `Comparators, timers, validity logic, glitch-free clock/data muxes, crossbar, state machine, command registers, and protected event logs.`,
    verification: `Inject stuck, noisy, drifting, stale, contradictory, and intermittently recovering channels. Verify no chatter, no unsafe switching transient, correct override priority, and behavior when all channels are invalid.`,
    space: `Do not claim redundancy when both channels share an unprotected selector, clock, reset, or power rail. Protect and monitor the manager itself, and define the safe outcome for no-valid-source conditions.`,
    refs: ["ecss", "spacecube", "nasaSee"]
  },
  {
    n: 25,
    title: "Cryptography and secure communications",
    purpose: `Establish trust in boot images, commands, telemetry, stored data, and in-flight updates while accelerating cryptographic operations at line rate.`,
    path: `Key/trust anchor → secure boot measurement → authenticated command or data stream → AES/GCM or approved cipher/hash/signature → replay protection → protocol output and security telemetry.`,
    steps: [
      `Start with a threat model and mission security policy; choose approved algorithms, key sizes, modes, and lifecycle controls.`,
      `Anchor boot in immutable or protected logic that verifies each next-stage image before release from reset.`,
      `Implement authenticated encryption or MAC verification as a streaming engine with explicit nonce, sequence, and associated-data handling.`,
      `Store keys in device-supported secure storage or an external secure element; zeroize working keys on tamper/reset paths as required.`,
      `Reject replayed, expired, malformed, or unauthenticated commands before they reach functional decoders.`,
      `Authenticate FPGA bitstreams, software, model/parameter updates, and rollback metadata.`
    ],
    resources: `AES/GCM, SHA, signature-verification accelerators, true/random number interfaces, monotonic counters, secure key storage, protected boot ROM, and bus firewalls.`,
    verification: `Use standard known-answer and negative test vectors; test nonce/sequence rollover, reset, interrupted update, corrupt signature, rollback attempt, fault injection, and timing/side-channel requirements from the security plan.`,
    space: `Security and radiation recovery must cooperate: a corrupted update should fail closed and fall back to a verified image, while bit errors in counters or metadata must not permanently lock out recovery.`,
    refs: ["esaSecurity", "microchipReconfig", "ecss"]
  },
  {
    n: 26,
    title: "Motor and actuator control",
    purpose: `Generate deterministic drive commands and acquire feedback for reaction wheels, gimbals, valves, pumps, antenna mechanisms, robotic joints, or deployment devices.`,
    path: `Command/setpoint → range/rate/interlock validation → control law or commutation → PWM/step/valve outputs → power driver; current/position/speed feedback → capture/filter/fault logic.`,
    steps: [
      `Define actuator electrical interface, update rate, limits, dead time, braking, startup, shutdown, and single-fault safe state.`,
      `Capture encoder, resolver, Hall, current, and limit-switch feedback with synchronized and filtered inputs.`,
      `Implement commutation, PWM, step generation, or a bounded inner current/speed loop with explicit fixed-point scaling.`,
      `Apply independent command range, slew, duration, direction, and interlock checks before outputs.`,
      `Insert dead time and mutually exclusive gate logic in hardware; use external driver protection as a second layer.`,
      `Latch overcurrent, stall, runaway, encoder loss, limit conflict, and timeout with safe output shutdown.`
    ],
    resources: `PWM/capture units, quadrature decoder, ADC/SPI interfaces, DSP control loop, timers, interlock logic, redundant inhibit outputs, and watchdog.`,
    verification: `Use a motor/actuator plant model and hardware-in-the-loop; test startup, reversal, load steps, sensor faults, stuck switches, missed commutation, driver delay, saturation, and emergency shutdown latency.`,
    space: `Make power-up outputs safe, use independent hardware current limiting and inhibits for hazardous motion, protect control state, and prevent a reset from producing an unintended pulse.`,
    refs: ["gnc", "ecssEngineering", "ecss"]
  },
  {
    n: 27,
    title: "Power-system supervision",
    purpose: `Sequence rails, monitor voltage/current/temperature, control converters or load switches, and isolate a failing load before it collapses the spacecraft bus.`,
    path: `Voltage/current/temperature ADCs and power-good inputs → filtering/limits → sequencing and protection FSM → enable/inhibit/load-shed outputs → event telemetry.`,
    steps: [
      `Define rail dependencies, ramp windows, inrush limits, undervoltage/overvoltage thresholds, thermal limits, and required isolation.`,
      `Synchronize digital status and sample ADCs; use persistence and hysteresis to prevent chatter near limits.`,
      `Implement a table-driven or explicit power sequence with per-step timeout and rollback to a known safe state.`,
      `Separate fast hardware shutdown thresholds from slower supervisory decisions and ground-command policies.`,
      `Apply retry limits, cool-down time, and load-shedding priority; record the first fault before removing power.`,
      `Provide independent emergency inhibit paths where a single FPGA failure cannot safely control hazardous power.`
    ],
    resources: `ADC/SPI/I2C interfaces, comparators, filters, timers, sequencing FSM, PWM if digital power control is used, nonvolatile/event log interface, and redundant enables.`,
    verification: `Use programmable supplies/electronic loads or a plant simulator; test ramps, brownouts, shorts, inrush, sensor faults, thermal trips, reset mid-sequence, retry exhaustion, and simultaneous faults.`,
    space: `Analyze FPGA output behavior during unpowered/partial-power states, latch-up or SEFI response, and external pull resistors. Critical shutdown should not depend only on complex reprogrammable logic.`,
    refs: ["ecssEngineering", "ecss", "nasaSee"]
  },
  {
    n: 28,
    title: "Onboard processor acceleration",
    purpose: `Move repetitive parallel kernels from a flight CPU into FPGA datapaths while the CPU keeps scheduling, configuration, exceptions, and higher-level algorithms.`,
    path: `CPU descriptors/data → DMA → accelerator input buffers → pipelined kernel → output buffers → interrupt/status and CPU post-processing.`,
    steps: [
      `Profile the real application and select kernels dominated by parallel arithmetic or data movement, not control-heavy code.`,
      `Define a stable hardware/software contract: buffers, strides, formats, precision, commands, completion, errors, and cache coherency.`,
      `Create a bit-accurate fixed-point or reduced-precision model and quantify acceptable error.`,
      `Pipeline and parallelize the kernel to the required throughput; tile data to fit on-chip memory and burst external memory efficiently.`,
      `Use DMA and double buffering so computation overlaps transfers.`,
      `Add timeout, abort, version, self-test, and bypass paths so the CPU can recover from accelerator failure.`
    ],
    resources: `DSP/AI engines, BRAM/URAM scratchpads, DMA, AXI or NoC interconnect, external DDR, interrupt/status registers, and performance counters.`,
    verification: `Compare hardware outputs with the software reference over nominal and corner data, then measure end-to-end latency, bandwidth, power, CPU load, coherency, overlap, timeout, and reset recovery.`,
    space: `Protect descriptors and shared memory, contain malformed lengths/addresses, monitor progress, and ensure an accelerator cannot overwrite flight-software memory or block the bus indefinitely.`,
    refs: ["spacecube", "amdXqr", "ecss"]
  },
  {
    n: 29,
    title: "Soft-core processor implementation",
    purpose: `Instantiate a configurable processor such as RISC-V or MicroBlaze inside the FPGA for local control, protocol handling, housekeeping, or algorithm orchestration.`,
    path: `Boot ROM/verified image → soft CPU → local instruction/data memory and peripherals → FPGA accelerators/network → watchdog and supervisor.`,
    steps: [
      `Define why a soft CPU is preferable to a state machine or external processor and allocate its criticality.`,
      `Configure ISA, privilege, caches, MMU/MPU, debug, timers, interrupt controller, and tightly coupled memory.`,
      `Create a memory map with bus firewalls, bounded DMA access, and separate critical/noncritical peripherals.`,
      `Boot from protected ROM or verified nonvolatile storage; verify firmware integrity before enabling mission outputs.`,
      `Run a small RTOS or bare-metal scheduler with watchdog, stack/heap guards, exception logging, and deterministic critical paths.`,
      `Keep high-throughput work in hardware accelerators connected by FIFOs or DMA rather than polling loops.`
    ],
    resources: `Processor IP, BRAM/ECC memory, bus interconnect, timers, interrupt controller, debug module, MPU/firewall, boot ROM, and accelerator interfaces.`,
    verification: `Verify RTL subsystem integration plus software unit/integration tests, interrupt storms, memory faults, illegal accesses, stack overflow, watchdog, boot corruption, firmware update, and worst-case execution time.`,
    space: `Use ECC/parity for memories, lockstep or redundant processors only when justified, protect the boot path, and retain an external or hardware-level recovery route if the soft CPU stops executing.`,
    refs: ["spacecube", "microchipRtg4", "ecss"]
  },
  {
    n: 30,
    title: "In-flight reconfiguration",
    purpose: `Replace all or part of the FPGA design after launch to add algorithms, change protocols, correct defects, or recover from persistent faults.`,
    path: `Ground package → authenticated uplink → staging memory → integrity/signature check → independent configuration controller → FPGA JTAG/SelectMAP/ICAP or vendor interface → self-test → commit or rollback.`,
    steps: [
      `Define whether updates are full-device, partial-region, parameter-only, or nonvolatile reprogramming, and which functions must remain alive.`,
      `Create a signed package containing target device/board ID, version, compatibility, length, hash, rollback version, and the bitstream.`,
      `Store the complete candidate image before programming and verify it independently of transport CRC.`,
      `Use a trusted supervisor to place interfaces in safe state, stop affected traffic, configure the FPGA, and enforce a timeout.`,
      `Run power-on and application self-tests before declaring the image operational; keep a golden image that the candidate cannot overwrite.`,
      `On interruption or failed test, power-cycle/reconfigure from the golden image and report the exact failure stage.`
    ],
    resources: `Secure staging memory, hash/signature accelerator or trusted MCU, configuration port, golden/candidate image selector, watchdog, reset/power control, version store, and self-test logic.`,
    verification: `Interrupt power and communication at every update phase; corrupt headers, payload, signature, metadata, and self-test results; attempt rollback and wrong-target images; prove deterministic recovery from each case.`,
    space: `The update controller, golden image, and minimum command/telemetry path must not depend on the image being replaced. Combine security, radiation error handling, version control, and operational rehearsal.`,
    refs: ["microchipReconfig", "esaSecurity", "amdXqr", "ecss"]
  }
];

function makeReferences(refKeys) {
  return refKeys.map((key) => {
    const [label, href] = referenceCatalog[key];
    return `[${label}](${href})`;
  }).join(", ");
}

function makeUseBody(use) {
  const steps = use.steps.map((step, index) => `${index + 1}. ${step}`).join("\n\n");
  return [
    `## ${use.n}. ${use.title}`,
    `**What it does.** ${use.purpose}`,
    `### Data path\n\n${use.path}`,
    `### Implementation sequence\n\n${steps}`,
    `### FPGA resources and interfaces\n\n${use.resources}`,
    `### Verification\n\n${use.verification}`,
    `### Space-specific design\n\n${use.space}`,
    `**Primary references:** ${makeReferences(use.refs)}`
  ].join("\n\n");
}

const chartSource = {
  id: "taxonomy_sql",
  label: "Report taxonomy of 30 FPGA space uses",
  query: {
    engine: "portable-sql",
    language: "sql",
    sql: "SELECT * FROM (VALUES ('Payload and science', 10, 'Sensors, imagery, radar, navigation and instruments'), ('Communications and networking', 7, 'Radio, coding, beamforming, optical links and protocols'), ('Avionics, control and reliability', 10, 'Storage, GNC, timing, C&DH, mitigation, actuators and power'), ('Computing and reconfiguration', 3, 'Acceleration, soft processors and in-flight updates')) AS t(category, use_count, examples)",
    description: "Materializes the report taxonomy used to organize the 30 implementation recipes.",
    executed_at: "2026-07-15T00:00:00Z"
  }
};

const documentSources = Object.entries(referenceCatalog).map(([id, [label, href]]) => ({ id, label, href }));
const sources = [chartSource, ...documentSources];

const blocks = [
  {
    id: "title",
    type: "markdown",
    body: "# How FPGAs Are Used in Space: 30 Implementation Recipes"
  },
  {
    id: "technical_summary",
    type: "markdown",
    body: `## Technical summary\n\nEvery FPGA space application follows the same basic discipline: define the external interface and failure behavior; capture and timestamp data; buffer clock/rate differences; implement a deterministic streaming or control pipeline; protect state and memory; expose health telemetry; and verify normal, corner, and injected-fault behavior. The 30 sections below show that sequence for every use from payload acquisition to in-flight reconfiguration.\n\nThis is an engineering recipe, not a drop-in flight design. Exact sample rates, word widths, codes, clock domains, latency, redundancy, radiation margins, and qualification evidence come from a mission’s requirements and selected parts. The most reusable pattern is to keep high-rate deterministic work in hardware, complex policies in software, and the highest-level recovery authority independent of the FPGA it may need to restore.`
  },
  {
    id: "scope",
    type: "markdown",
    body: `## How to read each recipe\n\nEach section defines six things: the function; the end-to-end data path; a concrete implementation sequence; typical FPGA resources; verification evidence; and the extra controls needed for space. Arrows describe hardware flow, not software call order. “Protect” means select a justified mechanism—ECC, parity, TMR, duplication, CRC, scrubbing, watchdog, physical separation, external supervision, or operational recovery—based on the fault model.\n\nWhere a function can run in either FPGA logic or software, the recipe puts cycle-accurate, high-throughput, interface-adjacent work in the FPGA and leaves catalog search, mission policy, large dynamic data structures, and frequently changing algorithms on a processor unless latency demands otherwise.`
  },
  {
    id: "taxonomy_intro",
    type: "markdown",
    body: `## The 30 uses fall into four implementation families\n\nPayload/science and avionics/reliability contain the most recipes because those groups cover both data-plane and control-plane functions. The chart is a taxonomy of this document, not a measurement of industry deployment. Use it as a navigation aid: nearby functions often share interfaces, verification models, and mitigation patterns.`
  },
  {
    id: "taxonomy_chart_block",
    type: "chart",
    chartId: "taxonomy_chart"
  },
  {
    id: "common_architecture",
    type: "markdown",
    body: `## A common flight implementation surrounds the algorithm\n\nA robust FPGA design usually has eight layers: **I/O termination**, **clock/reset and synchronization**, **framing and timestamping**, **elastic buffering**, **the mission algorithm**, **protected storage**, **packet/DMA/network output**, and **health/recovery control**. The algorithm is often the easy middle. Most mission failures arise at boundaries: an unconstrained clock crossing, stale calibration, buffer overflow, corrupt descriptor, unsafe reset, ambiguous partial packet, failed update, or a recovery path that shares the failed resource.\n\nBefore RTL, create requirements, interface-control documents, a fixed-point golden model, throughput/latency budgets, a clock/reset diagram, a sensitive-state inventory, and a fault-response table. After RTL, require lint, CDC/RDC review, self-checking simulation, assertions, timing closure, hardware stress, fault injection, and configuration-controlled builds. [ECSS-E-ST-20-40C](https://ecss.nl/standard/ecss-e-st-20-40c-asic-fpga-and-ip-core-engineering-11-october-2023/) provides the current European FPGA engineering framework; the [ECSS mitigation handbook](https://ecss.nl/home/ecss-e-hb-20-40a-engineering-techniques-for-radiation-effects-mitigation-in-asics-and-fpgas-handbook/) describes radiation mitigation and validation guidance.`
  },
  ...uses.map((use) => ({ id: `use_${String(use.n).padStart(2, "0")}`, type: "markdown", body: makeUseBody(use) })),
  {
    id: "integration_strategy",
    type: "markdown",
    body: `## Build one end-to-end thread before scaling the design\n\nFor any selected use, begin with one channel, one frame or packet type, one clock domain, and a software golden model. Prove capture → processing → output with self-checking simulation. Then add channels, parallelism, external memory, modes, redundancy, and fault recovery one at a time. Every addition should preserve a measurable invariant: no accepted input disappears silently; no output is reported valid without its metadata; no buffer can overflow without a defined response; no reset creates an unsafe external pulse; and every autonomous recovery is bounded and telemetered.`
  },
  {
    id: "limitations",
    type: "markdown",
    body: `## Limitations and tailoring questions\n\nThe recipes are device- and mission-neutral. They do not select a flight part, guarantee radiation tolerance, define a safety case, or replace the applicable CCSDS, ECSS, NASA, export-control, cybersecurity, or procurement requirements. Vendor IP behavior and radiation characteristics vary by exact device, package, speed/temperature grade, tool version, configuration mode, and lot.\n\nTo turn any recipe into an implementable specification, answer: What orbit/trajectory and lifetime? What are the electrical interfaces and data rates? Which outputs can affect safety? What latency and data loss are acceptable? Which faults must be masked, detected, or recovered? Is in-flight update required? Which processor, memory, network, and qualification ecosystem is mandated? Those answers determine architecture and verification depth.`
  },
  {
    id: "next_steps",
    type: "markdown",
    body: `## Recommended next step\n\nChoose one use case and write a one-page mission slice containing inputs, outputs, rates, clocks, latency, memory, operating modes, fault responses, and test evidence. Then implement a terrestrial demonstrator with the same block boundaries and fault telemetry. Good first choices are payload acquisition plus packetization, UART/SPI protocol conversion, a protected FIFO/memory path, or the telemetry processor described in the companion beginner report.`
  }
];

const artifact = {
  surface: "report",
  manifest: {
    version: 1,
    surface: "report",
    title: "How FPGAs Are Used in Space: 30 Implementation Recipes",
    description: "A detailed implementation-oriented companion explaining the data path, engineering steps, FPGA blocks, verification, and space-specific design for 30 FPGA applications.",
    generatedAt: "2026-07-15T00:00:00Z",
    charts: [
      {
        id: "taxonomy_chart",
        title: "Implementation recipes by functional family",
        subtitle: "All 30 uses in this document; counts organize the guide and do not measure deployment frequency.",
        showDescription: true,
        type: "bar",
        dataset: "taxonomy",
        sourceId: "taxonomy_sql",
        encodings: {
          x: { field: "category", type: "nominal", label: "Functional family" },
          y: { field: "use_count", type: "quantitative", label: "Number of recipes", unit: "uses" },
          tooltip: [
            { field: "category", type: "text", label: "Family" },
            { field: "use_count", type: "quantitative", label: "Recipes" },
            { field: "examples", type: "text", label: "Scope" }
          ]
        },
        valueFormat: "number",
        unit: "uses",
        layout: "full"
      }
    ],
    sources,
    blocks
  },
  snapshot: {
    version: 1,
    generatedAt: "2026-07-15T00:00:00Z",
    status: "ready",
    datasets: {
      taxonomy: [
        { category: "Payload and science", use_count: 10, examples: "Sensors, imagery, radar, navigation and instruments" },
        { category: "Communications and networking", use_count: 7, examples: "Radio, coding, beamforming, optical links and protocols" },
        { category: "Avionics, control and reliability", use_count: 10, examples: "Storage, GNC, timing, C&DH, mitigation, actuators and power" },
        { category: "Computing and reconfiguration", use_count: 3, examples: "Acceleration, soft processors and in-flight updates" }
      ]
    }
  },
  sources
};

fs.writeFileSync(outputPath, JSON.stringify(artifact, null, 2), "utf8");
console.log(JSON.stringify({ outputPath, uses: uses.length, blocks: blocks.length, sources: sources.length }));
