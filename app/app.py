"""
SurfCast SD — Plotly Dash app.

Surfline-style surf conditions dashboard for San Diego breaks.
Uses live ETL data when available, falls back to synthetic data for display.

Run locally:   python app/app.py
Deploy:        gunicorn app.app:server
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import json

import dash_leaflet as dl
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import ALL, Dash, Input, Output, callback_context, dcc, html
from dash.exceptions import PreventUpdate

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# ── COLORS ───────────────────────────────────────────────────────────────────

NAV_BG = "#0f1923"
NAV_BORDER = "#1e2d3a"
NAV_TEXT = "#ffffff"
NAV_MUTED = "#8892b0"
NAV_DIM = "#ccd6f6"
BG = "#f5f5f5"
SURFACE = "#ffffff"
SURFACE_ALT = "#f8f9fa"
BORDER = "#e0e0e0"
TEXT = "#1a1a1a"
TEXT_MUTED = "#666666"
BRAND = "#ff6b35"
ACCENT = "#1d9bf0"

RATING_COLORS = {
    "epic":      "#d54530",
    "great":     "#ff8900",
    "good":      "#ffcd1e",
    "fair":      "#30d2e8",
    "poor_fair": "#408fff",
    "poor":      "#98a2af",
}

FONT = "Source Sans Pro, Helvetica, sans-serif"

# ── BREAKS & STATIONS ────────────────────────────────────────────────────────

BREAKS: dict[str, dict] = {
    "la_jolla_shores": {"name": "La Jolla Shores",     "loc": "La Jolla, CA",       "lat": 32.8579, "lon": -117.2575},
    "blacks":          {"name": "Blacks Beach",          "loc": "La Jolla, CA",       "lat": 32.8807, "lon": -117.2436},
    "pb_point":        {"name": "Pacific Beach Point",   "loc": "Pacific Beach, CA",  "lat": 32.7970, "lon": -117.2550},
    "ocean_beach":     {"name": "Ocean Beach",           "loc": "Ocean Beach, CA",    "lat": 32.7443, "lon": -117.2535},
    "sunset_cliffs":   {"name": "Sunset Cliffs",         "loc": "Point Loma, CA",     "lat": 32.7118, "lon": -117.2502},
    "imperial_beach":  {"name": "Imperial Beach",        "loc": "Imperial Beach, CA", "lat": 32.5805, "lon": -117.1318},
}

NDBC_STATIONS: dict[str, str] = {
    "46232": "Point Loma South",
    "46254": "Mission Bay West",
}

# Surf zone polygons — [lat, lon] vertices tracing each break's surfable area
# Each shape runs along the shore (N→S) then closes offshore, ~300–500m wide
BREAK_POLYGONS: dict[str, list[list[float]]] = {
    "blacks": [                     # Long beach below Torrey Pines cliffs
        [32.894, -117.248],         # north shoreline
        [32.894, -117.256],         # north offshore
        [32.876, -117.255],         # south offshore
        [32.876, -117.248],         # south shoreline
    ],
    "la_jolla_shores": [            # Sandy beach south of Blacks
        [32.870, -117.252],
        [32.870, -117.258],
        [32.855, -117.257],
        [32.855, -117.251],
    ],
    "pb_point": [                   # Crystal Pier area, Pacific Beach
        [32.803, -117.253],
        [32.803, -117.260],
        [32.788, -117.259],
        [32.788, -117.252],
    ],
    "ocean_beach": [                # OB Pier and surrounding break
        [32.754, -117.250],
        [32.754, -117.257],
        [32.740, -117.256],
        [32.740, -117.249],
    ],
    "sunset_cliffs": [              # Rocky reef stretch along the cliffs
        [32.733, -117.248],
        [32.733, -117.256],
        [32.708, -117.254],
        [32.708, -117.247],
    ],
    "imperial_beach": [             # Southernmost SD beach near the pier
        [32.593, -117.128],
        [32.593, -117.144],
        [32.573, -117.142],
        [32.573, -117.126],
    ],
}

# Approximate NDBC buoy locations (offshore San Diego)
BUOYS: dict[str, dict] = {
    "46232": {"name": "NDBC 46232 · Point Loma South", "lat": 32.748, "lon": -117.373},
    "46254": {"name": "NDBC 46254 · Mission Bay West",  "lat": 32.748, "lon": -117.487},
}

SURF_GUIDES: dict[str, str] = {
    "la_jolla_shores": (
        "La Jolla Shores is a long, sandy beach break suitable for all skill levels. "
        "Best conditions arrive with WNW to NW swells hitting the exposed beach. "
        "The underwater canyon to the north can focus swell energy on larger days. "
        "Morning glass-offs before the onshore sea breeze kicks in (typically 11am–noon) "
        "provide the cleanest conditions."
    ),
    "blacks": (
        "Blacks Beach, below the Torrey Pines cliffs, is San Diego's premier big-wave venue. "
        "Access via a steep trail. A powerful beach break with peaks up and down the beach. "
        "Best on larger NW swells with light offshore winds. "
        "The cliffs provide some wind protection."
    ),
    "pb_point": (
        "Pacific Beach Point is a consistent beach break that handles a variety of swell directions. "
        "The jetty at the south end creates a semi-sheltered pocket that holds shape in moderate onshore conditions. "
        "Best at mid-tide on W to NW swells. Popular and often crowded on weekends."
    ),
    "ocean_beach": (
        "Ocean Beach Pier creates a sandbar generating quality peaks on either side. "
        "The pier provides some protection from direct wind. Works best on W and WNW swells. "
        "Watch for rip currents near the pier structure. Best surfing on an incoming tide."
    ),
    "sunset_cliffs": (
        "Sunset Cliffs is a series of rocky reef breaks along the Point Loma coastline. "
        "Multiple takeoff spots ranging from beginner-friendly to heavy slabs. "
        "S to SW swells activate the southern-facing reefs. NW swells light up the more exposed breaks. "
        "Heavy water — not for beginners."
    ),
    "imperial_beach": (
        "Imperial Beach, San Diego's southernmost beach, offers quality surf on S swells "
        "blocked elsewhere in the county. The pier provides a sandbar. "
        "Water quality can be affected by the Tijuana River outflow — check advisories before paddling out. "
        "Best on WNW to SW swells."
    ),
}

COMPASS = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]

# ── DATA HELPERS ─────────────────────────────────────────────────────────────

def _rating_score(wvht_m: float, dpd: float, wind_mph: float, wind_deg: float) -> str:
    if any(np.isnan(v) for v in [wvht_m, dpd, wind_mph, wind_deg]):
        return "poor"
    offshore = 45 <= (wind_deg % 360) <= 135
    ft = wvht_m * 3.281
    if ft >= 6 and dpd >= 14 and wind_mph <= 8 and offshore:
        return "epic"
    if 4 <= ft < 10 and dpd >= 13 and wind_mph <= 10 and offshore:
        return "great"
    if 3 <= ft < 10 and dpd >= 10 and wind_mph <= 15:
        return "good"
    if 2 <= ft < 6:
        return "fair"
    if 1 <= ft < 3 and dpd >= 8:
        return "poor_fair"
    return "poor"


def _rating_label(rating: str) -> str:
    return {"epic": "EPIC", "great": "GOOD", "good": "FAIR TO GOOD",
            "fair": "FAIR", "poor_fair": "POOR TO FAIR", "poor": "POOR"}.get(rating, "POOR")


def _wind_compass(deg: float) -> str:
    return COMPASS[round(deg / 22.5) % 16]


def generate_forecast(break_id: str, hours: int = 48) -> pd.DataFrame:
    """Synthetic 48-hour forecast. Replace body with live ETL data when ready."""
    rng = np.random.default_rng(abs(hash(break_id)) % 2**31)
    now = datetime.now(tz=timezone.utc).replace(minute=0, second=0, microsecond=0)
    times = [now + timedelta(hours=i) for i in range(hours)]
    t = np.linspace(0, 4 * np.pi, hours)

    wvht = np.clip(0.7 + 0.35 * np.sin(t) + 0.15 * np.sin(2.3 * t) + rng.normal(0, 0.04, hours), 0.3, 2.5)
    dpd  = np.clip(12 + 3 * np.sin(t / 2) + rng.normal(0, 0.3, hours), 7, 20)
    wspd = np.clip(8 + 6 * np.sin(t + np.pi / 4) + rng.normal(0, 0.5, hours), 1, 25)
    wdir = (280 + 30 * np.sin(t / 3) + rng.normal(0, 5, hours)) % 360
    tide = 0.8 + 0.7 * np.sin(2 * np.pi * np.arange(hours) / 12.4)

    ratings = [_rating_score(w, d, s, dr) for w, d, s, dr in zip(wvht, dpd, wspd, wdir)]

    return pd.DataFrame({
        "time":         times,
        "wvht_m":       wvht,
        "wvht_ft_lo":   wvht * 3.281 * 0.85,
        "wvht_ft_hi":   wvht * 3.281 * 1.15,
        "dpd":          dpd,
        "wind_mph":     wspd,
        "wind_deg":     wdir,
        "tide_m":       tide,
        "rating":       ratings,
    })


def generate_buoy_data(hours: int = 72) -> pd.DataFrame:
    """Synthetic buoy timeseries. Replace with fetch_buoy_swell() when ETL is ready."""
    rng = np.random.default_rng(99)
    now = datetime.now(tz=timezone.utc)
    times = [now - timedelta(hours=i) for i in range(hours, 0, -1)]
    t = np.linspace(0, 2 * np.pi, hours)

    base_wvht = 0.6 + 0.4 * np.sin(t) + rng.normal(0, 0.04, hours)
    base_dpd  = 12 + 4 * np.sin(t + np.pi / 4) + rng.normal(0, 0.3, hours)
    base_mwd  = (280 + 20 * np.sin(t / 2)) % 360

    dfs = []
    for station in NDBC_STATIONS:
        noise = rng.normal(0, 0.04, hours)
        dfs.append(pd.DataFrame({
            "timestamp_utc": times,
            "station":       station,
            "WVHT": np.clip(base_wvht + noise, 0.2, 3.0),
            "DPD":  np.clip(base_dpd  + rng.normal(0, 0.2, hours), 5, 22),
            "MWD":  base_mwd,
        }))
    return pd.concat(dfs, ignore_index=True)


def _try_live_data() -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    """Attempt to load live ETL data; return (buoy_df, None) or (None, None)."""
    try:
        from etl.fetch_buoy import fetch_buoy_swell
        buoy = fetch_buoy_swell(days=3, use_cache=True)
        if not buoy.empty:
            return buoy, None
    except Exception:
        pass
    return None, None


# ── CHART BUILDERS ────────────────────────────────────────────────────────────

def _forecast_chart(df: pd.DataFrame) -> go.Figure:
    colors = [RATING_COLORS[r] for r in df["rating"]]
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df["time"],
        y=df["wvht_ft_hi"],
        name="Wave Height",
        marker_color=colors,
        marker_opacity=0.85,
        width=1000 * 60 * 50,
    ))
    fig.add_trace(go.Scatter(
        x=df["time"], y=df["tide_m"],
        name="Tide (m)", mode="lines",
        line=dict(color=ACCENT, width=2),
        yaxis="y2",
    ))
    fig.update_layout(
        plot_bgcolor=SURFACE, paper_bgcolor=SURFACE,
        margin=dict(l=40, r=55, t=8, b=36),
        height=240,
        showlegend=False,
        bargap=0.08,
        xaxis=dict(
            showgrid=False,
            tickformat="%-I%p",
            nticks=12,
            tickfont=dict(size=10, color=TEXT_MUTED, family=FONT),
        ),
        yaxis=dict(
            title="ft", showgrid=True, gridcolor="#f0f0f0",
            tickfont=dict(size=10, color=TEXT_MUTED, family=FONT),
            title_font=dict(size=11, color=TEXT_MUTED),
            rangemode="tozero",
        ),
        yaxis2=dict(
            title="Tide m", overlaying="y", side="right",
            showgrid=False,
            tickfont=dict(size=10, color=ACCENT, family=FONT),
            title_font=dict(size=11, color=ACCENT),
        ),
    )
    return fig


_FILL_COLORS: dict[str, str] = {
    ACCENT:    "rgba(29, 155, 240, 0.12)",
    "#00c97f": "rgba(0, 201, 127, 0.12)",
}


def _buoy_chart(x, y, color: str, title: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=y, mode="lines",
        line=dict(color=color, width=2),
        fill="tozeroy",
        fillcolor=_FILL_COLORS.get(color, "rgba(100, 100, 100, 0.12)"),
    ))
    fig.update_layout(
        plot_bgcolor=SURFACE, paper_bgcolor=SURFACE,
        margin=dict(l=28, r=8, t=28, b=28),
        height=130,
        showlegend=False,
        title=dict(text=title, font=dict(size=11, color=TEXT_MUTED, family=FONT), x=0.02, y=0.97),
        xaxis=dict(showgrid=False, tickformat="%-I%p", nticks=6,
                   tickfont=dict(size=9, color="#aaa", family=FONT)),
        yaxis=dict(showgrid=True, gridcolor="#f2f2f2",
                   tickfont=dict(size=9, color="#aaa", family=FONT),
                   fixedrange=True, rangemode="tozero"),
    )
    return fig


# ── COMPONENT BUILDERS ────────────────────────────────────────────────────────

def _navbar() -> html.Div:
    return html.Div(
        style={
            "background": NAV_BG, "height": "52px",
            "display": "flex", "alignItems": "center", "padding": "0 24px",
            "position": "sticky", "top": "0", "zIndex": "1000",
            "borderBottom": f"1px solid {NAV_BORDER}",
        },
        children=[
            html.Span("SurfCast SD", style={
                "color": BRAND, "fontWeight": "700", "fontSize": "20px",
                "letterSpacing": "-0.3px", "marginRight": "32px", "fontFamily": FONT,
            }),
            html.Div([
                html.A("Cams & Forecast", href="#forecast", style={"color": NAV_DIM, "marginRight": "20px", "textDecoration": "none", "fontSize": "14px", "fontFamily": FONT}),
                html.A("Buoy Data",       href="#buoy",     style={"color": NAV_DIM, "marginRight": "20px", "textDecoration": "none", "fontSize": "14px", "fontFamily": FONT}),
                html.A("About",           href="#guide",    style={"color": NAV_DIM, "textDecoration": "none", "fontSize": "14px", "fontFamily": FONT}),
            ], style={"display": "flex", "alignItems": "center", "flex": "1"}),
            html.Span("San Diego, CA", style={"color": NAV_MUTED, "fontSize": "13px", "fontFamily": FONT}),
        ],
    )


def _break_header(break_id: str, fc: pd.DataFrame) -> html.Div:
    info   = BREAKS[break_id]
    rating = fc.iloc[0]["rating"]
    color  = RATING_COLORS[rating]
    return html.Div(
        style={"background": NAV_BG, "padding": "16px 24px 0", "borderBottom": f"1px solid {NAV_BORDER}"},
        children=[
            html.H1(info["name"], style={
                "color": NAV_TEXT, "fontSize": "26px", "fontWeight": "700",
                "margin": "0 0 2px", "fontFamily": FONT, "letterSpacing": "-0.3px",
            }),
            html.Div(info["loc"], style={"color": NAV_MUTED, "fontSize": "13px", "marginBottom": "14px", "fontFamily": FONT}),
            html.Div([
                _tab("Report & Forecast", active=True,  color=color),
                _tab("Charts",            active=False, color=color),
                _tab("Surf Guide",        active=False, color=color),
            ], style={"display": "flex"}),
        ],
    )


def _tab(label: str, active: bool, color: str) -> html.Div:
    return html.Div(label, style={
        "color":        NAV_TEXT if active else NAV_MUTED,
        "fontWeight":   "600"    if active else "400",
        "fontSize":     "14px",
        "paddingBottom":"10px",
        "borderBottom": f"2px solid {color}" if active else "2px solid transparent",
        "marginRight":  "24px",
        "cursor":       "pointer",
        "fontFamily":   FONT,
    })


def _surf_map(active_break: str) -> html.Div:
    markers = []

    for bid, info in BREAKS.items():
        fc     = generate_forecast(bid, hours=1)
        rating = fc.iloc[0]["rating"]
        hi     = fc.iloc[0]["wvht_ft_hi"]
        lo     = fc.iloc[0]["wvht_ft_lo"]
        color  = RATING_COLORS[rating]
        active = bid == active_break

        popup = dl.Popup(
            html.Div([
                html.Div(info["name"], style={
                    "fontWeight": "700", "fontSize": "13px", "marginBottom": "6px", "fontFamily": FONT,
                }),
                html.Div(f"{lo:.0f}–{hi:.0f} ft", style={
                    "fontSize": "22px", "fontWeight": "700", "color": TEXT, "fontFamily": FONT,
                    "fontVariantNumeric": "tabular-nums",
                }),
                html.Div(_rating_label(rating), style={
                    "color": color, "fontSize": "11px", "fontWeight": "700",
                    "letterSpacing": "0.4px", "marginBottom": "8px", "fontFamily": FONT,
                }),
                html.Div("Click to load conditions →", style={
                    "color": ACCENT, "fontSize": "10px", "fontFamily": FONT,
                }),
            ], style={"minWidth": "140px", "padding": "2px"}),
            autoPan=False,
        )

        markers.append(dl.Polygon(
            id={"type": "break-marker", "index": bid},
            positions=BREAK_POLYGONS[bid],
            color=color,
            weight=2.5 if active else 1.5,
            fillColor=color,
            fillOpacity=0.45 if active else 0.18,
            n_clicks=0,
            children=[
                popup,
                dl.Tooltip(
                    f"{info['name']}  ·  {lo:.0f}–{hi:.0f} ft  ·  {_rating_label(rating)}",
                    sticky=True,
                ),
            ],
        ))

    # NDBC buoy markers — dashed border, informational only
    for station, binfo in BUOYS.items():
        markers.append(dl.CircleMarker(
            center=[binfo["lat"], binfo["lon"]],
            radius=6,
            color=ACCENT,
            weight=1.5,
            fillColor=ACCENT,
            fillOpacity=0.25,
            dashArray="5,4",
            children=dl.Tooltip(binfo["name"]),
        ))

    return html.Div(
        style={
            "background": SURFACE,
            "border": f"1px solid {BORDER}",
            "borderRadius": "8px",
            "overflow": "hidden",
            "marginBottom": "24px",
        },
        children=[
            html.Div(
                style={
                    "padding": "12px 16px", "borderBottom": f"1px solid {BORDER}",
                    "display": "flex", "justifyContent": "space-between", "alignItems": "center",
                },
                children=[
                    html.Div("San Diego Coast", style={
                        "fontWeight": "700", "fontSize": "14px", "color": TEXT, "fontFamily": FONT,
                    }),
                    html.Div(
                        "● Surf breaks  ○ NDBC buoys  ·  Click a break to load its data",
                        style={"color": TEXT_MUTED, "fontSize": "12px", "fontFamily": FONT},
                    ),
                ],
            ),
            dl.Map(
                center=[32.75, -117.26],
                zoom=11,
                style={"height": "400px", "width": "100%"},
                children=[
                    dl.TileLayer(
                        url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
                        attribution=(
                            '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                            ' &copy; <a href="https://carto.com">CARTO</a>'
                        ),
                        maxZoom=19,
                    ),
                ] + markers,
            ),
        ],
    )


def _nearby_spots(current_break: str) -> html.Div:
    cards = []
    for bid, info in BREAKS.items():
        fc     = generate_forecast(bid, hours=1)
        rating = fc.iloc[0]["rating"]
        hi     = fc.iloc[0]["wvht_ft_hi"]
        lo     = fc.iloc[0]["wvht_ft_lo"]
        color  = RATING_COLORS[rating]
        active = bid == current_break
        cards.append(html.Div(
            id={"type": "spot-card", "index": bid},
            n_clicks=0,
            style={
                "minWidth": "130px", "flexShrink": "0",
                "background": "#1e2d3a" if active else "#162231",
                "border":     f"1px solid {color}" if active else f"1px solid {NAV_BORDER}",
                "borderRadius": "6px", "padding": "10px 14px",
                "marginRight": "8px", "cursor": "pointer",
            },
            children=[
                html.Div(
                    f"{'● ' if active else ''}{info['name']}",
                    style={"color": NAV_TEXT if active else NAV_DIM, "fontSize": "12px",
                           "fontWeight": "600", "marginBottom": "4px", "fontFamily": FONT},
                ),
                html.Div(f"{lo:.0f}–{hi:.0f} ft", style={
                    "color": NAV_TEXT, "fontSize": "15px", "fontWeight": "700", "fontFamily": FONT,
                }),
                html.Div(_rating_label(rating), style={
                    "color": color, "fontSize": "10px", "fontWeight": "700",
                    "letterSpacing": "0.4px", "fontFamily": FONT,
                }),
            ],
        ))
    return html.Div(
        style={"background": NAV_BG, "padding": "12px 24px", "borderBottom": f"1px solid {NAV_BORDER}"},
        children=[
            html.Div("Nearby Spots", style={
                "color": NAV_MUTED, "fontSize": "11px", "fontWeight": "600",
                "letterSpacing": "0.5px", "marginBottom": "10px", "fontFamily": FONT,
                "textTransform": "uppercase",
            }),
            html.Div(cards, style={"display": "flex", "overflowX": "auto", "paddingBottom": "4px"}),
        ],
    )


def _conditions_card(fc: pd.DataFrame) -> html.Div:
    row    = fc.iloc[0]
    rating = row["rating"]
    color  = RATING_COLORS[rating]
    lo, hi = row["wvht_ft_lo"], row["wvht_ft_hi"]
    tide   = row["tide_m"]
    wind   = row["wind_mph"]
    period = row["dpd"]
    wdir   = row["wind_deg"]
    trend  = "Rising" if np.sin(tide * np.pi) > 0 else "Falling"

    def stat_chip(label: str, value: str, sub: str) -> html.Div:
        return html.Div(
            style={"background": SURFACE_ALT, "borderRadius": "6px", "padding": "12px"},
            children=[
                html.Div(label, style={"color": "#aaa", "fontSize": "10px", "fontWeight": "700",
                                       "letterSpacing": "0.5px", "marginBottom": "4px",
                                       "textTransform": "uppercase", "fontFamily": FONT}),
                html.Div(value, style={"fontSize": "22px", "fontWeight": "700",
                                       "color": TEXT, "fontFamily": FONT,
                                       "fontVariantNumeric": "tabular-nums"}),
                html.Div(sub,   style={"color": TEXT_MUTED, "fontSize": "12px", "fontFamily": FONT}),
            ],
        )

    return html.Div(
        style={"background": SURFACE, "borderRadius": "8px", "border": f"1px solid {BORDER}", "overflow": "hidden"},
        children=[
            html.Div("Current Surf Conditions", style={
                "background": SURFACE_ALT, "padding": "10px 16px",
                "fontSize": "12px", "fontWeight": "700", "color": TEXT_MUTED,
                "letterSpacing": "0.5px", "borderBottom": f"1px solid {BORDER}",
                "fontFamily": FONT, "textTransform": "uppercase",
            }),
            html.Div(
                style={"padding": "16px"},
                children=[
                    html.Div(
                        style={"display": "flex", "alignItems": "flex-end", "marginBottom": "16px"},
                        children=[
                            html.Div(f"{lo:.0f}–{hi:.0f}", style={
                                "fontSize": "48px", "fontWeight": "700", "color": TEXT,
                                "lineHeight": "1", "fontFamily": FONT,
                                "fontVariantNumeric": "tabular-nums",
                            }),
                            html.Div(
                                style={"marginLeft": "8px", "paddingBottom": "4px"},
                                children=[
                                    html.Div("ft", style={"color": TEXT_MUTED, "fontSize": "16px", "fontFamily": FONT}),
                                    html.Div(_rating_label(rating), style={
                                        "background": color, "color": "#fff",
                                        "fontSize": "10px", "fontWeight": "700",
                                        "padding": "2px 8px", "borderRadius": "3px",
                                        "letterSpacing": "0.5px", "fontFamily": FONT,
                                    }),
                                ],
                            ),
                        ],
                    ),
                    html.Div(
                        style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "10px"},
                        children=[
                            stat_chip("Tide",     f"{tide:.1f}m",         trend),
                            stat_chip("Wind",     f"{wind:.0f} mph",      _wind_compass(wdir)),
                            stat_chip("Period",   f"{period:.0f}s",       "Dominant"),
                            stat_chip("Swell Dir",f"{wdir % 360:.0f}°",  _wind_compass(wdir)),
                        ],
                    ),
                ],
            ),
        ],
    )


def _rating_row(fc: pd.DataFrame) -> html.Div:
    """Colored dot row for the next 8 hours (matches Surfline's rating strip)."""
    slots = fc.head(8)
    cells = []
    for _, row in slots.iterrows():
        color = RATING_COLORS[row["rating"]]
        hour  = row["time"].strftime("%I%p").lstrip("0").lower()
        cells.append(html.Div(
            style={
                "flex": "1", "textAlign": "center", "padding": "8px 4px",
                "borderRight": f"1px solid {BORDER}",
            },
            children=[
                html.Div(hour, style={"color": TEXT_MUTED, "fontSize": "10px",
                                      "marginBottom": "4px", "fontFamily": FONT}),
                html.Div("●",  style={"color": color, "fontSize": "20px", "lineHeight": "1"}),
                html.Div(_rating_label(row["rating"]), style={
                    "color": color, "fontSize": "9px", "fontWeight": "700",
                    "letterSpacing": "0.3px", "marginTop": "3px", "fontFamily": FONT,
                }),
            ],
        ))
    return html.Div(
        style={
            "display": "flex",
            "borderTop": f"1px solid {BORDER}",
            "borderBottom": f"1px solid {BORDER}",
        },
        children=[
            html.Div("Today", style={
                "width": "60px", "flexShrink": "0",
                "color": TEXT_MUTED, "fontSize": "11px", "padding": "8px",
                "borderRight": f"1px solid {BORDER}", "fontFamily": FONT,
                "display": "flex", "alignItems": "center",
            }),
        ] + cells,
    )


def _forecast_section(break_id: str, fc: pd.DataFrame) -> html.Div:
    name = BREAKS[break_id]["name"]
    return html.Div(
        id="forecast",
        style={
            "background": SURFACE, "border": f"1px solid {BORDER}",
            "borderRadius": "8px", "overflow": "hidden",
        },
        children=[
            html.Div(
                style={
                    "padding": "12px 16px", "borderBottom": f"1px solid {BORDER}",
                    "display": "flex", "justifyContent": "space-between", "alignItems": "center",
                },
                children=[
                    html.Div(f"{name} Surf Forecast", style={
                        "fontWeight": "700", "fontSize": "14px", "color": TEXT, "fontFamily": FONT,
                    }),
                    html.Div("48-hour  ·  NDBC + NWS", style={
                        "color": TEXT_MUTED, "fontSize": "12px", "fontFamily": FONT,
                    }),
                ],
            ),
            _rating_row(fc),
            dcc.Graph(
                figure=_forecast_chart(fc),
                config={"displayModeBar": False},
                style={"margin": "0"},
            ),
        ],
    )


def _buoy_section(buoy_df: pd.DataFrame) -> html.Div:
    cards = []
    for station, station_name in NDBC_STATIONS.items():
        sdf = (
            buoy_df[buoy_df["station"] == station]
            .sort_values("timestamp_utc")
            .tail(48)
        )
        if sdf.empty:
            continue

        hs_latest  = sdf["WVHT"].iloc[-1] * 3.281
        dpd_latest = sdf["DPD"].iloc[-1]

        fig_hs = _buoy_chart(
            sdf["timestamp_utc"], sdf["WVHT"] * 3.281,
            color=ACCENT, title="Wave Height (ft)",
        )
        fig_pd = _buoy_chart(
            sdf["timestamp_utc"], sdf["DPD"],
            color="#00c97f", title="Dominant Period (s)",
        )

        cards.append(html.Div(
            style={
                "background": SURFACE, "border": f"1px solid {BORDER}",
                "borderRadius": "8px", "overflow": "hidden", "marginBottom": "16px",
            },
            children=[
                html.Div(
                    style={
                        "padding": "12px 16px", "borderBottom": f"1px solid {BORDER}",
                        "display": "flex", "justifyContent": "space-between", "alignItems": "center",
                    },
                    children=[
                        html.Div([
                            html.Div(f"NDBC {station}", style={
                                "fontWeight": "700", "fontSize": "14px", "color": TEXT, "fontFamily": FONT,
                            }),
                            html.Div(station_name, style={
                                "color": TEXT_MUTED, "fontSize": "12px", "fontFamily": FONT,
                            }),
                        ]),
                        html.Div([
                            html.Span(f"Hs {hs_latest:.1f} ft", style={
                                "color": ACCENT, "fontSize": "13px", "fontWeight": "600",
                                "marginRight": "12px", "fontFamily": FONT,
                            }),
                            html.Span(f"DPD {dpd_latest:.0f}s", style={
                                "color": "#00c97f", "fontSize": "13px", "fontWeight": "600", "fontFamily": FONT,
                            }),
                        ]),
                    ],
                ),
                html.Div(
                    style={
                        "display": "grid", "gridTemplateColumns": "1fr 1fr",
                        "gap": "1px", "background": BORDER,
                    },
                    children=[
                        html.Div(style={"background": SURFACE}, children=[
                            dcc.Graph(figure=fig_hs, config={"displayModeBar": False}),
                        ]),
                        html.Div(style={"background": SURFACE}, children=[
                            dcc.Graph(figure=fig_pd, config={"displayModeBar": False}),
                        ]),
                    ],
                ),
            ],
        ))

    return html.Div(
        id="buoy",
        style={"padding": "0 24px"},
        children=[
            html.Div("Nearby Buoys", style={
                "fontSize": "18px", "fontWeight": "700", "color": TEXT,
                "margin": "24px 0 16px", "fontFamily": FONT,
            }),
        ] + cards,
    )


def _surf_guide(break_id: str) -> html.Div:
    return html.Div(
        id="guide",
        style={"padding": "24px", "borderTop": f"1px solid {BORDER}"},
        children=[
            html.Div("Surf Guide", style={
                "fontSize": "18px", "fontWeight": "700", "color": TEXT,
                "marginBottom": "12px", "fontFamily": FONT,
            }),
            html.P(SURF_GUIDES.get(break_id, ""), style={
                "color": "#444", "fontSize": "14px", "lineHeight": "1.75",
                "fontFamily": FONT, "maxWidth": "720px", "margin": "0",
            }),
        ],
    )


def _footer() -> html.Div:
    return html.Div(
        style={"background": NAV_BG, "padding": "32px 24px", "marginTop": "48px", "textAlign": "center"},
        children=[
            html.Div("SurfCast SD", style={
                "color": BRAND, "fontWeight": "700", "fontSize": "18px",
                "marginBottom": "8px", "fontFamily": FONT,
            }),
            html.Div("UCSD Surf & Sail Club · Data: NDBC, NOAA, NWS", style={
                "color": "#4a5568", "fontSize": "12px", "fontFamily": FONT,
            }),
        ],
    )


# ── PAGE ASSEMBLY ─────────────────────────────────────────────────────────────

def _page(break_id: str) -> html.Div:
    fc      = generate_forecast(break_id)
    live, _ = _try_live_data()
    buoy_df = live if live is not None else generate_buoy_data()

    return html.Div([
        _break_header(break_id, fc),
        _nearby_spots(break_id),

        html.Div(
            style={"maxWidth": "1400px", "margin": "0 auto", "padding": "24px 24px 0"},
            children=[
                _surf_map(break_id),
                html.Div(
                    style={"display": "grid", "gridTemplateColumns": "1fr 320px", "gap": "24px"},
                    children=[_forecast_section(break_id, fc), _conditions_card(fc)],
                ),
            ],
        ),

        html.Div(
            style={"maxWidth": "1400px", "margin": "0 auto"},
            children=[_buoy_section(buoy_df)],
        ),

        html.Div(
            style={"maxWidth": "1400px", "margin": "0 auto"},
            children=[_surf_guide(break_id)],
        ),

        _footer(),
    ])


# ── APP ───────────────────────────────────────────────────────────────────────

app = Dash(
    __name__,
    external_stylesheets=[
        "https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@300;400;600;700&display=swap",
    ],
    title="SurfCast SD",
    suppress_callback_exceptions=True,
)
server = app.server  # expose for gunicorn

app.layout = html.Div(
    style={"background": BG, "minHeight": "100vh", "fontFamily": FONT},
    children=[
        _navbar(),
        html.Div(
            style={
                "background": SURFACE, "borderBottom": f"1px solid {BORDER}",
                "padding": "6px 24px",
            },
            children=[
                dcc.Dropdown(
                    id="break-select",
                    options=[{"label": v["name"], "value": k} for k, v in BREAKS.items()],
                    value="la_jolla_shores",
                    clearable=False,
                    style={"maxWidth": "280px", "fontSize": "14px", "fontFamily": FONT},
                ),
            ],
        ),
        html.Div(id="page-content"),
        dcc.Interval(id="tick", interval=60 * 60 * 1000, n_intervals=0),
    ],
)


@app.callback(
    Output("page-content", "children"),
    Input("break-select", "value"),
    Input("tick", "n_intervals"),
)
def render_page(break_id: str, _: int) -> html.Div:
    return _page(break_id or "la_jolla_shores")


@app.callback(
    Output("break-select", "value"),
    Input({"type": "break-marker", "index": ALL}, "n_clicks"),
    Input({"type": "spot-card",    "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def select_break_from_click(marker_clicks: list, spot_clicks: list) -> str:
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    prop_id = ctx.triggered[0]["prop_id"].split(".")[0]
    try:
        return json.loads(prop_id)["index"]
    except Exception:
        raise PreventUpdate


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=True)
