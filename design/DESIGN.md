# DESIGN.md — "Brushed Silver Noir" · v2

> **Version 2** (system version 1.1.0, 2026-11-04). This is `design.md` plus five learnings from its first real build, the DΛЯK Audio Model 01 demo. Nothing from v1 was removed or renamed; every addition is marked **New in v2**.
>
> A reusable design template for any project, in any stack: websites, apps, prototypes, tests, decks, Framer, React, plain HTML/CSS.
> **Source:** structure and motion extracted layer by layer from the Portfolite Framer template. Text colors are a **brushed silver-charcoal**, sampled pixel by pixel from studio artwork.
> **Signature:** motion first. Live backgrounds, blur reveals, heavy springs, tickers, a reactive cursor.

**How to use this file:** Sections 1–9 are tool-agnostic and are the source of truth. Section 10 maps everything to Framer. Hand this file to any designer, developer or AI agent and it is enough to rebuild the theme.

**New in v2, at a glance:**

| # | Learning | Where |
|---|---|---|
| 1 | Split headlines into words, each carrying its own metal gradient | 3.3 |
| 2 | A dark halo keeps headlines and copy crisp over live backgrounds | 3.4 |
| 3 | Mist brightness depends on its role: hero underlay vs. closing section | 6.3 |
| 4 | Reveal anything already scrolled past, so anchor jumps never leave hidden content | 6.6 |
| 5 | Optional signature hero: monochrome liquid chrome | 6.9 |

---

## 1. Theme

Monochrome, cinematic, premium. A pure black stage, near-black glass surfaces, metallic silver type, and almost no color. Contrast comes from **light, blur and motion**, never from hue.

**Mood words:** dark luxury · machined metal · editorial · calm confidence · cinematic.

**Imagery:** black-and-white photography only. Color never enters through images.

---

## 2. Design tokens (paste-ready)

```css
:root {
  /* Surfaces */
  --bg:               #000000;
  --surface:          #0D0D0D;
  --surface-nav:      rgba(0, 0, 0, 0.80);
  --border:           rgba(255, 255, 255, 0.10);

  /* Brushed silver-charcoal (headlines, labels) */
  --silver-highlight: #DCDCDC;
  --silver-light:     #C2C2C2;
  --silver-mid:       #808080;
  --silver-charcoal:  #464646;
  --silver-gradient:  linear-gradient(180deg, #DCDCDC 0%, #C2C2C2 30%, #808080 62%, #464646 100%);

  /* Reading text */
  --text-body:        #E6E4DF;                  /* off-white */
  --text-secondary:   rgba(230, 228, 223, 0.60);

  /* Single accent */
  --accent-star:      #FFD700;                  /* review stars only */

  /* Fonts */
  --font-display: "Satoshi", "Inter", system-ui, sans-serif;
  --font-title:   "Plus Jakarta Sans", "Inter", system-ui, sans-serif;
  --font-body:    "Inter Display", "Inter", system-ui, sans-serif;

  /* Glass blur levels */
  --blur-button:  5px;
  --blur-label:   6px;
  --blur-nav:     12px;
  --blur-card:    50px;
  --blur-pill:    68px;

  /* Radii in use */
  --radius-xs: 4px;
  --radius-sm: 17px;
  --radius-md: 20px;
  --radius-lg: 48px;

  /* Easing */
  --ease-standard: cubic-bezier(0.44, 0, 0.56, 1);  /* template's tween curve */
  --ease-out-soft: cubic-bezier(0.16, 1, 0.3, 1);   /* CSS stand-in for springs */
}
```

Same tokens as JSON, for design tools and JS:

```json
{
  "color": {
    "bg": "#000000", "surface": "#0D0D0D", "surfaceNav": "rgba(0,0,0,0.80)", "border": "rgba(255,255,255,0.10)",
    "silver": { "highlight": "#DCDCDC", "light": "#C2C2C2", "mid": "#808080", "charcoal": "#464646" },
    "text": { "body": "#E6E4DF", "secondary": "rgba(230,228,223,0.60)" },
    "accent": { "star": "#FFD700" }
  },
  "blur": { "button": 5, "label": 6, "nav": 12, "card": 50, "pill": 68 },
  "radius": { "xs": 4, "sm": 17, "md": 20, "lg": 48 },
  "breakpoints": { "tablet": 810, "desktop": 1200 }
}
```

