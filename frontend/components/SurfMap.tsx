"use client"

import { MapContainer, TileLayer, CircleMarker, Tooltip, Popup } from "react-leaflet"
import "leaflet/dist/leaflet.css"
import { BREAKS, RATING_COLORS, RATING_LABELS, generateForecast, type BreakId } from "@/lib/surf-data"

interface SurfMapProps {
  activeBreak: BreakId
  onBreakSelect: (id: BreakId) => void
}

const BUOYS = [
  { name: "NDBC 46232 · Point Loma South", lat: 32.748, lon: -117.373 },
  { name: "NDBC 46254 · Mission Bay West",  lat: 32.748, lon: -117.487 },
]

export default function SurfMap({ activeBreak, onBreakSelect }: SurfMapProps) {
  const breakEntries = Object.entries(BREAKS) as [BreakId, (typeof BREAKS)[BreakId]][]

  return (
    <div style={{ background: "#fff", border: "1px solid #e0e0e0", borderRadius: 8, overflow: "hidden", marginBottom: 24 }}>
      <div style={{ padding: "12px 16px", borderBottom: "1px solid #e0e0e0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ fontWeight: 700, fontSize: 14, color: "#1a1a1a" }}>San Diego Coast</div>
        <div style={{ color: "#666", fontSize: 12 }}>● Surf breaks &nbsp;○ NDBC buoys · Click a break to load its data</div>
      </div>
      <MapContainer
        center={[32.75, -117.26]}
        zoom={11}
        style={{ height: 400, width: "100%" }}
        scrollWheelZoom={false}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com">CARTO</a>'
        />

        {breakEntries.map(([bid, info]) => {
          const row = generateForecast(bid, 1)[0]
          const color = RATING_COLORS[row.rating]
          const active = bid === activeBreak
          return (
            <CircleMarker
              key={bid}
              center={[info.lat, info.lon]}
              radius={active ? 13 : 9}
              pathOptions={{
                color: "#fff",
                weight: active ? 2.5 : 1.5,
                fillColor: color,
                fillOpacity: active ? 1 : 0.75,
              }}
              eventHandlers={{ click: () => onBreakSelect(bid) }}
            >
              <Tooltip sticky>
                {info.name} · {Math.round(row.wvhtFtLo)}–{Math.round(row.wvhtFtHi)} ft · {RATING_LABELS[row.rating]}
              </Tooltip>
              <Popup>
                <div style={{ minWidth: 140, fontFamily: "sans-serif" }}>
                  <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 6 }}>{info.name}</div>
                  <div style={{ fontSize: 22, fontWeight: 700, color: "#1a1a1a" }}>
                    {Math.round(row.wvhtFtLo)}–{Math.round(row.wvhtFtHi)} ft
                  </div>
                  <div style={{ color, fontSize: 11, fontWeight: 700, letterSpacing: "0.4px", marginBottom: 8 }}>
                    {RATING_LABELS[row.rating]}
                  </div>
                  <button
                    onClick={() => onBreakSelect(bid)}
                    style={{ color: "#1d9bf0", fontSize: 10, background: "none", border: "none", padding: 0, cursor: "pointer" }}
                  >
                    Load conditions →
                  </button>
                </div>
              </Popup>
            </CircleMarker>
          )
        })}

        {BUOYS.map((b) => (
          <CircleMarker
            key={b.name}
            center={[b.lat, b.lon]}
            radius={6}
            pathOptions={{ color: "#1d9bf0", weight: 1.5, fillColor: "#1d9bf0", fillOpacity: 0.25, dashArray: "5,4" }}
          >
            <Tooltip>{b.name}</Tooltip>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  )
}
