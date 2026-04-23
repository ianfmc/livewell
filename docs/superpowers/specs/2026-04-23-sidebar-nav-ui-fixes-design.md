# Sidebar Navigation & UI Fixes Design

## Goal

Replace the top navigation bar with a collapsible left sidebar, left-justify contract card details, and remove the arrow from the Daily Signals nav link.

## Changes

### 1. Sidebar Navigation (`App.tsx`)

Replace the nav `Button` links in the `AppBar` with a MUI `Drawer` (`variant="temporary"`, `anchor="left"`).

**AppBar** retains three elements only:
- Hamburger `IconButton` (left) — toggles the drawer open/closed
- LIVEWELL `Typography` title
- Theme toggle `Button` (right, pushed by a `Box sx={{ flexGrow: 1 }}` spacer)

**Drawer** contents:
- MUI `List` with one `ListItemButton` per route:
  - Dashboard → `/`
  - Daily Signals → `/signals`
- Clicking any item calls `navigate(path)` then closes the drawer (`setOpen(false)`)
- Clicking the backdrop (outside the drawer) closes it — default MUI temporary drawer behaviour, no extra code needed

**State:** single `const [open, setOpen] = useState(false)` in `App`.

No changes to any page component — the drawer overlays content and does not affect page layout.

### 2. Left-justify contract card details (`contract-card.tsx`)

In the `Stack` that wraps Strike and Expiry lines:

```tsx
// Before
<Stack spacing={0.5} alignItems="flex-end">

// After
<Stack spacing={0.5} alignItems="flex-start">
```

### 3. Remove arrow from "Daily Signals" link

The arrow is on the `Button<typeof Link>` for Daily Signals in the current AppBar. This button is removed entirely when the sidebar is introduced — the new `ListItemButton` entries in the Drawer do not render arrows by default. No explicit arrow-removal code is needed; this fix is a natural consequence of change 1.

## Files Changed

| File | Change |
|---|---|
| `src/App.tsx` | Replace nav buttons with hamburger + Drawer; slim AppBar |
| `src/components/contract-card.tsx` | Left-justify Strike/Expiry Stack |

## Testing

- Existing component and page tests must continue to pass (`npm test`)
- The `contract-card` test renders a card — verify it still passes after the `alignItems` change
- No new tests required for the drawer (it is infrastructure with no product logic)
- Manual verification: open drawer, navigate to each page, confirm drawer closes; confirm contract card details are left-aligned; confirm no arrow visible on Daily Signals
