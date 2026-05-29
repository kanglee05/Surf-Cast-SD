"use client"

import { useState, Suspense } from "react"
import { useSearchParams } from "next/navigation"
import Link from "next/link"
import dynamic from "next/dynamic"
import { BREAKS, RATING_COLORS, RATING_LABELS, generateForecast, windCompass, type BreakId } from "@/lib/surf-data"

const SurfMap = dynamic(() => import("@/components/SurfMap"), { ssr: false, loading: () => (
  <div style={{ height: 400, background: "#f5f5f5", borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", color: "#666", marginBottom: 24 }}>Loading map…</div>
) })

const BRAND = "#e1fcad"
const NAV_BG = "#0f1923"
const NAV_BORDER = "#1e2d3a"
const NAV_MUTED = "#8892b0"
const NAV_DIM = "#ccd6f6"
const BG = "#f5f5f5"
const SURFACE = "#ffffff"
const BORDER = "#e0e0e0"
const TEXT = "#1a1a1a"
const TEXT_MUTED = "#666666"
const ACCENT = "#1d9bf0"

function DashboardInner() {
  const searchParams = useSearchParams()
  const initialBreak = (searchParams.get("break") as BreakId) || "la_jolla_shores"
  const [activeBreak, setActiveBreak] = useState<BreakId>(initialBreak)

  const fc = generateForecast(activeBreak)
  const current = fc[0]
  const breakInfo = BREAKS[activeBreak]
  const ratingColor = RATING_COLORS[current.rating]

  const hourLabel = (d: Date) => d.toLocaleTimeString([], { hour: "numeric", hour12: true })

  return (
    <div style={{ background: BG, minHeight: "100vh", fontFamily: "var(--font-sans), sans-serif" }}>

      {/* Navbar */}
      <nav style={{ background: NAV_BG, height: 52, display: "flex", alignItems: "center", padding: "0 24px", position: "sticky", top: 0, zIndex: 1000, borderBottom: `1px solid ${NAV_BORDER}` }}>
        <Link href="/" style={{ color: BRAND, fontWeight: 700, fontSize: 20, letterSpacing: "-0.3px", marginRight: 32, textDecoration: "none" }}>
          SurfCast SD
        </Link>
        <div style={{ display: "flex", alignItems: "center", flex: 1, gap: 20 }}>
          <a href="#forecast" style={{ color: NAV_DIM, textDecoration: "none", fontSize: 14 }}>Cams &amp; Forecast</a>
          <a href="#buoy" style={{ color: NAV_DIM, textDecoration: "none", fontSize: 14 }}>Buoy Data</a>
          <a href="#guide" style={{ color: NAV_DIM, textDecoration: "none", fontSize: 14 }}>About</a>
        </div>
        <span style={{ color: NAV_MUTED, fontSize: 13 }}>San Diego, CA</span>
      </nav>

      {/* Break header */}
      <div style={{ background: NAV_BG, padding: "16px 24px 0", borderBottom: `1px solid ${NAV_BORDER}` }}>
        <h1 style={{ color: "#fff", fontSize: 26, fontWeight: 700, margin: "0 0 2px", letterSpacing: "-0.3px" }}>{breakInfo.name}</h1>
        <div style={{ color: NAV_MUTED, fontSize: 13, marginBottom: 14 }}>{breakInfo.loc}</div>
        <div style={{ display: "flex", gap: 0 }}>
          {["Report & Forecast", "Charts", "Surf Guide"].map((tab, i) => (
            <div key={tab} style={{ color: i === 0 ? "#fff" : NAV_MUTED, fontWeight: i === 0 ? 600 : 400, fontSize: 14, paddingBottom: 10, borderBottom: i === 0 ? `2px solid ${ratingColor}` : "2px solid transparent", marginRight: 24, cursor: "pointer" }}>
              {tab}
            </div>
          ))}
        </div>
      </div>

      {/* Nearby spots */}
      <div style={{ background: NAV_BG, padding: "12px 24px", borderBottom: `1px solid ${NAV_BORDER}` }}>
        <div style={{ color: NAV_MUTED, fontSize: 11, fontWeight: 600, letterSpacing: "0.5px", marginBottom: 10, textTransform: "uppercase" }}>Nearby Spots</div>
        <div style={{ display: "flex", overflowX: "auto", gap: 8, paddingBottom: 4 }}>
          {(Object.keys(BREAKS) as BreakId[]).map((bid) => {
            const row = generateForecast(bid, 1)[0]
            const color = RATING_COLORS[row.rating]
            const active = bid === activeBreak
            return (
              <button
                key={bid}
                onClick={() => setActiveBreak(bid)}
                style={{ minWidth: 130, flexShrink: 0, background: active ? "#1e2d3a" : "#162231", border: active ? `1px solid ${color}` : `1px solid ${NAV_BORDER}`, borderRadius: 6, padding: "10px 14px", cursor: "pointer", textAlign: "left" }}
              >
                <div style={{ color: active ? "#fff" : NAV_DIM, fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
                  {active ? "● " : ""}{BREAKS[bid].name}
                </div>
                <div style={{ color: "#fff", fontSize: 15, fontWeight: 700 }}>
                  {Math.round(row.wvhtFtLo)}–{Math.round(row.wvhtFtHi)} ft
                </div>
                <div style={{ color, fontSize: 10, fontWeight: 700, letterSpacing: "0.4px" }}>
                  {RATING_LABELS[row.rating]}
                </div>
              </button>
            )
          })}
        </div>
      </div>

      {/* Break selector */}
      <div style={{ background: SURFACE, borderBottom: `1px solid ${BORDER}`, padding: "6px 24px" }}>
        <select
          value={activeBreak}
          onChange={(e) => setActiveBreak(e.target.value as BreakId)}
          style={{ maxWidth: 280, fontSize: 14, padding: "6px 10px", borderRadius: 6, border: `1px solid ${BORDER}`, background: SURFACE, color: TEXT }}
        >
          {(Object.keys(BREAKS) as BreakId[]).map((bid) => (
            <option key={bid} value={bid}>{BREAKS[bid].name}</option>
          ))}
        </select>
      </div>

      {/* Main content */}
      <div style={{ maxWidth: 1400, margin: "0 auto", padding: "24px 24px 0" }}>

        {/* Map */}
        <SurfMap activeBreak={activeBreak} onBreakSelect={setActiveBreak} />

        {/* Forecast + conditions side by side */}
        <div id="forecast" style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 24, marginBottom: 24 }}>

          {/* Forecast card */}
          <div style={{ background: SURFACE, borderRadius: 8, border: `1px solid ${BORDER}`, overflow: "hidden" }}>
            <div style={{ padding: "12px 16px", borderBottom: `1px solid ${BORDER}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ fontWeight: 700, fontSize: 14, color: TEXT }}>{breakInfo.name} Surf Forecast</div>
              <div style={{ color: TEXT_MUTED, fontSize: 12 }}>48-hour · NDBC + NWS</div>
            </div>

            {/* Rating strip */}
            <div style={{ display: "flex", borderTop: `1px solid ${BORDER}`, borderBottom: `1px solid ${BORDER}` }}>
              <div style={{ width: 60, flexShrink: 0, color: TEXT_MUTED, fontSize: 11, padding: 8, borderRight: `1px solid ${BORDER}`, display: "flex", alignItems: "center" }}>Today</div>
              {fc.slice(0, 8).map((row, i) => (
                <div key={i} style={{ flex: 1, textAlign: "center", padding: "8px 4px", borderRight: `1px solid ${BORDER}` }}>
                  <div style={{ color: TEXT_MUTED, fontSize: 10, marginBottom: 4 }}>{hourLabel(row.time)}</div>
                  <div style={{ color: RATING_COLORS[row.rating], fontSize: 20, lineHeight: 1 }}>●</div>
                  <div style={{ color: RATING_COLORS[row.rating], fontSize: 9, fontWeight: 700, letterSpacing: "0.3px", marginTop: 3 }}>{RATING_LABELS[row.rating]}</div>
                </div>
              ))}
            </div>

            {/* Simple bar chart (pure CSS, no library needed for MVP) */}
            <div style={{ padding: "16px 16px 8px" }}>
              <div style={{ display: "flex", alignItems: "flex-end", gap: 2, height: 120 }}>
                {fc.slice(0, 24).map((row, i) => (
                  <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "flex-end", height: "100%" }}>
                    <div
                      style={{
                        width: "100%",
                        background: RATING_COLORS[row.rating],
                        opacity: 0.8,
                        borderRadius: "2px 2px 0 0",
                        height: `${(row.wvhtFtHi / 10) * 100}%`,
                        minHeight: 4,
                      }}
                    />
                  </div>
                ))}
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6 }}>
                {[0, 6, 12, 18, 23].map((i) => (
                  <span key={i} style={{ color: TEXT_MUTED, fontSize: 10 }}>{hourLabel(fc[i].time)}</span>
                ))}
              </div>
            </div>
          </div>

          {/* Conditions card */}
          <div style={{ background: SURFACE, borderRadius: 8, border: `1px solid ${BORDER}`, overflow: "hidden" }}>
            <div style={{ background: "#f8f9fa", padding: "10px 16px", fontSize: 12, fontWeight: 700, color: TEXT_MUTED, letterSpacing: "0.5px", borderBottom: `1px solid ${BORDER}`, textTransform: "uppercase" }}>
              Current Surf Conditions
            </div>
            <div style={{ padding: 16 }}>
              <div style={{ display: "flex", alignItems: "flex-end", marginBottom: 16 }}>
                <div style={{ fontSize: 48, fontWeight: 700, color: TEXT, lineHeight: 1, fontVariantNumeric: "tabular-nums" }}>
                  {Math.round(current.wvhtFtLo)}–{Math.round(current.wvhtFtHi)}
                </div>
                <div style={{ marginLeft: 8, paddingBottom: 4 }}>
                  <div style={{ color: TEXT_MUTED, fontSize: 16 }}>ft</div>
                  <div style={{ background: ratingColor, color: "#fff", fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 3, letterSpacing: "0.5px" }}>
                    {RATING_LABELS[current.rating]}
                  </div>
                </div>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                {[
                  { label: "Tide",      value: `${current.tideM.toFixed(1)}m`,             sub: current.tideM > 1 ? "Rising" : "Falling" },
                  { label: "Wind",      value: `${Math.round(current.windMph)} mph`,         sub: windCompass(current.windDeg) },
                  { label: "Period",    value: `${Math.round(current.dpd)}s`,               sub: "Dominant" },
                  { label: "Swell Dir", value: `${Math.round(current.windDeg % 360)}°`,     sub: windCompass(current.windDeg) },
                ].map(({ label, value, sub }) => (
                  <div key={label} style={{ background: "#f8f9fa", borderRadius: 6, padding: 12 }}>
                    <div style={{ color: "#aaa", fontSize: 10, fontWeight: 700, letterSpacing: "0.5px", marginBottom: 4, textTransform: "uppercase" }}>{label}</div>
                    <div style={{ fontSize: 22, fontWeight: 700, color: TEXT, fontVariantNumeric: "tabular-nums" }}>{value}</div>
                    <div style={{ color: TEXT_MUTED, fontSize: 12 }}>{sub}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Surf guide */}
        <div id="guide" style={{ padding: "24px 0 48px", borderTop: `1px solid ${BORDER}` }}>
          <div style={{ fontSize: 18, fontWeight: 700, color: TEXT, marginBottom: 12 }}>Surf Guide</div>
          <p style={{ color: "#444", fontSize: 14, lineHeight: 1.75, maxWidth: 720, margin: 0 }}>
            {SURF_GUIDES[activeBreak]}
          </p>
        </div>
      </div>

      {/* Footer */}
      <div style={{ background: NAV_BG, padding: "32px 24px", marginTop: 48, textAlign: "center" }}>
        <div style={{ color: BRAND, fontWeight: 700, fontSize: 18, marginBottom: 8 }}>SurfCast SD</div>
        <div style={{ color: "#4a5568", fontSize: 12 }}>UCSD Surf &amp; Sail Club · Data: NDBC, NOAA, NWS</div>
      </div>
    </div>
  )
}

const SURF_GUIDES: Record<BreakId, string> = {
  la_jolla_shores: "La Jolla Shores is a long, sandy beach break suitable for all skill levels. Best conditions arrive with WNW to NW swells hitting the exposed beach. Morning glass-offs before the onshore sea breeze kicks in (typically 11am–noon) provide the cleanest conditions.",
  blacks: "Blacks Beach, below the Torrey Pines cliffs, is San Diego's premier big-wave venue. Access via a steep trail. A powerful beach break with peaks up and down the beach. Best on larger NW swells with light offshore winds.",
  pb_point: "Pacific Beach Point is a consistent beach break that handles a variety of swell directions. The jetty at the south end creates a semi-sheltered pocket. Best at mid-tide on W to NW swells. Popular and often crowded on weekends.",
  ocean_beach: "Ocean Beach Pier creates a sandbar generating quality peaks on either side. Works best on W and WNW swells. Watch for rip currents near the pier structure. Best surfing on an incoming tide.",
  sunset_cliffs: "Sunset Cliffs is a series of rocky reef breaks along the Point Loma coastline. S to SW swells activate the southern-facing reefs. NW swells light up the more exposed breaks. Heavy water — not for beginners.",
  imperial_beach: "Imperial Beach, San Diego's southernmost beach, offers quality surf on S swells blocked elsewhere. The pier provides a sandbar. Water quality can be affected by the Tijuana River outflow — check advisories before paddling out.",
}

export default function DashboardPage() {
  return (
    <Suspense fallback={<div style={{ background: "#0f1923", minHeight: "100vh" }} />}>
      <DashboardInner />
    </Suspense>
  )
}
