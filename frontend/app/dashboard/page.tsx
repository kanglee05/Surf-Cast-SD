"use client"

import { useState, useEffect, Suspense } from "react"
import { useSearchParams } from "next/navigation"
import Link from "next/link"
import dynamic from "next/dynamic"
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell, AreaChart, Area,
} from "recharts"
import {
  BREAKS, RATING_COLORS, RATING_LABELS, generateForecast, fetchForecast,
  windCompass, type BreakId, type Rating, type ForecastRow,
} from "@/lib/surf-data"

const SurfMap = dynamic(() => import("@/components/SurfMap"), {
  ssr: false,
  loading: () => (
    <div style={{ height: 400, background: "#f0f0f0", borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", color: "#999", marginBottom: 24 }}>
      Loading map…
    </div>
  ),
})

const BRAND      = "#e1fcad"
const NAV_BG     = "#0f1923"
const NAV_BORDER = "#1e2d3a"
const NAV_MUTED  = "#8892b0"
const NAV_DIM    = "#ccd6f6"
const SURFACE    = "#ffffff"
const BORDER     = "#e0e0e0"
const TEXT       = "#1a1a1a"
const TEXT_MUTED = "#666666"
const ACCENT     = "#1d9bf0"

function ratingScore(r: Rating) {
  return ({ epic: 10, great: 8, good: 6, fair: 4, poor_fair: 2, poor: 1 } as const)[r]
}

function getBestWindow(fc: ForecastRow[]) {
  const hours = fc.slice(0, 24)
  let best = 0, bestIdx = 0
  for (let i = 0; i < hours.length - 2; i++) {
    const avg = (ratingScore(hours[i].rating) + ratingScore(hours[i + 1].rating) + ratingScore(hours[i + 2].rating)) / 3
    if (avg > best) { best = avg; bestIdx = i }
  }
  const fmt = (d: Date) => d.toLocaleTimeString([], { hour: "numeric", hour12: true })
  return {
    label: `${fmt(hours[bestIdx].time)} – ${fmt(hours[Math.min(bestIdx + 2, hours.length - 1)].time)}`,
    rating: hours[bestIdx].rating,
  }
}

function getWaterTemp() {
  const m = new Date().getMonth()
  const f = [59, 58, 59, 61, 63, 66, 69, 70, 70, 68, 65, 61][m]
  return { f, c: Math.round((f - 32) * 5 / 9) }
}

function getUV() {
  const m = new Date().getMonth()
  return [4, 5, 7, 9, 10, 11, 11, 10, 9, 7, 5, 4][m]
}

function getSunTimes() {
  const m = new Date().getMonth()
  return {
    sunrise: ["6:48","6:38","6:12","5:36","5:07","4:53","4:59","5:22","5:47","6:11","6:38","6:57"][m],
    sunset:  ["5:04","5:32","6:00","6:27","6:53","7:15","7:14","6:49","6:08","5:29","5:02","4:50"][m],
  }
}

function generateBuoyData(offset: number) {
  const now = new Date()
  return Array.from({ length: 48 }, (_, i) => {
    const t = (i / 48) * 2 * Math.PI + offset
    const wvht = Math.max(0.3, Math.min(3.2, 0.7 + 0.4 * Math.sin(t) + 0.1 * Math.sin(2.1 * t + 0.5)) * 3.281)
    const dpd  = Math.max(6, Math.min(20, 12 + 3.5 * Math.sin(t + 0.8) + 0.5 * Math.sin(1.7 * t)))
    const time = new Date(now.getTime() - (48 - i) * 3_600_000)
    return {
      label: time.toLocaleTimeString([], { hour: "numeric", hour12: true }),
      wvht: parseFloat(wvht.toFixed(1)),
      dpd:  parseFloat(dpd.toFixed(1)),
    }
  })
}

function SwellCompass({ degrees }: { degrees: number }) {
  const ticks = [0, 45, 90, 135, 180, 225, 270, 315]
  return (
    <svg viewBox="0 0 80 80" width={68} height={68}>
      <circle cx={40} cy={40} r={36} fill="none" stroke={BORDER} strokeWidth={1} />
      {ticks.map((d) => {
        const a = (d - 90) * Math.PI / 180
        return <line key={d} x1={40 + 28 * Math.cos(a)} y1={40 + 28 * Math.sin(a)} x2={40 + 34 * Math.cos(a)} y2={40 + 34 * Math.sin(a)} stroke={BORDER} strokeWidth={1} />
      })}
      {([ ["N",40,9], ["S",40,73], ["E",73,43], ["W",7,43] ] as [string,number,number][]).map(([l,x,y]) => (
        <text key={l} x={x} y={y} textAnchor="middle" fill="#bbb" fontSize={8} fontWeight={700}>{l}</text>
      ))}
      <g transform={`rotate(${degrees}, 40, 40)`}>
        <polygon points="40,12 37,32 40,38 43,32" fill={ACCENT} opacity={0.9} />
        <polygon points="40,68 37,48 40,38 43,48" fill="#ddd" opacity={0.6} />
      </g>
      <circle cx={40} cy={40} r={2.5} fill={TEXT} />
    </svg>
  )
}

function QuickCard({ label, value, sub, accentColor, topColor }: { label: string; value: string; sub: string; accentColor: string; topColor: string }) {
  return (
    <div style={{ background: SURFACE, borderRadius: 8, border: `1px solid ${BORDER}`, borderTop: `3px solid ${topColor}`, padding: "14px 16px" }}>
      <div style={{ color: "#aaa", fontSize: 10, fontWeight: 700, letterSpacing: "0.5px", textTransform: "uppercase", marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700, color: accentColor, fontVariantNumeric: "tabular-nums", lineHeight: 1.2 }}>{value}</div>
      <div style={{ color: TEXT_MUTED, fontSize: 12, marginTop: 2 }}>{sub}</div>
    </div>
  )
}

function StatChip({ label, value, sub, accent }: { label: string; value: string; sub: string; accent?: string }) {
  return (
    <div style={{ background: "#f8f9fa", borderRadius: 6, padding: 12 }}>
      <div style={{ color: "#aaa", fontSize: 10, fontWeight: 700, letterSpacing: "0.5px", textTransform: "uppercase", marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700, color: accent || TEXT, fontVariantNumeric: "tabular-nums" }}>{value}</div>
      <div style={{ color: TEXT_MUTED, fontSize: 12 }}>{sub}</div>
    </div>
  )
}

const SURF_GUIDES: Record<BreakId, string> = {
  la_jolla_shores: "A long, sandy beach break suitable for all skill levels. Best conditions arrive with WNW to NW swells hitting the exposed beach. Morning glass-offs before the onshore sea breeze kicks in (typically 11am–noon) provide the cleanest conditions.",
  blacks:          "San Diego's premier big-wave venue, below the Torrey Pines cliffs. Access via a steep trail. Best on larger NW swells with light offshore winds. The cliffs provide some wind protection.",
  pb_point:        "A consistent beach break handling a variety of swell directions. The jetty at the south end creates a semi-sheltered pocket that holds shape in moderate onshore conditions. Best at mid-tide on W to NW swells.",
}

function DashboardInner() {
  const searchParams = useSearchParams()
  const initialBreak = (searchParams.get("break") as BreakId) || "la_jolla_shores"
  const [activeBreak, setActiveBreak] = useState<BreakId>(initialBreak)
  const [fc, setFc] = useState<ForecastRow[]>(() => generateForecast(activeBreak))

  useEffect(() => {
    const load = () => fetchForecast(activeBreak).then(data => {
      if (data.length > 0) setFc(data)
    })
    load()
    const interval = setInterval(load, 30 * 60 * 1000)
    return () => clearInterval(interval)
  }, [activeBreak])

  const now = new Date()
  const current = fc.reduce((best, row) => {
    const rowTime = new Date(String(row.time))
    const bestTime = new Date(String(best.time))
    return Math.abs(rowTime.getTime() - now.getTime()) < Math.abs(bestTime.getTime() - now.getTime()) ? row : best
  }, fc[0])

  const breakInfo = BREAKS[activeBreak]
  const ratingColor = RATING_COLORS[current.rating]
  const bestWindow = getBestWindow(fc)
  const waterTemp  = getWaterTemp()
  const uv         = getUV()
  const sun        = getSunTimes()
  const buoy1      = generateBuoyData(0)
  const buoy2      = generateBuoyData(1.2)
  const uvLabel = uv <= 2 ? "Low" : uv <= 5 ? "Moderate" : uv <= 7 ? "High" : uv <= 10 ? "Very High" : "Extreme"
  const uvColor = uv <= 2 ? "#22c55e" : uv <= 5 ? "#eab308" : uv <= 7 ? "#f97316" : "#ef4444"

  const chartData = fc.slice(0, 24).map((row) => ({
    label: row.time.toLocaleTimeString([], { hour: "numeric", hour12: true }),
    wvht:  parseFloat(row.wvhtFtHi.toFixed(1)),
    tide:  parseFloat(row.tideM.toFixed(2)),
    rating: row.rating,
  }))

  const hourLabel = (d: Date) => d.toLocaleTimeString([], { hour: "numeric", hour12: true })

  return (
    <div style={{ background: "#f5f5f5", minHeight: "100vh", fontFamily: "var(--font-sans), sans-serif" }}>

      <nav style={{ background: NAV_BG, height: 52, display: "flex", alignItems: "center", padding: "0 24px", position: "sticky", top: 0, zIndex: 1000, borderBottom: `1px solid ${NAV_BORDER}` }}>
        <Link href="/" style={{ color: BRAND, fontWeight: 700, fontSize: 20, letterSpacing: "-0.3px", marginRight: 32, textDecoration: "none" }}>
          SurfCast SD
        </Link>
        <div style={{ display: "flex", alignItems: "center", flex: 1, gap: 20 }}>
          <a href="#forecast" style={{ color: NAV_DIM, textDecoration: "none", fontSize: 14 }}>Forecast</a>
          <a href="#buoy"     style={{ color: NAV_DIM, textDecoration: "none", fontSize: 14 }}>Buoy Data</a>
          <a href="#guide"    style={{ color: NAV_DIM, textDecoration: "none", fontSize: 14 }}>Surf Guide</a>
        </div>
        <span style={{ color: NAV_MUTED, fontSize: 13 }}>San Diego, CA</span>
      </nav>

      <div style={{ background: NAV_BG, padding: "16px 24px 0", borderBottom: `1px solid ${NAV_BORDER}` }}>
        <h1 style={{ color: "#fff", fontSize: 26, fontWeight: 700, margin: "0 0 2px", letterSpacing: "-0.3px" }}>{breakInfo.name}</h1>
        <div style={{ color: NAV_MUTED, fontSize: 13, marginBottom: 14 }}>{breakInfo.loc}</div>
        <div style={{ display: "flex" }}>
          {(["Forecast", "Buoy Data", "Surf Guide"] as const).map((tab, i) => (
            <a key={tab} href={["#forecast","#buoy","#guide"][i]} style={{ color: i === 0 ? "#fff" : NAV_MUTED, fontWeight: i === 0 ? 600 : 400, fontSize: 14, paddingBottom: 10, borderBottom: i === 0 ? `2px solid ${ratingColor}` : "2px solid transparent", marginRight: 24, textDecoration: "none" }}>
              {tab}
            </a>
          ))}
        </div>
      </div>

      <div style={{ background: NAV_BG, padding: "12px 24px", borderBottom: `1px solid ${NAV_BORDER}` }}>
        <div style={{ color: NAV_MUTED, fontSize: 11, fontWeight: 600, letterSpacing: "0.5px", marginBottom: 10, textTransform: "uppercase" }}>Nearby Spots</div>
        <div style={{ display: "flex", overflowX: "auto", gap: 8, paddingBottom: 4 }}>
          {(Object.keys(BREAKS) as BreakId[]).map((bid) => {
            const EXPOSURE: Record<string, number> = { la_jolla_shores: 0.80, blacks: 1.05, pb_point: 0.95 }
            const liveWvhtM = fc[0]?.wvhtM ?? 1.3
            const exp = EXPOSURE[bid] ?? 1.0
            const fakeRow = generateForecast(bid, 1)[0]
            const row = { ...fakeRow, wvhtM: liveWvhtM * exp, wvhtFtLo: liveWvhtM * exp * 3.281 * 0.85, wvhtFtHi: liveWvhtM * exp * 3.281 * 1.15, rating: fc[0]?.rating ?? fakeRow.rating }
            const color  = RATING_COLORS[row.rating]
            const active = bid === activeBreak
            return (
              <button key={bid} onClick={() => setActiveBreak(bid)}
                style={{ minWidth: 130, flexShrink: 0, background: active ? "#1e2d3a" : "#162231", border: active ? `1px solid ${color}` : `1px solid ${NAV_BORDER}`, borderRadius: 6, padding: "10px 14px", cursor: "pointer", textAlign: "left" }}>
                <div style={{ color: active ? "#fff" : NAV_DIM, fontSize: 12, fontWeight: 600, marginBottom: 4 }}>{active ? "● " : ""}{BREAKS[bid].name}</div>
                <div style={{ color: NAV_DIM, fontSize: 12, marginTop: 2 }}>{BREAKS[bid].loc}</div>
              </button>
            )
          })}
        </div>
      </div>

      <div style={{ background: SURFACE, borderBottom: `1px solid ${BORDER}`, padding: "8px 24px" }}>
        <select value={activeBreak} onChange={(e) => setActiveBreak(e.target.value as BreakId)}
          style={{ maxWidth: 280, fontSize: 14, padding: "6px 10px", borderRadius: 6, border: `1px solid ${BORDER}`, background: SURFACE, color: TEXT }}>
          {(Object.keys(BREAKS) as BreakId[]).map((bid) => (
            <option key={bid} value={bid}>{BREAKS[bid].name}</option>
          ))}
        </select>
      </div>

      <div style={{ maxWidth: 1400, margin: "0 auto", padding: "24px 24px 0" }}>

        <SurfMap activeBreak={activeBreak} onBreakSelect={setActiveBreak} />

        <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12, marginBottom: 24 }}>
          <div style={{ background: SURFACE, borderRadius: 8, border: `1px solid ${BORDER}`, borderTop: `3px solid ${RATING_COLORS[bestWindow.rating]}`, padding: "14px 16px" }}>
            <div style={{ color: "#aaa", fontSize: 10, fontWeight: 700, letterSpacing: "0.5px", textTransform: "uppercase", marginBottom: 6 }}>Best Window</div>
            <div style={{ fontSize: 13, fontWeight: 700, color: TEXT, lineHeight: 1.4 }}>{bestWindow.label}</div>
            <div style={{ fontSize: 10, fontWeight: 700, color: RATING_COLORS[bestWindow.rating], letterSpacing: "0.5px", marginTop: 4 }}>{RATING_LABELS[bestWindow.rating]}</div>
          </div>
          <QuickCard label="Water Temp" value={`${waterTemp.f}°F`} sub={`${waterTemp.c}°C`}    accentColor={ACCENT}    topColor={ACCENT} />
          <QuickCard label="UV Index"   value={String(uv)}          sub={uvLabel}                accentColor={uvColor}   topColor={uvColor} />
          <QuickCard label="Sunrise"    value={sun.sunrise}          sub="Dawn patrol"            accentColor="#f59e0b"   topColor="#f59e0b" />
          <QuickCard label="Sunset"     value={sun.sunset}           sub="Evening glass"          accentColor="#f97316"   topColor="#f97316" />
        </div>

        <div id="forecast" style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 24, marginBottom: 24 }}>

          <div style={{ background: SURFACE, borderRadius: 8, border: `1px solid ${BORDER}`, overflow: "hidden" }}>
            <div style={{ padding: "12px 16px", borderBottom: `1px solid ${BORDER}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ fontWeight: 700, fontSize: 14, color: TEXT }}>{breakInfo.name} — 24-Hour Forecast</div>
              <div style={{ color: TEXT_MUTED, fontSize: 12 }}>NDBC + NWS · Bars = wave ht · Line = tide</div>
            </div>

            <div style={{ display: "flex", borderBottom: `1px solid ${BORDER}` }}>
              <div style={{ width: 52, flexShrink: 0, color: TEXT_MUTED, fontSize: 11, padding: 8, borderRight: `1px solid ${BORDER}`, display: "flex", alignItems: "center" }}>Today</div>
              {fc.slice(0, 8).map((row, i) => (
                <div key={i} style={{ flex: 1, textAlign: "center", padding: "8px 4px", borderRight: `1px solid ${BORDER}` }}>
                  <div style={{ color: TEXT_MUTED, fontSize: 10, marginBottom: 4 }}>{hourLabel(row.time)}</div>
                  <div style={{ color: RATING_COLORS[row.rating], fontSize: 18, lineHeight: 1 }}>●</div>
                  <div style={{ color: RATING_COLORS[row.rating], fontSize: 9, fontWeight: 700, marginTop: 3 }}>{RATING_LABELS[row.rating]}</div>
                </div>
              ))}
            </div>

            <div style={{ padding: "16px 8px 8px", height: 220 }}>
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData} margin={{ left: -10, right: 32, top: 4, bottom: 0 }}>
                  <CartesianGrid vertical={false} stroke="#f0f0f0" />
                  <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fill: TEXT_MUTED, fontSize: 10 }} interval={3} />
                  <YAxis yAxisId="wave" tickLine={false} axisLine={false} tick={{ fill: TEXT_MUTED, fontSize: 10 }} tickFormatter={(v) => `${v}ft`} domain={[0, 10]} />
                  <YAxis yAxisId="tide" orientation="right" tickLine={false} axisLine={false} tick={{ fill: ACCENT, fontSize: 10 }} tickFormatter={(v) => `${v}m`} domain={[0, 2]} />
                  <Tooltip
                    contentStyle={{ background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 6, fontSize: 12 }}
                    formatter={(val: unknown, name: unknown) => [name === "tide" ? `${val}m` : `${val}ft`, name === "tide" ? "Tide" : "Wave Ht"]}
                  />
                  <Bar yAxisId="wave" dataKey="wvht" maxBarSize={22} radius={[2, 2, 0, 0]}>
                    {chartData.map((entry, i) => (
                      <Cell key={i} fill={RATING_COLORS[entry.rating]} fillOpacity={0.85} />
                    ))}
                  </Bar>
                  <Line yAxisId="tide" dataKey="tide" stroke={ACCENT} strokeWidth={2} dot={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div style={{ background: SURFACE, borderRadius: 8, border: `1px solid ${BORDER}`, overflow: "hidden" }}>
            <div style={{ background: "#f8f9fa", padding: "10px 16px", fontSize: 12, fontWeight: 700, color: TEXT_MUTED, letterSpacing: "0.5px", borderBottom: `1px solid ${BORDER}`, textTransform: "uppercase" }}>
              Current Conditions
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

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 10 }}>
                <StatChip label="Tide"       value={`${current.tideM.toFixed(1)}m`}       sub={current.tideM > 1 ? "Rising" : "Falling"} />
                <StatChip label="Wind"       value={`${Math.round(current.windMph)} mph`}  sub={windCompass(current.windDeg)} />
                <StatChip label="Period"     value={`${Math.round(current.dpd)}s`}         sub="Dominant" />
                <StatChip label="Water Temp" value={`${waterTemp.f}°F`}                   sub={`${waterTemp.c}°C`} accent={ACCENT} />
              </div>

              <div style={{ background: "#f8f9fa", borderRadius: 6, padding: "12px 16px", display: "flex", alignItems: "center", gap: 16 }}>
                <SwellCompass degrees={(current.mwd ?? current.windDeg) % 360} />
                <div>
                  <div style={{ color: "#aaa", fontSize: 10, fontWeight: 700, letterSpacing: "0.5px", textTransform: "uppercase", marginBottom: 4 }}>Swell Direction</div>
                  <div style={{ fontSize: 24, fontWeight: 700, color: TEXT, fontVariantNumeric: "tabular-nums" }}>{Math.round((current.mwd ?? current.windDeg) % 360)}°</div>
                  <div style={{ color: TEXT_MUTED, fontSize: 13 }}>{windCompass(current.mwd ?? current.windDeg)}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div id="buoy" style={{ marginBottom: 32 }}>
          <div style={{ fontSize: 18, fontWeight: 700, color: TEXT, marginBottom: 16 }}>Nearby Buoys</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
            {([
              { id: "46232", name: "NDBC 46232 · Point Loma South", data: buoy1 },
              { id: "46254", name: "NDBC 46254 · Mission Bay West",  data: buoy2 },
            ]).map(({ id, name, data }) => {
              const latest = data[data.length - 1]
              return (
                <div key={id} style={{ background: SURFACE, borderRadius: 8, border: `1px solid ${BORDER}`, overflow: "hidden" }}>
                  <div style={{ padding: "12px 16px", borderBottom: `1px solid ${BORDER}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div style={{ fontWeight: 700, fontSize: 14, color: TEXT }}>{name}</div>
                    <div style={{ display: "flex", gap: 16 }}>
                      <span style={{ color: ACCENT, fontSize: 13, fontWeight: 600 }}>Hs {latest.wvht} ft</span>
                      <span style={{ color: "#22c55e", fontSize: 13, fontWeight: 600 }}>DPD {latest.dpd}s</span>
                    </div>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1, background: BORDER }}>
                    <div style={{ background: SURFACE, padding: 12 }}>
                      <div style={{ color: TEXT_MUTED, fontSize: 11, fontWeight: 600, marginBottom: 8 }}>Wave Height (ft)</div>
                      <div style={{ height: 110 }}>
                        <ResponsiveContainer width="100%" height="100%">
                          <AreaChart data={data.slice(-24)} margin={{ left: -20, right: 4, top: 4, bottom: 0 }}>
                            <defs>
                              <linearGradient id={`wg-${id}`} x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%"  stopColor={ACCENT} stopOpacity={0.3} />
                                <stop offset="95%" stopColor={ACCENT} stopOpacity={0.02} />
                              </linearGradient>
                            </defs>
                            <XAxis dataKey="label" hide />
                            <YAxis tickLine={false} axisLine={false} tick={{ fill: TEXT_MUTED, fontSize: 9 }} domain={["auto","auto"]} />
                            <Tooltip contentStyle={{ fontSize: 11, border: `1px solid ${BORDER}`, borderRadius: 4 }} formatter={(v: unknown) => [`${v} ft`, "Hs"]} />
                            <Area dataKey="wvht" stroke={ACCENT} strokeWidth={2} fill={`url(#wg-${id})`} dot={false} />
                          </AreaChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                    <div style={{ background: SURFACE, padding: 12 }}>
                      <div style={{ color: TEXT_MUTED, fontSize: 11, fontWeight: 600, marginBottom: 8 }}>Dominant Period (s)</div>
                      <div style={{ height: 110 }}>
                        <ResponsiveContainer width="100%" height="100%">
                          <AreaChart data={data.slice(-24)} margin={{ left: -20, right: 4, top: 4, bottom: 0 }}>
                            <defs>
                              <linearGradient id={`dg-${id}`} x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%"  stopColor="#22c55e" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#22c55e" stopOpacity={0.02} />
                              </linearGradient>
                            </defs>
                            <XAxis dataKey="label" hide />
                            <YAxis tickLine={false} axisLine={false} tick={{ fill: TEXT_MUTED, fontSize: 9 }} domain={["auto","auto"]} />
                            <Tooltip contentStyle={{ fontSize: 11, border: `1px solid ${BORDER}`, borderRadius: 4 }} formatter={(v: unknown) => [`${v}s`, "DPD"]} />
                            <Area dataKey="dpd" stroke="#22c55e" strokeWidth={2} fill={`url(#dg-${id})`} dot={false} />
                          </AreaChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        <div id="guide" style={{ padding: "24px 0 48px", borderTop: `1px solid ${BORDER}` }}>
          <div style={{ fontSize: 18, fontWeight: 700, color: TEXT, marginBottom: 12 }}>Surf Guide</div>
          <p style={{ color: "#444", fontSize: 14, lineHeight: 1.75, maxWidth: 720, margin: 0 }}>
            {SURF_GUIDES[activeBreak]}
          </p>
        </div>
      </div>

      <div style={{ background: NAV_BG, padding: "32px 24px", marginTop: 48, textAlign: "center" }}>
        <div style={{ color: BRAND, fontWeight: 700, fontSize: 18, marginBottom: 8 }}>SurfCast SD</div>
        <div style={{ color: "#4a5568", fontSize: 12 }}>UCSD Surf &amp; Sail Club · Data: NDBC, NOAA, NWS</div>
      </div>
    </div>
  )
}

export default function DashboardPage() {
  return (
    <Suspense fallback={<div style={{ background: "#0f1923", minHeight: "100vh" }} />}>
      <DashboardInner />
    </Suspense>
  )
}