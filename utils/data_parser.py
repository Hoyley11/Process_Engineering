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
        
        # 1. Find the row that contains "Stream Number" (Usually index 0)
        stream_row_matches = df_raw.index[df_raw[0] == 'Stream Number'].tolist()
        if not stream_row_matches:
            st.error("Could not find 'Stream Number' in the first column. Check file format.")
            return None
        stream_row_idx = stream_row_matches[0]
        
        # 2. Extract Stream Numbers (Starts from Column D / index 3)
        # We drop NaN values in case there are empty columns at the far right
        stream_numbers = df_raw.iloc[stream_row_idx, 3:].dropna().astype(str).tolist()
        num_streams = len(stream_numbers)
        
        # 3. Create clean column names by combining Description (Col A) and Units (Col B)
        # Based on standard SysCAD format, actual numeric data starts 3 rows below 'Stream Number'
        data_start_row = stream_row_idx + 3 
        
        clean_properties = []
        for idx in range(data_start_row, len(df_raw)):
            desc = str(df_raw.iloc[idx, 0]) if pd.notna(df_raw.iloc[idx, 0]) else ""
            unit = str(df_raw.iloc[idx, 1]) if pd.notna(df_raw.iloc[idx, 1]) else ""
            
            if desc and unit:
                clean_properties.append(f"{desc.strip()} ({unit.strip()})")
            elif desc:
                clean_properties.append(desc.strip())
            else:
                clean_properties.append(f"Unknown_Property_{idx}")
                
        # 4. Extract the actual numeric data matrix
        # Slice rows from data start to end, and columns from index 3 to the end of the streams
        df_data = df_raw.iloc[data_start_row:, 3:3+num_streams]
        
        # 5. Build the intermediate DataFrame
        df_tidy = pd.DataFrame(df_data.values, index=clean_properties, columns=stream_numbers)
        
        # 6. TRANSPOSE! (Flip 90 degrees)
        # Now: Rows = Streams, Columns = Properties
        df_final = df_tidy.T
        
        # 7. Convert text numbers into actual math numbers (floats) where possible
        df_final = df_final.apply(pd.to_numeric, errors='ignore')
        
        # Clean up the index name for clarity
        df_final.index.name = "Stream_Number"
        
        return df_final
        
    except Exception as e:
        st.error(f"Error parsing SysCAD file: {str(e)}")
        return None
