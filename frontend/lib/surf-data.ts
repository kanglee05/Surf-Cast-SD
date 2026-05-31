export type BreakId = "la_jolla_shores" | "blacks" | "pb_point"
export type Rating = "epic" | "great" | "good" | "fair" | "poor_fair" | "poor"

export interface BreakInfo { name: string; loc: string; lat: number; lon: number }
export interface ForecastRow {
  time: Date; wvhtM: number; wvhtFtLo: number; wvhtFtHi: number
  dpd: number; windMph: number; windDeg: number; tideM: number; rating: Rating
  mwd?: number
}

export const BREAKS: Record<BreakId, BreakInfo> = {
  la_jolla_shores: { name: "La Jolla Shores",    loc: "La Jolla, CA",       lat: 32.8579, lon: -117.2575 },
  blacks:          { name: "Blacks Beach",         loc: "La Jolla, CA",       lat: 32.8807, lon: -117.2436 },
  pb_point:        { name: "Pacific Beach Point",  loc: "Pacific Beach, CA",  lat: 32.7970, lon: -117.2550 },
}

export const RATING_COLORS: Record<Rating, string> = {
  epic: "#d54530", great: "#ff8900", good: "#ffcd1e",
  fair: "#30d2e8", poor_fair: "#408fff", poor: "#98a2af",
}

export const RATING_LABELS: Record<Rating, string> = {
  epic: "EPIC", great: "GOOD", good: "FAIR TO GOOD",
  fair: "FAIR", poor_fair: "POOR TO FAIR", poor: "POOR",
}

export const COMPASS = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
export const windCompass = (deg: number) => COMPASS[Math.round(deg / 22.5) % 16]

// Seeded PRNG (mulberry32)
function seededRng(seed: number) {
  let s = seed
  return () => {
    s = (s + 0x6D2B79F5) | 0
    let t = Math.imul(s ^ (s >>> 15), 1 | s)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function hashBreak(id: string) {
  let h = 0
  for (const c of id) h = (Math.imul(31, h) + c.charCodeAt(0)) | 0
  return Math.abs(h) % 2147483647
}

function ratingScore(wvhtM: number, dpd: number, windMph: number, windDeg: number): Rating {
  const offshore = windDeg >= 45 && windDeg <= 135
  const ft = wvhtM * 3.281
  if (ft >= 6 && dpd >= 14 && windMph <= 8 && offshore) return "epic"
  if (ft >= 4 && ft < 10 && dpd >= 13 && windMph <= 10 && offshore) return "great"
  if (ft >= 3 && ft < 10 && dpd >= 10 && windMph <= 15) return "good"
  if (ft >= 2 && ft < 6) return "fair"
  if (ft >= 1 && ft < 3 && dpd >= 8) return "poor_fair"
  return "poor"
}

export function generateForecast(breakId: BreakId, hours = 48): ForecastRow[] {
  const rng = seededRng(hashBreak(breakId))
  const now = new Date()
  now.setMinutes(0, 0, 0)

  return Array.from({ length: hours }, (_, i) => {
    const t = (i / hours) * 4 * Math.PI
    const wvht = Math.max(0.3, Math.min(2.5, 0.7 + 0.35 * Math.sin(t) + 0.15 * Math.sin(2.3 * t) + (rng() - 0.5) * 0.08))
    const dpd  = Math.max(7,   Math.min(20, 12 + 3 * Math.sin(t / 2) + (rng() - 0.5) * 0.6))
    const wspd = Math.max(1,   Math.min(25, 8  + 6 * Math.sin(t + Math.PI / 4) + (rng() - 0.5) * 1))
    const wdir = (((280 + 30 * Math.sin(t / 3) + (rng() - 0.5) * 10) % 360) + 360) % 360
    const tide = 0.8 + 0.7 * Math.sin((2 * Math.PI * i) / 12.4)
    return {
      time: new Date(now.getTime() + i * 3_600_000),
      wvhtM: wvht, wvhtFtLo: wvht * 3.281 * 0.85, wvhtFtHi: wvht * 3.281 * 1.15,
      dpd, windMph: wspd, windDeg: wdir, tideM: tide,
      rating: ratingScore(wvht, dpd, wspd, wdir),
    }
  })
}

export async function fetchForecast(breakId: BreakId, hours = 48): Promise<ForecastRow[]> {
  try {
    const resp = await fetch(`/api/forecast?break=${breakId}`)
    if (!resp.ok) throw new Error("API error")
    const data = await resp.json()
    return data.forecast.map((r: any) => ({
      time: new Date(r.time),
      wvhtM: r.wvhtM,
      wvhtFtLo: r.wvhtFtLo,
      wvhtFtHi: r.wvhtFtHi,
      dpd: r.dpd,
      windMph: r.windMph,
      windDeg: r.windDeg,
      tideM: r.tideM,
      rating: r.rating as Rating,
      mwd: r.mwd as number ?? 0,
    }))
  } catch {
    return generateForecast(breakId, hours)
  }
}
