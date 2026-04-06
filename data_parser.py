# utils/data_parser.py
import pandas as pd
import streamlit as st

def parse_syscad_mass_balance(uploaded_file):
    """
    Parses a standard SysCAD mass balance export.
    Converts wide format (streams as columns) to long/tidy format (streams as rows).
    """
    try:
        # Read the raw excel file without headers to inspect the structure
        df_raw = pd.read_excel(uploaded_file, header=None)
        
        # 1. Find the row that contains "Stream Number"
        # Usually it's the first row (index 0), but this makes it robust
        stream_row_idx = df_raw[df_raw[0] == 'Stream Number'].index[0]
        
        # 2. Extract Stream Numbers (Column D onwards, typically index 3+)
        # We drop NaN values in case there are empty columns at the end
        stream_numbers = df_raw.iloc[stream_row_idx, 3:].dropna().astype(str).tolist()
        
        # 3. Create clean column names by combining Description (Col A) and Units (Col B)
        # E.g., "Solids" + "t/h" -> "Solids (t/h)"
        property_descriptions = df_raw[0].fillna('')
        property_units = df_raw[1].fillna('')
        
        clean_properties = []
        for desc, unit in zip(property_descriptions, property_units):
            if desc and unit:
                clean_properties.append(f"{desc.strip()} ({unit.strip()})")
            elif desc:
                clean_properties.append(desc.strip())
            else:
                clean_properties.append("Unknown Property")
                
        # 4. Extract the actual data matrix
        # Rows = from below the header rows to the end
        # Columns = from column D (index 3) to the end
        data_start_row = stream_row_idx + 3 # Skipping Graphic and GenDesc rows
        
        # Slice the dataframe to just the numeric data
        df_data = df_raw.iloc[data_start_row:, 3:3+len(stream_numbers)]
        
        # 5. Build the final Tidy DataFrame
        df_tidy = df_data.copy()
        # Set the columns to be our stream numbers
        df_tidy.columns = stream_numbers
        # Set the index to be our cleaned property names
        df_tidy.index = clean_properties[data_start_row:]
        
        # 6. TRANSPOSE! 
        # Now: Rows = Streams, Columns = Properties
        df_final = df_tidy.T
        
        # Clean up the index name for clarity
        df_final.index.name = "Stream_Number"
        
        return df_final
        
    except Exception as e:
        st.error(f"Error parsing SysCAD file: {str(e)}")
        return None
