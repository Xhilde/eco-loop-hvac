"""
export_modified_idf.py
-----------------------
Deliverable #2 support: exports a "modified" version of the baseline IDF
where the original fixed HTGSETP_SCH / CLGSETP_SCH schedules are replaced
with the actual hour-by-hour setpoint sequence the LLM produced during the
AI-controlled run (from llm_setpoint_log.csv). This lets anyone re-run the
exact AI-driven setpoint sequence through EnergyPlus without needing the
live LLM/Ollama loop.
"""

import csv
import sys

EPLUS_ROOT = r"C:\EnergyPlusV26-1-0"
sys.path.insert(0, EPLUS_ROOT)

from eppy.modeleditor import IDF

IDF.setiddname(EPLUS_ROOT + r"\Energy+.idd")

# --- load the LLM's actual applied setpoint sequence ---
with open("llm_setpoint_log.csv", newline="") as f:
    reader = csv.DictReader(f)
    log_rows = list(reader)

print(f"Loaded {len(log_rows)} logged setpoint decisions")

# keep only the real evaluation week (07/14-07/20), in case earlier
# sizing-day rows got logged too
week_rows = [r for r in log_rows if r["month"] == "7" and 14 <= int(r["day"]) <= 20]
print(f"{len(week_rows)} rows are within the 07/14-07/20 evaluation week")

# --- build Schedule:Compact field lists for heating and cooling ---
# Schedule:Compact format: Through: date, For: days, Until: HH:MM, value, ...
# We build one "Until" entry per logged hour, grouped by day.

def build_schedule_fields(week_rows, key):
    fields = []
    days_seen = sorted(set((int(r["month"]), int(r["day"])) for r in week_rows))
    for month, day in days_seen:
        day_rows = [r for r in week_rows if int(r["month"]) == month and int(r["day"]) == day]
        day_rows.sort(key=lambda r: int(r["hour"]))
        fields.append(f"Through: {month:02d}/{day:02d}")
        fields.append("For: AllDays")
        for r in day_rows:
            hour = int(r["hour"])
            end_hour = hour + 1
            fields.append(f"Until: {end_hour:02d}:00")
            fields.append(r[key])
    return fields

heat_fields = build_schedule_fields(week_rows, "heating_setpoint")
cool_fields = build_schedule_fields(week_rows, "cooling_setpoint")

# --- edit the IDF ---
idf = IDF("idf/baseline.idf")

for sched_name, fields, out_name in [
    ("HTGSETP_SCH", heat_fields, "AI_HTGSETP_SCH"),
    ("CLGSETP_SCH", cool_fields, "AI_CLGSETP_SCH"),
]:
    old = [s for s in idf.idfobjects["SCHEDULE:COMPACT"] if s.Name == sched_name][0]
    sched_type = old.Schedule_Type_Limits_Name
    idf.removeidfobject(old)

    new_sched = idf.newidfobject("SCHEDULE:COMPACT", Name=out_name,
                                   Schedule_Type_Limits_Name=sched_type)
    # bypass eppy's Field_N attribute mechanism (breaks on dynamic extension);
    # directly extend the underlying field-value list instead
    new_sched.obj.extend(fields)

# repoint the dual setpoint thermostats to the renamed AI schedules
for dsp in idf.idfobjects["THERMOSTATSETPOINT:DUALSETPOINT"]:
    dsp.Heating_Setpoint_Temperature_Schedule_Name = "AI_HTGSETP_SCH"
    dsp.Cooling_Setpoint_Temperature_Schedule_Name = "AI_CLGSETP_SCH"

idf.saveas("idf/ai_controlled.idf")
print("Saved idf/ai_controlled.idf")