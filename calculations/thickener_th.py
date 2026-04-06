import math

def calculate(tag, process_data, manual_inputs):
    """
    Calculates Thickener diameter based on Flux and Rise Rate.
    """
    try:
        # 1. Extract and sanitize inputs
        solids_tph = float(process_data.get('solids_tph', 0))
        overflow_m3h = float(process_data.get('overflow_m3h', 0))
        
        flux = float(manual_inputs.get('design_flux', 0.4))
        rise_rate = float(manual_inputs.get('settling_rate', 3.0))
        step = float(manual_inputs.get('round_up_to', 2.5))
        
        # 2. Area Calculations
        # Area required for solids handling (Flux)
        area_solids = solids_tph / flux if flux > 0 else 0
        
        # Area required for liquid clarity (Rise Rate)
        area_clarity = overflow_m3h / rise_rate if rise_rate > 0 else 0
        
        # 3. Diameter Calculation (Governing Area)
        req_area = max(area_solids, area_clarity)
        
        if req_area <= 0:
            return {"status": "Error: Required area is zero. Check input flows."}
            
        calc_dia = math.sqrt((4 * req_area) / math.pi)
        
        # 4. Rounding Logic
        final_dia = math.ceil(calc_dia / step) * step
        
        # 5. Structural Determination
        is_on_ground = final_dia >= 25.0
        struct_text = "On-Ground (Concrete Tunnel)" if is_on_ground else "Freestanding (Steel Legs)"
        
        # 6. Rake Drive Torque Heuristic (Standard Duty)
        # Torque (Nm) = K * D^2
        torque_nm = 1200 * (final_dia ** 2)
        
        # --- THE FIX: ENSURING THESE KEYS EXIST ---
        return {
            "tag": tag,
            "status": "Sized",
            "description_3_line": f"{final_dia}m {struct_text} Thickener. Sized for {solids_tph}tph solids.",
            "critical_dimensions": {
                "Diameter (m)": final_dia,
                "Structure": struct_text,
                "Governing Criteria": "Solids Flux" if area_solids > area_clarity else "Rise Rate",
                "Required Area (m2)": round(req_area, 1)
            },
            "mto": {
                "Design Torque (Nm)": int(torque_nm),
                "Drive Type": "Hydraulic" if is_on_ground else "Electric Multi-Drive"
            },
            "installed_power_kw": 15.0 if final_dia < 30 else 30.0 # Placeholder for drive power
        }
        
    except Exception as e:
        return {"status": f"Error in calculation: {str(e)}"}
