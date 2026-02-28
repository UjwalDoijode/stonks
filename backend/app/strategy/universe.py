"""
NIFTY 500 universe — symbols for NSE with yfinance suffix.

Organised into tiers for efficient scanning:
  Tier 1 (NIFTY 50)   — always scanned
  Tier 2 (Next 50)     — always scanned
  Tier 3 (NIFTY 200)   — scanned when ranking top picks
  Tier 4 (NIFTY 500)   — full universe for weekly deep scans

The stock ranker scores the full 500, but live scanning
only iterates the top-ranked subset for speed.
"""

from typing import Optional

# ─── NIFTY 50 (Tier 1) ──────────────────────────────────
NIFTY_50_SYMBOLS: list[str] = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
    "LT.NS", "AXISBANK.NS", "BAJFINANCE.NS", "ASIANPAINT.NS", "MARUTI.NS",
    "HCLTECH.NS", "SUNPHARMA.NS", "TITAN.NS", "WIPRO.NS", "ULTRACEMCO.NS",
    "NESTLEIND.NS", "BAJAJFINSV.NS", "TECHM.NS", "POWERGRID.NS", "NTPC.NS",
    "TATAMOTORS.NS", "M&M.NS", "ONGC.NS", "JSWSTEEL.NS", "TATASTEEL.NS",
    "ADANIENT.NS", "ADANIPORTS.NS", "COALINDIA.NS", "HDFCLIFE.NS", "SBILIFE.NS",
    "GRASIM.NS", "BAJAJ-AUTO.NS", "DRREDDY.NS", "DIVISLAB.NS", "CIPLA.NS",
    "BRITANNIA.NS", "EICHERMOT.NS", "APOLLOHOSP.NS", "HEROMOTOCO.NS", "INDUSINDBK.NS",
    "BPCL.NS", "TATACONSUM.NS", "DABUR.NS", "GODREJCP.NS", "PIDILITIND.NS",
]

# ─── Next 50 (Tier 2) ───────────────────────────────────
NIFTY_NEXT50_SYMBOLS: list[str] = [
    "SIEMENS.NS", "HAVELLS.NS", "AMBUJACEM.NS", "DLF.NS", "SRF.NS",
    "BANKBARODA.NS", "PNB.NS", "ICICIGI.NS", "ICICIPRULI.NS", "NAUKRI.NS",
    "SHREECEM.NS", "BERGEPAINT.NS", "HINDPETRO.NS", "IOC.NS", "GAIL.NS",
    "MCDOWELL-N.NS", "COLPAL.NS", "MARICO.NS", "TORNTPHARM.NS", "LUPIN.NS",
    "ABBOTINDIA.NS", "BIOCON.NS", "PEL.NS", "MUTHOOTFIN.NS", "VOLTAS.NS",
    "TRENT.NS", "AUROPHARMA.NS", "INDUSTOWER.NS", "CANBK.NS", "IDFCFIRSTB.NS",
    "ACC.NS", "TATAPOWER.NS", "BHEL.NS", "SAIL.NS", "RECLTD.NS",
    "PFC.NS", "IRCTC.NS", "POLYCAB.NS", "PIIND.NS", "ASTRAL.NS",
    "ABB.NS", "BALKRISIND.NS", "JUBLFOOD.NS", "MPHASIS.NS", "COFORGE.NS",
    "LTIM.NS", "PERSISTENT.NS", "TVSMOTOR.NS", "MRF.NS", "HAL.NS",
]

# ─── NIFTY 200 additions (Tier 3) ───────────────────────
NIFTY_200_EXTRA: list[str] = [
    "BEL.NS", "LICI.NS", "JIOFIN.NS", "ZOMATO.NS", "LODHA.NS",
    "PAYTM.NS", "CUMMINSIND.NS", "GODREJPROP.NS", "PAGEIND.NS", "ALKEM.NS",
    "ESCORTS.NS", "FEDERALBNK.NS", "IPCALAB.NS", "MAXHEALTH.NS", "OBEROIRLTY.NS",
    "PHOENIXLTD.NS", "PRESTIGE.NS", "SOLARINDS.NS", "TATAELXSI.NS", "FORTIS.NS",
    "CROMPTON.NS", "DELHIVERY.NS", "HONAUT.NS", "INDHOTEL.NS", "KPITTECH.NS",
    "LAURUSLABS.NS", "LICHSGFIN.NS", "METROBRAND.NS", "NYKAA.NS", "OFSS.NS",
    "PATANJALI.NS", "PETRONET.NS", "PIIND.NS", "SYNGENE.NS", "THERMAX.NS",
    "TIINDIA.NS", "UPL.NS", "VEDL.NS", "ZYDUSLIFE.NS", "APLAPOLLO.NS",
    "BANDHANBNK.NS", "CUB.NS", "DEEPAKNTR.NS", "EXIDEIND.NS", "GMRINFRA.NS",
    "HINDCOPPER.NS", "IDBI.NS", "JKCEMENT.NS", "KAJARIACER.NS", "MANAPPURAM.NS",
    "MFSL.NS", "NHPC.NS", "NMDC.NS", "PVRINOX.NS", "RAMCOCEM.NS",
    "SONACOMS.NS", "SUPREMEIND.NS", "TATACHEM.NS", "TORNTPOWER.NS", "WHIRLPOOL.NS",
    "BATAINDIA.NS", "BHARATFORG.NS", "CONCOR.NS", "EMAMILTD.NS", "ENDURANCE.NS",
    "GLAND.NS", "GLAXO.NS", "HATSUN.NS", "KAYNES.NS", "LATENTVIEW.NS",
    "LALPATHLAB.NS", "MCX.NS", "NATCOPHARM.NS", "NAVINFLUOR.NS", "PGHH.NS",
    "RELAXO.NS", "SUNTV.NS", "SUVENPHAR.NS", "TRIDENT.NS", "UNOMINDA.NS",
    "AJANTPHARM.NS", "ATUL.NS", "CARBORUNIV.NS", "CENTRALBK.NS", "CGPOWER.NS",
    "COROMANDEL.NS", "DMART.NS", "FACT.NS", "GRINDWELL.NS", "GSPL.NS",
    "HUDCO.NS", "IRFC.NS", "IEX.NS", "IRB.NS", "JSL.NS",
    "JUBLINGREA.NS", "KIMS.NS", "MOTHERSON.NS", "NAM-INDIA.NS", "NATIONALUM.NS",
]

