from __future__ import annotations

import os
import threading
import time
from typing import Any

import yfinance as yf
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="India Daily Trend Analyzer API", version="0.1.0")
_configured_cors_origins = [
    origin.strip().rstrip("/")
    for origin in os.environ.get("CORS_ORIGINS", "").split(",")
    if origin.strip()
]
if "*" in _configured_cors_origins:
    raise ValueError("CORS_ORIGINS must list explicit origins; wildcard origins are not allowed.")
_cors_origins = list(dict.fromkeys([
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    *_configured_cors_origins,
]))
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)

_cache: dict[str, tuple[float, Any]] = {}
_cache_lock = threading.Lock()
_cache_ttl_seconds = 900
_universe = [
    {"symbol": "RELIANCE", "name": "Reliance Industries", "exchange": "NSE"},
    {"symbol": "TCS", "name": "Tata Consultancy Services", "exchange": "NSE"},
    {"symbol": "HDFCBANK", "name": "HDFC Bank", "exchange": "NSE"},
    {"symbol": "ICICIBANK", "name": "ICICI Bank", "exchange": "NSE"},
    {"symbol": "INFY", "name": "Infosys", "exchange": "NSE"},
    {"symbol": "SBIN", "name": "State Bank of India", "exchange": "NSE"},
    {"symbol": "BHARTIARTL", "name": "Bharti Airtel", "exchange": "NSE"},
    {"symbol": "ITC", "name": "ITC", "exchange": "NSE"},
    {"symbol": "LT", "name": "Larsen & Toubro", "exchange": "NSE"},
    {"symbol": "TATAMOTORS", "name": "Tata Motors", "exchange": "NSE"},
    {"symbol": "AXISBANK", "name": "Axis Bank", "exchange": "NSE"},
    {"symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank", "exchange": "NSE"},
    {"symbol": "BAJFINANCE", "name": "Bajaj Finance", "exchange": "NSE"},
    {"symbol": "HINDUNILVR", "name": "Hindustan Unilever", "exchange": "NSE"},
    {"symbol": "MARUTI", "name": "Maruti Suzuki India", "exchange": "NSE"},
    {"symbol": "SUNPHARMA", "name": "Sun Pharmaceutical Industries", "exchange": "NSE"},
    {"symbol": "WIPRO", "name": "Wipro", "exchange": "NSE"},
    {"symbol": "TATASTEEL", "name": "Tata Steel", "exchange": "NSE"},
    {"symbol": "ADANIENT", "name": "Adani Enterprises", "exchange": "NSE"},
    {"symbol": "^NSEI", "name": "Nifty 50", "exchange": "NSE"},
]

