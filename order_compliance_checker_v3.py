
import streamlit as st
import pandas as pd
import fnmatch
import re

st.title("School Bus Order Compliance Checker")

# Upload inputs
order_file = st.file_uploader("Upload Order Spreadsheet", type=["xlsx", "xls"])
spec_file = st.file_uploader("Upload State Spec Spreadsheet", type=["xlsx", "xls"])

# Select state and vehicle type
selected_state = st.selectbox("Select State", options=["MN", "AL", "TX", "CA", "Other..."])
vehicle_type = st.selectbox("Select Vehicle Type", options=["MFSAB", "Type AI", "Type AII", "Type W/C"])
strict_mode = st.checkbox("Use strict pattern matching", value=False)

if order_file and spec_file and selected_state and vehicle_type:
    try:
        # Read in order sheet
        order_xls = pd.ExcelFile(order_file)
        order_df = order_xls.parse("Mapics")
        order_codes = order_df["Item Numbers"].dropna().astype(str).str.strip().str.upper().tolist()

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

                # Use fuzzy matching to find vehicle column
                matching_cols = [col for col in data_df.columns if vehicle_type.lower() in str(col).lower().strip()]

                if not matching_cols:
                    st.error(f"Vehicle column matching '{vehicle_type}' not found after parsing.")
                else:
                    vehicle_col = matching_cols[0]
                    raw_patterns = data_df[vehicle_col].dropna().astype(str).str.strip().str.upper()

                    if strict_mode:
                        required_patterns = [
                            p for p in raw_patterns
                            if re.fullmatch(r"[0-9*?]{3}-[0-9*?]{2}-[0-9*?]{2}", p)
                        ]
                    else:
                        required_patterns = [
                            p for p in raw_patterns
                            if "-" in p and any(char.isdigit() for char in p)
                        ]

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

                    csv = result_df.to_csv(index=False).encode("utf-8")
                    st.download_button("Download Summary CSV", csv, "compliance_summary.csv", "text/csv")

                    # Debug info
                    with st.expander("Debug Info"):
                        st.write("Order Codes Sample:", order_codes[:10])
                        st.write("Patterns Checked Sample:", required_patterns[:10])

    except Exception as e:
        st.error(f"An error occurred: {e}")
