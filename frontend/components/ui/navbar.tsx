"use client"

import { useState } from "react"
import { Menu, X, Waves, Wind, Anchor, MapPin, Info, ChevronDown } from "lucide-react"
import Link from "next/link"
import {
  NavigationMenu,
  NavigationMenuContent,
  NavigationMenuItem,
  NavigationMenuList,
  NavigationMenuTrigger,
} from "@/components/ui/navigation-menu"

const BRAND = "#e1fcad"
const NAV_BG = "rgba(15,25,35,0.85)"
const NAV_BORDER = "rgba(255,255,255,0.08)"

const BREAKS = [
  { title: "La Jolla Shores",    url: "/dashboard?break=la_jolla_shores", description: "Sandy beach break, all levels. Best WNW swells." },
  { title: "Blacks Beach",        url: "/dashboard?break=blacks",           description: "Premier big-wave venue below Torrey Pines cliffs." },
  { title: "Pacific Beach Point", url: "/dashboard?break=pb_point",         description: "Consistent break, semi-sheltered pocket at mid-tide." },
  { title: "Ocean Beach",         url: "/dashboard?break=ocean_beach",      description: "Pier sandbar, best W/WNW swells on incoming tide." },
  { title: "Sunset Cliffs",       url: "/dashboard?break=sunset_cliffs",    description: "Rocky reef series along Point Loma coastline." },
  { title: "Imperial Beach",      url: "/dashboard?break=imperial_beach",   description: "SD's southernmost beach, works on S swells." },
]

const DATA_LINKS = [
  { title: "NDBC Buoys",  url: "/dashboard#buoy",  description: "Live swell height, period & direction from offshore stations.", icon: <Anchor className="size-5 shrink-0" /> },
  { title: "NOAA Wind",   url: "/dashboard",        description: "Hourly wind speed and direction per break.", icon: <Wind className="size-5 shrink-0" /> },
  { title: "Tide Data",   url: "/dashboard",        description: "Hourly tide heights from NOAA CO-OPS station.", icon: <Waves className="size-5 shrink-0" /> },
  { title: "Surf Guide",  url: "/dashboard#guide",  description: "Break-by-break surf guides for each location.", icon: <Info className="size-5 shrink-0" /> },
]

