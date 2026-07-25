import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

baseline_kwh = 16142.2
ai_kwh = 15198.7
baseline_viol_pct = 40.0
ai_viol_pct = 23.1

GRAY = "#9CA3AF"
BLUE = "#2563EB"
GREEN = "#16A34A"
TEXT_DARK = "#1F2937"

plt.rcParams["font.family"] = "sans-serif"

fig, axes = plt.subplots(1, 2, figsize=(11, 5.6))
fig.patch.set_facecolor("white")

def style_axis(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.yaxis.grid(True, color="#E5E7EB", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", length=0, labelsize=10, colors=TEXT_DARK)

def draw_bars(ax, values, labels, value_fmt, ylabel, title, delta_text):
    bars = ax.bar(labels, values, color=[GRAY, BLUE], width=0.55, zorder=3)

    # value labels directly above each bar
    for bar, v in zip(bars, values):
        ax.annotate(value_fmt(v), xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    xytext=(0, 6), textcoords="offset points", ha="center",
                    fontsize=12, fontweight="bold", color=TEXT_DARK)

    ax.set_ylabel(ylabel, fontsize=10.5, color=TEXT_DARK, labelpad=8)
    ax.set_title(title, fontsize=13, fontweight="bold", color=TEXT_DARK, pad=16)

    # give generous headroom above the tallest bar for the connector + label
    ymax = max(values) * 1.32
    ax.set_ylim(0, ymax)

    # connector line + delta label, drawn INSIDE the plot area (data coords),
    # so it can never collide with the title above the axes
    x0 = bars[0].get_x() + bars[0].get_width() / 2
    x1 = bars[1].get_x() + bars[1].get_width() / 2
    connector_y = max(values) * 1.12
    ax.plot([x0, x1], [connector_y, connector_y], color=GREEN, linewidth=1.4, zorder=4)
    ax.plot([x0, x0], [connector_y - ymax * 0.015, connector_y], color=GREEN, linewidth=1.4, zorder=4)
    ax.plot([x1, x1], [connector_y - ymax * 0.015, connector_y], color=GREEN, linewidth=1.4, zorder=4)
    ax.text((x0 + x1) / 2, connector_y + ymax * 0.025, delta_text,
             ha="center", va="bottom", fontsize=13, fontweight="bold", color=GREEN, zorder=5)

    style_axis(ax)

savings_pct = 100 * (baseline_kwh - ai_kwh) / baseline_kwh
viol_reduction = baseline_viol_pct - ai_viol_pct

draw_bars(
    axes[0], [baseline_kwh, ai_kwh],
    ["Baseline\n(fixed schedule)", "AI-Controlled\n(LLM)"],
    lambda v: f"{v:,.0f} kWh",
    "Total Electricity (kWh)", "Weekly Energy Consumption",
    f"\u2193 {savings_pct:.1f}%",
)

draw_bars(
    axes[1], [baseline_viol_pct, ai_viol_pct],
    ["Baseline\n(fixed schedule)", "AI-Controlled\n(LLM)"],
    lambda v: f"{v:.1f}%",
    "% of Timesteps with |PMV| > 0.5", "Thermal Comfort Violations",
    f"\u2193 {viol_reduction:.1f} pts",
)

fig.suptitle("Eco-Loop: Baseline vs. AI-Controlled HVAC",
             fontsize=15, fontweight="bold", color=TEXT_DARK, y=1.02)
fig.text(0.5, 0.955, "07/14 \u2013 07/20 \u00b7 Chicago Peak Summer Week \u00b7 DOE Medium Office",
          ha="center", fontsize=10.5, color="#6B7280")

plt.tight_layout(rect=[0, 0, 1, 0.93])
plt.savefig("results_comparison_chart.png", dpi=220, bbox_inches="tight", facecolor="white")
print("Saved: results_comparison_chart.png")