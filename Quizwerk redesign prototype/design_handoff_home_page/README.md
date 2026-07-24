# Handoff: Quizwerk (HQuiz) Home Page Redesign

## Overview
A redesigned marketing home page for the quiz platform currently at quiz.campilot.org ("HQuiz", working rename: "Quizwerk"). The page targets two audiences — School (teachers, lecturers, students, parents) and Corporate (businesses, employees, HR personnel) — and links into the product's Generate-Quiz and Join-Live-Quiz flows. This handoff covers the **home page only**; the interactive generate/quiz/results screens in the prototype are demo stubs, not part of this deliverable (their entry points are).

## About the Design Files
The files in this bundle are **design references created in HTML** — a prototype showing intended look and behavior, not production code to copy directly. Your task is to **recreate this design in the target codebase's existing environment** (the current site is Next.js/React — reuse its stack, routing and component patterns). The prototype file `Quizwerk Landing.dc.html` uses a custom template runtime; read it for markup/values, don't port the runtime.

## Fidelity
**High-fidelity.** Colors, typography, spacing, copy and states are final intent. Recreate pixel-perfectly with the codebase's conventions (CSS modules/Tailwind/etc.).

## Design Tokens
Fonts: **Archivo** for everything (Google Fonts). Headings weight **800**, letter-spacing −0.015 to −0.02em; body weight 400.

Colors:
- Ground `--color-bg`: `#f3f2f2`
- Ink `--color-text`: `#201e1d`
- Divider: `color-mix(in srgb, #201e1d 40%, transparent)`, always **2px** rules
- Brand navy (accent): `#0a3264`
- Navy ramp: 100 `#e7ecf3` · 200 `#cdd8e6` · 300 `#a5b7d0` · 400 `#476490` · 600 `#082a54` (hover) · 700 `#062042` (small accent text ≥4.5:1) · 800 `#041730` · 900 `#030f20`
- Neutral track for bars/progress: light gray ≈ `#e4e3e2`

Rules of the visual language (from the Modernist system):
- **Zero border-radius** on all UI (only device-mockup hardware is rounded)
- Everything flush left — headings, copy, and labels inside buttons; never centered
- 2px horizontal rules draw the section seams; grid structure stays visible
- Navy is spent sparingly: primary buttons, small marks (8–10px squares), stat numerals, and exactly two full navy field moments (the Categories band and the closing poster)
- Photography renders grayscale (`filter: grayscale(1) contrast(1.08)`)
- Button labels never wrap (`white-space: nowrap`)
- Focus: `outline: 2px solid <accent>; outline-offset: 2px` (paper-colored outline inside the navy band)

Spacing rhythm: 28px leading unit; section padding 70–84px; content column `max-width: 1200px` with `padding-inline: clamp(20px, 5vw, 72px)`.

## Screens / Views — Home Page, top to bottom

### 1. Nav bar
Flex row, bottom rule 2px. Brand wordmark (Archivo 800, 18px) left with `margin-right:auto`; links: Product, Categories, Pricing, Join a quiz (15px, ink, hover navy); primary button "Generate a quiz" (navy fill `#0a3264`, paper text, 14px Archivo 800, padding ~10px 16px, hover `#082a54`). Links are anchor-scrolls; button routes to /generate.