_nifty50 = [
    {"symbol": "ADANIENT", "name": "Adani Enterprises", "exchange": "NSE"},
    {"symbol": "ADANIPORTS", "name": "Adani Ports and Special Economic Zone", "exchange": "NSE"},
    {"symbol": "APOLLOHOSP", "name": "Apollo Hospitals Enterprise", "exchange": "NSE"},
    {"symbol": "ASIANPAINT", "name": "Asian Paints", "exchange": "NSE"},
    {"symbol": "AXISBANK", "name": "Axis Bank", "exchange": "NSE"},
    {"symbol": "BAJAJ-AUTO", "name": "Bajaj Auto", "exchange": "NSE"},
    {"symbol": "BAJFINANCE", "name": "Bajaj Finance", "exchange": "NSE"},
    {"symbol": "BAJAJFINSV", "name": "Bajaj Finserv", "exchange": "NSE"},
    {"symbol": "BEL", "name": "Bharat Electronics", "exchange": "NSE"},
    {"symbol": "BHARTIARTL", "name": "Bharti Airtel", "exchange": "NSE"},
    {"symbol": "CIPLA", "name": "Cipla", "exchange": "NSE"},
    {"symbol": "COALINDIA", "name": "Coal India", "exchange": "NSE"},
    {"symbol": "DRREDDY", "name": "Dr. Reddy's Laboratories", "exchange": "NSE"},
    {"symbol": "EICHERMOT", "name": "Eicher Motors", "exchange": "NSE"},
    {"symbol": "ETERNAL", "name": "Eternal", "exchange": "NSE"},
    {"symbol": "GRASIM", "name": "Grasim Industries", "exchange": "NSE"},
    {"symbol": "HCLTECH", "name": "HCL Technologies", "exchange": "NSE"},
    {"symbol": "HDFCBANK", "name": "HDFC Bank", "exchange": "NSE"},
    {"symbol": "HDFCLIFE", "name": "HDFC Life Insurance", "exchange": "NSE"},
    {"symbol": "HEROMOTOCO", "name": "Hero MotoCorp", "exchange": "NSE"},
    {"symbol": "HINDALCO", "name": "Hindalco Industries", "exchange": "NSE"},
    {"symbol": "HINDUNILVR", "name": "Hindustan Unilever", "exchange": "NSE"},
    {"symbol": "ICICIBANK", "name": "ICICI Bank", "exchange": "NSE"},
    {"symbol": "INDUSINDBK", "name": "IndusInd Bank", "exchange": "NSE"},
    {"symbol": "INFY", "name": "Infosys", "exchange": "NSE"},
    {"symbol": "ITC", "name": "ITC", "exchange": "NSE"},
    {"symbol": "JIOFIN", "name": "Jio Financial Services", "exchange": "NSE"},
    {"symbol": "JSWSTEEL", "name": "JSW Steel", "exchange": "NSE"},
    {"symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank", "exchange": "NSE"},
    {"symbol": "LT", "name": "Larsen & Toubro", "exchange": "NSE"},
    {"symbol": "M&M", "name": "Mahindra & Mahindra", "exchange": "NSE"},
    {"symbol": "MARUTI", "name": "Maruti Suzuki India", "exchange": "NSE"},
    {"symbol": "NESTLEIND", "name": "Nestle India", "exchange": "NSE"},
    {"symbol": "NTPC", "name": "NTPC", "exchange": "NSE"},
    {"symbol": "ONGC", "name": "Oil and Natural Gas Corporation", "exchange": "NSE"},
    {"symbol": "POWERGRID", "name": "Power Grid Corporation of India", "exchange": "NSE"},
    {"symbol": "RELIANCE", "name": "Reliance Industries", "exchange": "NSE"},
    {"symbol": "SBIN", "name": "State Bank of India", "exchange": "NSE"},
    {"symbol": "SBILIFE", "name": "SBI Life Insurance", "exchange": "NSE"},
    {"symbol": "SHRIRAMFIN", "name": "Shriram Finance", "exchange": "NSE"},
    {"symbol": "SUNPHARMA", "name": "Sun Pharmaceutical Industries", "exchange": "NSE"},
    {"symbol": "TCS", "name": "Tata Consultancy Services", "exchange": "NSE"},
    {"symbol": "TATACONSUM", "name": "Tata Consumer Products", "exchange": "NSE"},
    {"symbol": "TATAMOTORS", "name": "Tata Motors", "exchange": "NSE"},
    {"symbol": "TATASTEEL", "name": "Tata Steel", "exchange": "NSE"},
    {"symbol": "TECHM", "name": "Tech Mahindra", "exchange": "NSE"},
    {"symbol": "TITAN", "name": "Titan Company", "exchange": "NSE"},
    {"symbol": "TRENT", "name": "Trent", "exchange": "NSE"},
    {"symbol": "ULTRACEMCO", "name": "UltraTech Cement", "exchange": "NSE"},
    {"symbol": "WIPRO", "name": "Wipro", "exchange": "NSE"},
]


def _constituents(snapshot: str) -> list[dict[str, str]]:
    stocks = []
    for line in snapshot.strip().splitlines():
        symbol, name = line.split("|", 1)
        stocks.append({"symbol": symbol, "name": name, "exchange": "NSE"})
    return stocks