---

## 3. Color

### 3.1 Brushed silver-charcoal (locked)

Sampled from the letter pixels of six #DARK_MUSIC images. Neutral grey, with no blue or warm cast.

| Token | Value | Measured range | Role |
|---|---|---|---|
| `silver-highlight` | `#DCDCDC` | `#D7D7D7`–`#E3E3E3` | Specular glints, top edge of letters |
| `silver-light` | `#C2C2C2` | `#B5B5B5`–`#C2C2C2` | Upper face of the metal |
| `silver-mid` | `#808080` | `#7A7A7A`–`#888888` | Body of the metal |
| `silver-charcoal` | `#464646` | `#424242`–`#4B4B48` | Shadow side, bottom of letters |

### 3.2 Where each color goes

| Text | Treatment |
|---|---|
| **H1 / H2 headlines** | Brushed-silver gradient fill (3.3) |
| **H3 / H4, card titles** | Brushed-silver gradient, or flat `silver-light` at small sizes |
| **Taglines, labels, badges** | Flat `silver-light`, UPPERCASE, wide tracking `0.25em`–`0.4em` (the engraved tagline treatment) |
| **Body and large body** | `text-body` |
| **Small body, captions, meta** | `text-secondary` |
| **Button labels** | `text-body` |
| **Review stars** | `accent-star`, the only color in the system |

### 3.3 Brushed-silver headline

```css
.headline-silver {
  background:
    repeating-linear-gradient(0deg,                     /* fine horizontal brushed grain */
      rgba(255, 255, 255, 0.05) 0 1px,
      rgba(0, 0, 0, 0.06) 1px 2px),
    var(--silver-gradient);                              /* light-to-charcoal sweep */
  -webkit-background-clip: text;
          background-clip: text;
  color: transparent;
}

.label-engraved {
  color: var(--silver-light);
  text-transform: uppercase;
  letter-spacing: 0.3em;
}
```

For image or video work, apply the same four stops as a vertical metal gradient with horizontal brushed grain and bright bevel edges, as in the #DARK_MUSIC artwork.

**New in v2: split headlines into words.** A gradient clipped to a whole multi-line headline stretches across every line, so the top line gets only the highlight and the bottom line only the charcoal, and the metal looks flat. Wrap each word in its own span and give every word the full gradient. Each word then reads as its own piece of engraved metal, top-light to bottom-charcoal, like the #DARK_MUSIC letters.

```css
.headline-silver,
.headline-silver .word { /* the background, clip and color from .headline-silver above */ }
.headline-silver.is-split { background: none; }        /* the words carry the metal now */
.headline-silver .word { display: inline-block; padding-bottom: .08em; } /* keep descenders inside the clip */
```

```js
function splitWords(el) {
  const words = el.textContent.trim().split(/\s+/);
  el.textContent = '';
  words.forEach((w, i) => {
    const s = document.createElement('span');
    s.className = 'word';
    s.style.setProperty('--i', i);                       /* stagger index for the 6.4 reveal */
    s.textContent = w;
    el.append(s, i < words.length - 1 ? ' ' : '');
  });
  el.classList.add('is-split');
}
```

Split **always**, including under reduced motion. The split is for the metal finish, not only for the animation. Reduced motion simply shows the words still. The same spans drive the word-by-word reveal in 6.4.

### 3.4 Headlines over live backgrounds *(New in v2)*

Silver text over moving metal or Mist can lose its edges, because the background passes through the same greys as the text. Give any headline or copy that sits on a live background a soft dark halo. It reads as depth, not as an outline.

```css
.on-live-bg .headline-silver { filter: drop-shadow(0 0 28px rgba(0, 0, 0, .85)); } /* headlines */
.on-live-bg .body-lg         { text-shadow: 0 0 22px rgba(0, 0, 0, .9), 0 0 4px rgba(0, 0, 0, .6); } /* supporting copy */
.on-live-bg .legal           { text-shadow: 0 0 16px rgba(0, 0, 0, .9); } /* small print */
```

- Use `filter: drop-shadow` on gradient text, since `text-shadow` would show through the transparent fill.
- Pair it with `text-wrap: balance` on headlines, so the halo wraps around even lines.
- Keep the halo black and soft. A visible ring means the blur is too small.

