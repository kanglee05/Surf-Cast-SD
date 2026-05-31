import { NextResponse } from "next/server"
import { Storage } from "@google-cloud/storage"

const BUCKET = "surfcast-sd-wind"
const PREDICT_API = "https://surfcast-api-19545389323.us-west1.run.app/predict"
const storage = new Storage()

function getDateStr(daysBack = 0): string {
  const d = new Date()
  d.setUTCDate(d.getUTCDate() - daysBack)
  return `${d.getUTCFullYear()}${String(d.getUTCMonth()+1).padStart(2,"0")}${String(d.getUTCDate()).padStart(2,"0")}`
}

function parseCSV(text: string) {
  const lines = text.trim().split("\n")
  const headers = lines[0].split(",")
  return lines.slice(1).map(line => {
    const vals = line.split(",")
    const row: Record<string, string> = {}
    headers.forEach((h, i) => { row[h.trim()] = vals[i]?.trim() ?? "" })
    return row
  })
}

async function readCSVFromGCS(): Promise<string | null> {
  for (let i = 0; i <= 2; i++) {
    try {
      const fileName = `forecast_${getDateStr(i)}.csv`
      const file = storage.bucket(BUCKET).file(fileName)
      const [contents] = await file.download()
      return contents.toString("utf-8")
    } catch { continue }
  }
  return null
}

async function getLiveTide(): Promise<number | null> {
  try {
    const url = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?product=water_level&station=9410170&datum=MLLW&time_zone=gmt&units=metric&format=json&date=latest"
    const resp = await fetch(url)
    const data = await resp.json()
    return parseFloat(data.data?.[0]?.v ?? null)
  } catch {
    return null
  }
}

async function getLiveBuoy(): Promise<{ wvhtM: number; dpd: number; mwd: number; windMph: number; windDeg: number; tempC: number } | null> {
  try {
    const url = "https://www.ndbc.noaa.gov/data/realtime2/46232.txt"
    const resp = await fetch(url)
    const text = await resp.text()
    const lines = text.trim().split("\n")
    const dataLine = lines[2]
    const parts = dataLine.trim().split(/\s+/)
    const wvht = parseFloat(parts[8])
    const dpd = parseFloat(parts[9])
    const mwd = parseFloat(parts[11])
    const windDeg = parseFloat(parts[5])
    const windMs = parseFloat(parts[6])
    const windMph = windMs * 2.237
    const tempC = parseFloat(parts[14])
    if (isNaN(wvht) || isNaN(dpd)) return null
    return {
      wvhtM: wvht,
      dpd,
      mwd: isNaN(mwd) ? 270 : mwd,
      windMph: isNaN(windMph) ? 0 : Math.round(windMph),
      windDeg: isNaN(windDeg) ? 0 : windDeg,
      tempC: isNaN(tempC) ? 17 : tempC,
    }
  } catch {
    return null
  }
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const breakId = searchParams.get("break") ?? "la_jolla_shores"

  const [csvText, liveTide, liveBuoy] = await Promise.all([
    readCSVFromGCS(),
    getLiveTide(),
    getLiveBuoy(),
  ])

  if (!csvText) {
    return NextResponse.json({ error: "No forecast data available" }, { status: 404 })
  }

  const rows = parseCSV(csvText)
  const filtered = rows
    .filter(r => r.break_id === breakId && String(r.station) === "46232")
    .slice(0, 48)

  if (filtered.length === 0) {
    return NextResponse.json({ error: "No data for this break" }, { status: 404 })
  }

  const features = filtered.map(r => ({
    WVHT: parseFloat(r.WVHT) || 0,
    DPD: parseFloat(r.DPD) || 0,
    MWD: parseFloat(r.MWD) || 0,
    APD: parseFloat(r.APD) || 0,
    tide_height_m: parseFloat(r.tide_height_m) || 0,
    wind_speed_mph: parseFloat(r.wind_speed_mph) || 0,
    wind_direction_deg: parseFloat(r.wind_direction_deg) || 0,
    is_calm: parseFloat(r.wind_speed_mph) === 0 ? 1 : 0,
    sunrise_hour_utc: parseFloat(r.sunrise_hour_utc) || 13,
    sunset_hour_utc: parseFloat(r.sunset_hour_utc) || 3,
    day_length_hours: parseFloat(r.day_length_hours) || 14,
    hours_since_sunrise: parseFloat(r.hours_since_sunrise) || 0,
    season_sin: parseFloat(r.season_sin) || 0,
    season_cos: parseFloat(r.season_cos) || 0,
    temp_c: parseFloat(r.temp_c) || 18,
    humidity_pct: parseFloat(r.humidity_pct) || 70,
  }))

  let ratings: string[] = []
  try {
    const predResp = await fetch(PREDICT_API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ features }),
    })
    const predData = await predResp.json()
    ratings = predData.ratings ?? []
  } catch (e) {
    console.error("Prediction API failed:", e)
    ratings = filtered.map(() => "fair")
  }

  const EXPOSURE: Record<string, number> = {
    la_jolla_shores: 0.80,
    blacks: 1.05,
    pb_point: 0.95,
    ocean_beach: 0.90,
    sunset_cliffs: 0.95,
    imperial_beach: 0.85,
  }
  const exposure = EXPOSURE[breakId] ?? 1.0

  const forecast = filtered.map((r, i) => {
    const forecastWvhtM = (parseFloat(r.WVHT) || 0) * exposure
    const wvhtM = i === 0 && liveBuoy ? liveBuoy.wvhtM * exposure : forecastWvhtM
    const dpd = i === 0 && liveBuoy ? liveBuoy.dpd : parseFloat(r.DPD) || 0
    const tideM = i === 0 && liveTide !== null ? liveTide : parseFloat(r.tide_height_m) || 0
    const mwd = i === 0 && liveBuoy ? liveBuoy.mwd : parseFloat(r.MWD) || 0
    const windMph = i === 0 && liveBuoy ? liveBuoy.windMph : parseFloat(r.wind_speed_mph) || 0
    const windDeg = i === 0 && liveBuoy ? liveBuoy.windDeg : parseFloat(r.wind_direction_deg) || 0
    const tempC = i === 0 && liveBuoy ? liveBuoy.tempC : parseFloat(r.temp_c) || 0
    return {
      time: r.timestamp_utc,
      wvhtM,
      wvhtFtLo: wvhtM * 3.281 * 0.85,
      wvhtFtHi: wvhtM * 3.281 * 1.15,
      dpd,
      windMph,
      windDeg,
      mwd,
      tideM,
      rating: ratings[i] ?? "fair",
      apd: parseFloat(r.APD) || 0,
      tempC,
      humidity: parseFloat(r.humidity_pct) || 0,
    }
  })

  return NextResponse.json({ breakId, forecast })
}