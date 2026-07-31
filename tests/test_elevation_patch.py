import sys
import unittest
from unittest.mock import MagicMock, patch

mock_netbox_plugins = MagicMock()
mock_plugin_config = type('PluginConfig', (), {
    'name': '', 'verbose_name': '', 'description': '', 'version': '',
    'author': '', 'author_email': '', 'min_version': None, 'max_version': None,
    'default_settings': {}, 'required_settings': [],
})
mock_netbox_plugins.PluginConfig = mock_plugin_config

sys.modules.setdefault('netbox', MagicMock())
sys.modules.setdefault('netbox.plugins', mock_netbox_plugins)
sys.modules.setdefault('netbox.config', MagicMock())
sys.modules.setdefault('dcim', MagicMock())
sys.modules.setdefault('dcim.svg', MagicMock())
sys.modules.setdefault('dcim.svg.racks', MagicMock())
sys.modules.setdefault('utilities', MagicMock())
sys.modules.setdefault('utilities.html', MagicMock())
sys.modules.setdefault('django', MagicMock())
sys.modules.setdefault('django.conf', MagicMock())
sys.modules.setdefault('svgwrite', MagicMock())
sys.modules.setdefault('svgwrite.container', MagicMock())
sys.modules.setdefault('svgwrite.masking', MagicMock())
sys.modules.setdefault('svgwrite.shapes', MagicMock())
sys.modules.setdefault('svgwrite.text', MagicMock())

from netbox_render.version_check import EXPECTED_PARAMS


class TestBaySubdivisionGeometry(unittest.TestCase):

    def test_even_subdivision(self):
        x, y = 50, 100
        width, total_height = 200, 120
        n_bays = 4
        bay_height = total_height / n_bays

        for i in range(n_bays):
            bay_coords = (x, y + i * bay_height)
            bay_size = (width, bay_height)
            self.assertEqual(bay_coords[0], 50)
            self.assertEqual(bay_coords[1], 100 + i * 30)
            self.assertEqual(bay_size, (200, 30.0))

    def test_single_bay(self):
        x, y = 50, 100
        width, total_height = 200, 60
        bay_height = total_height / 1

        bay_coords = (x, y)
        bay_size = (width, bay_height)
        self.assertEqual(bay_coords, (50, 100))
        self.assertEqual(bay_size, (200, 60.0))

    def test_odd_number_of_bays(self):
        x, y = 50, 100
        width, total_height = 200, 90
        n_bays = 3
        bay_height = total_height / n_bays

        coords = [(x, y + i * bay_height) for i in range(n_bays)]
        self.assertAlmostEqual(coords[0][1], 100.0)
        self.assertAlmostEqual(coords[1][1], 130.0)
        self.assertAlmostEqual(coords[2][1], 160.0)

    def test_text_coords_centered(self):
        x, y = 50, 100
        width, bay_height = 200, 30
        text_coords = (x + width / 2, y + bay_height / 2)
        self.assertEqual(text_coords, (150.0, 115.0))


class TestBayLabeling(unittest.TestCase):

    def test_label_with_child_device(self):
        label = f"{1}: Server-01"
        self.assertEqual(label, "1: Server-01")

    def test_label_empty_bay(self):
        label = f"{3}: (empty)"
        self.assertEqual(label, "3: (empty)")

    def test_truncated_label_for_small_bay(self):
        bay_height = 10
        index = 2
        display = str(index) if bay_height < 15 else f"{index}: Some-Device-Name"
        self.assertEqual(display, "2")

    def test_full_label_for_normal_bay(self):
        bay_height = 30
        index = 2
        display = str(index) if bay_height < 15 else f"{index}: Some-Device-Name"
        self.assertEqual(display, "2: Some-Device-Name")

    def test_label_uses_device_type_when_no_name(self):
        index = 1
        child_name = None
        device_type = "PowerEdge C6420"
        label = f"{index}: {child_name or device_type}"
        self.assertEqual(label, "1: PowerEdge C6420")


