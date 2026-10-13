# Visual review

Screenshots are in `design/screenshots/<page>-<width>-<theme>.png` (gitignored),
taken with Playwright at 1440×900 and 390×844, in both dark and light, on the
demo data. The references are in `design/reference/`: the TR marketing site, the
TR web app login, and the web app's CSS tokens.

## Round 1

**Global**
- Still looks like Streamlit: every chart used Plotly's default colors (a blue
  portfolio line, an orange cumulative line, a green savings line). Green on
  "Ahorro" also reads as "income". **Fixed:** the template now builds on
  Streamlit's (`streamlit+finanzas`), and lines use the theme ink through
  Streamlit's color placeholder.
- Still looks like Streamlit: segmented controls (range pills, scope, view) drew
  as a bordered button group with an outlined selection. **Fixed:** no borders,
  muted text, and the selected option sits on a gray pill, like the top
  navigation.
- Still looks like Streamlit: number inputs had +/- steppers. **Fixed:** hidden
  (the keyboard arrows still work).
- Still looks like Streamlit: the expander ("Cómo sincronizar") was a rounded
  bordered box. **Fixed:** it is now a flat row between hairlines.
- The fixed header covered the page title and the month selector. **Fixed:**
  top padding = header height + 28px.
- The navigation pill started 3px to the right of the content edge and its text
  14px further in. **Fixed:** the nav text now lines up with the page's left edge.

**Gastos**
- The category rows were separated by uneven gaps with no hairline, and the
  share bars stopped at 360px, which looked unfinished. **Fixed:** the rows sit in a
  gap-free keyed container, with inset hairlines and full-width bars, and the
  amount column has a fixed minimum width so every bar track ends at the same x.
- A category that didn't change showed "0,00 € vs sep". **Fixed:** "Igual que en sep".
- The small multiples had no month labels. **Fixed:** they now have short Spanish
  months.

**Cartera**
- The date ticks were in English ("01 May", "01 Jul") and clipped at the
  bottom. **Fixed:** the ticks are explicit Spanish dates ("14 jun"), and the
  hover shows the date and the amount.

**Inicio**
- The right-hand y-axis cut off the "€" of "2.000 €". **Fixed:** `automargin`
  plus 4px right margin.

## Round 2

**Mobile (390)**
- Still looks like Streamlit: below about 640px `st.navigation(position="top")`
  folds into a "»" button that opens a sidebar drawer. **Fixed:** on mobile, the
  header and the drawer are hidden, and a horizontally scrolling row of page links
  (`st.page_link`) sits at the top. The current page is marked through a keyed
  container. CSS hides that row on desktop.
- Movimientos: the category filter kept its 260px width while the search box
  stretched. **Fixed:** the filters go full width on mobile.
- Gastos: the three-column small multiples overlapped their titles ("Restaurantes
  y bares" ran into "Facturas y suministros") and their month labels. **Fixed:**
  two columns, month-only labels, and 20px bottom margin so the last row keeps
  its labels.
- No horizontal scroll at 390 on any page (`scrollWidth == 390` checked by the
  screenshot script).

**Interaction (found while clicking through)**
- The disabled primary button ("Guardar 0 cambios") rendered as an empty box,
  because its text color equals its background. **Fixed:** the disabled state is
  a gray fill with muted text.
- The open-category styling (inverted avatar, hover underline) also hit the
  nested transaction rows. **Fixed:** scoped to the category's own row.

**Light theme**
- Checked every page. Hairlines, avatars, pills and the form surface come from
  TR's light tokens (gray1/gray2). Green `#007A35` and red `#C9241A` pass AA on
  white and on the gray surface. Nothing is left from the default Streamlit look.

## Remaining differences (accepted Streamlit limits)

- **Data editors** (Movimientos → "Editar categorías", Ajustes → Categorías) are
  Streamlit's canvas grid. They follow the theme colors and font, but keep the
  grid look, and the amounts in the grid use a decimal point ("-11.35 €")
  because the grid's number format can't be localized to "es". They are editing
  tools behind an explicit mode, not the main reading view.
- **The desktop top bar** is Streamlit's header. It is restyled (background,
  hairline, pills) but keeps its fixed 60px height.
- **Native widgets** (select, multiselect, text input, toggle) keep Streamlit's
  internal shapes, recolored by the theme. Their dropdown menus are
  Streamlit's.
- **Plotly hover labels** use Streamlit's theme styling, so they are a small
  rectangle rather than TR's pill.
- **Deep-linking straight to a sub-page** (e.g. opening `/gastos` in a new tab)
  logs two 404s for `/gastos/_stcore/health` and `/host-config`. That is
  Streamlit probing a path-relative endpoint before falling back. In-app
  navigation doesn't trigger it, and the app logs no other console errors.

None of these affect the hero, the navigation or the list rows. The exit
criterion in the brief (moving to FastAPI + React) was not reached.

## Flows checked in the browser (Playwright, demo database)

| Flow | Result |
|---|---|
| Change month on Inicio → hero switches to "Ahorro en septiembre" | pass |
| Navigate to Gastos → month is still September | pass |
| Expand a category in Gastos → its transactions appear | pass |
| Objetivos: set savings goal to 650, Guardar → stored in DB, shown after rerun | pass |
| Movimientos: Editar categorías, change TMB to "Ocio y suscripciones", tick "crear regla", Guardar → category saved (manual) and rule `TMB` created | pass |
| Ajustes: add rule `starbucks`, then Eliminar → added, then removed | pass |
| Keyboard focus ring visible (2px solid) | pass |
| Streamlit exceptions / browser console errors | none |