---

## 4. Typography

| Style | Font | Weight | Desktop ≥1200 | Tablet 810–1199 | Phone <810 | Line height | Tracking | Align |
|---|---|---|---|---|---|---|---|---|
| H1 | Satoshi | 400 | 92px | 74px | 44px | 1.0 | — | center |
| H2 | Satoshi | 400 | 92px | 64px | 44px | 1.0 | — | left |
| H3 | Satoshi | 500 | 36px | 34px | 30px | normal | -0.01em | left |
| H4 | Plus Jakarta Sans | 600 | 24px | 24px | 24px | 1.4 | — | left |
| Body large | Inter Display | 400 | 24px | 20px | 18px | 1.4 | — | left |
| Body | Inter Display | 400 | 18px | 18px | 18px | 1.6 | — | left |
| Body small | Inter Display (inherited) | 400 | 15px | 15px | 15px | 1.5 | -0.02em | center |

**Character:** huge headlines at a *light* weight. Editorial, not shouty. The metal finish adds the weight that the font weight holds back.

```css
h1 { font: 400 92px/1 var(--font-display); }
@media (max-width: 1199.98px) { h1 { font-size: 74px; } h2 { font-size: 64px; } }
@media (max-width: 809.98px)  { h1, h2 { font-size: 44px; } h3 { font-size: 30px; } }
```

**Fonts:** Satoshi (Fontshare, free), Plus Jakarta Sans (Google Fonts), Inter Display (rsms.me/inter). Fall back to Inter if a font is unavailable.

---

## 5. Surfaces & UI

- **Page:** always `--bg`. Surfaces step up only to `--surface`.
- **Cards:** `--surface` + 1px solid `--border` + a soft shadow on badges and service tiles.
- **Glass:** blur things rather than filling them.

| Element | Treatment |
|---|---|
| Nav (fixed) | `--surface-nav` + `backdrop-filter: blur(12px)` |
| Review cards | Dark vertical gradient + `blur(50px)` |
| Project labels | `blur(6px)`–`blur(12px)` |
| Secondary button | Gradient `--surface` → transparent (180°) + 1px border + `blur(5px)`. **Hover flips the gradient to 0°.** |
| Section pill / tag | `blur(68px)` + status dot |

- **Edge fade:** a fixed strip at the bottom of the viewport with a 7px blur that fades toward the bottom, so content softly dissolves at the screen edge.

```css
.edge-fade {
  position: fixed; inset: auto 0 0 0; height: 120px; pointer-events: none;
  backdrop-filter: blur(7px);
  mask-image: linear-gradient(to bottom, transparent, #000);
}
```

---

## 6. Motion (the signature)

### 6.1 Principles

1. **Nothing just appears.** Every section and element enters with motion.
2. **Something is always alive.** At least one continuous motion on screen: the Mist background, a ticker, or a floating element.
3. **Blur is part of motion.** Text reveals come out of a blur, not only a fade.
4. **Heavy for big things, quick for small things.** Large media uses slow, weighty springs. Text and UI use fast, settled springs.
5. **Play once.** Entrances don't replay when you scroll back up.

### 6.2 Motion tokens

Springs are given as **stiffness / damping / mass** and work directly in Motion (Framer Motion), React Spring, GSAP or SwiftUI. The CSS duration is an approximate stand-in using `--ease-out-soft`.

| Token | Spring (s / d / m) | CSS stand-in | Used for |
|---|---|---|---|
| `spring-heavy` | 50 / 30 / 1 | ~1.6s | Collage and large media assembly |
| `spring-text` | 400 / 100 / 1 | ~0.7s | Word-by-word text reveals |
| `spring-ui` | 200 / 40 / 1 | ~0.6s | Hero buttons |
| `spring-section` | 360 / 60 / 0.5 | ~0.45s | Section content rising in |
| `spring-slide` | 127 / 25 / 1 | ~0.8s | Cards sliding in from the side |
| `tween-standard` | — | 0.4–0.7s, `--ease-standard` | Fades, scale-ins |
| `loop-float` | — | 2s, linear, mirror, infinite | Floating element |

### 6.3 Live background — "Mist"

