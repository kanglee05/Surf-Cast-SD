# Design System — SurfCast SD

## Product Context
- **What this is:** A surf conditions dashboard aggregating NDBC buoy data, NOAA wind forecasts, and Surfline ratings for San Diego surf breaks
- **Who it's for:** San Diego surfers and UCSD club members checking conditions before a session; also a showcase of the club's ML pipeline
- **Reference:** Surfline's break report page — replicate the information hierarchy and visual language for SD breaks
- **Project type:** Plotly Dash dashboard app (Python), deployable to Render/Railway/Heroku

## Memorable Thing
> "Open it like Surfline — close it knowing the session."

## Aesthetic Direction
- **Reference:** Surfline break report pages — dark nav, clean white content area, bold data presentation
- **Decoration level:** Minimal — data and typography carry all the weight
- **Mood:** Professional surf forecasting tool. Not a marketing site, not a vibe board. Serious, clean, immediately useful.
- **Anti-patterns:** Gradient blobs, centered-everything marketing layouts, generic ocean photos as decoration, heavy shadows

## Color Palette

### Navigation / Dark Sections
| Token       | Value     | Usage                              |
|-------------|-----------|-------------------------------------|
| `nav-bg`    | `#0f1923` | Top nav, break header, nearby spots |
| `nav-border`| `#1e2d3a` | Dividers within dark sections       |
| `nav-text`  | `#ffffff` | Primary text on dark               |
| `nav-muted` | `#8892b0` | Secondary text on dark             |
| `nav-dim`   | `#ccd6f6` | Tertiary text / inactive links      |

### Content / Light Sections
| Token        | Value     | Usage                              |
|--------------|-----------|-------------------------------------|
| `bg`         | `#f5f5f5` | Page background                    |
| `surface`    | `#ffffff` | Cards, panels                      |
| `surface-alt`| `#f8f9fa` | Card headers, stat chip backgrounds |
| `border`     | `#e0e0e0` | Card borders, dividers             |
| `text`       | `#1a1a1a` | Primary body text                  |
| `text-muted` | `#666666` | Labels, metadata                   |

### Brand & Accent
| Token      | Value     | Usage                              |
|------------|-----------|-------------------------------------|
| `brand`    | `#ff6b35` | Logo, primary brand mark           |
| `accent`   | `#1d9bf0` | Links, tide line, buoy wave height  |

### Surf Rating Colors (match Surfline encoding)
| Rating      | Color     | Label      |
|-------------|-----------|------------|
| Epic/Great  | `#d54530` | EPIC       |
| Good        | `#ff8900` | GOOD       |
| Fair-Good   | `#ffcd1e` | FAIR TO GOOD |
| Fair        | `#30d2e8` | FAIR       |
| Poor-Fair   | `#408fff` | POOR TO FAIR |
| Poor        | `#98a2af` | POOR       |

### Chart Color Assignments
| Data Series     | Color     |
|-----------------|-----------|
| Wave height bars| Rating color (dynamic) |
| Tide line       | `#1d9bf0` |
| Wind speed      | `#a0aec0` |
| Period line     | `#00c97f` |
| Direction       | `#f6ad55` |

### CSS Custom Properties
```css
:root {
  --nav-bg:      #0f1923;
  --nav-border:  #1e2d3a;
  --nav-text:    #ffffff;
  --nav-muted:   #8892b0;
  --nav-dim:     #ccd6f6;
  --bg:          #f5f5f5;
  --surface:     #ffffff;
  --surface-alt: #f8f9fa;
  --border:      #e0e0e0;
  --text:        #1a1a1a;
  --text-muted:  #666666;
  --brand:       #ff6b35;
  --accent:      #1d9bf0;
  --rating-epic: #d54530;
  --rating-good: #ff8900;
  --rating-fair-good: #ffcd1e;
  --rating-fair: #30d2e8;
  --rating-poor-fair: #408fff;
  --rating-poor: #98a2af;
}
```

## Typography
- **Primary UI font:** Source Sans Pro (Google Fonts CDN) — used for all text
- **Data readouts / numbers:** `font-variant-numeric: tabular-nums` on all numeric displays
- **Font loading:**
  ```
  https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@300;400;600;700&display=swap
  ```

### Scale
| Token    | Size  | Usage                             |
|----------|-------|-----------------------------------|
| text-xs  | 10px  | Chart axis labels, badge text     |
| text-sm  | 12px  | Metadata, secondary labels        |
| text-base| 14px  | Body text, nav links              |
| text-lg  | 18px  | Section headings                  |
| text-xl  | 22px  | Stat values                       |
| text-hero| 48px  | Current wave height number        |

## Layout — Page Structure

Mirrors Surfline's break report page exactly:

```
┌─────────────────────────────────────────────────────────────┐
│  NAV (dark)  SurfCast SD | Cams & Forecast | Buoy | About   │
├─────────────────────────────────────────────────────────────┤
│  BREAK HEADER (dark)  [Break Selector] | La Jolla, CA       │
│  Tabs: Report & Forecast  Charts  Surf Guide                 │
├─────────────────────────────────────────────────────────────┤
│  NEARBY SPOTS (dark)  [LJ Shores] [Blacks] [PB] [OB] ...    │
├───────────────────────────────────────┬─────────────────────┤
│  FORECAST CHART (light)               │  CURRENT CONDITIONS │
│  [rating dot row — 8 hrs]             │  2-3 ft  [FAIR]     │
│  [wave height bar chart]              │  ─────────────────  │
│  [tide overlay line]                  │  TIDE  WIND         │
│                                       │  1.2m  12 mph       │
│                                       │  ─────────────────  │
│                                       │  PERIOD  SWELL DIR  │
│                                       │  13s     WNW        │
├───────────────────────────────────────┴─────────────────────┤
│  BUOY DATA                                                   │
│  NDBC 46232 (Point Loma)  |  NDBC 46254 (Mission Bay)       │
│  [Hs chart]  [Period chart]  [Hs chart]  [Period chart]      │
├─────────────────────────────────────────────────────────────┤
│  SURF GUIDE  (text description of the break)                 │
├─────────────────────────────────────────────────────────────┤
│  FOOTER (dark)                                               │
└─────────────────────────────────────────────────────────────┘
```

## Component Specs

### Top Navigation
- Height: 52px
- Background: `var(--nav-bg)` sticky, `z-index: 1000`
- Logo: brand color `#ff6b35`, 700 weight, 20px
- Nav links: 14px, `var(--nav-dim)`, no underline

### Break Header
- Same dark background as nav
- Break name: 26px, 700 weight, white
- Location subtitle: 13px, `var(--nav-muted)`
- Active tab: white text, 2px bottom border in current rating color

### Nearby Spots Strip
- Horizontal scroll, dark background
- Cards: 130px min-width, `#162231` background, `#1e2d3a` border
- Active card: brighter background `#1e2d3a`, colored border matching rating
- Wave height: 15px 700 weight white; rating label: 10px uppercase

### Conditions Card
- White card, 8px border-radius, 1px `var(--border)` border
- Header: uppercase 12px label on `var(--surface-alt)` background
- Hero wave height: 48px 700 weight — format `"2-3 ft"`
- Rating badge: solid color pill, white text, 10px uppercase
- Stat chips: 2×2 grid, each on `var(--surface-alt)`, 6px radius
  - Label: 10px uppercase muted; Value: 22px 700; Sub: 12px muted

### Forecast Chart
- Height: 240px
- White plot/paper background
- Wave height: `go.Bar` colored by rating, slight opacity 0.85
- Tide: `go.Scatter` blue line, right y-axis
- No legend, no modebar
- X-axis: hour labels, light gridlines off

### Rating Row (above forecast chart)
- Full width, flexbox, 8 equal columns
- Each cell: colored dot `●` (20px), rating label (9px uppercase)
- Left label column: "Today" or day name (60px wide)

### Buoy Cards
- White card, 8px radius
- Header: station name + key stats (Hs, DPD) inline right
- 2-column chart grid: Wave Height | Period
- Chart height: 120px each, no modebar

## Spacing
- Base unit: 8px
- Page padding: 24px sides
- Max content width: 1400px centered
- Card gap: 24px
- Section margin-bottom: 24px

## Surf Breaks (San Diego)
| ID               | Name                  | Lat       | Lon        |
|------------------|-----------------------|-----------|------------|
| la_jolla_shores  | La Jolla Shores       | 32.8579   | -117.2575  |
| blacks           | Blacks Beach          | 32.8807   | -117.2436  |
| pb_point         | Pacific Beach Point   | 32.7970   | -117.2550  |
| ocean_beach      | Ocean Beach           | 32.7443   | -117.2535  |
| sunset_cliffs    | Sunset Cliffs         | 32.7118   | -117.2502  |
| imperial_beach   | Imperial Beach        | 32.5805   | -117.1318  |

## NDBC Buoys
| Station | Name              |
|---------|-------------------|
| 46232   | Point Loma South  |
| 46254   | Mission Bay West  |

## Deployment
- **Target platform:** Render (free tier) or Railway
- **Entry point:** `app/app.py` — `server = app.server` exposed for gunicorn
- **Command:** `gunicorn app.app:server`
- **Port:** read from `PORT` env var (Dash handles this via `host="0.0.0.0"`)
- **Required env vars:** none for mock data mode; ETL vars optional

## Decisions Log
| Date       | Decision                             | Rationale |
|------------|--------------------------------------|-----------|
| 2026-05-26 | Surfline visual language as reference | "Make that" — replicate the UX surfers already trust |
| 2026-05-26 | Source Sans Pro as sole typeface      | Surfline uses it; consistent with reference |
| 2026-05-26 | Dark nav / light content split        | Matches Surfline pattern; nav recedes, data pops |
| 2026-05-26 | Mock data with live ETL fallback      | App runs immediately; plugs in real data when ETL ships |
| 2026-05-26 | Single-file app.py                    | Club project — easy to read and run, no over-abstraction |
| 2026-05-26 | Gunicorn + server export for deploy   | Standard Dash deployment pattern for Render/Railway |