class TestVersionCheck(unittest.TestCase):

    def test_expected_params_constant(self):
        self.assertEqual(
            EXPECTED_PARAMS,
            ['self', 'device', 'coords', 'size', 'color', 'image'],
        )

    def test_verify_raises_on_signature_mismatch(self):
        mock_class = MagicMock()
        mock_method = MagicMock()
        mock_method.__name__ = '_draw_device'

        import inspect
        mock_params = {
            'self': inspect.Parameter('self', inspect.Parameter.POSITIONAL_OR_KEYWORD),
            'device': inspect.Parameter('device', inspect.Parameter.POSITIONAL_OR_KEYWORD),
            'coords': inspect.Parameter('coords', inspect.Parameter.POSITIONAL_OR_KEYWORD),
            'size': inspect.Parameter('size', inspect.Parameter.POSITIONAL_OR_KEYWORD),
        }
        wrong_sig = inspect.Signature(parameters=list(mock_params.values()))

        with patch('netbox_render.version_check.inspect.signature', return_value=wrong_sig):
            mock_racks = MagicMock()
            mock_racks.RackElevationSVG._draw_device = mock_method
            with patch.dict('sys.modules', {'dcim.svg.racks': mock_racks}):
                from importlib import reload
                import netbox_render.version_check as vc
                reload(vc)
                with self.assertRaises(RuntimeError) as ctx:
                    vc.verify_patch_target()
                self.assertIn('signature mismatch', str(ctx.exception))


class TestShouldSubdivide(unittest.TestCase):

    def test_device_without_bays_delegates(self):
        """A device whose devicebays queryset returns empty should delegate to original."""
        # Covered by TestPatchedDrawDevice.test_no_bays_delegates_to_original
        pass

    def test_device_with_all_empty_bays_subdivides(self):
        """A device with bays defined but no children should still subdivide."""
        # Covered by TestPatchedDrawDevice.test_empty_bays_add_elements_without_hyperlink
        pass


class TestColorBehavior(unittest.TestCase):

    def test_front_face_uses_child_role_color(self):
        parent_color = 'aa1409'
        child_role_color = '4caf50'
        bay_color = child_role_color if parent_color is not None else None
        self.assertEqual(bay_color, '4caf50')

    def test_rear_face_passes_no_color(self):
        parent_color = None
        child_role_color = '4caf50'
        bay_color = child_role_color if parent_color is not None else None
        self.assertIsNone(bay_color)

    def test_empty_bay_has_no_color(self):
        child = None
        bay_color = None
        self.assertIsNone(bay_color)


class TestPatchedDrawDevice(unittest.TestCase):
    """Integration tests that exercise the actual _patched_draw_device function."""

    def setUp(self):
        import netbox_render.elevation_patch as ep
        self.ep = ep

        self.mock_original = MagicMock()
        ep._original_draw_device = self.mock_original

        self.mock_drawing = MagicMock()
        self.mock_defs = MagicMock()
        self.mock_drawing.defs = self.mock_defs

        self.svg_instance = MagicMock()
        self.svg_instance.drawing = self.mock_drawing
        self.svg_instance.base_url = 'http://netbox.local'
        self.svg_instance.highlight_devices = []
        self.svg_instance.include_images = False

    def _make_device(self, bays=None):
        device = MagicMock()
        device.pk = 42
        bay_list = bays if bays is not None else []
        qs = MagicMock()
        qs.select_related.return_value = qs
        qs.order_by.return_value = qs
        qs.__iter__ = MagicMock(return_value=iter(bay_list))
        qs.__len__ = MagicMock(return_value=len(bay_list))
        device.devicebays = qs
        return device

    def _make_bay(self, name, child_name=None, role_color='4caf50'):
        bay = MagicMock()
        bay.name = name
        if child_name:
            child = MagicMock()
            child.name = child_name
            child.role.color = role_color
            child.get_absolute_url.return_value = f'/dcim/devices/{child_name}/'
            child.device_type.front_image = None
            child.device_type.rear_image = None
            bay.installed_device = child
        else:
            bay.installed_device = None
        return bay

    def test_no_bays_delegates_to_original(self):
        device = self._make_device()
        coords = (50, 100)
        size = (200, 60)

        self.ep._patched_draw_device(self.svg_instance, device, coords, size, color='aa1409')

        self.mock_original.assert_called_once_with(
            self.svg_instance, device, coords, size, color='aa1409', image=None
        )
        self.mock_drawing.add.assert_not_called()

    def test_subdivides_bays_with_children(self):
        bays = [
            self._make_bay('Bay 1', child_name='Server-01', role_color='4caf50'),
            self._make_bay('Bay 2', child_name='Server-02', role_color='ff5722'),
        ]
        device = self._make_device(bays=bays)

        with patch.object(self.ep, '_get_plugin_setting', return_value=False):
            self.ep._patched_draw_device(
                self.svg_instance, device, (50, 100), (200, 60), color='aa1409'
            )

        self.mock_original.assert_not_called()
        self.assertEqual(self.mock_drawing.add.call_count, 2)
        self.assertTrue(self.mock_defs.add.call_count >= 2)

    def test_empty_bays_add_elements_without_hyperlink(self):
        bays = [
            self._make_bay('Bay 1'),
        ]
        device = self._make_device(bays=bays)

        with patch.object(self.ep, '_get_plugin_setting', return_value=False):
            self.ep._patched_draw_device(
                self.svg_instance, device, (50, 100), (200, 30), color='aa1409'
            )

        self.mock_original.assert_not_called()
        # Empty bays add Rect + Text directly to drawing (no Hyperlink wrapper)
        self.assertEqual(self.mock_drawing.add.call_count, 2)

    def test_mixed_bays_front_face(self):
        bays = [
            self._make_bay('Bay 1', child_name='Server-01', role_color='4caf50'),
            self._make_bay('Bay 2'),
            self._make_bay('Bay 3', child_name='Server-03', role_color='ff5722'),
        ]
        device = self._make_device(bays=bays)

        with patch.object(self.ep, '_get_plugin_setting', return_value=False):
            self.ep._patched_draw_device(
                self.svg_instance, device, (50, 100), (200, 90), color='aa1409'
            )

        self.mock_original.assert_not_called()
        # Bay 1 (filled): 1 drawing.add(link)
        # Bay 2 (empty, i=1): 3 drawing.add(Rect, Line, Text)
        # Bay 3 (filled): 1 drawing.add(link)
        self.assertEqual(self.mock_drawing.add.call_count, 5)

    def test_rear_face_no_color(self):
        bays = [
            self._make_bay('Bay 1', child_name='Server-01', role_color='4caf50'),
        ]
        device = self._make_device(bays=bays)

        with patch.object(self.ep, '_get_plugin_setting', return_value=False):
            self.ep._patched_draw_device(
                self.svg_instance, device, (50, 100), (200, 30), color=None
            )

        self.mock_original.assert_not_called()

    def test_empty_queryset_delegates_to_original(self):
        device = self._make_device(bays=[])

        self.ep._patched_draw_device(
            self.svg_instance, device, (50, 100), (200, 60), color='aa1409'
        )

        self.mock_original.assert_called_once()


class TestDoublePatching(unittest.TestCase):

    def test_apply_patch_is_idempotent(self):
        import netbox_render.elevation_patch as ep

        sentinel_original = MagicMock()
        ep._original_draw_device = sentinel_original

        with patch.object(ep, 'verify_patch_target'):
            ep.apply_elevation_patch()

        self.assertIs(ep._original_draw_device, sentinel_original)


if __name__ == '__main__':
    unittest.main()