A slow, flowing black-and-white fluid gradient behind the hero and the footer, so the page bookends in smoke.

| Setting | Value |
|---|---|
| Colors | Black / White / Black |
| Speed | 20 (slow drift) |
| Rotation | -50° |
| Swirl / iterations | 50 / 16 |
| Softness | 47 |
| Noise / grain | 0.2 opacity |
| Pattern | Checks, size 45, scale 0.01, proportion 1, offset -299 |
| Entrance | Fades in, 0.6s linear, 0.8s delay |

**Build options:** a WebGL fluid or noise shader gives the real look (recommended). Large blurred white blobs animated slowly over black, plus a grain overlay, give a lighter CSS approximation.

**New in v2: brightness by role.** The Mist does two different jobs, and each needs its own brightness. Values are a multiplier on the Mist's white (1 = full).

| Role | Brightness | Why |
|---|---|---|
| **Hero underlay**, behind a centrepiece or headline | ~0.35–0.4 | Atmosphere only. It gives depth without competing with the headline or the hero object. |
| **Closing section**, footer or final CTA, as the main background | ~0.85 | The Mist *is* the visual. Full smoke bookends the page. |

The same Mist in both places, at different strengths, ties the opening and the close together without repeating the same picture.

### 6.4 Hero intro (on load)

| Order | Element | From | Motion |
|---|---|---|---|
| 1 | Section pill | opacity 0 | 0.6s linear, delay 0.8s |
| 2 | Headline | opacity 0, y +10px, **blur 10px**, split **by word** | `spring-text`, 0.05s stagger |
| 3 | Subtext | opacity 0, y +5px, blur 2px, split by word | `spring-text` |
| 4 | Button 1 / Button 2 | opacity 0, x -12px | `spring-ui`, delay 1.0s / 1.1s |
| ∞ | Floating icon | y 0 → 10px | `loop-float` |

```css
.word { display: inline-block; opacity: 0; transform: translateY(10px); filter: blur(10px);
        animation: word-in .7s var(--ease-out-soft) forwards; animation-delay: calc(var(--i) * 50ms + 500ms); }
@keyframes word-in { to { opacity: 1; transform: none; filter: blur(0); } }
```

### 6.5 Collage assembly (project grid, on load)

The image columns start far off-screen and settle into place with `spring-heavy`. It's slow and weighty, like a cinematic opening.

| Column | Starts from |
|---|---|
| Column 1 | y -706px |
| Column 5 | y -268px, **scale 1.8** |
| Column 6 | y -739px |
| Grid container | scale 0.88 → 1 on view, 0.4s `--ease-standard` |

### 6.6 Section entrances

| Element | From | Motion |
|---|---|---|
| Section content | opacity 0, y +40px | `spring-section`, delay 0.2s |
| Service cards | opacity 0, x -50px | `spring-slide`, delay 0.1s |
| Badge cards | opacity 0, x -50px | `spring-slide`, delay 0.45s |
| Footer buttons | opacity 0, y +40px | `spring-section`, delay 0.3s |
| Footer | Scroll-linked: moves from y -500px to 0 as it enters | Scroll-driven |

Trigger these **when the element enters the viewport** (IntersectionObserver, `whileInView`, or GSAP ScrollTrigger), once. *(The source template fires most of them on page load. This template corrects that to on-view.)*

**New in v2: reveal anything already scrolled past.** An anchor link, a fast fling or a restored scroll position can carry an element past the viewport without it ever intersecting, so it stays invisible. On every scroll, also fire any still-pending entrance whose element is already above the viewport.

```js
const pending = new Set();
const io = new IntersectionObserver((entries) => entries.forEach((e) => e.isIntersecting && reveal(e.target)));
function reveal(el) { if (!pending.delete(el)) return; io.unobserve(el); el.classList.add('is-in'); }
document.querySelectorAll('[data-reveal]').forEach((el) => { pending.add(el); io.observe(el); });

addEventListener('scroll', () => {                       // the fallback
  for (const el of pending) if (el.getBoundingClientRect().bottom < 0) reveal(el);
}, { passive: true });
```

Entrances still play once. The fallback only makes sure nothing is left hidden.

### 6.7 Continuous motion — tickers

Infinite marquees with faded edges. The values are relative speeds from the source; tune to taste.

