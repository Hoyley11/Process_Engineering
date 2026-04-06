# utils/data_manager.py
import pandas as pd
import json
from pathlib import Path
import os

# Define paths relative to the root directory
DATA_DIR = Path("data")
STATES_DIR = DATA_DIR / "states"
MASTER_LIST_PATH = DATA_DIR / "equipment_list.csv"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
STATES_DIR.mkdir(exist_ok=True)

def initialize_master_list():
    """Creates a blank master CSV if it doesn't exist."""
    if not MASTER_LIST_PATH.exists():
        df = pd.DataFrame(columns=[
            "Tag", "Type", "Status", "Description", 
            "Installed Power (kW)", "Absorbed Power (kW)", "Last Updated"
        ])
        df.to_csv(MASTER_LIST_PATH, index=False)

def save_equipment_sizing(equipment_tag, sizing_results):
    """
    Saves the detailed JSON state and updates the master CSV list.
    sizing_results: The standardized dictionary returned by your calculation modules.
    """
    initialize_master_list()
    
    # 1. Save detailed nested data as JSON
    json_path = STATES_DIR / f"{equipment_tag}.json"
    with open(json_path, "w") as f:
        json.dump(sizing_results, f, indent=4)
        
    # 2. Update Master CSV List
    df = pd.read_csv(MASTER_LIST_PATH)
    
    # Extract high-level data for the tracker
    new_entry = {
        "Tag": equipment_tag,
        "Type": equipment_tag.split('-')[1] if '-' in equipment_tag else "Unknown",
        "Status": sizing_results.get("status", "Draft"),
        "Description": sizing_results.get("description_3_line", "").replace('\n', ' | '), # Flatten for CSV
        "Installed Power (kW)": sizing_results.get("installed_power_kw", 0.0),
        "Absorbed Power (kW)": sizing_results.get("absorbed_power_kw", 0.0),
        "Last Updated": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
    }
    
    # Check if equipment already exists in the list to update, else append
    if equipment_tag in df['Tag'].values:
        # Update existing row
        idx = df[df['Tag'] == equipment_tag].index[0]
        for key, value in new_entry.items():
            df.at[idx, key] = value
    else:
        # Add new row using pd.concat (append is deprecated)
        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        
    df.to_csv(MASTER_LIST_PATH, index=False)
    
def load_equipment_state(equipment_tag):
    """Loads a previously saved JSON state for review."""
    json_path = STATES_DIR / f"{equipment_tag}.json"
    if json_path.exists():
        with open(json_path, "r") as f:
            return json.load(f)
    return None

def get_master_list():
    """Returns the master list as a pandas DataFrame."""
    initialize_master_list()
    return pd.read_csv(MASTER_LIST_PATH)
