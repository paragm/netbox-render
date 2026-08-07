<p align="center">
  <img src="https://raw.githubusercontent.com/paragm/netbox-render/main/docs/images/icon.svg" alt="netbox-render" width="128" height="128">
</p>

# netbox-render

A NetBox plugin I wrote to fix a visibility gap in rack elevations: devices with device bays render as a single opaque block, hiding what's actually installed. This plugin subdivides that block into labeled, color-coded, clickable sections — one per bay.

## What it does

Out of the box, NetBox shows a device-bay device as one rectangle with an occupancy count like "3/4". To see what's installed, you have to click into the parent and check the Device Bays tab.

I patched `RackElevationSVG._draw_device` so each bay gets its own section showing:

- Bay index (1, 2, 3, ...) sorted by bay name
- Child device name, or "(empty)"
- Role color on the front face (rear renders grey, matching stock behavior)
- Clickable link to the child device page

Devices without bays are untouched.

### Before and after

| Without plugin | With plugin |
|:-:|:-:|
| ![Stock NetBox elevation](https://raw.githubusercontent.com/paragm/netbox-render/main/docs/images/elevation-without-plugin.png) | ![With netbox-render](https://raw.githubusercontent.com/paragm/netbox-render/main/docs/images/elevation-with-plugin.png) |
| Single opaque block | Subdivided with bay labels and role colors |

### Bay ordering

Bays sort alphabetically by name — there's no numeric position field in NetBox's device bay model. Name them "Slot 01", "Slot 02", etc. for predictable ordering.

## Compatibility

| NetBox | Plugin | Status |
|--------|--------|--------|
| 4.6.x  | 0.2.0  | Tested |

Startup checks verify the patched method signature hasn't changed. If it has, the plugin raises a `RuntimeError` instead of loading.

## Installation

```bash
pip install netbox-render
```

Add to `configuration.py`:

```python
PLUGINS = ['netbox_render']
```

Restart NetBox:

```bash
sudo systemctl restart netbox netbox-rq
```

For development: `pip install -e .`

## Configuration

```python
PLUGINS_CONFIG = {
    'netbox_render': {
        'enable_images': True,       # default: False
        'layouts': {                  # default: {} (auto-calculate)
            'mac-mini-shelf-2u': {'columns': 3},
            'rpi-cluster-2u': {'columns': 5},
        },
    },
}
```

| Key | Default | Description |
|-----|---------|-------------|
| `enable_images` | `False` | Show device type front/rear images in bay sections |
| `layouts` | `{}` | Per-device-type grid layout overrides (key = device type slug) |

### Grid layout

Dense shelves (many bays in few rack units) automatically switch to a grid layout when vertical stacking would make bays too short. The column count is auto-calculated to produce the most square cells.

Override with `layouts` using the device type slug as the key and `{'columns': N}` as the value. Invalid values (zero, non-integer, exceeding bay count) fall back to auto-calculation with a logged warning.

See the [shelf devices guide](docs/shelf-devices-guide.md) for detailed examples.

## Shelf device guide

See [Shelf-devices Guide](https://raw.githubusercontent.com/paragm/netbox-render/main/docs/shelf-devices-guide.md) for a walkthrough on modeling rack shelves using device bays and how this plugin renders them.

## Known limitations

- Bay ordering is name-based, not positional — no way around this without modifying NetBox's data model
- Images off by default
- Rear face always renders grey (matches stock NetBox)
- Both faces show the same bay breakdown
- No migrations, no DB changes — rendering only
- Monkeypatch approach: I patch an internal method, so test after every NetBox upgrade

## Support

- **Bugs / feature requests**: [GitHub Issues](https://github.com/paragm/netbox-render/issues)
- **Questions**: [GitHub Discussions](https://github.com/paragm/netbox-render/discussions)
- **Security**: [Security Advisories](https://github.com/paragm/netbox-render/security/advisories/new) (not public issues)

## License

Apache-2.0
