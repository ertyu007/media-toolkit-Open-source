---
name: Clipora
description: "Local-first Windows media toolkit landing page"
colors:
  ground: "#0b0b0f"
  ground-deep: "#08080c"
  panel: "#14141b"
  panel-deep: "#111117"
  rail: "#2a2a35"
  ink: "#f1eff8"
  muted: "#a7a4b6"
  dim: "#8c899c"
  faint: "#6f6c7f"
  signal: "#8b5cf6"
  signal-light: "#c4b5fd"
  signal-deep: "#6d28d9"
  complete: "#5eead4"
  armed: "#fbbf24"
typography:
  display:
    fontFamily: '"IBM Plex Sans Thai", "Leelawadee UI", "Segoe UI", Tahoma, sans-serif'
    fontSize: "clamp(2.65rem, 5vw, 5rem)"
    fontWeight: 600
    lineHeight: 1.08
    letterSpacing: "-0.03em"
  headline:
    fontFamily: '"IBM Plex Sans Thai", "Leelawadee UI", "Segoe UI", Tahoma, sans-serif'
    fontSize: "clamp(1.8rem, 3.2vw, 2.9rem)"
    fontWeight: 600
    lineHeight: 1.22
    letterSpacing: "-0.025em"
  body:
    fontFamily: '"IBM Plex Sans Thai", "Leelawadee UI", "Segoe UI", Tahoma, sans-serif'
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.75
  label:
    fontFamily: '"IBM Plex Mono", "Cascadia Code", Consolas, monospace'
    fontSize: "0.75rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "0.16em"
rounded:
  hairline: "2px"
  focus: "4px"
  xs: "6px"
  node: "7px"
  sm: "8px"
  brand: "9px"
  md: "10px"
  callout: "12px"
  lg: "14px"
  route: "16px"
  xl: "18px"
  pill: "99px"
spacing:
  xs: "8px"
  sm: "12px"
  md: "16px"
  lg: "24px"
  xl: "32px"
  xxl: "44px"
  section: "clamp(64px, 9vw, 116px)"
components:
  button-primary:
    backgroundColor: "{colors.signal-deep}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "0 20px"
    height: "48px"
  button-primary-hover:
    backgroundColor: "#7c3aed"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "0 20px"
    height: "48px"
  button-ghost:
    backgroundColor: "rgba(255,255,255,0.035)"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "0 20px"
    height: "48px"
  nav-download:
    backgroundColor: "#191922"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "8px 14px"
  chip:
    backgroundColor: "rgba(139,92,246,0.09)"
    textColor: "#d6ccf7"
    rounded: "{rounded.xs}"
    padding: "3px 8px"
  panel:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.muted}"
    rounded: "{rounded.lg}"
    padding: "clamp(20px, 2.4vw, 30px)"
  render-deck:
    backgroundColor: "{colors.panel-deep}"
    textColor: "{colors.ink}"
    rounded: "{rounded.xl}"
    padding: "16px"
---

# Design System: Clipora

## Overview

**Creative North Star: "The Studio Deck"**

Clipora's site is a working render deck, not a brochure. The media pipeline is the first object on the page, already running: a waveform, a timecode, four queued jobs, and one active row. The rest of the page follows the same instrument logic — features are rack modules, the workflow is a signal route, and downloads are a release manifest. The visitor should feel the product operating before reading a list of claims.

The world is **Midnight Amethyst**, the existing app theme: a near-black control surface, raised charcoal panels, hairline rails, and a violet signal that means "this is the live path." Mint marks completed output; amber marks an armed or caution state. The palette is restrained on purpose. Violet is an operational signal, not a wash, and the one animated moment lives in the deck.

The copy is direct, formal Thai. Technical names stay as they are (FFmpeg, yt-dlp, Demucs, H.264) because they are the product's own vocabulary. No invented screenshots, benchmarks, testimonials, or customer logos appear; the deck is explicitly labeled synthetic data.

**Key Characteristics:**
- One live object: the hero render deck, with a synthetic job cycle and a static reduced-motion state.
- Dark, tonal surfaces separated by 1px rails rather than drop shadows.
- Violet signal used sparingly; mint for completion; amber for caution.
- IBM Plex Sans Thai for voice, IBM Plex Mono for measurement.
- Drawn 1.6px line icons, never glyphs or color emoji.
- Promotion and download first; proof and limits are visible, not buried.

## Colors

Midnight Amethyst: a near-black ground, charcoal panels, and a single electric-violet signal, with mint and amber reserved for machine state.

