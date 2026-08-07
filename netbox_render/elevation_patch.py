import logging
import math

from django.conf import settings
from svgwrite.container import Hyperlink
from svgwrite.masking import ClipPath
from svgwrite.shapes import Line, Rect
from svgwrite.text import Text

from dcim.svg.racks import RackElevationSVG, get_device_description
from utilities.html import foreground_color

from .version_check import verify_patch_target

logger = logging.getLogger('netbox_render')

_original_draw_device = None

MIN_CELL_HEIGHT = 8
MIN_CELL_WIDTH = 30
LABEL_FONT_SIZE = 13
CHAR_WIDTH_RATIO = 0.55


def _get_plugin_setting(key, default=None):
    return settings.PLUGINS_CONFIG.get('netbox_render', {}).get(key, default)


def _cell_font_size(cell_width: float) -> int:
    if cell_width >= 100:
        return LABEL_FONT_SIZE
    return max(9, min(LABEL_FONT_SIZE, int(cell_width * 0.16)))


def _wrap_label(label: str, cell_width: float, font_size: int) -> list[str]:
    char_width = font_size * CHAR_WIDTH_RATIO
    max_chars = max(2, int(cell_width / char_width))
    if len(label) <= max_chars:
        return [label]
    result = []
    remaining = label
    while remaining:
        if len(remaining) <= max_chars:
            result.append(remaining)
            break
        break_at = max_chars
        for i in range(max_chars, 0, -1):
            if remaining[i - 1] in ' -_':
                break_at = i
                break
        result.append(remaining[:break_at])
        remaining = remaining[break_at:].lstrip()
    return result


def _optimal_columns(n_bays, width, height):
    best = (float('inf'), n_bays, 0)
    best_cols = 1
    for cols in range(1, n_bays + 1):
        cell_w = width / cols
        if cell_w < MIN_CELL_WIDTH:
            continue
        rows = math.ceil(n_bays / cols)
        cell_h = height / rows
        if cell_h < MIN_CELL_HEIGHT:
            continue
        ratio = max(cell_w, cell_h) / min(cell_w, cell_h)
        empty = (cols * rows) - n_bays
        key = (ratio + empty * 0.5, empty, -cols)
        if key < best:
            best = key
            best_cols = cols
    return best_cols


def _resolve_columns(device_type_slug, n_bays, width, height):
    layouts = _get_plugin_setting('layouts', {})
    if isinstance(layouts, dict) and device_type_slug in layouts:
        try:
            cols = int(layouts[device_type_slug].get('columns', 1))
        except (TypeError, ValueError, AttributeError):
            cols = 0
        if 1 <= cols <= n_bays:
            return cols
        logger.warning("netbox_render: invalid columns=%r for %s, falling back to auto", cols, device_type_slug)
    return _optimal_columns(n_bays, width, height)


def _render_wrapped_text(container, lines, text_x, bay_y, cell_height,
                         font_size, clip_id, text_color, css_extra,
                         stroke_outline=False):
    line_height = font_size * 1.3
    total_text_height = len(lines) * line_height
    font_style = f'font-size:{font_size}px' if font_size != LABEL_FONT_SIZE else None
    padding_bottom = 3

    if stroke_outline:
        text_start_y = bay_y + cell_height - total_text_height - padding_bottom + font_size * 0.4
    else:
        text_start_y = bay_y + (cell_height - total_text_height) / 2 + font_size * 0.4

    for j, line_text in enumerate(lines):
        line_y = text_start_y + j * line_height
        base_kwargs = dict(insert=(text_x, line_y))
        if font_style:
            base_kwargs['style'] = font_style

        if stroke_outline:
            container.add(Text(
                line_text, stroke='black', stroke_width='0.3em',
                stroke_linejoin='round', class_=f'device-image-label{css_extra}',
                **base_kwargs,
            ))
            container.add(Text(
                line_text, fill='white',
                class_=f'device-image-label{css_extra}',
                **base_kwargs,
            ))
        else:
            container.add(Text(
                line_text, fill=text_color,
                clip_path=f"url(#{clip_id})",
                class_=f'label{css_extra}',
                **base_kwargs,
            ))


