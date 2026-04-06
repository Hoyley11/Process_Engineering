# snippet to add to the bottom of your Sizing Engine page
        
        # ... (after hopper_hp.calculate is run and results are displayed) ...
        
        # Add a save mechanism
        if st.button("Save & Commit Sizing to Database"):
            from utils import data_manager
            
            # Save to CSV and JSON
            data_manager.save_equipment_sizing(equip_tag, results)
            st.success(f"Successfully committed {equip_tag} to the project data!")
