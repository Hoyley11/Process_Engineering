import pandas as pd
import streamlit as st

def parse_syscad_mass_balance(uploaded_file):
    """
    Parses a standard SysCAD mass balance export.
    Keeps Stream Number as the index and inserts Stream Name as a distinct column.
    """
    try:
        df_raw = pd.read_excel(uploaded_file, header=None)
        
        # 1. Find the row that contains "Stream Number"
        stream_row_matches = df_raw.index[df_raw[0] == 'Stream Number'].tolist()
        if not stream_row_matches:
            st.error("Could not find 'Stream Number' in the first column. Check file format.")
            return None
        stream_row_idx = stream_row_matches[0]
        
        # Extract Stream Numbers
        stream_numbers_raw = df_raw.iloc[stream_row_idx, 3:].dropna()
        stream_numbers = stream_numbers_raw.astype(str).tolist()
        num_streams = len(stream_numbers)
        
        # 2. Find the GenDesc (Stream Names) Row
        name_row_idx = None
        for col in range(3):
            matches = df_raw.index[df_raw[col] == 'GenDesc'].tolist()
            if matches:
                name_row_idx = matches[0]
                break
                
        # Extract names if found
        if name_row_idx is not None:
            stream_names = df_raw.iloc[name_row_idx, 3:3+num_streams].fillna("").astype(str).tolist()
            stream_names = [name.strip() for name in stream_names]
        else:
            stream_names = [""] * num_streams

        # 3. Create clean column names (Properties)
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
                
        # 4. Extract data and build intermediate DataFrame (Columns = Stream Numbers ONLY)
        df_data = df_raw.iloc[data_start_row:, 3:3+num_streams]
        df_tidy = pd.DataFrame(df_data.values, index=clean_properties, columns=stream_numbers)
        
        # 5. Transpose and convert to numeric
        df_final = df_tidy.T
        for col in df_final.columns:
            df_final[col] = pd.to_numeric(df_final[col], errors='coerce')
            
        df_final = df_final.fillna(0)
        
        # 6. Insert Stream Name as a distinct column at the very front
        df_final.insert(0, 'Stream_Name', stream_names)
        df_final.index.name = "Stream_Number"
        
        return df_final
        
    except Exception as e:
        st.error(f"Error parsing SysCAD file: {str(e)}")
        return None
