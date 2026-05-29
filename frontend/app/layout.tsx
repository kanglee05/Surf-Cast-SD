import type { Metadata } from "next"
import { Source_Sans_3 } from "next/font/google"
import "./globals.css"

const sourceSans = Source_Sans_3({
  variable: "--font-sans",
  subsets: ["latin"],
  weight: ["300", "400", "600", "700"],
})

export const metadata: Metadata = {
  title: "SurfCast SD",
  description: "Live surf conditions for San Diego breaks — NDBC buoys, NOAA forecasts, tide data.",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${sourceSans.variable} h-full antialiased`}>
      <body className="min-h-full">{children}</body>
    </html>
  )
}