_nifty100 = _constituents("""
ABB|ABB India
ADANIENSOL|Adani Energy Solutions
ADANIENT|Adani Enterprises
ADANIGREEN|Adani Green Energy
ADANIPORTS|Adani Ports and Special Economic Zone
ADANIPOWER|Adani Power
AMBUJACEM|Ambuja Cements
APOLLOHOSP|Apollo Hospitals Enterprise
ASIANPAINT|Asian Paints
DMART|Avenue Supermarts
AXISBANK|Axis Bank
BSE|BSE
BAJAJ-AUTO|Bajaj Auto
BAJFINANCE|Bajaj Finance
BAJAJFINSV|Bajaj Finserv
BAJAJHLDNG|Bajaj Holdings & Investment
BANKBARODA|Bank of Baroda
BEL|Bharat Electronics
BPCL|Bharat Petroleum Corporation
BHARTIARTL|Bharti Airtel
BOSCHLTD|Bosch
BRITANNIA|Britannia Industries
CGPOWER|CG Power and Industrial Solutions
CANBK|Canara Bank
CHOLAFIN|Cholamandalam Investment and Finance Company
CIPLA|Cipla
COALINDIA|Coal India
CUMMINSIND|Cummins India
DLF|DLF
DIVISLAB|Divi's Laboratories
DRREDDY|Dr. Reddy's Laboratories
EICHERMOT|Eicher Motors
ETERNAL|Eternal
GAIL|GAIL (India)
GODREJCP|Godrej Consumer Products
GRASIM|Grasim Industries
HCLTECH|HCL Technologies
HDFCAMC|HDFC Asset Management Company
HDFCBANK|HDFC Bank
HDFCLIFE|HDFC Life Insurance Company
HINDALCO|Hindalco Industries
HAL|Hindustan Aeronautics
HINDUNILVR|Hindustan Unilever
HINDZINC|Hindustan Zinc
POWERINDIA|Hitachi Energy India
HYUNDAI|Hyundai Motor India
ICICIBANK|ICICI Bank
ITC|ITC
IOC|Indian Oil Corporation
IRFC|Indian Railway Finance Corporation
INFY|Infosys
INDIGO|InterGlobe Aviation
JSWSTEEL|JSW Steel
JINDALSTEL|Jindal Steel
JIOFIN|Jio Financial Services
KOTAKBANK|Kotak Mahindra Bank
LTM|LTM
LT|Larsen & Toubro
M&M|Mahindra & Mahindra
MARUTI|Maruti Suzuki India
MAXHEALTH|Max Healthcare Institute
MAZDOCK|Mazagon Dock Shipbuilders
MUTHOOTFIN|Muthoot Finance
NTPC|NTPC
NESTLEIND|Nestle India
ONGC|Oil & Natural Gas Corporation
PIDILITIND|Pidilite Industries
POLYCAB|Polycab India
PFC|Power Finance Corporation
POWERGRID|Power Grid Corporation of India
PNB|Punjab National Bank
RELIANCE|Reliance Industries
SBILIFE|SBI Life Insurance Company
MOTHERSON|Samvardhana Motherson International
SHRIRAMFIN|Shriram Finance
ENRIN|Siemens Energy India
SIEMENS|Siemens
SOLARINDS|Solar Industries India
SBIN|State Bank of India
SUNPHARMA|Sun Pharmaceutical Industries
TVSMOTOR|TVS Motor Company
TATACAP|Tata Capital
TCS|Tata Consultancy Services
TATACONSUM|Tata Consumer Products
TMCV|Tata Motors
TMPV|Tata Motors Passenger Vehicles
TATAPOWER|Tata Power
TATASTEEL|Tata Steel
TECHM|Tech Mahindra
TITAN|Titan Company
TORNTPHARM|Torrent Pharmaceuticals
TRENT|Trent
ULTRACEMCO|UltraTech Cement
UNIONBANK|Union Bank of India
VBL|Varun Beverages
VAML|Vedanta Aluminium Metal
VEDL|Vedanta
IDEA|Vodafone Idea
WIPRO|Wipro
ZYDUSLIFE|Zydus Lifesciences
""")

