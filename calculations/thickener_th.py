import math

def calculate(tag, process_data, manual_inputs):
    try:
        # Inputs
        solids_tph = float(process_data.get('solids_tph', 0))
        overflow_m3h = float(process_data.get('overflow_m3h', 0))
        
        design_flux = float(manual_inputs.get('design_flux', 0.5))
        settling_rate = float(manual_inputs.get('settling_rate', 3.0))
        round_up_to = float(manual_inputs.get('round_up_to', 5.0))
        
        # 1. Calculate Area Requirement
        area_flux = solids_tph / design_flux
        area_settling = overflow_m3h / settling_rate
        
        governing_area = max(area_flux, area_settling)
        raw_diameter = math.sqrt((4 * governing_area) / math.pi)
        
        # 2. Round Up Logic
        final_diameter = math.ceil(raw_diameter / round_up_to) * round_up_to
        
        # 3. Structural Selection (On-ground vs Freestanding)
        # Rule of thumb: > 25m are typically on-ground with concrete tunnels
        structure = "On-Ground (Concrete)" if final_diameter > 25 else "Freestanding (Steel legs)"
        
        # 4. Rake Drive Estimate (Hydraulic/Electric Torque)
        # Torque (kNm) = K * D^2 (Simplified Metso/Outotec heuristic)
        torque_kNm = 0.5 * (final_diameter ** 2) 
        drive_power_kw = (torque_kNm * 0.1) / 0.9 # Very low RPM, high torque
        
        return {
            "tag": tag,
            "status": "Sized",
            "installed_power_kw": round(drive_power_kw, 1),
            "description_3_line": f"{final_diameter}m {structure} Thickener. Sized for {solids_tph}tph @ {design_flux} t/m2.h flux.",
            "critical_dimensions": {
                "Diameter (m)": final_diameter,
                "Structure": structure,
                "Governing Criteria": "Flux" if area_flux > area_settling else "Settling"
            },
            "mto": {"Torque (kNm)": round(torque_kNm, 1)}
        }
    except Exception as e:
        return {"status": f"Error: {str(e)}"}
