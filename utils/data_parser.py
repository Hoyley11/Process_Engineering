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
        
        # 1. Find the row that contains "Stream Number" (Usually in Column A / index 0)
        stream_row_matches = df_raw.index[df_raw[0] == 'Stream Number'].tolist()
        if not stream_row_matches:
            st.error("Could not find 'Stream Number' in the first column. Check file format.")
            return None
        stream_row_idx = stream_row_matches[0]
        
        # 2. Extract Stream Numbers
        # Start from Column D (index 3) to the end. Drop NaNs to find actual streams.
        stream_numbers_raw = df_raw.iloc[stream_row_idx, 3:].dropna()
        stream_numbers = stream_numbers_raw.astype(str).tolist()
        num_streams = len(stream_numbers)
        
        # --- FIXED: 3. Find the GenDesc (Stream Names) Row ---
        # SysCAD puts 'GenDesc' in Column C (index 2), but we search the first 3 cols to be safe.
        name_row_idx = None
        for col in range(3):
            matches = df_raw.index[df_raw[col] == 'GenDesc'].tolist()
            if matches:
                name_row_idx = matches[0]
                break
                
        # If we found the row, combine the Number and the Name
        if name_row_idx is not None:
            stream_names = df_raw.iloc[name_row_idx, 3:3+num_streams].fillna("").astype(str).tolist()
            combined_headers = []
            for num, name in zip(stream_numbers, stream_names):
                clean_name = name.strip()
                if clean_name and clean_name != 'nan':
                    combined_headers.append(f"{num} | {clean_name}")
                else:
                    combined_headers.append(num)
        else:
            # Fallback if the SysCAD file didn't include names
            combined_headers = stream_numbers

        # 4. Create clean column names (Properties)
        # Numeric data starts exactly 3 rows below the Stream Number row
        data_start_row = stream_row_idx + 3 
        
        clean_properties = []
        for idx in range(data_start_row, len(df_raw)):
            desc = str(df_raw.iloc[idx, 0]) if pd.notna(df_raw.iloc[idx, 0]) else ""
            unit = str(df_raw.iloc[idx, 1]) if pd.notna(df_raw.iloc[idx, 1]) else ""
            
            if desc and unit and unit != 'nan':
                clean_properties.append(f"{desc.strip()} ({unit.strip()})")
            elif desc and desc != 'nan':
                clean_properties.append(desc.strip())
            else:
                clean_properties.append(f"Unknown_Property_{idx}")
                
        # 5. Extract the actual numeric data matrix
        df_data = df_raw.iloc[data_start_row:, 3:3+num_streams]
        
        # 6. Build the intermediate DataFrame using our new combined headers!
        df_tidy = pd.DataFrame(df_data.values, index=clean_properties, columns=combined_headers)
        
        # 7. TRANSPOSE! (Flip 90 degrees)
        df_final = df_tidy.T
        
        # 8. Convert text numbers into actual math numbers
        for col in df_final.columns:
            df_final[col] = pd.to_numeric(df_final[col], errors='coerce')
            
        # Fill blanks with 0 so math doesn't crash
        df_final = df_final.fillna(0)
        
        # Clean up the index name for clarity
        df_final.index.name = "Stream_Number"
        
        return df_final
        
    except Exception as e:
        st.error(f"Error parsing SysCAD file: {str(e)}")
        return None
