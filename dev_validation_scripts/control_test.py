import sys

EPLUS_ROOT = r"C:\EnergyPlusV26-1-0"
sys.path.insert(0, EPLUS_ROOT)

from pyenergyplus.api import EnergyPlusAPI

api = EnergyPlusAPI()
state = api.state_manager.new_state()

handles = {"temp": -1, "heat_act": -1, "cool_act": -1}
call_count = [0]

# TEST OVERRIDE: force cooling setpoint way up to prove the actuator works.
# If this is wired correctly, Core_bottom's temperature should now sit near
# 27C instead of the 24C we saw in the baseline read-only run.
TEST_COOLING_SETPOINT = 27.0

def my_callback(state):
    ex = api.exchange

    if ex.warmup_flag(state):
        return

    if handles["temp"] == -1:
        handles["temp"] = ex.get_variable_handle(state, "Zone Mean Air Temperature", "Core_bottom")
        handles["heat_act"] = ex.get_actuator_handle(state, "Schedule:Compact", "Schedule Value", "HTGSETP_SCH")
        handles["cool_act"] = ex.get_actuator_handle(state, "Schedule:Compact", "Schedule Value", "CLGSETP_SCH")
        if -1 in (handles["temp"], handles["heat_act"], handles["cool_act"]):
            print("ERROR: could not resolve one or more handles")
            return

    # override the cooling setpoint EVERY timestep, so it holds instead of
    # snapping back to the original schedule
    ex.set_actuator_value(state, handles["cool_act"], TEST_COOLING_SETPOINT)

    call_count[0] += 1
    if call_count[0] % 4 != 0:
        return

    temp = ex.get_variable_value(state, handles["temp"])
    sim_time = f"{ex.month(state):02d}/{ex.day_of_month(state):02d} {ex.hour(state):02d}:00"
    print(f"[{sim_time}] Core_bottom temp={temp:.2f}C  (forced cooling setpoint={TEST_COOLING_SETPOINT}C)")

api.runtime.callback_begin_zone_timestep_after_init_heat_balance(state, my_callback)

args = [
    "-w", r"weather\chicago.epw",
    "-d", r"results_control_test",
    "-r", r"idf\baseline.idf",
]

api.runtime.run_energyplus(state, args)