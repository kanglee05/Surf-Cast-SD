import { cn } from "@/lib/utils"
import { ArrowRight } from "lucide-react"

export function Footer({ className }: { className?: string }) {
  return (
    <footer
      className={cn(
        "border-t",
        className,
      )}
      style={{
        borderColor: "#1e2d3a",
        background: "radial-gradient(35% 128px at 50% 0%, rgba(225,252,173,0.06), transparent)",
      }}
    >
      <div className="relative mx-auto max-w-5xl px-4">
        <div
          className="relative grid grid-cols-1 md:grid-cols-4"
          style={{ borderLeft: "1px solid #1e2d3a", borderRight: "1px solid #1e2d3a" }}
        >
          <div style={{ borderRight: "1px solid #1e2d3a" }}>
            <SocialCard title="NDBC Buoys" href="https://www.ndbc.noaa.gov/" />
            <LinksGroup
              title="Surf Breaks"
              links={[
                { title: "La Jolla Shores",   href: "/dashboard?break=la_jolla_shores" },
                { title: "Blacks Beach",       href: "/dashboard?break=blacks" },
                { title: "Pacific Beach Point",href: "/dashboard?break=pb_point" },
              ]}
            />
          </div>

          <div style={{ borderRight: "1px solid #1e2d3a" }}>
            <SocialCard title="NOAA Forecasts" href="https://www.weather.gov/" />
            <LinksGroup
              title="Data Sources"
              links={[
                { title: "NDBC Station 46232", href: "https://www.ndbc.noaa.gov/station_page.php?station=46232" },
                { title: "NDBC Station 46254", href: "https://www.ndbc.noaa.gov/station_page.php?station=46254" },
                { title: "NOAA Wind API",      href: "https://api.weather.gov/" },
                { title: "CO-OPS Tide Data",   href: "https://tidesandcurrents.noaa.gov/" },
                { title: "Surf Rating Model",  href: "/dashboard" },
              ]}
            />
          </div>

          <div style={{ borderRight: "1px solid #1e2d3a" }}>
            <SocialCard title="GitHub" href="https://github.com/" />
            <LinksGroup
              title="Community"
              links={[
                { title: "UCSD Surf & Sail Club", href: "#" },
                { title: "Wave Science",           href: "#" },
                { title: "Reading Buoy Data",      href: "#" },
                { title: "Swell Forecasting",      href: "#" },
                { title: "Surf Safety",            href: "#" },
              ]}
            />
          </div>

          <div>
            <SocialCard title="Instagram" href="#" />
            <LinksGroup
              title="Project"
              links={[
                { title: "About",    href: "/dashboard#guide" },
                { title: "Contact",  href: "#" },
                { title: "API",      href: "#" },
                { title: "Privacy",  href: "#" },
                { title: "Terms",    href: "#" },
              ]}
            />
          </div>
        </div>
      </div>

      <div className="flex justify-center p-3" style={{ borderTop: "1px solid #1e2d3a" }}>
        <p style={{ color: "#8892b0", fontSize: 12 }}>
          © {new Date().getFullYear()} SurfCast SD · UCSD Surf &amp; Sail Club · Data: NDBC, NOAA, NWS
        </p>
      </div>
    </footer>
  )
}

function LinksGroup({ title, links }: { title: string; links: { title: string; href: string }[] }) {
  return (
    <div className="p-3">
      <h3
        className="mt-2 mb-4 text-xs font-medium tracking-wider uppercase"
        style={{ color: "rgba(225,252,173,0.5)" }}
      >
        {title}
      </h3>
      <ul className="space-y-2">
        {links.map((link) => (
          <li key={link.title}>
            <a
              href={link.href}
              className="text-xs transition-colors hover:text-white"
              style={{ color: "#8892b0" }}
            >
              {link.title}
            </a>
          </li>
        ))}
      </ul>
    </div>
  )
}

function SocialCard({ title, href }: { title: string; href: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="group flex items-center justify-between p-3 text-sm transition-colors hover:bg-white/5"
      style={{ borderBottom: "1px solid #1e2d3a", color: "#e1fcad" }}
    >
      <span className="font-medium">{title}</span>
      <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
    </a>
  )
}
