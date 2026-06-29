"""
3_Pricing.py

Market Intelligence — live commodity prices, 24-month trends, FX exposure,
and lending rate analysis for procurement negotiation context.

Data sources:
  - Live spot prices / FX / lending rates: st.session_state.reference_data
    (fetched at startup by utils/data_fetcher.py via yfinance + public APIs)
  - 24-month historical series: data/prices/*.csv (static, pulled by
    scripts/pull_prices.py)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import altair as alt
import pandas as pd
import streamlit as st

from ui_helpers import section_label, badge, kpi_card

# ── Paths ──────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent.parent.parent
PRICES_DIR = ROOT / "data" / "prices"

# ── Supplier currency map ──────────────────────────────────────────────────────

SUPPLIER_CURRENCIES = {
    "Ivoire Cacao Export":             ("USD", "cocoa"),
    "Golden Coast Cocoa Traders":      ("USD", "cocoa"),
    "Lowlands Dairy Co-op":            ("EUR", "dairy"),
    "Galil Dairy Suppliers":           ("ILS", "dairy"),
    "Cana Doce Açúcar":               ("USD", "sugar"),
    "Siam Sugar Partners":             ("USD", "sugar"),
    "Sierra Verde Coffee Cooperative": ("USD", "coffee"),
    "EuroPack Solutions":              ("PLN", "packaging"),
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def load_price_series(commodity: str) -> pd.DataFrame | None:
    fp = PRICES_DIR / f"{commodity}_24mo.csv"
    if not fp.exists():
        return None
    df = pd.read_csv(fp, parse_dates=["date"])
    return df.sort_values("date").reset_index(drop=True)


def get_fx_rate(fx_df: pd.DataFrame, pair: str) -> float | None:
    if fx_df.empty:
        return None
    row = fx_df[fx_df["currency_pair"] == pair]
    return float(row.iloc[0]["rate"]) if not row.empty else None


def get_live_price(bm_df: pd.DataFrame, commodity_name: str) -> dict | None:
    if bm_df.empty:
        return None
    row = bm_df[bm_df["commodity"] == commodity_name]
    if row.empty:
        return None
    return row.iloc[0].to_dict()


def pct_change_color(pct: float | None) -> str:
    if pct is None:
        return "gray"
    return "green" if pct > 0 else "red"


def early_payment_apr(discount_pct: float, discount_days: int, net_days: int) -> float | None:
    """Annualised return of taking an early payment discount."""
    diff = net_days - discount_days
    if diff <= 0 or discount_pct >= 100:
        return None
    return round((discount_pct / (100 - discount_pct)) * (365 / diff) * 100, 1)


# ── Session state guard ────────────────────────────────────────────────────────

if "reference_data" not in st.session_state:
    st.warning("Market data not yet loaded. Please return to Home and reload.")
    st.stop()

rd = st.session_state.reference_data
fx_df: pd.DataFrame = rd["fx_rates"]
bm_df: pd.DataFrame = rd["commodity_benchmarks"]
lr_df: pd.DataFrame = rd["lending_rates"]

# ── Page header ────────────────────────────────────────────────────────────────

st.title("Market Intelligence")
st.caption(
    "Live commodity prices, FX rates, and lending rates for negotiation context. "
    "Commodity history from 24-month static series; spot prices and rates fetched live."
)
st.divider()

# ── Tabs ───────────────────────────────────────────────────────────────────────

tab_comm, tab_fx, tab_money = st.tabs([
    "📦 Commodity Prices",
    "💱 FX Exposure",
    "💰 Cost of Money",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Commodity Prices
# ══════════════════════════════════════════════════════════════════════════════

with tab_comm:
    st.markdown(section_label("24-Month Trend + Live Spot Price"), unsafe_allow_html=True)
    st.caption("Historical weekly close from static CSV · Live spot from Yahoo Finance (ICE/CME Futures)")

    # SB=F raw quote is ¢/lb; series is converted to USD/MT on load below
    COMMODITIES = [
        ("cocoa",  "Cocoa",               "CC=F", "USD/MT",  "ICE"),
        ("sugar",  "Sugar (No. 11)",      "SB=F", "USD/MT",  "ICE"),
        ("dairy",  "Dairy (Class III)",   "DC=F", "USD/cwt", "CME"),
    ]

    for csv_key, display_name, ticker, unit, exchange in COMMODITIES:
        st.markdown(f"**{display_name}** · {ticker} · {unit} · {exchange}")

        series = load_price_series(csv_key)
        # SB=F CSV is stored in ¢/lb; convert to USD/MT for display
        if csv_key == "sugar" and series is not None and not series.empty:
            series = series.copy()
            series["price"] = series["price"] * 22.0462
        live = get_live_price(bm_df, display_name if csv_key != "dairy" else "Dairy (Class III Milk)")

        col_chart, col_stat = st.columns([3, 1], gap="large")

        with col_chart:
            if series is not None and not series.empty:
                chart_df = series[["date", "price"]].copy()
                line = alt.Chart(chart_df).mark_line(
                    color="#c8102e", strokeWidth=2
                ).encode(
                    x=alt.X("date:T", title=""),
                    y=alt.Y("price:Q", title=unit),
                    tooltip=[
                        alt.Tooltip("date:T", title="Date", format="%b %d, %Y"),
                        alt.Tooltip("price:Q", title=unit, format=",.2f"),
                    ],
                )
                area = alt.Chart(chart_df).mark_area(
                    color="#c8102e", opacity=0.07
                ).encode(
                    x=alt.X("date:T"),
                    y=alt.Y("price:Q"),
                )
                layers = [area, line]

                if live and live.get("price_usd") is not None:
                    rule_df = pd.DataFrame({"price": [live["price_usd"]]})
                    rule = alt.Chart(rule_df).mark_rule(
                        color="#0f172a", strokeDash=[6, 3], strokeWidth=1.5
                    ).encode(y=alt.Y("price:Q"))
                    layers.append(rule)

                chart = alt.layer(*layers).properties(height=180)
                st.altair_chart(chart, use_container_width=True)
            else:
                if csv_key == "dairy":
                    st.caption(
                        "CME Class III Milk (DC=F) has thin coverage on Yahoo Finance. "
                        "Dairy pricing is negotiated directly rather than tracked against "
                        "a liquid public benchmark — data gap is realistic for this category."
                    )
                else:
                    st.caption("No historical series available.")

        with col_stat:
            if live and live.get("price_usd") is not None:
                price_val = live["price_usd"]
                price_ils = live.get("price_ils")
                as_of = live.get("as_of_date", "")

                st.markdown(
                    f"<div style='font-size:1.6rem;font-weight:700;color:#0f172a;line-height:1.1'>"
                    f"{price_val:,.2f}</div>"
                    f"<div style='font-size:0.75rem;color:#64748b'>{unit} · live spot</div>"
                    f"<div style='font-size:0.72rem;color:#94a3b8;margin-top:4px'>as of {as_of}</div>",
                    unsafe_allow_html=True,
                )
                if price_ils:
                    st.markdown(
                        f"<div style='font-size:0.8rem;color:#475569;margin-top:6px'>"
                        f"≈ {price_ils:,.4f} ILS/{unit.split('/')[1]}</div>",
                        unsafe_allow_html=True,
                    )

                # 6-month change from static series
                if series is not None and len(series) > 1:
                    current_static = series.iloc[-1]["price"]
                    six_mo_idx = max(0, len(series) - 27)  # ~26 weeks
                    past_static = series.iloc[six_mo_idx]["price"]
                    if past_static:
                        chg = round((current_static - past_static) / past_static * 100, 1)
                        chg_color = "#16a34a" if chg > 0 else "#c8102e"
                        arrow = "▲" if chg > 0 else "▼"
                        st.markdown(
                            f"<div style='font-size:0.78rem;color:{chg_color};"
                            f"margin-top:8px;font-weight:600'>"
                            f"{arrow} {abs(chg)}% (6 months)</div>",
                            unsafe_allow_html=True,
                        )
            else:
                st.caption("Live price unavailable")

        st.divider()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — FX Exposure
# ══════════════════════════════════════════════════════════════════════════════

with tab_fx:
    st.markdown(section_label("Live FX Rates vs ILS"), unsafe_allow_html=True)

    if fx_df.empty:
        st.warning("FX rates could not be fetched. Check network connectivity.")
    else:
        # Rate cards
        fx_cols = st.columns(len(fx_df))
        for i, (_, row) in enumerate(fx_df.iterrows()):
            with fx_cols[i]:
                st.markdown(
                    f"<div style='background:white;border:1px solid #e2e8f0;border-radius:12px;"
                    f"padding:0.9rem 1rem;box-shadow:0 1px 3px rgba(0,0,0,0.05)'>"
                    f"<div style='font-size:0.65rem;font-weight:700;text-transform:uppercase;"
                    f"letter-spacing:0.07em;color:#64748b'>{row['currency_pair']}</div>"
                    f"<div style='font-size:1.5rem;font-weight:700;color:#0f172a;"
                    f"line-height:1.1;margin-top:2px'>{row['rate']:.4f}</div>"
                    f"<div style='font-size:0.7rem;color:#94a3b8'>as of {row['as_of_date']}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    st.divider()
    st.markdown(section_label("Supplier FX Exposure"), unsafe_allow_html=True)
    st.caption(
        "Each supplier's invoice currency determines your ILS cost. "
        "USD/EUR weakness increases effective procurement cost; "
        "ILS weakness increases cost for all non-ILS suppliers."
    )

    usdils = get_fx_rate(fx_df, "USD/ILS")
    eurils = get_fx_rate(fx_df, "EUR/ILS")
    plnils = get_fx_rate(fx_df, "PLN/ILS")

    currency_rate_map = {
        "USD": usdils,
        "EUR": eurils,
        "PLN": plnils,
        "ILS": 1.0,
    }

    exposure_rows = []
    for supplier, (currency, category) in SUPPLIER_CURRENCIES.items():
        rate = currency_rate_map.get(currency)
        exposure_rows.append({
            "Supplier": supplier,
            "Category": category.title(),
            "Invoice Currency": currency,
            "ILS Rate": f"{rate:.4f}" if rate else "—",
            "Exposure": (
                "None — domestic" if currency == "ILS"
                else f"FX risk — {currency} fluctuation affects ILS cost"
            ),
        })

    exp_df = pd.DataFrame(exposure_rows)

    def highlight_fx(row):
        if row["Invoice Currency"] == "ILS":
            return [""] * len(row)
        return ["background-color: #fff7ed"] * len(row)

    st.dataframe(
        exp_df.style.apply(highlight_fx, axis=1),
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        "6 of 8 suppliers invoice in non-ILS currencies (5 USD, 1 EUR, 1 PLN). "
        "An ILS depreciation of 5% increases effective procurement cost by ~5% across those contracts."
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Cost of Money
# ══════════════════════════════════════════════════════════════════════════════

with tab_money:
    st.markdown(section_label("Benchmark Lending Rates"), unsafe_allow_html=True)

    if lr_df.empty:
        st.warning("Lending rates unavailable.")
    else:
        rate_cols = st.columns(len(lr_df))
        for i, (_, row) in enumerate(lr_df.iterrows()):
            source_ok = "fallback" not in row["source"] and "hardcoded" not in row["source"]
            src_badge = "🟢 Live" if source_ok else "🟡 Estimate"
            with rate_cols[i]:
                st.markdown(
                    f"<div style='background:white;border:1px solid #e2e8f0;border-radius:12px;"
                    f"padding:0.9rem 1rem;box-shadow:0 1px 3px rgba(0,0,0,0.05);height:100%'>"
                    f"<div style='font-size:0.65rem;font-weight:700;text-transform:uppercase;"
                    f"letter-spacing:0.07em;color:#64748b'>{row['rate_type']} · {row['currency']}</div>"
                    f"<div style='font-size:1.5rem;font-weight:700;color:#0f172a;"
                    f"line-height:1.1;margin-top:2px'>{row['rate_pct']:.2f}%</div>"
                    f"<div style='font-size:0.7rem;color:#94a3b8'>{src_badge}</div>"
                    f"<div style='font-size:0.72rem;color:#475569;margin-top:6px'>"
                    f"{row['notes']}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    st.divider()

    # ── Early Payment Discount Calculator ─────────────────────────────────────

    st.markdown(section_label("Early Payment Discount Analysis"), unsafe_allow_html=True)
    st.caption(
        "Compare the annualised return of taking a supplier's early payment discount "
        "against your cost of capital (BOI prime rate). If the implied APR exceeds your "
        "borrowing cost, taking the discount is financially rational."
    )

    boi_rate = None
    if not lr_df.empty:
        boi_row = lr_df[lr_df["rate_type"] == "Prime Rate"]
        if not boi_row.empty:
            boi_rate = float(boi_row.iloc[0]["rate_pct"])

    c1, c2, c3 = st.columns(3)
    with c1:
        discount_pct = st.number_input(
            "Discount offered (%)", min_value=0.1, max_value=20.0,
            value=2.5, step=0.1,
            help="e.g. 2.5 for a 2.5% early payment discount",
        )
    with c2:
        discount_days = st.number_input(
            "Pay within (days)", min_value=1, max_value=30,
            value=10, step=1,
            help="Days within which you must pay to claim the discount",
        )
    with c3:
        net_days = st.number_input(
            "Standard net terms (days)", min_value=10, max_value=120,
            value=30, step=5,
            help="Full payment due date under standard terms",
        )

    apr = early_payment_apr(discount_pct, int(discount_days), int(net_days))

    if apr is not None and boi_rate is not None:
        spread = apr - boi_rate
        if spread > 10:
            verdict = "✅ Strongly worth taking"
            verdict_color = "#166534"
            verdict_bg = "#dcfce7"
        elif spread > 0:
            verdict = "✅ Worth taking"
            verdict_color = "#166534"
            verdict_bg = "#dcfce7"
        elif spread > -5:
            verdict = "⚠️ Marginal — consider cash flow needs"
            verdict_color = "#92400e"
            verdict_bg = "#fef3c7"
        else:
            verdict = "❌ Not worth taking vs. cost of capital"
            verdict_color = "#c8102e"
            verdict_bg = "#fee2e2"

        result_cols = st.columns(3)
        with result_cols[0]:
            st.markdown(
                f"<div style='background:white;border:1px solid #e2e8f0;border-radius:12px;"
                f"padding:1rem 1.1rem'>"
                f"<div style='font-size:0.65rem;font-weight:700;text-transform:uppercase;"
                f"color:#64748b;letter-spacing:0.07em'>Implied APR</div>"
                f"<div style='font-size:2rem;font-weight:700;color:#0f172a'>{apr:.1f}%</div>"
                f"<div style='font-size:0.72rem;color:#94a3b8'>annualised return of discount</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with result_cols[1]:
            st.markdown(
                f"<div style='background:white;border:1px solid #e2e8f0;border-radius:12px;"
                f"padding:1rem 1.1rem'>"
                f"<div style='font-size:0.65rem;font-weight:700;text-transform:uppercase;"
                f"color:#64748b;letter-spacing:0.07em'>Cost of Capital (BOI Prime)</div>"
                f"<div style='font-size:2rem;font-weight:700;color:#0f172a'>{boi_rate:.2f}%</div>"
                f"<div style='font-size:0.72rem;color:#94a3b8'>your ILS borrowing benchmark</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with result_cols[2]:
            st.markdown(
                f"<div style='background:{verdict_bg};border:1px solid #e2e8f0;border-radius:12px;"
                f"padding:1rem 1.1rem'>"
                f"<div style='font-size:0.65rem;font-weight:700;text-transform:uppercase;"
                f"color:#64748b;letter-spacing:0.07em'>Decision</div>"
                f"<div style='font-size:0.95rem;font-weight:700;color:{verdict_color};"
                f"margin-top:6px'>{verdict}</div>"
                f"<div style='font-size:0.72rem;color:#64748b;margin-top:4px'>"
                f"Spread: {spread:+.1f}pp vs cost of capital</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        st.caption(
            f"Formula: ({discount_pct}% / {100 - discount_pct}%) × (365 / {int(net_days) - int(discount_days)} days) = {apr:.1f}% APR  "
            f"·  Known example: Galil Dairy Suppliers offers 2.5% / 10 days / net 30"
        )
    else:
        st.info("Enter valid discount terms above to see the analysis.")

    st.divider()

    # ── SOFR / EURIBOR context ─────────────────────────────────────────────────

    st.markdown(section_label("FX Rate Context for USD & EUR Contracts"), unsafe_allow_html=True)

    sofr_rate = None
    euribor_rate = None
    if not lr_df.empty:
        sofr_row = lr_df[lr_df["rate_type"] == "SOFR"]
        if not sofr_row.empty:
            sofr_rate = float(sofr_row.iloc[0]["rate_pct"])
        eur_row = lr_df[lr_df["rate_type"] == "EURIBOR 3M"]
        if not eur_row.empty:
            euribor_rate = float(eur_row.iloc[0]["rate_pct"])

    context_rows = []
    if usdils and sofr_rate:
        context_rows.append(
            f"**USD contracts (5 suppliers):** SOFR at {sofr_rate:.2f}% is the USD benchmark. "
            f"At {usdils:.4f} ILS/USD, a 1% USD move changes your effective cost by "
            f"~{usdils * 0.01:.4f} ILS per USD of invoice value."
        )
    if eurils and euribor_rate:
        context_rows.append(
            f"**EUR contracts (Lowlands Dairy):** EURIBOR 3M at {euribor_rate:.2f}%. "
            f"At {eurils:.4f} ILS/EUR, EUR-denominated invoices carry both rate and FX exposure."
        )
    if plnils:
        context_rows.append(
            f"**PLN contracts (EuroPack Solutions):** PLN/ILS at {plnils:.4f}. "
            f"No liquid PLN lending benchmark used in this prototype — treat as directional."
        )

    for row in context_rows:
        st.markdown(row)

    if not context_rows:
        st.caption("FX context unavailable — rate fetch may have failed.")
