import math
import pandas as pd

# --- 1. STANDARD HOPPER DATABASE ---
# In a massive app, you might put this in a separate CSV, 
# but for now, it's perfect to keep it self-contained in the module.
STANDARD_HOPPERS = pd.DataFrame({
    'Nominal Live Vol (m3)': [1.25, 2.0, 2.9, 3.9, 5.0, 6.9, 8.6, 10.9, 13.8, 16.8, 20.0, 23.3, 35.0, 42.5, 51.0],
    'Diameter (mm)': [1300, 1500, 1700, 1900, 2100, 2300, 2500, 2700, 2900, 3100, 3250, 3400, 3850, 4000, 4350],
    'Dia Base (mm)': [433, 500, 567, 633, 700, 767, 833, 900, 967, 1033, 1083, 1133, 1283, 1333, 1450],
    'Cone Height (mm)': [751, 866, 981, 1097, 1212, 1328, 1443, 1559, 1674, 1790, 1876, 1963, 2223, 2309, 2511],
    'Cyl Height (mm)': [1199, 1384, 1569, 1753, 1938, 2122, 2307, 2491, 2676, 2860, 2999, 3137, 3552, 3691, 4014],
    'Total Height (mm)': [1950, 2250, 2550, 2850, 3150, 3450, 3750, 4050, 4350, 4650, 4875, 5100, 5775, 6000, 6525]
})

def calculate(equipment_tag, stream_data, manual_inputs):
    """
    The standardized execution function for Pump Hoppers.
    """
    # --- 2. EXTRACT INPUTS ---
    # Failsafes built-in using .get() to prevent crashes if a variable is missing
    flow_m3h = float(stream_data.get('max_flow_m3h', 0.0)) 
    res_time_min = float(manual_inputs.get('residence_time_min', 1.0))
    fvf = float(manual_inputs.get('fvf', 1.5))
    shape = manual_inputs.get('shape', 'Round')
    steel_thickness_mm = float(manual_inputs.get('steel_thickness_mm', 10.0))
    rubber_lined = manual_inputs.get('rubber_lined', True)

    # --- 3. VOLUME CALCULATIONS ---
    base_vol = flow_m3h * (res_time_min / 60.0)
    req_live_vol = base_vol * fvf

    # Adjust required lookup volume if hopper is square
    shape_factor = 1.0 if shape == "Round" else (math.pi / 4.0)
    lookup_vol = req_live_vol * shape_factor

    # Find the first standard hopper that is large enough
    valid_hoppers = STANDARD_HOPPERS[STANDARD_HOPPERS['Nominal Live Vol (m3)'] >= lookup_vol]
    
    if valid_hoppers.empty:
        return {"status": "Error: Flow exceeds standard sizes."}
    
    selected = valid_hoppers.iloc[0]

    # --- 4. MATERIAL TAKE-OFF (MTO) MATH ---
    # Convert mm to m for area calculations
    D = selected['Diameter (mm)'] / 1000.0
    Db = selected['Dia Base (mm)'] / 1000.0
    Hcyl = selected['Cyl Height (mm)'] / 1000.0
    Hcone = selected['Cone Height (mm)'] / 1000.0

    # Surface Area Calculations (Geometry)
    if shape == "Round":
        # Cylinder surface area = pi * D * H
        cyl_area = math.pi * D * Hcyl
        # Truncated cone surface area = pi * (R1 + R2) * slant_height
        R1, R2 = D/2, Db/2
        slant_h = math.sqrt((R1 - R2)**2 + Hcone**2)
        cone_area = math.pi * (R1 + R2) * slant_h
        baseplate_area = D * D # Assuming square baseplate footprint
    else:
        # Square hopper uses width = D
        cyl_area = 4 * D * Hcyl
        slant_h = math.sqrt(((D - Db)/2)**2 + Hcone**2)
        cone_area = 4 * ((D + Db)/2) * slant_h
        baseplate_area = D * D

    total_surface_area = cyl_area + cone_area
    
    # Mass calculations
    steel_density = 7850 # kg/m3
    fudge_factor = 1.075 # 7.5% contingency from your excel sheet
    
    steel_vol = total_surface_area * (steel_thickness_mm / 1000.0)
    baseplate_vol = baseplate_area * (steel_thickness_mm / 1000.0)
    
    carbon_steel_kg = (steel_vol + baseplate_vol) * steel_density * fudge_factor
    rubber_lining_m2 = total_surface_area * fudge_factor if rubber_lined else 0.0

    # --- 5. 3-LINE DESCRIPTION ---
    desc = f"{shape} pump hopper designed for max flow of {flow_m3h:.1f} m3/h at {res_time_min} min residence time.\n"
    desc += f"Calculated live volume: {req_live_vol:.1f} m3. Provided standard capacity: {(selected['Nominal Live Vol (m3)'] / shape_factor):.1f} m3.\n"
    desc += f"Construction: {steel_thickness_mm}mm Carbon Steel" + (" with Rubber Lining." if rubber_lined else ".")

    # --- 6. STANDARDIZED RETURN DICTIONARY ---
    # This format is critical so your master Equipment List reads it perfectly
    return {
        "tag": equipment_tag,
        "status": "Sized",
        "installed_power_kw": 0.0, 
        "absorbed_power_kw": 0.0,
        "description_3_line": desc,
        "mto": {
            "Carbon Steel (kg)": round(carbon_steel_kg, 1),
            "Rubber Lining (m2)": round(rubber_lining_m2, 1)
        },
        "critical_dimensions": {
            "Diameter/Width (mm)": int(selected['Diameter (mm)']),
            "Total Height (mm)": int(selected['Total Height (mm)'])
        }
    }
