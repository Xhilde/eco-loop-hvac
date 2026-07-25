import json
import urllib.request

def ask_llm_for_setpoints(outdoor_temp, zone_temp, zone_pmv, model="llama3.2"):
    """
    Sends current conditions to a local Ollama model and asks it to decide
    heating/cooling setpoints. Returns (heating_c, cooling_c) as floats,
    or None if anything goes wrong (caller should fall back to a safe default).
    """
    prompt = (
        f"You control a building's HVAC. Current conditions: "
        f"outdoor temperature = {outdoor_temp:.1f}C, zone temperature = {zone_temp:.1f}C, "
        f"zone comfort PMV = {zone_pmv:.2f} (target range: -0.5 to 0.5). "
        f"Reply with ONLY two numbers separated by a comma: heating_setpoint,cooling_setpoint "
        f"in Celsius. heating must be between 15 and 22. cooling must be between 22 and 28. "
        f"cooling must be at least 1.1 higher than heating. Example reply: 21.0,24.0"
    )

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }

    try:
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        text = data["response"].strip()
        heat_str, cool_str = text.split(",")
        return float(heat_str.strip()), float(cool_str.strip())
    except Exception as e:
        print(f"LLM call failed: {e}")
        return None


if __name__ == "__main__":
    result = ask_llm_for_setpoints(outdoor_temp=30.0, zone_temp=25.0, zone_pmv=0.1, model="llama3.2")
    print("LLM returned:", result)