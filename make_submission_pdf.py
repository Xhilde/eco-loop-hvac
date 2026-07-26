from fpdf import FPDF
import os

TEXT_FILES = [
    "README.md",
    "SYSTEM_ARCHITECTURE.md",
    "SAVINGS_DASHBOARD.md",
    "tools.py",
    "llm_decide.py",
    "llm_control.py",
    "run_baseline.py",
    "dashboard.py",
    "make_chart.py",
    "export_modified_idf.py",
    "llm_setpoint_log.csv",
]

IMAGE_FILES = [
    "results_comparison_chart.png",
]

pdf = FPDF()
pdf.set_auto_page_break(auto=True, margin=15)

# --- Title page ---
pdf.add_page()
pdf.set_font("Courier", "B", 18)
pdf.multi_cell(0, 10, "Eco-Loop Building Agents - Submission Package")
pdf.set_font("Courier", "", 11)
pdf.ln(5)
pdf.multi_cell(0, 6, "This document contains all source code, documentation, "
                     "and results for the Eco-Loop Building Agents project. "
                     "The full repository with commit history, both full IDF "
                     "building models, and the PoC demo video is available at:\n"
                     "https://github.com/Xhilde/eco-loop-hvac")

# --- Text files ---
for fname in TEXT_FILES:
    if not os.path.exists(fname):
        print(f"WARNING: {fname} not found, skipping")
        continue
    pdf.add_page()
    pdf.set_font("Courier", "B", 14)
    pdf.multi_cell(0, 8, fname)
    pdf.set_font("Courier", "", 8)
    pdf.ln(2)
    with open(fname, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    # fpdf2 chokes on some unicode; strip anything outside latin-1
    safe_content = content.encode("latin-1", errors="replace").decode("latin-1")
    pdf.multi_cell(0, 4, safe_content)
    print(f"Added: {fname}")

# --- IDF excerpt (just the AI-generated schedule, not the full 8000-line file) ---
pdf.add_page()
pdf.set_font("Courier", "B", 14)
pdf.multi_cell(0, 8, "idf/baseline.idf and idf/ai_controlled.idf (excerpt)")
pdf.set_font("Courier", "", 9)
pdf.ln(2)
pdf.multi_cell(0, 5,
    "Both full building model files (baseline.idf and ai_controlled.idf) "
    "are included in the GitHub repository under idf/. The full baseline "
    "file is ~8,300 lines (standard EnergyPlus building geometry, "
    "materials, and HVAC definitions) and is not reproduced here in full. "
    "Below is the AI-generated setpoint schedule embedded in "
    "ai_controlled.idf, showing the actual hour-by-hour heating/cooling "
    "setpoints the LLM produced during the evaluation week, replacing the "
    "original fixed HTGSETP_SCH / CLGSETP_SCH schedules.\n"
)
if os.path.exists("idf/ai_controlled.idf"):
    with open("idf/ai_controlled.idf", "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    start = next((i for i, l in enumerate(lines) if "AI_HTGSETP_SCH" in l), None)
    if start is not None:
        excerpt = "".join(lines[start:start + 40])
        safe_excerpt = excerpt.encode("latin-1", errors="replace").decode("latin-1")
        pdf.set_font("Courier", "", 7)
        pdf.multi_cell(0, 3.5, safe_excerpt)
    print("Added: idf/ai_controlled.idf excerpt")
else:
    print("WARNING: idf/ai_controlled.idf not found, skipping excerpt")

# --- Images ---
for fname in IMAGE_FILES:
    if not os.path.exists(fname):
        print(f"WARNING: {fname} not found, skipping")
        continue
    pdf.add_page()
    pdf.set_font("Courier", "B", 14)
    pdf.multi_cell(0, 8, fname)
    pdf.ln(4)
    pdf.image(fname, w=180)
    print(f"Added: {fname}")

pdf.output("Eco-Loop_Submission.pdf")
print("\nSaved: Eco-Loop_Submission.pdf")