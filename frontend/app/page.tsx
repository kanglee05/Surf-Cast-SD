import Link from "next/link"
import { ArrowUpRight } from "lucide-react"
import { BREAKS, RATING_LABELS, generateForecast, type BreakId } from "@/lib/surf-data"
import { Footer } from "@/components/ui/footer"
import { SurfcastNavbar } from "@/components/ui/navbar"
import { StaggerTestimonials } from "@/components/ui/stagger-testimonials"

const BRAND = "#e1fcad"
const NAV_BG = "#0f1923"
const NAV_BORDER = "#1e2d3a"
const NAV_MUTED = "#8892b0"

const STATS = [
  { val: "6",      label: "Surf Breaks" },
  { val: "2",      label: "NDBC Buoys"  },
  { val: "24/7",   label: "Live Data"   },
  { val: "Hourly", label: "Updates"     },
]


export default function LandingPage() {
  const breakConditions = (Object.keys(BREAKS) as BreakId[]).map((id) => ({
    id, info: BREAKS[id], row: generateForecast(id, 1)[0],
  }))

  return (
    <div style={{ fontFamily: "var(--font-sans), sans-serif", background: NAV_BG, color: "#fff" }}>

      {/* ── HERO ──────────────────────────────────────────────────────── */}
      <section style={{ position: "relative", height: "100vh", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden" }}>

        {/* Navbar */}
        <SurfcastNavbar />

        {/* 12-column grid overlay */}
        <div style={{ position: "absolute", inset: 0, zIndex: 10, display: "grid", gridTemplateColumns: "repeat(12, 1fr)", pointerEvents: "none" }}>
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} style={{ borderRight: "1px solid rgba(255,255,255,0.08)", height: "100%" }} />
          ))}
        </div>

        {/* Background image */}
        <div style={{ position: "absolute", inset: 0, backgroundImage: "url(https://images.unsplash.com/photo-1505459668311-8dfac7952bf0?auto=format&fit=crop&w=1920&q=80)", backgroundSize: "cover", backgroundPosition: "center" }}>
          <div style={{ position: "absolute", inset: 0, background: "rgba(0,0,0,0.48)" }} />
        </div>

        {/* Content */}
        <div style={{ position: "relative", zIndex: 20, maxWidth: 900, padding: "0 32px", textAlign: "center" }}>
          <h1 style={{ fontSize: "clamp(52px, 9vw, 96px)", fontWeight: 700, letterSpacing: "-3px", lineHeight: 1, margin: "0 0 24px", color: "#fff" }}>
            Know before you go.
          </h1>
          <p style={{ color: "rgba(255,255,255,0.70)", fontSize: 19, fontWeight: 300, lineHeight: 1.65, maxWidth: 520, margin: "0 auto 52px" }}>
            Live buoy, wind, and tide data for La Jolla Shores, Blacks Beach, Pacific Beach, Ocean Beach, Sunset Cliffs, and Imperial Beach.
          </p>

          {/* CTA — reference design with sliding arrows */}
          <Link href="/dashboard" className="group" style={{ display: "inline-flex", alignItems: "center", gap: 0, cursor: "pointer", textDecoration: "none" }}>
            <span
              className="transition-all duration-500 group-hover:bg-[#122023] group-hover:text-[#e1fcad]"
              style={{ background: BRAND, color: "#000", padding: "14px 28px", borderRadius: "9999px 0 0 9999px", fontSize: 16, fontWeight: 600, lineHeight: 1, whiteSpace: "nowrap" }}
            >
              View Live Conditions
            </span>
            <div
              className="transition-all duration-500 group-hover:bg-[#122023] group-hover:text-[#e1fcad]"
              style={{ background: BRAND, color: "#000", borderRadius: "9999px", width: 52, height: 52, display: "flex", alignItems: "center", justifyContent: "center", position: "relative", overflow: "hidden", flexShrink: 0 }}
            >
              <ArrowUpRight className="absolute h-5 w-5 transition-all duration-500 -translate-x-1/2 group-hover:translate-x-10" />
              <ArrowUpRight className="absolute h-5 w-5 transition-all duration-500 -translate-x-10 group-hover:-translate-x-1/2" />
            </div>
          </Link>
        </div>
      </section>

      {/* ── BELOW FOLD ────────────────────────────────────────────────── */}
      <div>
        <div style={{ maxWidth: 900, margin: "0 auto", padding: "80px 32px 64px", textAlign: "center" }}>

          {/* Stats bar */}
          <div style={{ display: "inline-flex", marginBottom: 64, border: `1px solid ${NAV_BORDER}`, borderRadius: 10, overflow: "hidden" }}>
            {STATS.map(({ val, label }, i) => (
              <div key={label} style={{ padding: "14px 32px", textAlign: "center", borderRight: i < STATS.length - 1 ? `1px solid ${NAV_BORDER}` : "none" }}>
                <div style={{ color: BRAND, fontSize: 22, fontWeight: 700, lineHeight: 1, fontVariantNumeric: "tabular-nums" }}>{val}</div>
                <div style={{ color: "rgba(225,252,173,0.45)", fontSize: 10, fontWeight: 600, letterSpacing: "0.5px", textTransform: "uppercase", marginTop: 4 }}>{label}</div>
              </div>
            ))}
          </div>

          {/* Conditions label */}
          <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 20 }}>
            <div style={{ flex: 1, height: 1, background: NAV_BORDER }} />
            <span style={{ color: BRAND, fontSize: 10, fontWeight: 700, letterSpacing: "2px", textTransform: "uppercase", whiteSpace: "nowrap" }}>Today&apos;s Conditions</span>
            <div style={{ flex: 1, height: 1, background: NAV_BORDER }} />
          </div>

          {/* Break chips */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
            {breakConditions.map(({ id, info, row }) => (
              <Link
                key={id}
                href={`/dashboard?break=${id}`}
                className="group"
                style={{ textAlign: "left", borderRadius: 10, padding: "18px 20px", background: "#0d1b29", border: `1px solid ${NAV_BORDER}`, borderTop: `3px solid ${BRAND}`, textDecoration: "none", display: "block", transition: "transform 0.2s, box-shadow 0.25s" }}
              >
                <div style={{ color: "rgba(225,252,173,0.55)", fontSize: 10, fontWeight: 700, letterSpacing: "0.5px", textTransform: "uppercase", marginBottom: 10 }}>
                  {info.name}
                </div>
                <div style={{ color: "#fff", fontSize: 26, fontWeight: 700, fontVariantNumeric: "tabular-nums", lineHeight: 1.1, marginBottom: 5 }}>
                  {Math.round(row.wvhtFtLo)}–{Math.round(row.wvhtFtHi)} ft
                </div>
                <div style={{ color: BRAND, fontSize: 10, fontWeight: 700, letterSpacing: "0.5px" }}>
                  {RATING_LABELS[row.rating]}
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* Testimonials */}
        <div style={{ borderTop: "1px solid #1e2d3a", paddingTop: 64 }}>
          <div style={{ textAlign: "center", marginBottom: 8 }}>
            <div style={{ color: "#e1fcad", fontSize: 10, fontWeight: 700, letterSpacing: "2.5px", textTransform: "uppercase", marginBottom: 12 }}>
              What Surfers Are Saying
            </div>
            <h2 style={{ color: "#fff", fontSize: 32, fontWeight: 700, letterSpacing: "-1px", margin: 0 }}>
              Built for SD locals, by SD locals.
            </h2>
          </div>
          <StaggerTestimonials />
        </div>

        <Footer />
      </div>
    </div>
  )
}
