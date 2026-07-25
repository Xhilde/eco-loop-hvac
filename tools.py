class ToolServer:
    """
    Wraps read/write access to the EnergyPlus simulation as named 'tools',
    the same way an LLM would call them. The EnergyPlus callback calls
    these methods instead of touching actuators directly.
    """

    def __init__(self):
        # live sensor values, updated by the EnergyPlus callback each timestep
        self.zone_temp = None
        self.zone_pmv = None
        self.outdoor_temp = None
        self.sim_time = None

        # control values, read by the EnergyPlus callback each timestep
        self.heating_setpoint = 21.0
        self.cooling_setpoint = 24.0

    def get_zone_conditions(self):
        return {
            "zone_temperature_c": round(self.zone_temp, 2) if self.zone_temp is not None else None,
            "zone_pmv": round(self.zone_pmv, 2) if self.zone_pmv is not None else None,
        }

    def get_site_conditions(self):
        return {
            "outdoor_temperature_c": round(self.outdoor_temp, 2) if self.outdoor_temp is not None else None,
            "sim_time": self.sim_time,
        }

    def set_hvac_setpoints(self, heating_c, cooling_c):
        DEADBAND_MIN = 1.1
        if cooling_c < heating_c + DEADBAND_MIN:
            return {
                "accepted": False,
                "error": f"cooling_c ({cooling_c}) must be >= heating_c ({heating_c}) + {DEADBAND_MIN}",
            }
        self.heating_setpoint = heating_c
        self.cooling_setpoint = cooling_c
        return {"accepted": True, "heating_c": heating_c, "cooling_c": cooling_c}