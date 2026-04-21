# DESIGN.md — LightyClaw Design System

_A project-agnostic design specification for all LightyClaw web applications._

**Version:** 1.0  
**Last updated:** 2026-04-21  
**Applies to:** All web projects (Concert Tracker, Paris Associations, Consensus, future projects)

---

## Philosophy

**Direct. Functional. No fluff.**

Every pixel serves a purpose. Decoration is waste. Users should accomplish their goal in the fewest clicks possible.

- **Clarity over beauty** — If it looks good but confuses users, it's bad design
- **Speed over animations** — No fade-ins, no loaders, instant state changes
- **Density over whitespace** — Show more data per screen, reduce scrolling
- **Consistency over creativity** — Same patterns everywhere, learn once, use everywhere

---

## Color System

### Dark Mode (Default)

| Token | Hex | Usage |
|-------|-----|-------|
| `--bg-primary` | `#0f1115` | Page background |
| `--bg-secondary` | `#161922` | Cards, panels, tables |
| `--bg-tertiary` | `#1e222c` | Hover states, inputs |
| `--border` | `#2a2f3a` | Borders, dividers |
| `--text-primary` | `#e2e8f0` | Headings, primary text |
| `--text-secondary` | `#94a3b8` | Labels, metadata, captions |
| `--text-muted` | `#64748b` | Placeholders, disabled |
| `--accent` | `#3b82f6` | Primary actions, links, active states |
| `--accent-hover` | `#2563eb` | Hover on accent elements |
| `--success` | `#10b981` | Success states, confirmations |
| `--warning` | `#f59e0b` | Warnings, attention needed |
| `--error` | `#ef4444` | Errors, deletions, critical |
| `--info` | `#06b6d4` | Information, tips |

### Light Mode (Optional — only if user requests)

| Token | Hex | Usage |
|-------|-----|-------|
| `--bg-primary` | `#f8fafc` | Page background |
| `--bg-secondary` | `#ffffff` | Cards, panels |
| `--bg-tertiary` | `#f1f5f9` | Hover states, inputs |
| `--border` | `#e2e8f0` | Borders, dividers |
| `--text-primary` | `#0f172a` | Headings, primary text |
| `--text-secondary` | `#475569` | Labels, metadata |
| `--text-muted` | `#94a3b8` | Placeholders, disabled |
| `--accent` | `#2563eb` | Primary actions, links |

---

## Typography

| Role | Font | Size | Weight | Line Height |
|------|------|------|--------|-------------|
| H1 | Inter/System | 24px | 700 | 1.2 |
| H2 | Inter/System | 20px | 600 | 1.3 |
| H3 | Inter/System | 16px | 600 | 1.4 |
| Body | Inter/System | 14px | 400 | 1.5 |
| Small | Inter/System | 12px | 400 | 1.4 |
| Mono | JetBrains Mono / SF Mono | 13px | 400 | 1.4 |

**Rules:**
- Max 3 font sizes per page
- Headings: `font-weight: 600-700`
- Body: `font-weight: 400`
- Code/data: Monospace, always

---

## Spacing Scale

Based on 4px grid:

| Token | Value | Usage |
|-------|-------|-------|
| `--space-1` | 4px | Inline icons, tight gaps |
| `--space-2` | 8px | Tight padding, icon gaps |
| `--space-3` | 12px | Button padding, small gaps |
| `--space-4` | 16px | Card padding, section gaps |
| `--space-5` | 20px | Form sections |
| `--space-6` | 24px | Major section gaps |
| `--space-8` | 32px | Page sections |
| `--space-10` | 40px | Major page sections |

**Density rule:** Default to `--space-4` (16px) padding. Only use larger for major page sections.

---

## Components

### Buttons

**Primary**
```
Background: --accent
Text: white
Padding: 8px 16px
Border-radius: 6px
Font: 14px, weight 500
Hover: --accent-hover
Active: scale(0.98)
```

**Secondary**
```
Background: --bg-tertiary
Text: --text-primary
Border: 1px solid --border
Padding: 8px 16px
Border-radius: 6px
Hover: background lightens 5%
```

**Danger**
```
Background: --error
Text: white
Padding: 8px 16px
Border-radius: 6px
Hover: darken 10%
```

**Ghost**
```
Background: transparent
Text: --text-secondary
Padding: 8px 16px
Hover: --bg-tertiary background
```

### Inputs

```
Background: --bg-tertiary
Border: 1px solid --border
Border-radius: 6px
Padding: 8px 12px
Font: 14px
Focus: border-color --accent, outline none, ring 2px accent/20%
Placeholder: --text-muted
Error: border-color --error
```

### Cards / Panels

```
Background: --bg-secondary
Border: 1px solid --border
Border-radius: 8px
Padding: --space-4 (16px)
Shadow: none (flat design)
Hover (if clickable): border-color --accent
```

### Tables

