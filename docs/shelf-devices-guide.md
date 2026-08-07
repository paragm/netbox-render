# Modeling shelf-mounted devices in NetBox

How I set up rack shelves holding multiple small devices (desktops, mini PCs, NUCs) using NetBox's device bay system, and how `netbox_render` makes them visible in rack elevations.

## The problem

A rack shelf with four desktops takes up 5U but NetBox shows it as one opaque block with an occupancy count. You can't see what's on the shelf without clicking into the Device Bays tab.

## Setup

### 1. Create the shelf device type

| Field | Value |
|-------|-------|
| Manufacturer | e.g. "Generic" |
| Model | e.g. "Desktop Shelf 5U" |
| U Height | Actual rack units (5, 10, etc.) |
| Subdevice Role | **Parent** |

Add device bay templates — one per slot. Name them "Slot 1", "Slot 2", etc. (names control sort order in the elevation).

Shelf types I use:

| Model | U Height | Bays |
|-------|----------|------|
| Desktop Shelf 5U | 5 | 4 |
| Desktop Shelf 10U | 10 | 2 |

### 2. Create child device types

Each device that sits on a shelf needs a child variant, even if a standalone type already exists. I use a `(Shelf)` suffix to distinguish them.

| Field | Value |
|-------|-------|
| Model | e.g. "Define 7 XL (Shelf)" |
| U Height | **0** |
| Subdevice Role | **Child** |

U Height must be 0 — otherwise NetBox tries to place the device independently in the rack.

### 3. Create the shelf device

Create a device using the shelf type, assign it to a rack position. The bays from the template get created automatically.

### 4. Install devices into bays

Create each child device, then go to the shelf's Device Bays tab and install them into the appropriate slots.

## Worked example

My production setup for a 5U shelf:

**Shelf type**: Generic Desktop Shelf 5U — 4 slots, full depth, parent role.

**Child type**: Framework Desktop (AMD Ryzen AI Max 300 Series) (Shelf) — u_height=0, child role.

**Shelf device**: Shelf-RU35 at rack unit 35 in the office rack (SJC1).

**Installed**: frame03 in Slot 1, three slots empty.

### What it looks like

**Stock NetBox:**
```
┌──────────────────────────┐
│                          │
│   Shelf-RU35  (1/4)     │  ← one block, no detail
│                          │
│                          │
└──────────────────────────┘
```

**With netbox_render:**
```
┌──────────────────────────┐
│ 1: frame03               │  ← clickable, colored by role
├──────────────────────────┤
│ 2: (empty)               │
├──────────────────────────┤
│ 3: (empty)               │
├──────────────────────────┤
│ 4: (empty)               │
└──────────────────────────┘
```

## Grid layout for dense shelves

When many devices share a small shelf (e.g. 6 Mac Minis in 2U, or 12 Raspberry Pis in 2U), stacking bays vertically makes them too short to read. The plugin supports a **grid layout** that arranges bays in rows and columns.

### Auto-calculation

If the per-bay height drops below 15 pixels, the plugin automatically picks a column count that minimizes the cell aspect ratio — producing the most square-ish cells possible. No configuration needed.

### Per-device-type overrides

For full control, set the column count per device type slug in `PLUGINS_CONFIG`:

```python
PLUGINS_CONFIG = {
    'netbox_render': {
        'layouts': {
            'mac-mini-shelf-2u': {'columns': 3},   # 6 bays → 3×2 grid
            'rpi-cluster-2u': {'columns': 5},       # 20 bays → 5×4 grid
        },
    },
}
```

The key is the device type **slug** (visible on the device type page in NetBox). The `columns` value must be an integer between 1 and the number of bays — invalid values log a warning and fall back to auto-calculation.

### What it looks like

**6 Mac Minis in a 2U shelf (columns: 3):**
```
┌──────────┬──────────┬──────────┐
│ 1: mini1 │ 2: mini2 │ 3: mini3 │
├──────────┼──────────┼──────────┤
│ 4: mini4 │ 5: mini5 │ 6: mini6 │
└──────────┴──────────┴──────────┘
```

**7 Raspberry Pis in a 2U shelf (columns: 3):**
```
┌──────────┬──────────┬──────────┐
│ 1: rpi-1 │ 2: rpi-2 │ 3: rpi-3 │
├──────────┼──────────┼──────────┤
│ 4: rpi-4 │ 5: rpi-5 │ 6: rpi-6 │
├──────────┼──────────┼──────────┤
│ 7: rpi-7 │ (empty)  │ (empty)  │
└──────────┴──────────┴──────────┘
```

Partial last rows are filled with empty blocked cells matching the stock NetBox style.

### Tips for grid layouts

- **`columns: 1`** forces a single-column vertical stack regardless of bay count
- The auto-calculation favors squarer cells — for a wide device with 6 bays in 2U, it may choose a single row of 6 narrow columns. Use an override if you prefer 3×2
- Grid lines render as thin separators so the layout is clear without being heavy

## Tips

- **Name shelves by position** (e.g. "Shelf-RU35") for easy lookup
- **Assign roles** to child devices — the plugin colors each section by role, so you can spot device types at a glance
- **Multiple shelves** in the same rack work fine — each is independent
- **Mixed racks** — the plugin only touches devices with bays, everything else renders normally
- **Full device objects** — children support interfaces, IPs, serial numbers, asset tags, everything
