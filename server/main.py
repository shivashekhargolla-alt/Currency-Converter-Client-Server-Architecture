"""
Currency Converter — Backend server
------------------------------------
This is the SERVER side of the client-server split.

Responsibilities:
- Talks to the external exchange rate API (open.er-api.com)
- Caches results so the external API isn't hammered on every client request
- Enriches raw rate data with currency names + country flags (pycountry)
- Exposes its own clean endpoints for the client to consume:
    GET /api/rates                       -> full list of currencies
    GET /api/convert?from=USD&to=INR&amount=100  -> converted amount

Run with:
    uvicorn main:app --reload --port 8000
"""

import time
from typing import Optional

import pycountry
import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Currency Converter API", version="1.0.0")

# Allow the Streamlit client (running on a different port) to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

EXTERNAL_API_URL = "https://open.er-api.com/v6/latest/USD"
CACHE_TTL_SECONDS = 3600

_cache = {"data": None, "fetched_at": 0.0}

FLAG_OVERRIDES = {
    "EUR": "\U0001F1EA\U0001F1FA",
    "XOF": "\U0001F30D",
    "XAF": "\U0001F30D",
    "XCD": "\U0001F334",
    "XPF": "\U0001F3DD",
}

# Currencies shared by multiple countries don't map to a single country
# via their code, so give them an explicit label instead.
COUNTRY_OVERRIDES = {
    "EUR": "Eurozone",
    "XOF": "West African States",
    "XAF": "Central African States",
    "XCD": "Eastern Caribbean",
    "XPF": "French Pacific Territories",
}


def code_to_flag(country_code: str) -> str:
    if not country_code or len(country_code) != 2:
        return "\U0001F3F3"
    return "".join(chr(ord(c) + 127397) for c in country_code.upper())


def get_currency_flag(currency_code: str) -> str:
    if currency_code in FLAG_OVERRIDES:
        return FLAG_OVERRIDES[currency_code]
    guess = currency_code[:2]
    try:
        if pycountry.countries.get(alpha_2=guess):
            return code_to_flag(guess)
    except Exception:
        pass
    return "\U0001F3F3"


def get_currency_country(currency_code: str) -> str:
    if currency_code in COUNTRY_OVERRIDES:
        return COUNTRY_OVERRIDES[currency_code]
    guess = currency_code[:2]
    try:
        country = pycountry.countries.get(alpha_2=guess)
        if country:
            return country.name
    except Exception:
        pass
    return ""


def get_currency_name(code: str) -> str:
    try:
        currency = pycountry.currencies.get(alpha_3=code)
        return currency.name if currency else code
    except Exception:
        return code


def fetch_rates() -> dict:
    """Fetch rates from the external API, using an in-memory cache."""
    now = time.time()
    if _cache["data"] is not None and (now - _cache["fetched_at"]) < CACHE_TTL_SECONDS:
        return _cache["data"]

    try:
        response = requests.get(EXTERNAL_API_URL, timeout=10)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Upstream API error: {exc}")

    rates = payload.get("rates", {})
    enriched = {
        code: {
            "code": code,
            "name": get_currency_name(code),
            "flag": get_currency_flag(code),
            "country": get_currency_country(code),
            "rate": rate,
        }
        for code, rate in rates.items()
    }

    _cache["data"] = enriched
    _cache["fetched_at"] = now
    return enriched


class ConversionResult(BaseModel):
    from_code: str
    to_code: str
    amount: float
    converted: float
    rate: float


@app.get("/api/rates")
def get_rates():
    """Return every currency with its name, flag, and rate relative to USD."""
    rates = fetch_rates()
    return {"base": "USD", "count": len(rates), "currencies": list(rates.values())}


@app.get("/api/convert", response_model=ConversionResult)
def convert(
    from_code: str = Query(..., alias="from"),
    to_code: str = Query(..., alias="to"),
    amount: float = Query(..., ge=0),
):
    rates = fetch_rates()
    from_code, to_code = from_code.upper(), to_code.upper()

    if from_code not in rates:
        raise HTTPException(status_code=404, detail=f"Unknown currency: {from_code}")
    if to_code not in rates:
        raise HTTPException(status_code=404, detail=f"Unknown currency: {to_code}")

    from_rate = rates[from_code]["rate"]
    to_rate = rates[to_code]["rate"]
    converted = amount / from_rate * to_rate
    rate = to_rate / from_rate

    return ConversionResult(
        from_code=from_code,
        to_code=to_code,
        amount=amount,
        converted=converted,
        rate=rate,
    )


@app.get("/api/health")
def health():
    return {"status": "ok"}
