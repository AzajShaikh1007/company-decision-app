import streamlit as st
import pandas as pd

st.set_page_config(page_title="Company Decision Engine", layout="wide")
st.title("📈 Company Decision Engine — Flowchart Automation")

st.markdown("""
Upload an Excel (.xlsx) with columns:
`Company`, `Revenue_Growth_pct`, `PE`, `PEG`, `ROE_5yr_Avg`, `Quick_Ratio`
""")

uploaded_file = st.file_uploader("Upload companies.xlsx", type=["xlsx"])
if uploaded_file is None:
    st.info("Try the sample data: copy the template into Excel and upload the .xlsx file.")
else:
    try:
        df = pd.read_excel(uploaded_file, engine="openpyxl")
    except Exception as e:
        st.error(f"Failed to read Excel file: {e}")
        st.stop()

    required_cols = ["Company","Revenue_Growth_pct","PE","PEG","ROE_5yr_Avg","Quick_Ratio"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"Missing columns in uploaded file: {missing}")
        st.stop()

    for col in required_cols[1:]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    def decide(row,
               rev_growth_threshold=10,
               pe_threshold=25,
               peg_threshold=2,
               roe_threshold=5,
               quick_ratio_threshold=1.5):
        rg = row["Revenue_Growth_pct"]
        pe = row["PE"]
        peg = row["PEG"]
        roe = row["ROE_5yr_Avg"]
        qr = row["Quick_Ratio"]

        if pd.isna(rg) or pd.isna(pe) or pd.isna(peg) or pd.isna(roe) or pd.isna(qr):
            return "Insufficient data"
        if rg < rev_growth_threshold:
            return "Low revenue growth"
        if pe >= pe_threshold:
            return "Likely overvalued"
        if peg >= peg_threshold:
            return "Low profit growth"
        if roe < roe_threshold:
            return "Weak profitability"
        if qr < quick_ratio_threshold:
            return "Liquidity issues"
        return "Invest"

    st.sidebar.header("Decision thresholds (adjust if needed)")
    rev_growth_threshold = st.sidebar.number_input("Revenue growth % threshold", value=10.0)
    pe_threshold = st.sidebar.number_input("P/E threshold", value=25.0)
    peg_threshold = st.sidebar.number_input("PEG threshold", value=2.0)
    roe_threshold = st.sidebar.number_input("ROE (5yr avg) threshold", value=5.0)
    quick_ratio_threshold = st.sidebar.number_input("Quick ratio threshold", value=1.5)

    df["Decision"] = df.apply(decide, axis=1,
                              rev_growth_threshold=rev_growth_threshold,
                              pe_threshold=pe_threshold,
                              peg_threshold=peg_threshold,
                              roe_threshold=roe_threshold,
                              quick_ratio_threshold=quick_ratio_threshold)

    st.subheader("Results")
    st.dataframe(df, height=400)

    @st.cache_data
    def to_excel(dataframe):
        import io
        with io.BytesIO() as buffer:
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                dataframe.to_excel(writer, index=False, sheet_name="Results")
            return buffer.getvalue()

    st.download_button("⬇️ Download results as Excel", data=to_excel(df), file_name="company_decisions.xlsx")
