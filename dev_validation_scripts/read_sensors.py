import sys

EPLUS_ROOT = r"C:\EnergyPlusV26-1-0"
sys.path.insert(0, EPLUS_ROOT)

from pyenergyplus.api import EnergyPlusAPI

api = EnergyPlusAPI()
state = api.state_manager.new_state()

# handles get filled in once EnergyPlus is ready; -1 means "not yet"
handles = {"temp": -1, "pmv": -1}
call_count = [0]

def my_callback(state):
    ex = api.exchange

    # skip warmup/sizing days entirely
    if ex.warmup_flag(state):
        return

    # get variable handles once, the first real timestep
    if handles["temp"] == -1:
        handles["temp"] = ex.get_variable_handle(state, "Zone Mean Air Temperature", "Core_bottom")
        handles["pmv"] = ex.get_variable_handle(state, "Zone Thermal Comfort Fanger Model PMV", "Core_bottom People")
        if handles["temp"] == -1 or handles["pmv"] == -1:
            print("ERROR: could not resolve one or more variable handles")
            return

    call_count[0] += 1
    # only print once per hour (every 4th timestep at 15-min resolution)
    if call_count[0] % 4 != 0:
        return

    temp = ex.get_variable_value(state, handles["temp"])
    pmv = ex.get_variable_value(state, handles["pmv"])
    sim_time = f"{ex.month(state):02d}/{ex.day_of_month(state):02d} {ex.hour(state):02d}:00"

    print(f"[{sim_time}] Core_bottom temp={temp:.2f}C  PMV={pmv:.2f}")

api.runtime.callback_begin_zone_timestep_after_init_heat_balance(state, my_callback)

args = [
    "-w", r"weather\chicago.epw",
    "-d", r"results",
    "-r", r"idf\baseline.idf",
]

api.runtime.run_energyplus(state, args)