def _patched_draw_device(self, device, coords, size, color=None, image=None):
    try:
        bay_list = list(
            device.devicebays
            .select_related('installed_device__role', 'installed_device__device_type')
            .order_by('name')
        )
    except Exception as e:
        logger.error("netbox_render: failed to query devicebays for %s (pk=%s): %s", device, device.pk, e)
        return _original_draw_device(self, device, coords, size, color=color, image=image)

    n_bays = len(bay_list)
    logger.debug(
        "netbox_render: device=%s pk=%s device_type_slug=%s devicebays=%d coords=%s size=%s",
        device, device.pk, device.device_type.slug, n_bays, coords, size,
    )
    if n_bays == 0:
        return _original_draw_device(self, device, coords, size, color=color, image=image)

    enable_images = _get_plugin_setting('enable_images', False)
    x, y = coords
    width, total_height = size

    columns = _resolve_columns(device.device_type.slug, n_bays, width, total_height)
    rows = math.ceil(n_bays / columns)
    cell_width = width / columns
    cell_height = total_height / rows
    logger.debug(
        "netbox_render: grid=%dx%d cell=%.1fx%.1f (height_per_bay=%.1f, threshold=%d)",
        columns, rows, cell_width, cell_height, total_height / n_bays, MIN_CELL_HEIGHT,
    )

    font_size = _cell_font_size(cell_width)

    for i, bay in enumerate(bay_list):
        index = i + 1
        child = bay.installed_device
        col = i % columns
        row = i // columns
        bay_x = x + col * cell_width
        bay_y = y + row * cell_height
        bay_coords = (bay_x, bay_y)
        bay_size = (cell_width, cell_height)

        if child:
            bay_color = child.role.color if color is not None else None
            label = f"{index}: {child.name or str(child.device_type)}"
            description = get_device_description(child)
            device_url = f'{self.base_url}{child.get_absolute_url()}'
        else:
            bay_color = None
            label = f"{index}: (empty)"
            description = f"Bay {bay.name}: empty"
            device_url = None

        text_color = f'#{foreground_color(bay_color)}' if bay_color else '#000000'
        text_x = bay_x + cell_width / 2

        is_shaded = self.highlight_devices and (not child or child not in self.highlight_devices)
        css_extra = ' shaded' if is_shaded else ''

        if cell_height < MIN_CELL_HEIGHT:
            label_lines = [str(index)]
        else:
            label_lines = _wrap_label(label, cell_width, font_size)

        clip_id = f"clip-bay-{device.pk}-{i}"
        clip_path = ClipPath(id=clip_id)
        clip_path.add(Rect(bay_coords, bay_size))
        self.drawing.defs.add(clip_path)

        container = self.drawing

        if device_url:
            link = Hyperlink(href=device_url, target="_parent")
            link.set_desc(description)
            container = link

        if bay_color:
            container.add(Rect(bay_coords, bay_size, style=f'fill: #{bay_color}', class_=f'slot{css_extra}'))
        else:
            container.add(Rect(bay_coords, bay_size, class_=f'slot blocked{css_extra}'))

        if row > 0:
            container.add(Line(
                start=(bay_x, bay_y),
                end=(bay_x + cell_width, bay_y),
                stroke='#000000',
                stroke_width=0.5,
                stroke_opacity=0.3,
            ))
        if col > 0:
            container.add(Line(
                start=(bay_x, bay_y),
                end=(bay_x, bay_y + cell_height),
                stroke='#000000',
                stroke_width=0.5,
                stroke_opacity=0.3,
            ))

        _render_wrapped_text(
            container, label_lines, text_x, bay_y, cell_height,
            font_size, clip_id, text_color, css_extra,
        )

        if child:
            child_dt = child.device_type
            logger.debug(
                "netbox_render: bay=%s child=%s child_device_type=%s (slug=%s) "
                "enable_images=%s include_images=%s front_image=%s rear_image=%s "
                "raw_front='%s' raw_rear='%s'",
                bay.name, child, child_dt, child_dt.slug,
                enable_images, self.include_images,
                bool(child_dt.front_image), bool(child_dt.rear_image),
                getattr(child_dt.front_image, 'name', ''), getattr(child_dt.rear_image, 'name', ''),
            )
        if enable_images and child and self.include_images:
            child_image = child.device_type.front_image if color is not None else child.device_type.rear_image
            if child_image:
                from svgwrite.image import Image
                url = f'{self.base_url}{child_image.url}' if child_image.url.startswith('/') else child_image.url
                img = Image(
                    href=url,
                    insert=bay_coords,
                    size=bay_size,
                    class_=f'device-image{css_extra}',
                )
                img.fit(scale='slice')
                container.add(img)
                _render_wrapped_text(
                    container, label_lines, text_x, bay_y, cell_height,
                    font_size, clip_id, text_color, css_extra,
                    stroke_outline=True,
                )

        if device_url:
            self.drawing.add(link)

    total_cells = columns * rows
    for i in range(n_bays, total_cells):
        col = i % columns
        row = i // columns
        bay_x = x + col * cell_width
        bay_y = y + row * cell_height
        self.drawing.add(Rect((bay_x, bay_y), (cell_width, cell_height), class_='slot blocked'))
        if row > 0:
            self.drawing.add(Line(
                start=(bay_x, bay_y),
                end=(bay_x + cell_width, bay_y),
                stroke='#000000',
                stroke_width=0.5,
                stroke_opacity=0.3,
            ))
        if col > 0:
            self.drawing.add(Line(
                start=(bay_x, bay_y),
                end=(bay_x, bay_y + cell_height),
                stroke='#000000',
                stroke_width=0.5,
                stroke_opacity=0.3,
            ))


def apply_elevation_patch():
    global _original_draw_device

    if _original_draw_device is not None:
        return

    verify_patch_target()

    _original_draw_device = RackElevationSVG._draw_device
    RackElevationSVG._draw_device = _patched_draw_device

    logger.info("netbox_render: rack elevation patch applied successfully")