### Primary
- **Amethyst Signal** (#8b5cf6): active progress, live job rows, focus rings, primary button border, route nodes, and the hero waveform. It is the color of "running now."
- **Amethyst Light** (#c4b5fd): timecode, active labels, hover text on dark surfaces, and small technical highlights. It is a tint of the signal, not a second accent.
- **Amethyst Deep** (#6d28d9): the primary button fill and the dark end of signal gradients. White text sits on it at full contrast.

### Secondary
- **Completed Mint** (#5eead4): completed job states, finished queue rows, and the deck's running-indicator dot. It never appears on a primary action.
- **Armed Amber** (#fbbf24): the SmartScreen caution callout only. It is an alert color, not a decorative accent.

### Neutral
- **Control Ground** (#0b0b0f): the page field, with a slightly deeper #08080c used for shadows and code wells.
- **Raised Panel** (#14141b): cards, racks, and the deck body; #111117 is the secondary panel tone.
- **Hairline Rail** (#2a2a35): 1px borders and dividers; the soft variant is `rgba(255,255,255,0.07)`.
- **Ink** (#f1eff8): headings and primary body text on dark surfaces.
- **Muted** (#a7a4b6): supporting copy and unselected labels.
- **Dim** (#8c899c): metadata, secondary labels, and quiet table text.
- **Faint** (#6f6c7f): the lowest-priority mono labels and tick marks; never body copy.

**The Signal Rarity Rule.** Violet is an operational signal, not a surface wash. It appears on the primary action, the active job, progress, and focus. It never colors long prose, and it never fills the page field.

**The Two-State Rule.** Mint means finished; amber means armed or caution. Neither color is used as a generic accent, and they are never mixed within one state.

## Typography

**Display Font:** IBM Plex Sans Thai (with Leelawadee UI, Segoe UI, Tahoma, sans-serif)
**Body Font:** IBM Plex Sans Thai (same stack)
**Label/Mono Font:** IBM Plex Mono (with Cascadia Code, Consolas, monospace)

**Character:** IBM Plex Sans Thai carries the formal Thai voice with a humanist, slightly technical skeleton. IBM Plex Mono is the instrument readout: timecode, filenames, logs, CLI examples, and measurement labels. The pairing reads as a tool, not a magazine.

### Hierarchy
- **Display** (600, clamp 2.65–5rem, 1.08): the hero statement. Three lines maximum on desktop; balance the lines, do not stretch the measure.
- **Headline** (600, clamp 1.8–2.9rem, 1.22): section headings and the download title. The heading carries its own weight; no kicker or eyebrow sits above it.
- **Title** (600, 1.22–1.45rem, 1.35): panel, route, step, and CLI titles. The callout subhead is 0.975rem because it is a note, not a section title.
- **Body** (400, 1rem/1.75; panel copy 0.94rem/1.8): supporting prose. Keep body measure around 54–56ch on this page; the hero lede is capped at 56ch.
- **Label** (400–500, 0.75rem/1.5, 0.16em uppercase): mono labels for panels, timecode, queues, manifests, and route tags. All functional text stays at or above 12px.

**The Measured Mono Rule.** Monospace is for data, code, timecode, and measurement. It is never used as a costume for ordinary prose.

## Layout

The page uses a 1180px maximum container with 48px gutters (32px below 620px). The hero is an asymmetric two-column split, roughly 1.02fr / 0.98fr with a 36–74px gap; below 920px it stacks with the deck capped at 560px. The feature rack is a 12-column grid with 16px gaps: audio spans 7, video spans 5, and URL/stem panels span the full width. The workflow is a four-step route that turns into a vertical rail below 760px. Install is a 0.82fr / 1.18fr split with a sticky left column above 920px; download is a 1.16fr / 0.84fr split.

Sections are separated by 1px rails and generous vertical rhythm: `clamp(64px, 9vw, 116px)` above 620px, 56px below. The sticky nav is 68px tall on desktop and 60px on mobile. Headings have more space above than below; panel internals use 8/12/16/24px steps. The page is designed to survive at 390px with no horizontal overflow, wrapping code blocks, and a single-column document grid.

## Elevation & Depth

The system is flat and tonal, not lifted. Panels are raised by background value, a 1px rail, and a single inset top highlight (`inset 0 1px 0 rgba(255,255,255,.06)`). There are no wide drop shadows, no zero-offset colored halos, and no glass or blur. The deck's violet pool is an ambient radial wash painted into the ground, not a shadow under the card.

**The Rail-First Rule.** Depth comes from a 1px rail, a tonal step, and an inset highlight. If a surface needs more separation, adjust its value or its spacing before adding a drop shadow.

## Shapes

Panels use 14px corners; the route surface uses 16px; the render deck and download deck use 18px; the callout uses 12px; buttons use 10px; small controls, nav actions, and the brand mark use 8–9px; chips use 6px; route nodes use 7px. Progress bars, scrollbars, and status pills are fully rounded (`99px`). Borders are always 1px; focus rings are 2px with a 4px offset. Route nodes are 13px circles; status dots are 5–6px. Icons are authored SVG with a 1.6px stroke, round caps, and round joins. The form language is instrument-like: soft enough to feel modern, square enough to read as a control surface.

## Components

### Buttons
- **Shape:** 10px radius, 48px minimum height, 20px horizontal padding, 1px border.
- **Primary:** Amethyst Deep fill with an Amethyst Signal border and white text; hover shifts to #7c3aed with a lighter border. The icon is drawn, 18px, and inherits the text color.
- **Ghost:** translucent white fill (`rgba(255,255,255,.035)`) with a hairline rail; hover raises the fill and border one step. Used for the secondary docs action.
- **Focus:** 2px Amethyst Light outline with a 4px offset; never remove the ring.

### Chips
- **Style:** 6px radius, violet-tinted fill (`rgba(139,92,246,.09)`), 1px #373150 border, #d6ccf7 text, 3px/8px padding. Used for format and capability tags, not for navigation.
- **State:** Chips are static labels here; they do not pretend to be filters.

### Cards / Containers
- **Corner Style:** 14px panels, 18px deck/download, 1px rails.
- **Background:** raised #14141b over the #0b0b0f ground; the deck uses a subtle vertical tonal gradient.
- **Shadow Strategy:** inset top highlight only; no drop shadows.
- **Internal Padding:** `clamp(20px,2.4vw,30px)` for panels, 16px for the deck, 44px for the download deck (26px on mobile).
- **Nesting:** lists inside panels use spacing and dividers, not a second bordered card.

### Inputs / Fields
- The site has no form inputs. The only interactive control is the deck toggle: 28px square, 8px radius, #171720 fill, hairline #32323e rail, with hover lift and a visible focus ring.

### Navigation
- Sticky, 94%-opaque #0a0a0e, 1px bottom rail. Brand mark is a 30px rounded square with a drawn waveform. Desktop links are 0.9rem muted text that resolves to ink on hover; the nav download is a compact 8px/14px button. Below 920px the text links collapse; the download action remains. The GitHub link keeps its drawn mark and hides its label below 620px.

### Render Deck
- The signature component: a raised 18px panel with a mono header, a 64-bar waveform, timecode/total, four job rows, a three-stage progress rail, a log line, and a synthetic-data label.
- One job is active at a time; completed jobs turn mint, the active row uses a 10% violet tint, and the progress rail fills with a violet gradient. The cycle is synthetic and labeled.
- The deck pauses on hover and focus, can be paused by the toggle, pauses off-screen via IntersectionObserver, and renders a single completed job when `prefers-reduced-motion: reduce` is set. The toggle is hidden in that state.

### Document Rows
- The docs grid uses two columns above 760px and one below. Each row is a 1px bottom rail, a title, a muted description, and a drawn arrow that shifts 2px up/right on hover. No card background; the row is the component.

## Do's and Don'ts

### Do:
- **Do** keep violet on the signal path: primary action, active job, progress, focus.
- **Do** use 1px rails, tonal steps, and inset highlights for depth.
- **Do** set functional text at 12px or larger; use tabular numerals for timecode.
- **Do** label demonstration data as synthetic and keep every claim traceable to the repository docs.
- **Do** draw icons as inline SVG with a consistent 1.6px stroke.
- **Do** respect reduced motion, keyboard focus, and 390px width.

### Don't:
- **Don't** put a kicker or eyebrow above a heading; the heading speaks for itself.
- **Don't** use gradient text, glass/blur decoration, or zero-offset colored halos.
- **Don't** use hard offset shadows or colored side stripes on cards or callouts.
- **Don't** use color emoji, Unicode glyphs, or an icon font in place of drawn icons.
- **Don't** nest cards inside cards; use spacing and dividers.
- **Don't** wash the page in violet or use mint/amber as generic accents.
- **Don't** invent screenshots, benchmarks, testimonials, customer logos, or features that are not in the docs.
- **Don't** use monospace for prose or set body copy below 12px.