### 2. Hero (two-column grid, `repeat(auto-fit, minmax(320px,1fr))`, gap 56px/clamp(32px,5vw,88px), align center)
Left:
- H1 display: "Type a topic." / "Run the quiz." — two lines, `clamp(42px, 5.4vw, 76px)`, line-height 1.06, letter-spacing −0.02em, optical left shift `margin-left:-0.058em`
- Sub (17px/28px, max 52ch): "Quizwerk turns any topic into a ready-to-run quiz — question types you choose, answer keys included, delivered live or exported to PDF. For the classroom and the training room alike."
- Buttons: primary "Generate a quiz" → /generate; ghost "Join a live quiz" (2px ink border, transparent) → /quiz-access
Right — **laptop + phone mockup** (decorative, aria-hidden):
- MacBook-style laptop: dark bezel `#101012`, radius 16px top, camera dot, aluminum base bar (gradient `#e4e4e8→#b6b6bd`, radius 0 0 12px, center lip). Screen shows presenter view: top bar (pulsing 7px navy square + "LIVE · 4F7KQ2" 11px uppercase tracking 0.1em in navy-700, right "3 / 5" tnum) above 2px rule; question (Archivo 800 16px); three answer rows, each = label line (letter + text left, % right, 12px) over full-width 8px bar (fill navy `#0a3264` for leader 62%, navy-300 for 21%/17%); footer "24 OF 26 ANSWERED" 11px uppercase muted. Content reserves 80px right padding where the phone overlaps; laptop block has `margin-right:96px`.
- iPhone-style phone, absolute bottom-right, width 164px: bezel `#101012` radius 28px, Dynamic Island pill, participant view (tiny LIVE tag, same question 11px, options A/B/C with A selected — 1.5px navy border + `#e7ecf3` fill — navy "Submit" button), home indicator. Container has 28px bottom padding so the phone hangs below the laptop base.

### 3. Stat row (grid auto-fit minmax(190px,1fr), 2px rules above and below the section)
Four stats: numeral (Archivo 800, clamp(34px,3.4vw,48px), **navy**) over uppercase 13px label at 70% ink: `12s / Topic to finished draft`, `3 / Question formats`, `50 / Questions per quiz, max`, `0 / Hours spent formatting`.

### 4. Categories band — FULL-BLEED NAVY (`#0a3264`, edge to edge)
Inner content in the 1200px column, padding 84px. All type reversed to paper `#f3f2f2`.
- Kicker "WHO IT'S FOR" (13px, tracking 0.08em, navy-200 `#cdd8e6`)
- H2 "Pick the seat you're sitting in" (32px/42px)
- Sub at 80% paper: "Two worlds, one generator. Choose a persona and we start you with a quiz that fits it — change anything before you run it."
- Two columns (auto-fit minmax(300px,1fr)): **School** ("Teachers, lecturers, students and parents.") and **Corporate** ("Businesses, employees and HR personnel.")
- Persona rows, each a full-width button: top rule 2px at 30% paper; 8px paper square; label (Archivo 800 17px paper) over one-line desc (13.5px at 72% paper); trailing paper "→". Hover: 12% paper tint. Personas: Teacher (Class quizzes, homework checks, exam revision), Lecturer (Lecture recaps and seminar prep for large cohorts), Student (Self-testing before the exam), Parent (Practice at home, marked automatically) · Business (Onboarding and product knowledge at scale), Employee (Upskill and certify at your own pace), HR personnel (Compliance training with an audit trail).
- Behavior: clicking a persona routes to /generate pre-filled with a persona-appropriate topic and shows a "Set up for: {persona}" tag there.

### 5. Features (kicker "WHAT QUIZWERK DOES"; 3 rows separated by 2px rules, each flex-wrap: number / text block / vignette)
Row = index numeral ("01" 15px tnum 800) + title (24px 800) + copy (15.5px/28px at 78% ink, max 52ch) + flat vignette panel (2px divider border, padding 20px, max-width 420px):
- **01 Generate from a topic** — vignette: "TOPIC" microlabel, ink-bordered input showing "Fire safety in the workplace", tags "Multiple choice" (navy tint) + "5 questions" (outline), navy "Generate quiz" button
- **02 Run it live** — vignette: "SESSION CODE" microlabel, giant code "4F7–KQ2" (Archivo 800, ~52px, tracking 0.08em), pulsing navy square + "24 participants joined"
- **03 Results, kept** — vignette: "CORRECT ANSWERS BY QUESTION", three rows `Q1/Q2/Q3` + 10px bars (92% navy, 71% navy, 38% navy-300) + tnum percentages

