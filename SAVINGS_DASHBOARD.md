# Eco-Loop — Quantitative Savings Dashboard

**Evaluation window:** 07/14 – 07/20 (Chicago summer peak week)
**Building model:** DOE Reference Medium Office (18 zones, 15 occupied)
**Comparison:** Baseline fixed HVAC schedule vs. AI-controlled (LLM) closed-loop operation

## Results Table

| Metric | Baseline (Fixed Schedule) | AI-Controlled (LLM) | Change |
|---|---|---|---|
| Total electricity consumption | 16,142.2 kWh | 15,198.7 kWh | **-5.8%** |
| Average PMV (thermal comfort) | -0.485 | -0.185 | Closer to ASHRAE 55 neutral (0) |
| Comfort violations (\|PMV\| > 0.5) | 40.0% of timesteps | 23.1% of timesteps | **-16.9 percentage points** |
| Max \|PMV\| deviation | 1.170 | 1.101 | Reduced |

## Key Finding

The AI-controlled strategy achieved a **5.8% reduction in total electricity
consumption** while **simultaneously reducing thermal comfort violations
from 40.0% to 23.1% of timesteps** — nearly halved. This demonstrates the
closed-loop controller did not trade occupant comfort for energy savings;
it improved both metrics together, correcting an over-conservative
baseline cooling schedule that had been running colder than necessary for
occupant comfort while also consuming more energy to do so.

## Methodology

- Both runs simulate the identical building model and weather file (Chicago
  TMY3), differing only in how HVAC setpoints are determined.
- **Baseline:** original fixed heating/cooling setpoint schedule as
  provided in the DOE reference building model (occupied heating 21°C,
  occupied cooling 24°C, with night/weekend setback).
- **AI-Controlled:** heating/cooling setpoints determined once per
  simulated hour by a local LLM (Llama 3.2) based on live outdoor
  temperature, zone temperature, and PMV comfort index, validated against
  ASHRAE 55 deadband and safety bounds before being applied.
- Electricity totals are computed by summing all hourly HVAC-relevant
  electricity submeters (fans, cooling, heating, interior lighting,
  interior equipment) across all 672 fifteen-minute timesteps in the
  evaluation week.
- Comfort is measured via the Fanger PMV model for the building's core
  occupied zone, sampled at every 15-minute zone timestep.

## Visual Comparison

![Results comparison chart](results_comparison_chart.png)

## Reproducing These Results

```powershell
python run_baseline.py
python llm_control.py
python dashboard.py
python make_chart.py
```

`dashboard.py` prints the full breakdown (row counts, PMV statistics,
electricity totals per run) to the console; the table above reflects its
output for the 07/14–07/20 evaluation week.