
import streamlit as st
import pandas as pd
import fnmatch

st.title("School Bus Order Compliance Checker")

# Upload inputs
order_file = st.file_uploader("Upload Order Spreadsheet", type=["xlsx", "xls"])
spec_file = st.file_uploader("Upload State Spec Spreadsheet", type=["xlsx", "xls"])

# Select state and vehicle type
selected_state = st.selectbox("Select State", options=["MN", "AL", "TX", "CA", "Other..."])
vehicle_type = st.selectbox("Select Vehicle Type", options=["MFSAB", "Type AI", "Type AII", "Type W/C"])

if order_file and spec_file and selected_state and vehicle_type:
    try:
        # Read in order sheet
        order_xls = pd.ExcelFile(order_file)
        order_df = order_xls.parse("Mapics")
        order_codes = order_df["Item Numbers"].dropna().astype(str).str.strip().tolist()

        # Read in state sheet
        spec_xls = pd.ExcelFile(spec_file)
        if selected_state not in spec_xls.sheet_names:
            st.error(f"State tab '{selected_state}' not found.")
        else:
            state_df = spec_xls.parse(selected_state)

            # Identify header row that includes vehicle type columns
            header_row_index = None
            for i, row in state_df.iterrows():
                if row.astype(str).str.contains(vehicle_type, case=False, na=False).any():
                    header_row_index = i
                    break

            if header_row_index is None:
                st.error(f"Vehicle type '{vehicle_type}' not found in {selected_state} tab.")
            else:
                # Re-parse with correct headers
                data_df = spec_xls.parse(selected_state, skiprows=header_row_index + 1)
                headers = state_df.iloc[header_row_index].astype(str).tolist()
                data_df.columns = headers

                if vehicle_type not in data_df.columns:
                    st.error(f"Vehicle column '{vehicle_type}' not found after parsing.")
                else:
                    required_patterns = data_df[vehicle_type].dropna().astype(str).str.strip()
                    required_patterns = [p for p in required_patterns if "-" in p and any(c.isdigit() for c in p)]

                    # Match patterns
                    matched, missing = [], []
                    for pattern in required_patterns:
                        if any(fnmatch.fnmatch(code, pattern) for code in order_codes):
                            matched.append(pattern)
                        else:
                            missing.append(pattern)

                    # Display result
                    st.subheader("Compliance Summary")
                    st.write(f"✅ Matched: {len(matched)}")
                    st.write(f"❌ Missing: {len(missing)}")

                    result_df = pd.DataFrame({
                        "Pattern": matched + missing,
                        "Status": ["✅ Matched"] * len(matched) + ["❌ Missing"] * len(missing)
                    })

                    st.dataframe(result_df)

                    # Optional export
                    csv = result_df.to_csv(index=False).encode('utf-8')
                    st.download_button("Download Summary CSV", csv, "compliance_summary.csv", "text/csv")

    except Exception as e:
        st.error(f"An error occurred: {e}")