```
Header: --bg-tertiary, font-weight 600
Rows: alternating --bg-primary / --bg-secondary
Border: 1px solid --border between rows
Cell padding: 12px 16px
Hover row: --bg-tertiary
```

### Badges / Tags

```
Background: --bg-tertiary
Text: --text-secondary
Padding: 2px 8px
Border-radius: 4px
Font: 12px, weight 500
```

**Status variants:**
- Success: bg-green-500/10, text-green-400
- Warning: bg-yellow-500/10, text-yellow-400
- Error: bg-red-500/10, text-red-400
- Info: bg-cyan-500/10, text-cyan-400

---

## Layout Patterns

### Page Structure

```
┌─────────────────────────────┐
│  Header (logo, nav, user)   │  48px height
├─────────────────────────────┤
│                             │
│  Main Content               │  max-width: 1200px, centered
│  (flexible layout)          │  padding: 24px
│                             │
└─────────────────────────────┘
```

### Grid System

- **Desktop:** 12-column grid, 24px gutters
- **Tablet:** 6-column grid, 16px gutters
- **Mobile:** Single column, full width
- **Breakpoints:**
  - sm: 640px
  - md: 768px
  - lg: 1024px
  - xl: 1280px

### Navigation

- **Sidebar** (desktop): Fixed 240px width, collapsible
- **Top bar** (mobile): Hamburger menu
- **Active state:** Accent color left border + background highlight
- **Collapsed:** Icons only, 64px width

---

## Icons

- **Library:** Lucide icons (consistent, lightweight)
- **Size:** 16px default, 20px for buttons
- **Stroke width:** 1.5px
- **Color:** Inherit from text color

---

## HTMX Patterns

### Loading States

```html
<!-- No spinners. Show skeleton or instant text change -->
<button hx-post="/save" hx-disabled-elt="this">
  Save
</button>
<!-- Button disabled instantly, re-enabled on completion -->
```

### Feedback

```html
<!-- Inline notifications, no toasts -->
<div id="notification" class="text-sm">
  <!-- HTMX swaps content here -->
</div>
```

### Forms

```html
<form hx-post="/api/create" hx-target="#result" hx-swap="innerHTML">
  <!-- Fields -->
  <button type="submit">Create</button>
</form>
<div id="result"><!-- Response appears here --></div>
```

---

## Animation Policy

**Allowed:**
- Color transitions: `transition: color 150ms`
- Background transitions: `transition: background 150ms`
- Opacity for disabled states: `opacity: 0.5`

**Forbidden:**
- No fade-in animations on page load
- No slide-in panels
- No loading spinners (use skeleton or text)
- No bounce, elastic, or playful animations

---

## Accessibility

- Minimum contrast ratio: 4.5:1 for normal text
- Focus indicators: 2px solid accent color outline
- Keyboard navigation: All interactive elements focusable
- Screen reader labels: Every icon button has aria-label
- Reduced motion: Respect `prefers-reduced-motion`

---

## Project-Specific Notes

### Concert Tracker
- **Accent color:** Use orange (#f97316) instead of blue for music theme
- **Key view:** Calendar grid, table list, detail modal
- **Data density:** Show 20+ concerts per page, compact rows

### Paris Associations
- **Accent color:** Keep blue (#3b82f6) — official, trustworthy
- **Key view:** Search table, entity detail, conflict graph
- **Data density:** Heavy tables, expandable rows

### Consensus
- **Accent color:** Purple (#8b5cf6) — collaborative, creative
- **Key view:** Voting cards, results dashboard
- **Interaction:** Real-time updates via HTMX polling

### Mairie-Watch
- **Accent color:** Indigo (#4f46e5) — civic, institutional, trustworthy
- **Key view:** PDF list, decision detail, classification results
- **Data density:** Document tables with metadata, expandable rows
- **Interaction:** Pipeline trigger, real-time classification updates

---

## Implementation Notes

### Tailwind CSS Classes

```css
/* Base setup */
@tailwind base;
@tailwind components;
@tailwind utilities;

/* Color tokens via CSS variables */
:root {
  --bg-primary: #0f1115;
  --bg-secondary: #161922;
  /* ... etc */
}

/* Utility classes */
.btn-primary {
  @apply bg-accent text-white px-4 py-2 rounded-md font-medium;
  @apply hover:bg-accent-hover active:scale-[0.98];
}
```

### FastAPI + Jinja2 Setup

```python
# Templates use the design system
@app.get("/")
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "theme": "dark"  # Always default to dark
    })
```

### HTMX + Server-Side Rendering

- All UI rendered server-side
- HTMX for partial updates
- No client-side state management needed
- Forms submit to FastAPI, return HTML fragments

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-04-21 | v1.0 — Initial design system | LightyClaw |

---

## Usage

1. Include this `DESIGN.md` in every new project root
2. Reference it when implementing UI components
3. Update project-specific notes section for each project
4. Keep consistent across all LightyClaw projects
