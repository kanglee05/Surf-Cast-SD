"use client"

import { Button } from "@/components/ui/button"
import { CheckCircleIcon } from "lucide-react"
import { CartesianGrid, Line, LineChart, XAxis } from "recharts"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { type ChartConfig, ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"

export function PricingWithChart() {
  return (
    <div className="mx-auto max-w-6xl">
      <div className="mx-auto mb-10 max-w-2xl text-center">
        <h1 className="text-4xl font-extrabold tracking-tight lg:text-5xl text-white">
          Pricing that Scales with You
        </h1>
        <p className="mt-4 text-sm md:text-base" style={{ color: "#8892b0" }}>
          Free for students and the surf community. Pro unlocks ML-powered forecasts and API access.
        </p>
      </div>

      <div className="grid rounded-xl border md:grid-cols-6" style={{ background: "#0d1b29", borderColor: "#1e2d3a" }}>

        {/* Free Plan */}
        <div className="flex flex-col justify-between p-6 md:col-span-2" style={{ borderRight: "1px solid #1e2d3a" }}>
          <div className="space-y-4">
            <div>
              <h2 className="text-xl font-semibold text-white">Free</h2>
              <span className="my-3 block text-3xl font-bold" style={{ color: "#e1fcad" }}>$0</span>
              <p className="text-sm" style={{ color: "#8892b0" }}>Best for surfers and UCSD students</p>
            </div>
            <a href="/dashboard" className="inline-flex w-full items-center justify-center rounded-md border px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-white/10" style={{ borderColor: "rgba(255,255,255,0.2)" }}>
              Get Started
            </a>
            <div className="my-6 h-px w-full" style={{ background: "#1e2d3a" }} />
            <ul className="space-y-3 text-sm" style={{ color: "#8892b0" }}>
              {[
                "Live buoy + wind + tide data",
                "6 San Diego surf breaks",
                "48-hour forecasts",
                "Interactive coastal map",
                "Surf ratings (Good/Fair/Poor)",
              ].map((item) => (
                <li key={item} className="flex items-center gap-2">
                  <CheckCircleIcon className="h-4 w-4 shrink-0" style={{ color: "#e1fcad" }} />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Pro Plan */}
        <div className="z-10 grid gap-8 overflow-hidden p-6 md:col-span-4 lg:grid-cols-2">
          <div className="flex flex-col justify-between space-y-6">
            <div>
              <h2 className="text-xl font-semibold text-white">Pro Monthly</h2>
              <span className="my-3 block text-3xl font-bold" style={{ color: "#e1fcad" }}>$9</span>
              <p className="text-sm" style={{ color: "#8892b0" }}>For serious surfers and teams</p>
            </div>
            <div className="h-fit w-full rounded-lg border p-2" style={{ background: "rgba(255,255,255,0.03)", borderColor: "#1e2d3a" }}>
              <PopularityChart />
            </div>
          </div>

          <div className="relative w-full">
            <div className="text-sm font-medium text-white">Everything in Free, plus:</div>
            <ul className="mt-4 space-y-3 text-sm" style={{ color: "#8892b0" }}>
              {[
                "ML-powered surf quality predictions",
                "Historical swell data (90 days)",
                "API access for your own tools",
                "Email alerts for epic conditions",
                "Priority data refresh (15-min)",
                "All future breaks added",
                "Export forecasts to CSV",
                "Team sharing (up to 5 seats)",
              ].map((item) => (
                <li key={item} className="flex items-center gap-2">
                  <CheckCircleIcon className="h-4 w-4 shrink-0" style={{ color: "#e1fcad" }} />
                  {item}
                </li>
              ))}
            </ul>
            <div className="mt-8 grid w-full grid-cols-2 gap-2.5">
              <a href="/pricing" className="inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-semibold transition-opacity hover:opacity-90" style={{ background: "#e1fcad", color: "#000" }}>
                Get Pro
              </a>
              <a href="/pricing" className="inline-flex items-center justify-center rounded-md border px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-white/10" style={{ borderColor: "rgba(255,255,255,0.2)" }}>
                Start free trial
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function PopularityChart() {
  const chartData = [
    { month: "Jan", interest: 120 },
    { month: "Feb", interest: 180 },
    { month: "Mar", interest: 155 },
    { month: "Apr", interest: 210 },
    { month: "May", interest: 260 },
    { month: "Jun", interest: 310 },
    { month: "Jul", interest: 290 },
    { month: "Aug", interest: 340 },
    { month: "Sep", interest: 360 },
    { month: "Oct", interest: 400 },
    { month: "Nov", interest: 430 },
    { month: "Dec", interest: 510 },
  ]

  const chartConfig = {
    interest: { label: "Surfers", color: "#e1fcad" },
  } satisfies ChartConfig

  return (
    <Card style={{ background: "transparent", border: "1px solid #1e2d3a" }}>
      <CardHeader className="space-y-0 border-b p-3" style={{ borderColor: "#1e2d3a" }}>
        <CardTitle className="text-sm text-white">Plan Popularity</CardTitle>
        <CardDescription className="text-xs" style={{ color: "#8892b0" }}>
          Monthly surfers considering Pro
        </CardDescription>
      </CardHeader>
      <CardContent className="p-3">
        <ChartContainer config={chartConfig}>
          <LineChart data={chartData} margin={{ left: 12, right: 12 }}>
            <CartesianGrid vertical={false} stroke="#1e2d3a" />
            <XAxis dataKey="month" tickLine={false} axisLine={false} tickMargin={8} tick={{ fill: "#8892b0", fontSize: 10 }} />
            <ChartTooltip cursor={false} content={<ChartTooltipContent />} />
            <Line dataKey="interest" type="monotone" stroke="#e1fcad" strokeWidth={2} dot={false} />
          </LineChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}