_nifty_midcap150 = _constituents("""
360ONE|360 ONE WAM
AIAENG|AIA Engineering
APLAPOLLO|APL Apollo Tubes
AUBANK|AU Small Finance Bank
ABBOTINDIA|Abbott India
ATGL|Adani Total Gas
ABCAPITAL|Aditya Birla Capital
AJANTPHARM|Ajanta Pharmaceuticals
ALKEM|Alkem Laboratories
ANTHEM|Anthem Biosciences
APARINDS|Apar Industries
ASHOKLEY|Ashok Leyland
ASTERDM|Aster DM Quality Care
ASTRAL|Astral
AUROPHARMA|Aurobindo Pharma
AIIL|Authum Investment & Infrastructure
BAJAJHFL|Bajaj Housing Finance
BALKRISIND|Balkrishna Industries
BANKINDIA|Bank of India
MAHABANK|Bank of Maharashtra
BERGEPAINT|Berger Paints India
BDL|Bharat Dynamics
BHARATFORG|Bharat Forge
BHEL|Bharat Heavy Electricals
BHARTIHEXA|Bharti Hexacom
GROWW|Billionbrains Garage Ventures
BIOCON|Biocon
BLUESTARCO|Blue Star
CRISIL|CRISIL
COCHINSHIP|Cochin Shipyard
COFORGE|Coforge
COLPAL|Colgate Palmolive (India)
CONCOR|Container Corporation of India
COROMANDEL|Coromandel International
DABUR|Dabur India
DALBHARAT|Dalmia Bharat
DIXON|Dixon Technologies (India)
EMBASSY|EMBASSY OFFICE PARKS REIT
ENDURANCE|Endurance Technologies
ESCORTS|Escorts Kubota
EXIDEIND|Exide Industries
NYKAA|FSN E-Commerce Ventures
FEDERALBNK|Federal Bank
FACT|Fertilisers and Chemicals Travancore
FORTIS|Fortis Healthcare
GVT&D|GE Vernova T&D India
GMRAIRPORT|GMR Airports
GICRE|General Insurance Corporation of India
GLAXO|Glaxosmithkline Pharmaceuticals
GLENMARK|Glenmark Pharmaceuticals
MEDANTA|Global Health
GODFRYPHLP|Godfrey Phillips India
GODREJIND|Godrej Industries
GODREJPROP|Godrej Properties
FLUOROCHEM|Gujarat Fluorochemicals
HDBFS|HDB Financial Services
HAVELLS|Havells India
HEROMOTOCO|Hero MotoCorp
HEXT|Hexaware Technologies
HINDCOPPER|Hindustan Copper
HINDPETRO|Hindustan Petroleum Corporation
HUDCO|Housing & Urban Development Corporation
ICICILIFE|ICICI Life Insurance
ICICIGI|ICICI Lombard General Insurance Company
ICICIAMC|ICICI Prudential Asset Management Company
IDFCFIRSTB|IDFC First Bank
ITCHOTELS|ITC Hotels
INDIANB|Indian Bank
INDHOTEL|Indian Hotels
IOB|Indian Overseas Bank
IRCTC|Indian Railway Catering And Tourism Corporation
IREDA|Indian Renewable Energy Development Agency
INDUSTOWER|Indus Towers
INDUSINDBK|IndusInd Bank
NAUKRI|Info Edge (India)
IPCALAB|Ipca Laboratories
JKCEMENT|J.K. Cement
JSWENERGY|JSW Energy
JSWINFRA|JSW Infrastructure
JSL|Jindal Stainless
JUBLFOOD|Jubilant Foodworks
KPRMILL|K.P.R. Mill
KEI|KEI Industries
KALYANKJIL|Kalyan Jewellers India
LTF|L&T Finance
LTTS|L&T Technology Services
LGEINDIA|LG Electronics India
LICHSGFIN|LIC Housing Finance
LAURUSLABS|Laurus Labs
LENSKART|Lenskart Solutions
LICI|Life Insurance Corporation of India
LINDEINDIA|Linde India
LLOYDSME|Lloyds Metals And Energy
LODHA|Lodha Developers
LUPIN|Lupin
MRF|MRF
M&MFIN|Mahindra & Mahindra Financial Services
MANKIND|Mankind Pharma
MARICO|Marico
MFSL|Max Financial Services
MEESHO|Meesho
MOTILALOFS|Motilal Oswal Financial Services
MPHASIS|MphasiS
MCX|Multi Commodity Exchange of India
NHPC|NHPC
NLCINDIA|NLC India
NMDC|NMDC
NTPCGREEN|NTPC Green Energy
NH|Narayana Hrudayalaya
NATIONALUM|National Aluminium
NAM-INDIA|Nippon Life India Asset Management
OBEROIRLTY|Oberoi Realty
OIL|Oil India
PAYTM|One 97 Communications
OFSS|Oracle Financial Services Software
POLICYBZR|PB Fintech
PIIND|PI Industries
PAGEIND|Page Industries
PATANJALI|Patanjali Foods
PERSISTENT|Persistent Systems
PETRONET|Petronet LNG
PHOENIXLTD|Phoenix Mills
PIRAMALFIN|Piramal Finance
PREMIERENE|Premier Energies
PRESTIGE|Prestige Estates Projects
RECLTD|REC
RADICO|Radico Khaitan
RVNL|Rail Vikas Nigam
SBICARD|SBI Cards and Payment Services
SRF|SRF
SCHAEFFLER|Schaeffler India
SHREECEM|Shree Cement
SAIL|Steel Authority of India
SUNDARMFIN|Sundaram Finance
SUPREMEIND|Supreme Industries
SUZLON|Suzlon Energy
SWIGGY|Swiggy
TATACOMM|Tata Communications
TATAINVEST|Tata Investment Corporation
THERMAX|Thermax
TORNTPOWER|Torrent Power
TIINDIA|Tube Investments of India
UNOMINDA|UNO Minda
UPL|UPL
UBL|United Breweries
UNITDSPR|United Spirits
VMM|Vishal Mega Mart
VOLTAS|Voltas
WAAREEENER|Waaree Energies
YESBANK|Yes Bank
""")