| Ticker | Speed | Direction | Gap | Slows on hover |
|---|---|---|---|---|
| Client logos (hero) | 50 | left | 100px | no |
| Skill tags, row 1 | 60 | left | 24px | no |
| Skill tags, row 2 | 60 | **right** | 24px | no |
| Reviews | 100 (fastest) | left | 24px | **yes, to 50%** |

The two skill rows run in **opposite directions**.

```css
.ticker { overflow: hidden; mask-image: linear-gradient(90deg, transparent, #000 10%, #000 90%, transparent); }
.ticker__track { display: flex; gap: 24px; width: max-content; animation: marquee 30s linear infinite; }
.ticker--reverse .ticker__track { animation-direction: reverse; }
@keyframes marquee { to { transform: translateX(-50%); } }   /* content duplicated once */
```

### 6.8 Other motion

- **Carousel** (recent work): centered, gap 10px, snaps to the center, arrow controls on pointer devices.
- **Smooth scroll:** soft, inertial page scroll (Lenis or equivalent, medium intensity).
- **Custom cursor:** a 12px light dot (`rgb(230,230,230)`, 6px blur) that morphs into a **"View Project"** label over work and an **"about me"** label over the portrait. Pointer devices only.
- **Hover states:** project cards, buttons, nav links, social icons and the menu button.
- **FAQ accordion:** open and close, with a press that scales to **0.97**.
- **Mobile menu:** the hamburger morphs into a close icon.
- **Reduced motion:** honor `prefers-reduced-motion`. Disable the springs, blur reveals, tickers and Mist, and fall back to simple fades.

### 6.9 Signature hero option — monochrome liquid chrome *(New in v2)*

An optional hero centrepiece: a live, liquid-metal sculpture made of the same steel as the headlines. Use it when a page needs one bold, living object. It satisfies rule 6 ("something is always alive") on its own. One centrepiece per page; never stack it with a second live hero effect.

**Look:**

| Setting | Value |
|---|---|
| Form | 5–6 spheres blended with a smooth union (`smin`, k ≈ 0.85), so they merge and separate like liquid |
| Shading | **Reflection only.** The metal shows a reflected studio and has no colour of its own. |
| Studio | Grey light only: an overhead softbox, a window grid, a sharp horizon line, side strips, soft floor stripes faded before the horizon. **No RGB dispersion, no warm or cool tints.** |
| Highlight cap | Brightest pixel ≈ `#DCDCDC` (`silver-highlight`), about 0.93, so the chrome never outshines the headline silver |
| Brushed grain | Horizontal micro-scratches nudging the surface normal, e.g. `noise(p.x·2, p.y·70)`, amplitude ≈ 0.02 |
| Background | Rays that miss the metal show the **Mist** at hero-underlay strength (6.3), so the hero and the footer share one atmosphere |
| Tone | Fresnel, soft ambient occlusion, ACES tone mapping, a film grain of about 0.2 to match the Mist |

**Layout:** the metal frames the copy and never sits on it.
- **Desktop and tablet:** the spheres orbit in a ring around the headline.
- **Phone:** the cluster sits in the upper half, smaller (about 0.6×), and the copy sits lower.
- The headline uses the halo from 3.4.

**Motion:**
- Each sphere has its own slow orbit speed plus a gentle drift, so neighbours bunch up, merge and split again.
- **Pointer:** one sphere follows the cursor (smoothing `1 − 0.0009^dt`), and its neighbours lean toward it.
- **Click:** sends a ripple through the metal that decays as `0.02^dt`.
- **Scroll:** merges the cluster into one mass as the hero leaves.
- **Reduced motion:** render one still frame, and redraw it on resize.

**Build:**
- **Engine:** a WebGL2 full-screen shader that raymarches about 64 steps. It is the same family as the Mist shader, and both can share one program.
- **Pausing:** pause when off-screen or when the tab is hidden.
- **Resolution:** cap the device pixel ratio at about 1.5, and adapt render scale to frame time. Start lower on phones (about 0.65).
- **Edges:** count rays that run out of steps while grazing the surface as hits, to avoid speckled edges.

---

## 7. Layout

**Breakpoints:** Desktop ≥1200px · Tablet 810–1199px · Phone <810px.

