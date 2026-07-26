# Eco-Loop Building Agents — System Architecture Document

**Author:** PAULOSTA KARMAKAR
**Problem Statement:** Eco-Loop Building Agents

## 1. Overview

Eco-Loop is a closed-loop control pipeline that pairs EnergyPlus (a
physics-based building energy simulation engine) with a locally-hosted
open-source LLM (Llama 3.2 via Ollama) acting as a supervisory reasoning
layer over the building's HVAC setpoints. Every simulated hour, the system
reads live sensor data from EnergyPlus, passes it to the LLM through a
validated tool-calling interface, and writes the LLM's decision back into
the running simulation via the EnergyPlus Actuator API.

## 2. Tool-Calling Architecture

The LLM never touches EnergyPlus directly. All interaction happens through
a `ToolServer` class (`tools.py`) that exposes a small, explicit set of
named operations:

- `get_zone_conditions()` — current zone temperature and PMV comfort index
- `get_site_conditions()` — outdoor temperature and simulation timestamp
- `set_hvac_setpoints(heating_c, cooling_c)` — proposes new setpoints

This mirrors the shape of a Model Context Protocol (MCP) tool server —
each capability is a named, schema-bound function rather than free-form
access to the simulation state — but is implemented as an in-process
Python interface rather than a networked MCP server, since the control
loop runs in a single process alongside EnergyPlus and does not need a
transport layer. The `ToolServer` is the sole authority for validating and
applying control actions:

- `set_hvac_setpoints` enforces a minimum 1.1°C heating/cooling deadband
  (ASHRAE 55) and rejects proposals outside safe bounds (heating 15-22°C,
  cooling 22-28°C).
- Rejected or malformed proposals never reach the actuators; the system
  holds the last accepted setpoint instead (zero-order hold).

This separation means the EnergyPlus-facing code (`llm_control.py`) never
needs to know *how* a decision was made — the LLM could be swapped for a
different model, a rule-based controller, or a human operator without
changing the simulation wiring at all. This was validated directly: the
project includes both an LLM-backed decision path and earlier rule-based
placeholders in `dev_validation_scripts/`, both driving the exact same
`ToolServer` interface.

## 3. Prompt Engineering Strategy

The LLM is given a compact, structured prompt each decision cycle
containing: outdoor temperature, current zone temperature, and current
PMV comfort index, plus explicit numeric constraints (heating range,
cooling range, minimum deadband) and a strict output format instruction
("reply with ONLY two numbers separated by a comma").

Design choices:
- **Numeric-only output contract.** Rather than asking the LLM to call a
  structured JSON tool schema (which smaller local models handle
  inconsistently), the prompt asks for a minimal two-number reply. This
  reduces parsing failure surface area, at the cost of not using a native
  function-calling API — an intentional tradeoff given Llama 3.2's
  reliability profile at this size.
- **Constraints stated in the prompt, not assumed.** The valid ranges and
  deadband rule are restated in the prompt text even though they are also
  enforced downstream by the validator — this reduces the rate of
  proposals that get rejected, since the model is nudged toward valid
  outputs before validation ever runs.
- **No conversation history.** Each decision is a fresh, single-turn
  prompt with only the current state — no memory of past decisions is
  passed back to the LLM. This keeps prompt size constant regardless of
  how long the simulation runs (see Section 5) and avoids compounding
  drift from earlier reasoning.

## 4. Prompt Latency Management

LLM inference introduces real wall-clock latency (observed: roughly
1-5 seconds per call locally) that cannot keep pace with EnergyPlus's
15-minute simulation timestep if called every timestep. To manage this:

- **Decision throttling.** The LLM is invoked once every 4 zone timesteps
  (i.e., once per simulated hour at a 15-minute timestep resolution), not
  every timestep. Between calls, the last accepted setpoint is held and
  reapplied to the actuators every timestep via zero-order hold.
- **Bounded retry behavior.** If an LLM call fails (network error, malformed
  response, timeout), the system does not retry mid-timestep or block the
  simulation — it logs the failure and falls back to holding the previous
  setpoint, then simply waits for the next scheduled decision point.
- **Fixed timeout.** The Ollama HTTP call is capped at 15 seconds; a hung
  or slow model response cannot stall the simulation indefinitely.

This bounds total added wall-clock time to roughly (number of simulated
hours) x (LLM latency), independent of simulation timestep resolution —
increasing timestep resolution for higher physical accuracy does not
increase LLM call volume.

## 5. Handling Lengthy Simulation Logs

A full annual EnergyPlus run can produce very large `.eso`/`.csv` output
files (tens of thousands of timesteps across many output variables). Two
strategies keep this tractable:

- **Simulation period scoping.** The IDF's `RunPeriod` is trimmed to a
  representative one-week window (a Chicago summer peak week) rather than
  a full year for development and evaluation. This keeps output file size
  and simulation wall-clock time manageable while remaining representative
  of peak cooling-load conditions, where control strategy differences are
  most visible.
- **Streaming analysis, not full-file loads for control.** The live
  control loop (`llm_control.py`) never reads the output CSV — it reads
  sensor values directly from the EnergyPlus Python API's in-memory state
  each timestep, so simulation length does not affect the LLM's per-decision
  prompt size or the loop's memory footprint. Only the post-hoc comparison
  script (`dashboard.py`) parses the full CSV output, and does so via
  streaming row-by-row iteration and column-index lookups rather than
  loading the entire file into a dense in-memory table.

## 6. Results Summary

Over the evaluation week (07/14-07/20, Chicago peak summer conditions),
AI-controlled operation reduced total electricity consumption by 5.8%
(16,142.2 kWh -> 15,198.7 kWh) while simultaneously reducing thermal
comfort violations (|PMV| > 0.5) from 40.0% to 23.1% of timesteps —
demonstrating the closed loop improved energy efficiency and occupant
comfort together rather than trading one for the other. This AI-controlled
setpoint sequence is embedded directly in `idf/ai_controlled.idf` (see
`export_modified_idf.py`), allowing it to be re-run independently of the
live LLM/Ollama loop.

## 7. Known Limitations / Future Work

- Control is applied building-wide via two shared setpoint schedules
  (all 15 occupied zones share `HTGSETP_SCH` / `CLGSETP_SCH` in this
  reference building model); per-zone control is a straightforward
  extension using the same `ToolServer` interface with per-zone actuator
  handles.
- The tool interface is MCP-shaped but not a literal MCP server; exposing
  the same methods over an MCP transport (e.g. stdio) is a small,
  well-scoped follow-up change.
- Grid carbon intensity / peak-demand signals were not incorporated into
  this evaluation; the `ToolServer` interface is designed to accommodate
  an additional `get_grid_signal()` tool without structural changes.