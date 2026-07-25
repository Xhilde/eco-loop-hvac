import sys

EPLUS_ROOT = r"C:\EnergyPlusV26-1-0"
sys.path.insert(0, EPLUS_ROOT)

from pyenergyplus.api import EnergyPlusAPI
from tools import ToolServer

api = EnergyPlusAPI()
state = api.state_manager.new_state()
tools = ToolServer()

handles = {"temp": -1, "pmv": -1, "outdoor": -1, "heat_act": -1, "cool_act": -1}
call_count = [0]

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

    # READ: update the ToolServer's live values from the simulation
    tools.zone_temp = ex.get_variable_value(state, handles["temp"])
    tools.zone_pmv = ex.get_variable_value(state, handles["pmv"])
    tools.outdoor_temp = ex.get_variable_value(state, handles["outdoor"])
    tools.sim_time = f"{ex.month(state):02d}/{ex.day_of_month(state):02d} {ex.hour(state):02d}:00"

    # DECIDE: simple test rule instead of an LLM for now -
    # if it's hot outside, set a higher (energy-saving) cooling setpoint
    if tools.outdoor_temp is not None and tools.outdoor_temp > 28:
        result = tools.set_hvac_setpoints(heating_c=21.0, cooling_c=26.0)
    else:
        result = tools.set_hvac_setpoints(heating_c=21.0, cooling_c=24.0)

    # WRITE: apply the ToolServer's setpoints to the actuators every timestep
    ex.set_actuator_value(state, handles["heat_act"], tools.heating_setpoint)
    ex.set_actuator_value(state, handles["cool_act"], tools.cooling_setpoint)

    call_count[0] += 1
    if call_count[0] % 4 != 0:
        return

    zc = tools.get_zone_conditions()
    sc = tools.get_site_conditions()
    print(f"[{sc['sim_time']}] outdoor={sc['outdoor_temperature_c']}C  "
          f"zone_temp={zc['zone_temperature_c']}C  pmv={zc['zone_pmv']}  "
          f"-> setpoints=({tools.heating_setpoint}, {tools.cooling_setpoint})  {result}")

api.runtime.callback_begin_zone_timestep_after_init_heat_balance(state, my_callback)

args = [
    "-w", r"weather\chicago.epw",
    "-d", r"results_tool_test",
    "-r", r"idf\baseline.idf",
]

api.runtime.run_energyplus(state, args)