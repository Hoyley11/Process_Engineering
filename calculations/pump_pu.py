import math

def calculate(tag, process_data, manual_inputs):
    """
    Calculates Pump absorbed power and recommends heavy-duty motor sizing.
    """
    try:
        flow_m3h = float(process_data.get('flow_m3h', 0))
        tdh = float(manual_inputs.get('tdh_m', 25))
        density = float(process_data.get('density_tm3', 1.0))
        is_slurry = manual_inputs.get('is_slurry', True)
        
        # 1. Engineering Margin / Service Factor
        # Cyclone Feed / High Density slurry requires higher torque margin (25%+)
        # Standard solution pumps usually need 15-20%
        margin = 1.25 if density > 1.4 or is_slurry else 1.15
        
        # 2. Efficiency Selection
        # Slurry pumps (especially cyclone feed) have lower efficiency due to clearances
        if is_slurry:
            base_eff = 0.58 if density > 1.5 else 0.65
        else:
            base_eff = 0.75 # Cleaner solution pumps
            
        if manual_inputs.get('sub_type') in ['AODD', 'Hose', 'Dosing']:
            base_eff = 0.45

        # 3. Power Calculation
        # Power (kW) = (Q * H * Rho * g) / (3600 * Eff)
        absorbed_power = (flow_m3h * tdh * density * 9.81) / (3600 * base_eff)
        required_motor = absorbed_power * margin
        
        # 4. Expanded Standard Motor List (to 1000kW)
        standard_motors = [
            0.37, 0.55, 0.75, 1.1, 1.5, 2.2, 3.0, 4.0, 5.5, 7.5, 11, 15, 
            18.5, 22, 30, 37, 45, 55, 75, 90, 110, 132, 160, 200, 250,
            315, 355, 400, 450, 500, 560, 630, 710, 800, 900, 1000
        ]
        
        installed_motor = next((x for x in standard_motors if x >= required_motor), required_motor * 1.1)

        desc = f"{manual_inputs.get('pump_type')} {'Slurry' if is_slurry else 'Solution'} Pump. "
        desc += f"Flow: {flow_m3h:.1f} m³/h @ {tdh}m Head. Density: {density:.2f} t/m³. "
        desc += f"Absorbed: {absorbed_power:.1f} kW. Installed: {installed_motor} kW."

        return {
            "tag": tag,
            "status": "Sized",
            "installed_power_kw": installed_motor,
            "absorbed_power_kw": round(absorbed_power, 2),
            "description_3_line": desc,
            "mto": {
                "Motor Rating (kW)": installed_motor,
                "Estimated Pump Eff (%)": base_eff * 100
            },
            "critical_dimensions": {
                "Motor (kW)": installed_motor,
                "Design Margin (%)": round((margin - 1) * 100, 0)
            }
        }
    except Exception as e:
        return {"tag": tag, "status": f"Error: {str(e)}"}
