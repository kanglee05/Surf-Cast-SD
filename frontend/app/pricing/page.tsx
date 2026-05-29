import { PricingWithChart } from "@/components/ui/pricing-with-chart"
import { SurfcastNavbar } from "@/components/ui/navbar"
import { Footer } from "@/components/ui/footer"

export const metadata = { title: "Pricing — SurfCast SD" }

export default function PricingPage() {
  return (
    <div style={{ background: "#0f1923", minHeight: "100vh", color: "#fff", fontFamily: "var(--font-sans), sans-serif", position: "relative" }}>
      <SurfcastNavbar />

      <div style={{ paddingTop: 120, paddingBottom: 80, paddingLeft: 40, paddingRight: 40, position: "relative" }}>
        {/* Subtle dot grid */}
        <div
          aria-hidden="true"
          style={{
            position: "absolute", inset: 0, zIndex: 0, pointerEvents: "none",
            backgroundImage: "radial-gradient(rgba(255,255,255,0.05) 1px, transparent 1px)",
            backgroundSize: "14px 14px",
            maskImage: "radial-gradient(circle at 50% 10%, rgba(0,0,0,1), rgba(0,0,0,0.2) 50%, rgba(0,0,0,0) 80%)",
          }}
        />
        <div style={{ position: "relative", zIndex: 1 }}>
          <PricingWithChart />
        </div>
      </div>

      <Footer />
    </div>
  )
}
