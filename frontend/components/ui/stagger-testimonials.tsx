"use client"

import React, { useState, useEffect } from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"

const SQRT_5000 = Math.sqrt(5000)

const testimonials = [
  { tempId: 0,  testimonial: "Checked SurfCast before my dawn patrol — called 3–4 ft good. Paddled out to perfect head-high glass. This thing is dialed.",          by: "Jake M., La Jolla local",        imgSrc: "https://i.pravatar.cc/150?img=1"  },
  { tempId: 1,  testimonial: "I used to drive 45 minutes to Blacks only to find it blown out. SurfCast tells me exactly when the glass holds. Game changer.",        by: "Tara S., Encinitas",             imgSrc: "https://i.pravatar.cc/150?img=3"  },
  { tempId: 2,  testimonial: "The buoy data and period readings are spot on. As soon as the models connect it'll be the only forecast I ever open.",                  by: "Marco D., Pacific Beach",        imgSrc: "https://i.pravatar.cc/150?img=5"  },
  { tempId: 3,  testimonial: "My crew texts me 'what's SurfCast saying?' every morning. It's become our single source of truth for SD surf.",                        by: "Priya K., Ocean Beach",          imgSrc: "https://i.pravatar.cc/150?img=7"  },
  { tempId: 4,  testimonial: "The swell compass and best-window feature alone are worth it. Finally a forecast built for surfers, not meteorologists.",               by: "Devon W., Sunset Cliffs",        imgSrc: "https://i.pravatar.cc/150?img=9"  },
  { tempId: 5,  testimonial: "Caught the best session of my year at Imperial Beach because SurfCast flagged a rare S swell window. Nothing else caught it.",          by: "Lucia R., Imperial Beach",       imgSrc: "https://i.pravatar.cc/150?img=11" },
  { tempId: 6,  testimonial: "Water temp and UV index on the same page as the forecast is the little detail that shows they actually surf.",                          by: "Sam T., Mission Bay",            imgSrc: "https://i.pravatar.cc/150?img=13" },
  { tempId: 7,  testimonial: "Dawn patrol crew loves it. Sunrise time right next to the forecast rating — zero extra tabs needed.",                                   by: "Kenji N., La Jolla Cove",        imgSrc: "https://i.pravatar.cc/150?img=15" },
  { tempId: 8,  testimonial: "Switched from Surfline two weeks ago. Cleaner UI, free, and the San Diego breaks are more accurate than the national apps.",            by: "Ally B., Coronado",              imgSrc: "https://i.pravatar.cc/150?img=17" },
  { tempId: 9,  testimonial: "The live buoy charts are exactly what I needed. DPD trend over 48 hours tells me everything about whether a swell is building.",       by: "Chris F., PB Point regular",     imgSrc: "https://i.pravatar.cc/150?img=19" },
]

interface Props { position: number; testimonial: typeof testimonials[0]; handleMove: (steps: number) => void; cardSize: number }

const BRAND   = "#e1fcad"
const NAV_BG  = "#0f1923"
const NAV_BORDER = "#1e2d3a"
const CARD_BG = "#0d1b29"
const MUTED   = "#8892b0"

const TestimonialCard: React.FC<Props> = ({ position, testimonial, handleMove, cardSize }) => {
  const isCenter = position === 0
  return (
    <div
      onClick={() => handleMove(position)}
      className="absolute left-1/2 top-1/2 cursor-pointer transition-all duration-500 ease-in-out p-8"
      style={{
        width: cardSize,
        height: cardSize,
        zIndex: isCenter ? 10 : 0,
        background: isCenter ? BRAND : CARD_BG,
        border: `2px solid ${isCenter ? BRAND : NAV_BORDER}`,
        clipPath: "polygon(50px 0%, calc(100% - 50px) 0%, 100% 50px, 100% 100%, calc(100% - 50px) 100%, 50px 100%, 0 100%, 0 0)",
        transform: `translate(-50%, -50%) translateX(${(cardSize / 1.5) * position}px) translateY(${isCenter ? -65 : position % 2 ? 15 : -15}px) rotate(${isCenter ? 0 : position % 2 ? 2.5 : -2.5}deg)`,
        boxShadow: isCenter ? `0px 8px 0px 4px ${NAV_BORDER}` : "none",
      }}
    >
      <span className="absolute block origin-top-right rotate-45" style={{ right: -2, top: 48, width: SQRT_5000, height: 2, background: NAV_BORDER }} />
      <img
        src={testimonial.imgSrc}
        alt={testimonial.by.split(",")[0]}
        className="mb-4 h-14 w-12 object-cover object-top"
        style={{ boxShadow: `3px 3px 0px ${NAV_BG}` }}
      />
      <h3 style={{ fontSize: "1rem", fontWeight: 500, color: isCenter ? "#000" : "#fff" }}>
        &ldquo;{testimonial.testimonial}&rdquo;
      </h3>
      <p style={{ position: "absolute", bottom: 32, left: 32, right: 32, fontSize: 13, fontStyle: "italic", color: isCenter ? "rgba(0,0,0,0.6)" : MUTED }}>
        — {testimonial.by}
      </p>
    </div>
  )
}

export const StaggerTestimonials: React.FC = () => {
  const [cardSize, setCardSize] = useState(365)
  const [list, setList] = useState(testimonials)

  const handleMove = (steps: number) => {
    const next = [...list]
    if (steps > 0) {
      for (let i = steps; i > 0; i--) {
        const item = next.shift(); if (!item) return
        next.push({ ...item, tempId: Math.random() })
      }
    } else {
      for (let i = steps; i < 0; i++) {
        const item = next.pop(); if (!item) return
        next.unshift({ ...item, tempId: Math.random() })
      }
    }
    setList(next)
  }

  useEffect(() => {
    const update = () => setCardSize(window.matchMedia("(min-width: 640px)").matches ? 365 : 290)
    update()
    window.addEventListener("resize", update)
    return () => window.removeEventListener("resize", update)
  }, [])

  return (
    <div className="relative w-full overflow-hidden" style={{ height: 600, background: NAV_BG }}>
      {list.map((t, index) => {
        const position = list.length % 2 ? index - (list.length + 1) / 2 : index - list.length / 2
        return <TestimonialCard key={t.tempId} testimonial={t} handleMove={handleMove} position={position} cardSize={cardSize} />
      })}
      <div className="absolute bottom-4 left-1/2 flex -translate-x-1/2 gap-2">
        <button
          onClick={() => handleMove(-1)}
          className="flex h-14 w-14 items-center justify-center text-2xl transition-colors group focus-visible:outline-none"
          style={{ background: CARD_BG, border: `2px solid ${NAV_BORDER}`, color: "#fff" }}
          onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = BRAND; (e.currentTarget as HTMLButtonElement).style.color = "#000" }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = CARD_BG; (e.currentTarget as HTMLButtonElement).style.color = "#fff" }}
          aria-label="Previous"
        >
          <ChevronLeft />
        </button>
        <button
          onClick={() => handleMove(1)}
          className="flex h-14 w-14 items-center justify-center text-2xl transition-colors focus-visible:outline-none"
          style={{ background: CARD_BG, border: `2px solid ${NAV_BORDER}`, color: "#fff" }}
          onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = BRAND; (e.currentTarget as HTMLButtonElement).style.color = "#000" }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = CARD_BG; (e.currentTarget as HTMLButtonElement).style.color = "#fff" }}
          aria-label="Next"
        >
          <ChevronRight />
        </button>
      </div>
    </div>
  )
}