**Page structure:**

```
Nav (fixed, glass)
Hero ............ Mist background (or the liquid chrome hero, 6.9) · pill · H1 · subtext · 2 buttons · logo ticker
Work ............ assembling image collage · "all projects" link
About ........... portrait · bio · skill chips · experience rows · work carousel
Process ......... 3 step cards
Services ........ 4 service tiles · 2 opposing skill tickers
Testimonials .... reviews ticker · 3 stat cards
FAQ ............. accordion
Footer CTA ...... Mist background · headline · button · socials
```

**Spacing:**

| Area | Padding (top / right / bottom / left) | Gap |
|---|---|---|
| Hero | 160 / 40 / 60 / 40 | 24 |
| Standard section | 100 / 80 / 100 / 80 | 24–44 |
| Work collage | 10 / 5 / 100 / 5 | 54 |

---

## 8. Components

| Component | States / variants | Anatomy |
|---|---|---|
| Nav | desktop · mobile · mobile open | Logo, links, CTA; fixed, glass |
| Nav link | default · hover · mobile | Text link |
| Menu button | closed · open (+ hover) | Hamburger ↔ close icon |
| Primary button | default · hover · mobile | Solid CTA |
| Secondary button | default · hover · mobile | Glass CTA; gradient flips on hover |
| Section pill | — | Status dot + label, heavy blur |
| Section badge | — | Small label pill above section titles |
| Project card | with button · without button (+ hover) · mobile | Image, frosted label; ratio about 1.07 : 1 |
| Custom cursor | default · "View Project" · "about me" | Dot that morphs into a label |
| Process step | desktop · mobile | Number, title, description |
| Service tile | — | Icon, title, description; slides in |
| Skill chip | — | Bordered tag |
| Experience row | desktop · mobile | Role, company, years |
| Review card | — | Glass card, star rating, quote, name |
| Stat card | — | Big number + label |
| FAQ item | closed · open | Question, toggle icon, answer |
| Status dot | on · off | Small indicator |
| Social icon | default · hover | Icon button |
| Liquid chrome hero *(New in v2, optional)* | live · still (reduced motion) | Full-bleed WebGL canvas, scrim, Mist on miss rays; frames the hero copy (6.9) |

**Icons:** Phosphor, **duotone** weight, in the light text color.

---

## 9. Rules

1. The background is always `#000`. Surfaces step up only to `#0D0D0D`.
2. Keep color out. Use silver, off-white and black only; gold is reserved for stars.
3. Headlines are metal: the brushed-silver gradient, light weight, large size.
4. Labels are engraved: flat silver, uppercase, wide tracking.
5. Every element moves on entry. Nothing just appears.
6. At least one thing is always alive on screen.
7. Use glass over solid: blur the nav, labels and review cards rather than filling them.
8. Photography is black and white.
9. Respect reduced-motion settings.

---

## 10. Framer mapping

Use this when building in Framer. The source project already contains all of it.

| Template element | Framer equivalent |
|---|---|
| Mist background | **Animated Gradient Background** component, preset *Mist*, settings as in 6.3 |
| Tickers | **Ticker** component: speed 50 / 60 / 60 / 100, gaps 100 / 24 / 24 / 24, fade edges on, reviews hover factor 0.5 |
| Carousel | **Carousel** component: align center, gap 10, snap center, mouse controls on |
| Smooth scroll | **Smooth Scroll** component, intensity 6 |
| Edge fade | **Blur Gradient** component: blur 7, direction to bottom, fixed to the bottom |
| Word-by-word reveal | Text effect, trigger on mount, tokenize by word |
| Entrances | Appear effects (set the trigger to *In View*) |
| Footer motion | Style transform effect, on view |
| Floating icon | Loop effect, y 10, 2s, mirror |
| Cursor | Custom cursor component with three variants |
| Icons | Phosphor, duotone |
| Liquid chrome hero *(v2)* | No native equivalent. Use a **code component** that hosts the WebGL canvas from 6.9. |
| Headline halo *(v2)* | Text shadow or a drop-shadow effect, ~28px blur, black at 85% |
| Brushed headline | Linear gradient text fill with the four silver stops. Clipping the brushed grain inside text is **to be confirmed** in Framer (native fill or a small code override). |