_periods = {"3M": "3mo", "6M": "6mo", "1Y": "1y", "2Y": "2y", "5Y": "5y"}


def _cached(key: str) -> Any | None:
    with _cache_lock:
        item = _cache.get(key)
        if item and time.time() - item[0] < _cache_ttl_seconds:
            return item[1]
        if item:
            _cache.pop(key, None)
    return None


def _store(key: str, value: Any) -> None:
    with _cache_lock:
        _cache[key] = (time.time(), value)


def _fetch_history(symbol: str, period: str) -> list[dict[str, Any]]:
    cache_key = f"{symbol}:{period}"
    cached = _cached(cache_key)
    if cached is not None:
        return cached
    try:
        frame = yf.download(
            symbol,
            period=period,
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=False,
            multi_level_index=False,
            timeout=20,
        )
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Market data provider failed: {error}") from error
    if frame.empty:
        raise HTTPException(status_code=404, detail=f"No daily market data available for {symbol}.")

    bars: list[dict[str, Any]] = []
    for timestamp, row in frame.iterrows():
        try:
            bar = {
                "time": timestamp.strftime("%Y-%m-%d"),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"]),
            }
        except (KeyError, TypeError, ValueError):
            continue
        if all(value == value for key, value in bar.items() if key != "time"):
            bars.append(bar)
    if not bars:
        raise HTTPException(status_code=404, detail=f"No valid daily bars available for {symbol}.")
    _store(cache_key, bars)
    return bars


def _yahoo_symbol(symbol: str, exchange: str) -> str:
    clean = symbol.strip().upper()
    if clean == "^NSEI":
        return clean
    if clean.endswith((".NS", ".BO")):
        return clean
    return f"{clean}.{ 'BO' if exchange.upper() == 'BSE' else 'NS' }"


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/search")
def search(q: str = Query(default="", max_length=40)) -> list[dict[str, str]]:
    stocks = {
        item["symbol"]: item
        for item in [*_nifty50, *_nifty100, *_nifty_midcap150, *_universe]
        if item["symbol"] != "^NSEI"
    }
    query = q.strip().casefold()
    if not query:
        return _nifty50[:8]
    matches = [
        item for item in stocks.values()
        if query in item["symbol"].casefold() or query in item["name"].casefold()
    ]
    return matches[:10]


@app.get("/api/universe")
def universe(
    index: str = Query(default="NIFTY50", pattern="^(NIFTY50|NIFTY100|MIDCAP150|STARTER)$"),
) -> list[dict[str, str]]:
    if index == "NIFTY50":
        return _nifty50
    if index == "NIFTY100":
        return _nifty100
    if index == "MIDCAP150":
        return _nifty_midcap150
    return [item for item in _universe if item["symbol"] != "^NSEI"]


@app.get("/api/history/{symbol}")
def history(
    symbol: str,
    period: str = Query(default="6M", pattern="^(3M|6M|1Y|2Y|5Y)$"),
    exchange: str = Query(default="NSE", pattern="^(NSE|BSE)$"),
) -> dict[str, Any]:
    yahoo_symbol = _yahoo_symbol(symbol, exchange)
    bars = _fetch_history(yahoo_symbol, _periods[period])
    return {
        "symbol": symbol.upper(),
        "exchange": exchange,
        "currency": "INR",
        "adjusted": True,
        "bars": bars,
        "source": "Yahoo Finance",
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