# ─── NIFTY 500 additions (Tier 4) ───────────────────────
NIFTY_500_EXTRA: list[str] = [
    "3MINDIA.NS", "AAVAS.NS", "ABCAPITAL.NS", "AEGISCHEM.NS", "AFFLE.NS",
    "AIAENG.NS", "ALOKINDS.NS", "AMARAJABAT.NS", "ANANDRATHI.NS", "ANGELONE.NS",
    "APTUS.NS", "ARVINDFASN.NS", "ASHOKLEY.NS", "ASTERDM.NS", "ASTRAZEN.NS",
    "ATUL.NS", "AUBANK.NS", "AUROBINDO.NS", "BSOFT.NS", "BIRLASOFT.NS",
    "BLUESTARCO.NS", "BRIGADE.NS", "CAMS.NS", "CANFINHOME.NS", "CASTROLIND.NS",
    "CDSL.NS", "CESC.NS", "CLEAN.NS", "CYIENT.NS", "DATAPATTNS.NS",
    "DCMSHRIRAM.NS", "DEVYANI.NS", "DIXON.NS", "EIDPARRY.NS", "ELGIEQUIP.NS",
    "EQUITASBNK.NS", "FINCABLES.NS", "FINEORG.NS", "FLUOROCHEM.NS", "GICRE.NS",
    "GILLETTE.NS", "GLENMARK.NS", "GNFC.NS", "GRANULES.NS", "GRAPHITE.NS",
    "GSFC.NS", "HAPPSTMNDS.NS", "HEG.NS", "IBULHSGFIN.NS", "IIFL.NS",
    "INDIACEM.NS", "INDIGOPNTS.NS", "INTELLECT.NS", "JBCHEPHARM.NS", "JKLAKSHMI.NS",
    "JMFINANCIL.NS", "JWL.NS", "KALYANKJIL.NS", "KEC.NS", "KEI.NS",
    "KFINTECH.NS", "KNRCON.NS", "KPITTECH.NS", "KRBL.NS", "KSB.NS",
    "LAXMIMACH.NS", "LINDEINDIA.NS", "LTTS.NS", "LUXIND.NS", "MAPMYINDIA.NS",
    "MASTEK.NS", "MEDANTA.NS", "METROPOLIS.NS", "MINDACORP.NS", "MOLD-TEK.NS",
    "MOTILALOFS.NS", "MSUMI.NS", "NBCC.NS", "NCC.NS", "NIACL.NS",
    "OLECTRA.NS", "PNBHOUSING.NS", "POLYMED.NS", "PPLPHARMA.NS", "RADICO.NS",
    "RITES.NS", "ROUTE.NS", "RVNL.NS", "SAPPHIRE.NS", "SCHAEFFLER.NS",
    "SHRIRAMFIN.NS", "SJVN.NS", "SKFINDIA.NS", "SNOWMAN.NS", "SOBHA.NS",
    "STAR.NS", "SUNDARMFIN.NS", "SUNFLAG.NS", "TATACOMM.NS", "TATAINVEST.NS",
    "TEAMLEASE.NS", "TECHNOE.NS", "TIMKEN.NS", "TITAGARH.NS", "TRITURBINE.NS",
    "TRIVENI.NS", "UCOBANK.NS", "UJJIVANSFB.NS", "UTIAMC.NS", "VAIBHAVGBL.NS",
    "VGUARD.NS", "VINATIORGA.NS", "VIPIND.NS", "VSTIND.NS", "WELCORP.NS",
    "WESTLIFE.NS", "YESBANK.NS", "ZENSARTECH.NS", "ZFCVINDIA.NS", "ZPOWERI.NS",
]

# ─── Aggregated lists ────────────────────────────────────
# Legacy alias for backward compatibility
NIFTY_100_SYMBOLS = NIFTY_50_SYMBOLS + NIFTY_NEXT50_SYMBOLS

NIFTY_200_SYMBOLS = NIFTY_100_SYMBOLS + NIFTY_200_EXTRA
NIFTY_500_SYMBOLS = NIFTY_200_SYMBOLS + NIFTY_500_EXTRA


def get_clean_symbol(symbol: str) -> str:
    """Remove .NS suffix for display."""
    return symbol.replace(".NS", "")


def get_universe(tier: str = "500") -> list[str]:
    """Return symbol list for the requested tier."""
    tiers = {
        "50": NIFTY_50_SYMBOLS,
        "100": NIFTY_100_SYMBOLS,
        "200": NIFTY_200_SYMBOLS,
        "500": NIFTY_500_SYMBOLS,
    }
    return tiers.get(tier, NIFTY_500_SYMBOLS)


def get_scan_universe(top_ranked: Optional[list[str]] = None, max_scan: int = 50) -> list[str]:
    """
    Return the subset to scan for signals.
    If stock ranker has produced top_ranked, scan those.
    Otherwise fall back to NIFTY 100 (Tier 1+2).
    """
    if top_ranked and len(top_ranked) > 0:
        return top_ranked[:max_scan]
    return NIFTY_100_SYMBOLS
