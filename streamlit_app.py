# streamlit_app.py
import streamlit as st
import pandas as pd
import requests
import os
from datetime import datetime

st.set_page_config(page_title="Company Decision Engine", layout="wide")
st.title("📈 Company Decision Engine — Upload or Live API")

# ========== COMPANY SYMBOLS ==========
COMPANIES = {
    "CHENNPETRO.NS": "Chennai Petroleum Corporation Ltd",
    "COALINDIA.NS": "Coal India Ltd",
    "BEML.NS": "BEML Ltd",
    "SUNPHARMA.NS": "Sun Pharmaceutical Industries Ltd",
    "HINDCOPPER.NS": "Hindustan Copper Ltd",
    "ITC.NS": "ITC Ltd",
    "IOC.NS": "Indian Oil Corporation Ltd",
    "ONGC.NS": "ONGC Ltd",
    "HINDUNILVR.NS": "Hindustan Unilever Ltd",
    "MAHANGAS.NS": "Mahanagar Gas Ltd",
    "CASTROLIND.NS": "Castrol India Ltd",
    "MCDOWELL-N.NS": "United Spirits Ltd",
    "PRAJIND.NS": "Praj Industries Ltd"
}

# ========== API KEY ==========
if "FMP_API_KEY" in st.secrets:
    API_KEY = st.secrets["FMP_API_KEY"]
else:
    API_KEY = os.environ.get("FMP_API_KEY")

if not API_KEY:
    st.error("❌ API Key missing! Add your FMP_API_KEY in Streamlit Secrets.")
    st.stop()

# ========== FMP FETCH FUNCTION ==========
@st.cache_data(ttl=12 * 60 * 60)
def fetch_company_metrics(symbol: str):
    """Fetch financial ratios for one company symbol and handle missing data."""
    base = "https://financialmodelingprep.com/api/v3"
    profile_url = f"{base}/profile/{symbol}?apikey={API_KEY}"
    ratios_url = f"{base}/ratios/{symbol}?limit=1&apikey={API_KEY}"

    result = {
        "Symbol": symbol,
        "Name": COMPANIES.get(symbol, ""),
        "PE": None,
        "PEG": None,
        "Revenue_Growth_pct": None,
        "Quick_Ratio": None,
        "ROE_pct": None,
        "Status": "Success"
    }

    try:
        profile = requests.get(profile_url, timeout=10).json()
        if isinstance(profile, list) and len(profile) > 0:
            result["PE"] = profile[0].get("pe", None)
        else:
            result["Status"] = "No profile data"
    except Exception as e:
        result["Status"] = f"Profile error: {str(e)}"

    try:
        ratios = requests.get(ratios_url, timeout=10).json()
        if isinstance(ratios, list) and len(ratios) > 0:
            r = ratios[0]
            if r.get("revenueGrowth") is not None:
                result["Revenue_Growth_pct"] = float(r["revenueGrowth"]) * 100
            result["PEG"] = r.get("pegRatio", r.get("peg_ratio", None))
            if r.get("returnOnEquity") is not None:
                result["ROE_pct"] = float(r["returnOnEquity"]) * 100
            result["Quick_Ratio"] = r.get("quickRatio", None)
        else:
            result["Status"] = "No ratios data"
    except Exception as e:
        result["Status"] = f"Ratios error: {str(e)}"

    # mark as failed if no key metrics
    if all(val is None for val in [result["PE"], result["Revenue_Growth_pct"], result["Quick_Ratio"]]):
        result["Status"] = "Failed - no usable data"

    return result

# ========== UI ==========
st.sidebar.header("Select Data Source")
mode = st.sidebar.radio("Choose mode", ["Upload Excel (manual)", "Live API (FMP)"])

# ========== EXCEL MODE ==========
if mode == "Upload Excel (manual)":
    st.info("Upload an Excel (.xlsx) with columns: Company, Revenue_Growth_pct, PE, PEG, ROE_5yr_Avg, Quick_Ratio")
    uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])
    if uploaded_file:
        df = pd.read_excel(uploaded_file, engine="openpyxl")
        st.success("✅ File uploaded successfully!")
        st.dataframe(df)
    else:
        st.warning("Please upload a file to continue.")

# ========== LIVE API MODE ==========
else:
    st.info("Fetching live data from FinancialModelingPrep (this may take 10–20 seconds)...")

    progress = st.progress(0)
    all_results = []

    for i, (sym, name) in enumerate(COMPANIES.items()):
        progress.progress((i + 1) / len(COMPANIES))
        data = fetch_company_metrics(sym)
        all_results.append(data)

    df = pd.DataFrame(all_results)

    # Split into success and failed
    failed_df = df[df["Status"] != "Success"]
    success_df = df[df["Status"] == "Success"]

    # Display results
    st.success(f"✅ Successfully fetched data for {len(success_df)} companies.")
    if len(failed_df) > 0:
        st.warning(f"⚠️ Failed or incomplete data for {len(failed_df)} companies:")
        st.dataframe(failed_df[["Symbol", "Name", "Status"]])

    st.dataframe(success_df.drop(columns=["Status"]), height=500)

    # Download successful data as Excel
    def to_excel_bytes(dataframe):
        import io
        with io.BytesIO() as buffer:
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                dataframe.to_excel(writer, index=False)
            return buffer.getvalue()

    st.download_button("⬇️ Download successful data (Excel)",
                       data=to_excel_bytes(success_df),
                       file_name="company_metrics_success.xlsx")
