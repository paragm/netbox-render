# Contributing

## Setup

```bash
git clone https://github.com/paragm/netbox-render.git
cd netbox-render
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

## Tests

```bash
python -m unittest discover -s tests -v
```

## Making changes

1. Branch from `main`
2. Keep changes focused — this plugin patches one internal method, so scope is narrow
3. Add/update tests
4. Follow PEP 8

## Pull requests

**Bug fixes** — include reproduction steps and confirm the fix against a live NetBox instance.

**Features** — open an issue first. This plugin is intentionally narrow (rack elevation rendering for device bays). I'll likely close anything that expands beyond that.

**Docs** — always welcome.

## Security

Don't open public issues for security problems. Use [Security Advisories](https://github.com/paragm/netbox-render/security/advisories/new).

## License

Contributions are licensed under Apache-2.0.
