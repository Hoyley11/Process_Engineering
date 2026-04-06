# calculations/hopper_hp.py

def calculate(equipment_tag, stream_data, manual_inputs):
    """
    Inputs:
    - stream_data: dict containing mapped SysCAD data (e.g., {'feed_flow_m3h': 200.3})
    - manual_inputs: dict containing user overrides (e.g., {'residence_time': 45})
    """
    
    # --- 1. Math & Sizing Logic ---
    vol_required = stream_data['feed_flow_m3h'] * (manual_inputs['residence_time'] / 60)
    
    # Calculate MTO (simplified example)
    steel_density = 7850 # kg/m3
    carbon_steel_mass = vol_required * 1.5 * steel_density * 0.01 # Placeholder math
    
    # Generate 3-line description
    desc = f"Hopper designed for {stream_data['feed_flow_m3h']:.1f} m3/h.\n"
    desc += f"Live Volume: {vol_required:.1f} m3.\n"
    desc += f"MOC: Carbon Steel with Rubber Lining."

    # --- 2. Standardized Output ---
    return {
        "tag": equipment_tag,
        "status": "Sized",
        "installed_power_kw": 0.0, # Hoppers have 0 power
        "absorbed_power_kw": 0.0,
        "description_3_line": desc,
        "mto": {
            "Carbon Steel (kg)": carbon_steel_mass,
            "Rubber Lining (m2)": 27.35 # Example
        },
        "critical_dimensions": {
            "Total Height (mm)": 3450,
            "Diameter (mm)": 2300
        }
    }