export function SurfcastNavbar() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [mobileBreaksOpen, setMobileBreaksOpen] = useState(false)
  const [mobileDataOpen, setMobileDataOpen] = useState(false)

  return (
    <>
    <nav
      className="backdrop-blur-sm"
      style={{
        position: "absolute", top: 0, left: 0, right: 0, zIndex: 30,
        background: NAV_BG,
        borderBottom: `1px solid ${NAV_BORDER}`,
      }}
    >
      <div style={{ maxWidth: 1400, margin: "0 auto", padding: "0 24px", height: 58, display: "flex", alignItems: "center", justifyContent: "space-between" }}>

        {/* Logo */}
        <Link href="/" style={{ color: BRAND, fontWeight: 700, fontSize: 18, textDecoration: "none", letterSpacing: "-0.3px", flexShrink: 0 }}>
          SurfCast SD
        </Link>

        {/* Desktop nav */}
        <div className="hidden lg:flex items-center gap-1">
          <NavigationMenu>
            <NavigationMenuList>

              {/* Breaks dropdown */}
              <NavigationMenuItem>
                <NavigationMenuTrigger
                  className="text-white/70 hover:text-white bg-transparent hover:bg-white/8 data-[state=open]:bg-white/8 data-[state=open]:text-white h-9 px-3 text-sm"
                  style={{ background: "transparent" }}
                >
                  Breaks
                </NavigationMenuTrigger>
                <NavigationMenuContent>
                  <ul className="w-[520px] p-3 grid grid-cols-2 gap-1" style={{ background: "#0f1923", border: "1px solid #1e2d3a", borderRadius: 8 }}>
                    {BREAKS.map((b) => (
                      <li key={b.title}>
                        <Link
                          href={b.url}
                          className="flex gap-3 rounded-md p-3 leading-none no-underline transition-colors hover:bg-white/6 group"
                          style={{ display: "flex" }}
                        >
                          <MapPin className="size-4 mt-0.5 shrink-0" style={{ color: BRAND }} />
                          <div>
                            <div className="text-sm font-semibold text-white">{b.title}</div>
                            <p className="text-xs leading-snug mt-0.5" style={{ color: "#8892b0" }}>{b.description}</p>
                          </div>
                        </Link>
                      </li>
                    ))}
                  </ul>
                </NavigationMenuContent>
              </NavigationMenuItem>

              {/* Data dropdown */}
              <NavigationMenuItem>
                <NavigationMenuTrigger
                  className="text-white/70 hover:text-white bg-transparent hover:bg-white/8 data-[state=open]:bg-white/8 data-[state=open]:text-white h-9 px-3 text-sm"
                  style={{ background: "transparent" }}
                >
                  Data
                </NavigationMenuTrigger>
                <NavigationMenuContent>
                  <ul className="w-72 p-3" style={{ background: "#0f1923", border: "1px solid #1e2d3a", borderRadius: 8 }}>
                    {DATA_LINKS.map((d) => (
                      <li key={d.title}>
                        <Link
                          href={d.url}
                          className="flex gap-3 rounded-md p-3 leading-none no-underline transition-colors hover:bg-white/6"
                          style={{ display: "flex" }}
                        >
                          <span style={{ color: BRAND }}>{d.icon}</span>
                          <div>
                            <div className="text-sm font-semibold text-white">{d.title}</div>
                            <p className="text-xs leading-snug mt-0.5" style={{ color: "#8892b0" }}>{d.description}</p>
                          </div>
                        </Link>
                      </li>
                    ))}
                  </ul>
                </NavigationMenuContent>
              </NavigationMenuItem>

              {/* Simple links */}
              <NavigationMenuItem>
                <Link href="/dashboard#guide" className="inline-flex h-9 items-center px-3 text-sm rounded-md transition-colors hover:bg-white/8" style={{ color: "rgba(255,255,255,0.7)" }}>
                  About
                </Link>
              </NavigationMenuItem>

            </NavigationMenuList>
          </NavigationMenu>
        </div>

        {/* CTA + mobile trigger */}
        <div className="flex items-center gap-3">
          <Link
            href="/dashboard"
            className="hidden lg:inline-flex items-center gap-2 text-sm font-semibold rounded-full px-4 py-2 transition-all duration-300 hover:opacity-90"
            style={{ background: BRAND, color: "#000" }}
          >
            View Conditions
          </Link>

          {/* Mobile hamburger */}
          <div className="lg:hidden">
            <button
              onClick={() => setMobileOpen(!mobileOpen)}
              className="inline-flex items-center justify-center rounded-md p-2 text-white transition-colors hover:bg-white/10"
            >
              {mobileOpen ? <X className="size-5" /> : <Menu className="size-5" />}
            </button>
          </div>
        </div>
      </nav>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div
          className="lg:hidden fixed inset-0 z-40"
          style={{ top: 58 }}
          onClick={() => setMobileOpen(false)}
        >
          <div
            className="absolute right-0 top-0 h-full w-72 flex flex-col gap-2 p-6 overflow-y-auto"
            style={{ background: "#0a1520", borderLeft: "1px solid #1e2d3a" }}
            onClick={(e) => e.stopPropagation()}
          >
            <span style={{ color: BRAND, fontWeight: 700, fontSize: 18, marginBottom: 8 }}>SurfCast SD</span>

            {/* Breaks accordion */}
            <button onClick={() => setMobileBreaksOpen(!mobileBreaksOpen)} className="flex items-center justify-between py-3 text-sm font-semibold text-white border-b" style={{ borderColor: "#1e2d3a" }}>
              Breaks <ChevronDown className={`size-4 transition-transform ${mobileBreaksOpen ? "rotate-180" : ""}`} />
            </button>
            {mobileBreaksOpen && (
              <div className="flex flex-col gap-1 pb-2">
                {BREAKS.map((b) => (
                  <Link key={b.title} href={b.url} onClick={() => setMobileOpen(false)} className="flex items-center gap-2 rounded-md p-2 text-sm transition-colors hover:bg-white/6" style={{ color: "#ccd6f6" }}>
                    <MapPin className="size-3.5 shrink-0" style={{ color: BRAND }} />{b.title}
                  </Link>
                ))}
              </div>
            )}

            {/* Data accordion */}
            <button onClick={() => setMobileDataOpen(!mobileDataOpen)} className="flex items-center justify-between py-3 text-sm font-semibold text-white border-b" style={{ borderColor: "#1e2d3a" }}>
              Data <ChevronDown className={`size-4 transition-transform ${mobileDataOpen ? "rotate-180" : ""}`} />
            </button>
            {mobileDataOpen && (
              <div className="flex flex-col gap-1 pb-2">
                {DATA_LINKS.map((d) => (
                  <Link key={d.title} href={d.url} onClick={() => setMobileOpen(false)} className="flex items-center gap-2 rounded-md p-2 text-sm transition-colors hover:bg-white/6" style={{ color: "#ccd6f6" }}>
                    <span style={{ color: BRAND }}>{d.icon}</span>{d.title}
                  </Link>
                ))}
              </div>
            )}

            <Link href="/dashboard#guide" onClick={() => setMobileOpen(false)} className="py-3 text-sm font-semibold border-b" style={{ color: "#fff", borderColor: "#1e2d3a" }}>About</Link>

            <Link href="/dashboard" onClick={() => setMobileOpen(false)} className="mt-4 flex items-center justify-center rounded-full py-3 text-sm font-semibold transition-opacity hover:opacity-90" style={{ background: BRAND, color: "#000" }}>
              View Conditions
            </Link>
          </div>
        </div>
      )}
    </>
  )
}