### 6. How it works (kicker; grid auto-fit minmax(210px,1fr))
Four steps, each: numeral, 18px title, short line: 01 Enter your topic / 02 Pick the format / 03 Review the draft / 04 Run it or ship it (copy in prototype).

### 7. "In the room" split (grid auto-fit minmax(300px,1fr))
Left: kicker "IN THE ROOM", H2 "Built for the room, not the browser tab" (32px), note (15.5px at 78% ink). Right: photo/screenshot slot, aspect 951/665, **grayscale filter**.

### 8. Pricing (id="pricing", 2px rule above, kicker "PRICING", H2 "Pick a plan that fits how you train")
Three columns (auto-fit minmax(250px,1fr)): each = 2px top rule (divider gray; **navy** on the featured Pro column), plan name (20px 800; Pro carries a "MOST TEAMS" microlabel in navy-700), price (44px 800: $0 / $20 "/ month" / $100 "/ year" — unit 15px at 70% ink), feature list (15px rows, each with an 8px navy square, gap 12px), button pinned to column bottom, shrunk to label (never full-width): ghost "Start free" / **primary "Get Pro"** / ghost "Go Premium". Features per plan as in prototype (Free: 5 quizzes a month, basic types, save & share, community templates; Pro: unlimited generation, advanced types, edit & customise, export PDF/text, priority support; Premium: everything in Pro, early access, personalised templates, premium support).

### 9. Testimonials (kicker "FROM CLASSROOMS AND BOARDROOMS"; grid auto-fit minmax(260px,1fr))
Three figures, each: 2px top rule, quote (Archivo 800 19px/27px, curly quotes), attribution (13px uppercase at 70% ink): Dana M. — Compliance trainer, logistics · R. Okafor — L&D lead, fintech · T. Adeyemi — Secondary school teacher (quote copy in prototype; placeholder personas — swap for real ones).

### 10. Poster close — FULL-BLEED NAVY
H3 "The next quiz writes itself." (clamp(34px,4.2vw,56px), line-height 1.06, paper) + ghost button with paper border/text: "Generate your first quiz — free".

### 11. Footer (13px at 70% ink, flex space-between wrap)
Brand wordmark (15px 800 ink) · links Product / Categories / Pricing / Join a live quiz · "© 2026 Quizwerk. All rights reserved."

## Interactions & Behavior
- Nav/footer links smooth-scroll to #categories / #product / #pricing on the home page
- "Generate a quiz" (nav, hero, pricing, poster) → generate page; "Join a live quiz" → join page; persona click → generate page with `?persona=&topic=` prefill
- Pulsing live dots: opacity 1→0.2→1, 1.4s ease-in-out infinite
- Hovers: primary buttons darken to `#082a54`; ghost buttons 7% ink tint; persona rows 12% paper tint; links turn navy
- Responsive: all grids are `auto-fit/minmax` so sections collapse to one column on mobile with no breakpoint-specific layouts; hero mockup stacks below text; nav wraps
- All hit targets ≥ 44px on touch

## State Management
Home page is static apart from anchor scrolling. Persona selection carries {persona, category: school|corporate, topic} to the generate flow (querystring or route state).

## Assets
- Archivo (Google Fonts, weights 400–800)
- The laptop/phone mockup is pure HTML/CSS (no images)
- Section 7 expects one real product screenshot or classroom photo, displayed grayscale
- Lucide icons if icons are added later (none on the home page currently)

## Files
- `Quizwerk Home (standalone).html` — the prototype as one self-contained file: open it directly in any browser (double-click works offline) to see the design and click through the demo flows. It is compiled/minified — use it to LOOK at the design; implement from this README's spec.
- `styles.css` — the design-system token sheet and component classes (.btn, .tag, .seg, .field, .nav). NOTE: its `--color-accent*` values are the original red; the build overrides them to the navy ramp listed above — use the navy values.
