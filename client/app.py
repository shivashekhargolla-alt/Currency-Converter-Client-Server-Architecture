"""
Currency Converter — Frontend client
--------------------------------------
This is the CLIENT side of the client-server split.

It never talks to open.er-api.com directly. Instead it calls our own
backend server's endpoints:
    GET {SERVER_URL}/api/rates
    GET {SERVER_URL}/api/convert

Run the server first (from the server/ folder):
    uvicorn main:app --reload --port 8000

Then run this client:
    streamlit run app.py
"""

import os

import pandas as pd
import requests
import streamlit as st

# In local dev this defaults to localhost. When deployed, set SERVER_URL
# via an environment variable or Streamlit secrets (see README).
SERVER_URL = os.environ.get("SERVER_URL") or st.secrets.get("SERVER_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Currency Converter",
    page_icon="\U0001F4B1",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(180deg, #0f1117 0%, #161a25 100%);
    }
    .main-title {
        font-size: 2.6rem;
        font-weight: 800;
        text-align: center;
        background: linear-gradient(90deg, #6EE7B7, #3B82F6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0rem;
    }
    .subtitle {
        text-align: center;
        color: #9CA3AF;
        font-size: 0.95rem;
        margin-bottom: 2rem;
    }
    .result-card {
        background: rgba(59, 130, 246, 0.08);
        border: 1px solid rgba(110, 231, 183, 0.25);
        border-radius: 16px;
        padding: 1.6rem;
        text-align: center;
        margin-top: 1rem;
        margin-bottom: 1.2rem;
    }
    .result-amount {
        font-size: 2.2rem;
        font-weight: 700;
        color: #6EE7B7;
    }
    .rate-caption {
        color: #9CA3AF;
        font-size: 0.85rem;
        margin-top: 0.4rem;
    }
    .server-badge {
        text-align: center;
        font-size: 0.75rem;
        color: #6B7280;
        margin-bottom: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="main-title">\U0001F4B1 Currency Converter</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Client app — talks to our own backend server</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Client-side API calls (to OUR server, not the external one)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300)
def fetch_rates_from_server() -> pd.DataFrame:
    response = requests.get(f"{SERVER_URL}/api/rates", timeout=10)
    response.raise_for_status()
    payload = response.json()
    df = pd.DataFrame(payload["currencies"])
    df["country_suffix"] = df["country"].apply(lambda c: f" ({c})" if c else "")
    df["Label"] = df["flag"] + " " + df["code"] + " - " + df["name"] + df["country_suffix"]
    return df


def convert_via_server(from_code: str, to_code: str, amount: float) -> dict:
    response = requests.get(
        f"{SERVER_URL}/api/convert",
        params={"from": from_code, "to": to_code, "amount": amount},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


try:
    df = fetch_rates_from_server()
    st.markdown(
        f'<div class="server-badge">\u2705 connected to server &middot; {len(df)} currencies loaded</div>',
        unsafe_allow_html=True,
    )
except requests.RequestException as e:
    st.error(
        "Could not reach the backend server. Make sure it's running:\n\n"
        "`uvicorn main:app --reload --port 8000` (from the server/ folder)\n\n"
        f"Details: {e}"
    )
    st.stop()

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

if "from_code" not in st.session_state:
    st.session_state.from_code = "USD"
if "to_code" not in st.session_state:
    st.session_state.to_code = "INR"


def swap_currencies():
    st.session_state.from_code, st.session_state.to_code = (
        st.session_state.to_code,
        st.session_state.from_code,
    )


def default_index(code: str, fallback: int = 0) -> int:
    match = df.index[df["code"] == code]
    return int(match[0]) if len(match) else fallback


col1, col_swap, col2 = st.columns([5, 1, 5])

with col1:
    from_label = st.selectbox("From", df["Label"], index=default_index(st.session_state.from_code))
    st.session_state.from_code = from_label.split(" ")[1]

with col_swap:
    st.markdown("<div style='height: 1.8rem;'></div>", unsafe_allow_html=True)
    st.button("\U0001F504", on_click=swap_currencies, help="Swap currencies", use_container_width=True)

with col2:
    to_label = st.selectbox("To", df["Label"], index=default_index(st.session_state.to_code))
    st.session_state.to_code = to_label.split(" ")[1]

amount = st.number_input("Amount", min_value=0.0, value=1.0, step=1.0)

from_code = st.session_state.from_code
to_code = st.session_state.to_code
from_flag = df.loc[df["code"] == from_code, "flag"].values[0]
to_flag = df.loc[df["code"] == to_code, "flag"].values[0]

try:
    result = convert_via_server(from_code, to_code, amount)
except requests.RequestException as e:
    st.error(f"Conversion request failed: {e}")
    st.stop()

st.markdown(
    f"""
    <div class="result-card">
        <div>{from_flag} {amount:,.2f} {from_code} =</div>
        <div class="result-amount">{to_flag} {result['converted']:,.2f} {to_code}</div>
        <div class="rate-caption">1 {from_code} = {result['rate']:.6f} {to_code}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.expander("View all exchange rates"):
    st.dataframe(
        df[["flag", "code", "name", "country", "rate"]].rename(
            columns={
                "flag": "Flag",
                "code": "Currency",
                "name": "Currency Name",
                "country": "Country",
                "rate": "Exchange Rate",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )
