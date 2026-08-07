from netbox.plugins import PluginConfig

from .version import __version__


class NetBoxRenderConfig(PluginConfig):
    name = 'netbox_render'
    verbose_name = 'Device Bay Rack Elevation Rendering'
    description = 'Subdivides device bay rectangles in rack elevation SVGs to show per-bay labels and links'
    version = __version__
    author = 'Parag Mehta'
    author_email = 'pmehta@pmehta.com'
    min_version = '4.6.0'
    max_version = '4.6.99'
    default_settings = {
        'enable_images': False,
        'layouts': {},
    }

    def ready(self):
        super().ready()
        from .elevation_patch import apply_elevation_patch
        apply_elevation_patch()


config = NetBoxRenderConfig
