import csv

def load_csv(path):
    with open(path, newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)
    return header, rows

def col_index(header, exact_name):
    for i, h in enumerate(header):
        if h.strip() == exact_name:
            return i
    raise ValueError(f"Column '{exact_name}' not found. Available: {header}")

def parse_datetime(d):
    d = d.strip()
    date_part, time_part = d.split("  ")
    month, day = date_part.split("/")
    hh, mm, ss = time_part.split(":")
    return int(month), int(day), int(hh), int(mm), int(ss)

def week_hourly_rows(rows):
    """Filter to hourly rows (mm=0, ss=0) within 07/14-07/20."""
    out = []
    for r in rows:
        try:
            m, day, hh, mm, ss = parse_datetime(r[0])
        except Exception:
            continue
        if m == 7 and 14 <= day <= 20 and mm == 0 and ss == 0:
            out.append(r)
    return out

def week_quarter_hour_rows(rows):
    """Filter to true 15-min zone-timestep rows within 07/14-07/20."""
    out = []
    for r in rows:
        try:
            m, day, hh, mm, ss = parse_datetime(r[0])
        except Exception:
            continue
        if m == 7 and 14 <= day <= 20 and mm in (0, 15, 30, 45) and ss == 0:
            out.append(r)
    return out

ELECTRICITY_SUBMETERS = [
    "Fans:Electricity [J](Hourly)",
    "Cooling:Electricity [J](Hourly)",
    "Heating:Electricity [J](Hourly)",
    "InteriorLights:Electricity [J](Hourly)",
    "InteriorEquipment:Electricity [J](Hourly)",
]

def total_electricity_kwh(mtr_path):
    header, rows = load_csv(mtr_path)
    week_rows = week_hourly_rows(rows)
    indices = [col_index(header, name) for name in ELECTRICITY_SUBMETERS]

    total_j = 0.0
    rows_used = 0
    for r in week_rows:
        if len(r) <= max(indices):
            continue
        row_total = sum(float(r[i]) for i in indices)
        total_j += row_total
        rows_used += 1

    print(f"  (electricity: summed {len(indices)} submeters across {rows_used} hourly rows)")
    return total_j / 3.6e6  # J -> kWh

def comfort_stats(out_path):
    header, rows = load_csv(out_path)
    week_rows = week_quarter_hour_rows(rows)
    pmv_idx = None
    for i, h in enumerate(header):
        if "CORE_BOTTOM PEOPLE:Zone Thermal Comfort Fanger Model PMV" in h:
            pmv_idx = i
            break
    if pmv_idx is None:
        raise ValueError("PMV column not found")

    pmv_vals = [float(r[pmv_idx]) for r in week_rows if len(r) > pmv_idx and r[pmv_idx].strip() != ""]
    avg_pmv = sum(pmv_vals) / len(pmv_vals)
    max_abs_pmv = max(abs(v) for v in pmv_vals)
    violations = sum(1 for v in pmv_vals if abs(v) > 0.5)
    violation_pct = 100 * violations / len(pmv_vals)
    return avg_pmv, max_abs_pmv, violation_pct, len(pmv_vals)

def analyze(out_path, mtr_path, label):
    print(f"\n=== {label} ===")
    kwh = total_electricity_kwh(mtr_path)
    avg_pmv, max_pmv, viol_pct, n = comfort_stats(out_path)
    print(f"Total electricity:    {kwh:.1f} kWh")
    print(f"PMV rows analyzed:    {n}")
    print(f"Average PMV:          {avg_pmv:.3f}")
    print(f"Max |PMV| deviation:  {max_pmv:.3f}")
    print(f"Comfort violations:   {viol_pct:.1f}% of timesteps with |PMV| > 0.5")
    return kwh, avg_pmv, viol_pct


if __name__ == "__main__":
    baseline_kwh, baseline_pmv, baseline_viol = analyze(
        r"results\eplusout.csv", r"results\eplusmtr.csv", "BASELINE (fixed schedule)"
    )
    ai_kwh, ai_pmv, ai_viol = analyze(
        r"results_llm_control\eplusout.csv", r"results_llm_control\eplusmtr.csv", "AI-CONTROLLED (LLM)"
    )

    savings_pct = 100 * (baseline_kwh - ai_kwh) / baseline_kwh

    print("\n=== COMPARISON ===")
    print(f"Energy: baseline={baseline_kwh:.1f} kWh, AI={ai_kwh:.1f} kWh -> {savings_pct:+.1f}% change")
    print(f"Comfort violations: baseline={baseline_viol:.1f}%, AI={ai_viol:.1f}%")