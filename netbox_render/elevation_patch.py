import logging

from django.conf import settings
from svgwrite.container import Hyperlink
from svgwrite.masking import ClipPath
from svgwrite.shapes import Line, Rect
from svgwrite.text import Text

from dcim.svg.racks import RackElevationSVG, get_device_description, truncate_text
from utilities.html import foreground_color

from .version_check import verify_patch_target

logger = logging.getLogger('netbox_render')

_original_draw_device = None


def _get_plugin_setting(key, default=None):
    return settings.PLUGINS_CONFIG.get('netbox_render', {}).get(key, default)


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
        "netbox_render: device=%s pk=%s devicebays=%d coords=%s size=%s",
        device, device.pk, n_bays, coords, size,
    )
    if n_bays == 0:
        return _original_draw_device(self, device, coords, size, color=color, image=image)

    enable_images = _get_plugin_setting('enable_images', False)
    x, y = coords
    width, total_height = size
    bay_height = total_height / n_bays

    for i, bay in enumerate(bay_list):
        index = i + 1
        child = bay.installed_device
        bay_y = y + i * bay_height
        bay_coords = (x, bay_y)
        bay_size = (width, bay_height)

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
        text_coords = (
            x + width / 2,
            bay_y + bay_height / 2,
        )

        is_shaded = self.highlight_devices and (not child or child not in self.highlight_devices)
        css_extra = ' shaded' if is_shaded else ''

        if bay_height < 15:
            display_name = str(index)
        else:
            display_name = truncate_text(label, width)

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

        if i > 0:
            container.add(Line(
                start=(x, bay_y),
                end=(x + width, bay_y),
                stroke='#000000',
                stroke_width=0.5,
                stroke_opacity=0.3,
            ))

        container.add(
            Text(display_name, insert=text_coords, fill=text_color,
                 clip_path=f"url(#{clip_id})", class_=f'label{css_extra}')
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
                container.add(
                    Text(label, insert=text_coords, stroke='black', stroke_width='0.2em',
                         stroke_linejoin='round', class_=f'device-image-label{css_extra}')
                )
                container.add(
                    Text(label, insert=text_coords, fill='white',
                         class_=f'device-image-label{css_extra}')
                )

        if device_url:
            self.drawing.add(link)
        # empty bays with no link are already added directly to self.drawing via container


def apply_elevation_patch():
    global _original_draw_device

    if _original_draw_device is not None:
        return

    verify_patch_target()

    _original_draw_device = RackElevationSVG._draw_device
    RackElevationSVG._draw_device = _patched_draw_device

    logger.info("netbox_render: rack elevation patch applied successfully")
