import math

def calculate(tag, process_data, manual_inputs):
    """
    Calculates Pump absorbed power and recommends motor sizing.
    """
    try:
        # Inputs from Mass Balance / Grid
        flow_m3h = float(process_data.get('flow_m3h', 0))
        tdh = float(manual_inputs.get('tdh_m', 25)) # Total Dynamic Head
        density = float(process_data.get('density_tm3', 1.0))
        
        # Equipment Type Flags
        is_slurry = manual_inputs.get('is_slurry', True)
        pump_type = manual_inputs.get('pump_type', 'Horizontal')
        
        # 1. Estimate Efficiency (Simplified Rule of Thumb)
        # Slurry pumps are less efficient than water/solution pumps
        base_eff = 0.70 if not is_slurry else 0.60
        if manual_inputs.get('sub_type') in ['Dosing', 'AODD', 'Hose']:
            base_eff = 0.45 # Lower efficiency for positive displacement/diaphragm
            
        # 2. Calculate Absorbed Power (BkP)
        # Power (kW) = (Flow(m3/h) * TDH(m) * Density * g) / (3600 * Efficiency)
        absorbed_power = (flow_m3h * tdh * density * 9.81) / (3600 * base_eff)
        
        # 3. Recommended Motor Sizing (Standard IEC Sizes)
        # Rule of thumb: 15-20% margin or next standard size
        required_motor = absorbed_power * 1.20
        
        standard_motors = [0.37, 0.55, 0.75, 1.1, 1.5, 2.2, 3.0, 4.0, 5.5, 7.5, 11, 15, 
                           18.5, 22, 30, 37, 45, 55, 75, 90, 110, 132, 160, 200, 250]
        
        installed_motor = next((x for x in standard_motors if x >= required_motor), standard_motors[-1])

        return {
            "tag": tag,
            "status": "Success",
            "results": {
                "Absorbed Power (kW)": round(absorbed_power, 2),
                "Recommended Motor (kW)": installed_motor,
                "Estimated Efficiency (%)": base_eff * 100
            },
            "mto": {
                "Motor Size (kW)": installed_motor,
                "Pump Category": f"{'Slurry' if is_slurry else 'Solution'} - {pump_type}"
            }
        }
    except Exception as e:
        return {"tag": tag, "status": f"Error: {str(e)}"}
