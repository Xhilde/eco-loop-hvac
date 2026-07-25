import sys

EPLUS_ROOT = r"C:\EnergyPlusV26-1-0"
sys.path.insert(0, EPLUS_ROOT)

from pyenergyplus.api import EnergyPlusAPI
from tools import ToolServer
from llm_decide import ask_llm_for_setpoints

api = EnergyPlusAPI()
state = api.state_manager.new_state()
tools = ToolServer()

handles = {"temp": -1, "pmv": -1, "outdoor": -1, "heat_act": -1, "cool_act": -1}
call_count = [0]

# throttle LLM calls: only ask the LLM once every N zone timesteps, since
# each call takes real wall-clock seconds and we don't want to slow the
# simulation to a crawl or hammer Ollama. At 15-min timesteps, N=4 means
# "ask once per simulated hour" - and we HOLD the last decision in between.
LLM_CALL_EVERY_N_STEPS = 4

def my_callback(state):
    ex = api.exchange

    if ex.warmup_flag(state):
        return

    if handles["temp"] == -1:
        handles["temp"] = ex.get_variable_handle(state, "Zone Mean Air Temperature", "Core_bottom")
        handles["pmv"] = ex.get_variable_handle(state, "Zone Thermal Comfort Fanger Model PMV", "Core_bottom People")
        handles["outdoor"] = ex.get_variable_handle(state, "Site Outdoor Air Drybulb Temperature", "Environment")
        handles["heat_act"] = ex.get_actuator_handle(state, "Schedule:Compact", "Schedule Value", "HTGSETP_SCH")
        handles["cool_act"] = ex.get_actuator_handle(state, "Schedule:Compact", "Schedule Value", "CLGSETP_SCH")
        if -1 in handles.values():
            print("ERROR: could not resolve one or more handles")
            return

    # READ
    tools.zone_temp = ex.get_variable_value(state, handles["temp"])
    tools.zone_pmv = ex.get_variable_value(state, handles["pmv"])
    tools.outdoor_temp = ex.get_variable_value(state, handles["outdoor"])
    tools.sim_time = f"{ex.month(state):02d}/{ex.day_of_month(state):02d} {ex.hour(state):02d}:00"

    call_count[0] += 1

    # DECIDE (only every N steps - LLM decision is HELD between calls)
    if call_count[0] % LLM_CALL_EVERY_N_STEPS == 0:
        result = ask_llm_for_setpoints(
            outdoor_temp=tools.outdoor_temp,
            zone_temp=tools.zone_temp,
            zone_pmv=tools.zone_pmv,
        )
        if result is not None:
            heat_c, cool_c = result
            tool_result = tools.set_hvac_setpoints(heating_c=heat_c, cooling_c=cool_c)
            if not tool_result["accepted"]:
                print(f"  [LLM proposal REJECTED by validator: {tool_result['error']}] -> holding previous setpoints")
        else:
            print("  [LLM call failed -> holding previous setpoints]")

    # WRITE (every timestep, holding the last accepted decision)
    ex.set_actuator_value(state, handles["heat_act"], tools.heating_setpoint)
    ex.set_actuator_value(state, handles["cool_act"], tools.cooling_setpoint)

    if call_count[0] % LLM_CALL_EVERY_N_STEPS != 0:
        return

    zc = tools.get_zone_conditions()
    sc = tools.get_site_conditions()
    print(f"[{sc['sim_time']}] outdoor={sc['outdoor_temperature_c']}C  "
          f"zone_temp={zc['zone_temperature_c']}C  pmv={zc['zone_pmv']}  "
          f"-> LLM setpoints=({tools.heating_setpoint}, {tools.cooling_setpoint})")

api.runtime.callback_begin_zone_timestep_after_init_heat_balance(state, my_callback)

args = [
    "-w", r"weather\chicago.epw",
    "-d", r"results_llm_control",
    "-r", r"idf\baseline.idf",
]

api.runtime.run_energyplus(state, args)