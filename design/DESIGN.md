# Design tokens

Visual language: Trade Republic app. Monochrome, calm, one big number per
screen, flat lists separated by hairlines, color only for meaning.

## Sources

The files are in `design/reference/`, which git ignores.

- `web-home-*.png` and `web-about-1440-dark.png`: the public marketing site
  (traderepublic.com/es-es) at 1440 and 390 px. It is light-only, uses large
  bold sans headlines on photography, and has black ink buttons.
- `webapp-login-*.png`: the web app login (app.traderepublic.com). It is dark,
  uses a near-black background, small semibold type and 6px radius controls.
- `_vars-dark.json` / `_vars-light.json`: the CSS custom properties of the web
  app's design system (`--core-colors-*`, `--core-radii-*`, `--core-spacing-*`),
  taken from its stylesheets. This is the main source for the values below.
  `:root` holds the dark theme and `:root[data-theme="light"]` overrides it for
  light.

TR's own palette is called `neutral-gray1` … `gray9`:
`#F2F3F4 #E6E7E9 #B5B7BA #93969A #6A6B6D #4A4C4F #3F4041 #2E2F30 #202020`.
Their accents are green `#02CA50` and red `#FF4034`, and both themes use the same pair.

The values marked **(AA)** below were changed from TR's because TR's value
fails WCAG AA (4.5:1) as text. TR's muted gray in light (`gray3`) is 2.0:1 on
white, and its green is 2.2:1 on white. Each replacement is the closest TR
gray, or a darker shade of the same hue, that passes.

## Color

### Dark (default)

| Token           | Value     | TR token                         | Contrast            |
|-----------------|-----------|----------------------------------|---------------------|
| bg              | `#000000` | neutral-black                    |                     |
| surface         | `#151515` | pro-surface-elevated-solid       |                     |
| surface-2       | `#202020` | gray9 (buttons-primary, border)  |                     |
| text / ink      | `#FFFFFF` | content-primary                  | 21:1                |
| muted **(AA)**  | `#93969A` | gray4 (TR uses gray6, 2.4:1)     | 7.07 bg, 6.15 surf  |
| hairline        | `#202020` | border-primary (gray9)           |                     |
| input-border    | `#2E2F30` | fills-primary (gray8)            |                     |
| positive        | `#02CA50` | accent-green                     | 9.57 bg, 8.32 surf  |
| negative        | `#FF4034` | accent-red                       | 6.03 bg, 5.25 surf  |

### Light

| Token              | Value     | TR token                        | Contrast            |
|--------------------|-----------|---------------------------------|---------------------|
| bg                 | `#FFFFFF` | neutral-white                   |                     |
| surface            | `#F2F3F4` | gray1 (surface-on-primary)      |                     |
| surface-2          | `#E6E7E9` | gray2 (fills-primary)           |                     |
| text               | `#000000` | content-primary                 | 21:1                |
| ink (buttons)      | `#202020` | buttons-inverted (gray9)        | 16.3:1              |
| muted **(AA)**     | `#6A6B6D` | gray5 (TR uses gray3, 2.0:1)    | 5.33 bg, 4.80 surf  |
| hairline           | `#E6E7E9` | border-primary (gray2)          |                     |
| input-border       | `#B5B7BA` | gray3                           |                     |
| positive **(AA)**  | `#007A35` | accent-green, darkened          | 5.48 bg, 4.93 surf  |
| negative **(AA)**  | `#C9241A` | accent-red, darkened            | 5.60 bg, 5.04 surf  |

### Charts

- Line: the ink color of the active theme. It comes through the first color
  of `chartCategoricalColors` in each theme table.
- Neutral bars: `#8A8D91`, between gray3 and gray4. It reaches about 3:1 on white
  and 6.8:1 on black, so one value works in both themes.
- Positive / negative graphics: `#00A843` / `#F0392D`. Graphics only need 3:1,
  and these pass on both backgrounds.
- Categorical ramp for stacked category bars: TR's grays, ink first.

No brand accent, no gradients, no shadows on static content. (TR uses soft
shadows on floating menus only.)

## Typography

TR ships "TradeRepublicSans", which is proprietary and not used here. The
replacement is Inter (Google Fonts, variable weight), with fallback
`system-ui, -apple-system, "Segoe UI", sans-serif`. TR uses semibold weights
for labels and amounts (580 for labels, 680 for headings). Inter is a variable
font, so those weights are approximated with 500/600/700. Every number uses
`font-feature-settings: "tnum"`.

| Role          | Size (desktop / mobile) | Weight | Letter-spacing |
|---------------|-------------------------|--------|----------------|
| Hero number   | 40px / 32px             | 700    | -0.02em        |
| Page title    | 28px / 24px             | 700    | -0.01em        |
| Section title | 20px                    | 600    | -0.005em       |
| Row title     | 16px                    | 500    | 0              |
| Body          | 15px                    | 400    | 0              |
| Caption/muted | 13px                    | 400    | 0              |

No all-caps labels. (The marketing site uses heavy 700+ headlines; the app
uses calmer semibold. The app is the closer model.)

## Shape and spacing

The radii are taken from `--core-radii-*`, which override the brief's defaults:

| Element                         | Radius  | TR token                    |
|---------------------------------|---------|-----------------------------|
| Cards, widgets, menus           | 8px     | radii-card / widget (r8)    |
| Inputs, buttons, pills, toggles | 6px     | radii-input / button (r6)   |
| Progress bars                   | 4px     | radii-bar (r4)              |
| Avatars                         | 9999px  | radii-avatar (full)         |
| Large framed groups             | 12px    | radii-slider-frame (r12)    |

- Spacing scale (TR `--core-spacing-sp*`): 4, 8, 12, 16, 20, 24, 32, 46.
- Page side padding: 16px mobile, 32px desktop. Max content width 1100px, centered.
- List row: min height 64px, padding 12px 0, 40px circular avatar on surface-2,
  16px gap. The hairline starts after the avatar (inset 56px).
- Stat row: label 13px muted above the value 20px/600, no borders.
- Progress bar: 6px tall (TR bars-bar-height), track = surface-2.
- Buttons are 40px tall (TR button-fixed-height-large).

## Numbers

- Money uses the existing `eur()` format: `1.234,56 €`.
- Signed amounts always show `+` or `−` (U+2212).
- Percentages: `1,2 %`.
