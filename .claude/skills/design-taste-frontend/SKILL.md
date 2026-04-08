---
name: design-taste-frontend
description: Senior UI/UX Engineer. Architect digital interfaces overriding default LLM biases. Enforces metric-based rules, strict component architecture, CSS hardware acceleration, and balanced design engineering. Use when building frontend UIs, landing pages, dashboards, components, or any web interface that needs to avoid generic AI aesthetics.
---

# High-Agency Frontend Skill

## 1. ACTIVE BASELINE CONFIGURATION

* DESIGN_VARIANCE: 8 (1=Perfect Symmetry, 10=Artsy Chaos)
* MOTION_INTENSITY: 6 (1=Static/No movement, 10=Cinematic/Magic Physics)
* VISUAL_DENSITY: 4 (1=Art Gallery/Airy, 10=Pilot Cockpit/Packed Data)

AI Instruction: Baseline is set to (8, 6, 4). Adapt values dynamically based on user requests.

## 2. DEFAULT ARCHITECTURE & CONVENTIONS

* DEPENDENCY VERIFICATION [MANDATORY]: Before importing ANY 3rd party library, check package.json. If missing, output the install command first.
* Framework: React or Next.js. Default to Server Components (RSC).
* RSC SAFETY: Global state works ONLY in Client Components.
* ANTI-EMOJI POLICY [CRITICAL]: NEVER use emojis anywhere. Use Radix or Phosphor icons or SVG.
* Viewport Stability [CRITICAL]: NEVER use h-screen for Hero sections. ALWAYS use min-h-[100dvh].
* Grid over Flex-Math: NEVER use complex flexbox percentage math. ALWAYS use CSS Grid.
* Icons: Use @phosphor-icons/react or @radix-ui/react-icons. Standardize strokeWidth globally.

## 3. DESIGN ENGINEERING DIRECTIVES

Rule 1: Deterministic Typography
* Display/Headlines: text-4xl md:text-6xl tracking-tighter leading-none
* ANTI-SLOP: Inter is BANNED for Premium/Creative. Use Geist, Outfit, Cabinet Grotesk, or Satoshi.
* Serif fonts BANNED for Dashboard/Software UIs.

Rule 2: Color Calibration
* Max 1 Accent Color. Saturation under 80%.
* THE LILA BAN: AI Purple/Blue aesthetic is BANNED. No purple glows, no neon gradients.
* Use neutral bases (Zinc/Slate) with singular accents (Emerald, Electric Blue, Deep Rose).

Rule 3: Layout Diversification
* ANTI-CENTER BIAS: Centered Hero/H1 BANNED when DESIGN_VARIANCE above 4.
* Force Split Screen, Left Aligned, or Asymmetric Whitespace layouts.

Rule 4: Anti-Card Overuse
* For VISUAL_DENSITY above 7, generic cards are BANNED. Use border-t, divide-y, or negative space.

Rule 5: Interactive UI States [MANDATORY]
* Loading: Skeletal loaders (no generic spinners).
* Empty States: Beautifully composed.
* Error States: Clear inline reporting.
* Tactile Feedback: On :active use -translate-y-[1px] or scale-[0.98].

Rule 6: Forms
* Label above input. Error text below. Use gap-2 for input blocks.

## 4. CREATIVE PROACTIVITY

* Liquid Glass: Beyond backdrop-blur. Add 1px inner border (border-white/10) and inner shadow.
* Magnetic Micro-physics (MOTION_INTENSITY above 5): Use Framer Motion useMotionValue and useTransform ONLY.
* Staggered Orchestration: Use staggerChildren or CSS animation-delay cascades.
* Layout Transitions: Always use Framer Motion layout and layoutId props.

## 5. PERFORMANCE GUARDRAILS

* Hardware Acceleration: Animate ONLY via transform and opacity. NEVER animate top/left/width/height.
* DOM Cost: Grain/noise filters on fixed pseudo-elements ONLY.
* Z-Index Restraint: No arbitrary z-50 spam. Use for Navbars, Modals, Overlays only.

## 6. DIAL DEFINITIONS

DESIGN_VARIANCE (1-10):
* 1-3: Symmetric grids, centered layouts
* 4-7: Overlapping elements, varied aspect ratios
* 8-10: Masonry, fractional CSS Grid, massive empty zones
* MOBILE OVERRIDE: Levels 4-10 MUST collapse to single-column on viewports under 768px

MOTION_INTENSITY (1-10):
* 1-3: CSS :hover and :active states only
* 4-7: transition cubic-bezier(0.16,1,0.3,1), animation-delay cascades
* 8-10: Framer Motion hooks, scroll-triggered reveals

VISUAL_DENSITY (1-10):
* 1-3: Art Gallery Mode. Huge whitespace.
* 4-7: Daily App Mode. Normal spacing.
* 8-10: Cockpit Mode. Tiny paddings, 1px dividers. font-mono for all numbers.

## 7. FORBIDDEN PATTERNS

Visual: NO neon outer glows, NO pure #000000 (use Zinc-950), NO oversaturated accents, NO gradient text on large headers, NO custom mouse cursors
Typography: NO Inter font (BANNED), NO oversized H1s, NO Serif on dashboards
Layout: NO 3-column equal card layouts. Use 2-col zig-zag or asymmetric grid.
Content: NO generic names (John Doe banned), NO generic SVG egg avatars, NO round fake numbers, NO startup slop names (Acme, Nexus), NO filler words (Elevate, Seamless, Unleash banned)
External: NO Unsplash. Use picsum.photos/seed/{string}/800/600. shadcn/ui MUST be customized.

## 8. CREATIVE ARSENAL

Navigation: Mac OS Dock Magnification, Magnetic Button, Gooey Menu, Dynamic Island, Radial Menu
Layout: Bento Grid, Masonry, Chroma Grid, Split Screen Scroll, Curtain Reveal
Cards: Parallax Tilt, Spotlight Border, True Glassmorphism, Holographic Foil, Morphing Modal
Scroll: Sticky Stack, Horizontal Hijack, Zoom Parallax, SVG Path Drawing, Liquid Swipe
Typography: Kinetic Marquee, Text Mask Reveal, Text Scramble, Gradient Stroke Animation
Micro-interactions: Particle Explosion Button, Skeleton Shimmer, Ripple Click, Mesh Gradient, Lens Blur

## 9. FINAL PRE-FLIGHT CHECK

- [ ] Mobile layout collapse guaranteed for high-variance designs
- [ ] Full-height sections use min-h-[100dvh] not h-screen
- [ ] useEffect animations have cleanup functions
- [ ] Empty, loading, and error states provided
- [ ] CPU-heavy animations isolated in their own Client Components
- [ ] No 3-column equal card grids | No Inter font | No pure #000000