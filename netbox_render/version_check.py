import inspect


EXPECTED_PARAMS = ['self', 'device', 'coords', 'size', 'color', 'image']


def verify_patch_target():
    from dcim.svg.racks import RackElevationSVG

    sig = inspect.signature(RackElevationSVG._draw_device)
    actual_params = list(sig.parameters.keys())
    if actual_params != EXPECTED_PARAMS:
        raise RuntimeError(
            f"netbox_render: RackElevationSVG._draw_device signature mismatch. "
            f"Expected {EXPECTED_PARAMS}, got {actual_params}. "
            f"This NetBox version may be incompatible — the plugin cannot safely patch elevation rendering."
        )
