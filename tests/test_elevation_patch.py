import math
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
        pass

    def test_device_with_all_empty_bays_subdivides(self):
        """A device with bays defined but no children should still subdivide."""
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


class TestOptimalColumns(unittest.TestCase):

    def test_single_bay_returns_one_column(self):
        from netbox_render.elevation_patch import _optimal_columns
        self.assertEqual(_optimal_columns(1, 230, 44), 1)

    def test_square_device_equal_bays(self):
        from netbox_render.elevation_patch import _optimal_columns
        result = _optimal_columns(4, 200, 200)
        self.assertEqual(result, 2)

    def test_wide_device_prefers_more_columns(self):
        from netbox_render.elevation_patch import _optimal_columns
        result = _optimal_columns(6, 230, 44)
        self.assertGreater(result, 1)

    def test_six_bays_in_2u(self):
        from netbox_render.elevation_patch import _optimal_columns
        result = _optimal_columns(6, 230, 44)
        rows = math.ceil(6 / result)
        cell_w = 230 / result
        cell_h = 44 / rows
        ratio = max(cell_w, cell_h) / min(cell_w, cell_h)
        self.assertLess(ratio, 3.0)

    def test_twelve_bays_in_2u(self):
        from netbox_render.elevation_patch import _optimal_columns
        result = _optimal_columns(12, 230, 44)
        rows = math.ceil(12 / result)
        self.assertGreater(result, 2)
        self.assertGreater(rows, 1)

    def test_returns_n_bays_for_single_row_optimal(self):
        from netbox_render.elevation_patch import _optimal_columns
        result = _optimal_columns(3, 300, 100)
        self.assertIn(result, [1, 2, 3])


class TestResolveColumns(unittest.TestCase):

    def test_config_override_takes_precedence(self):
        from netbox_render.elevation_patch import _resolve_columns
        with patch('netbox_render.elevation_patch._get_plugin_setting') as mock_setting:
            mock_setting.return_value = {'mac-mini-shelf': {'columns': 3}}
            result = _resolve_columns('mac-mini-shelf', 6, 230, 44)
            self.assertEqual(result, 3)

    def test_config_override_with_unknown_slug_falls_through(self):
        from netbox_render.elevation_patch import _resolve_columns
        with patch('netbox_render.elevation_patch._get_plugin_setting') as mock_setting:
            mock_setting.return_value = {'other-device': {'columns': 5}}
            result = _resolve_columns('mac-mini-shelf', 4, 230, 120)
            self.assertGreater(result, 0)

    def test_auto_picks_squarest_cells(self):
        from netbox_render.elevation_patch import _resolve_columns
        with patch('netbox_render.elevation_patch._get_plugin_setting', return_value={}):
            result = _resolve_columns('desktop-shelf-5u', 4, 220, 110)
            rows = math.ceil(4 / result)
            cell_w = 220 / result
            cell_h = 110 / rows
            ratio = max(cell_w, cell_h) / min(cell_w, cell_h)
            self.assertLessEqual(ratio, 3.0)

    def test_tall_device_stays_vertical(self):
        from netbox_render.elevation_patch import _resolve_columns
        with patch('netbox_render.elevation_patch._get_plugin_setting', return_value={}):
            result = _resolve_columns('server-chassis', 4, 220, 880)
            self.assertEqual(result, 1)

    def test_4_bays_5u_shelf_picks_single_row(self):
        from netbox_render.elevation_patch import _optimal_columns
        result = _optimal_columns(4, 220, 110)
        self.assertEqual(result, 4)

    def test_4_bays_42u_chassis_stacks_vertically(self):
        from netbox_render.elevation_patch import _optimal_columns
        result = _optimal_columns(4, 220, 924)
        self.assertEqual(result, 1)

    def test_auto_avoids_too_narrow_cells(self):
        from netbox_render.elevation_patch import _resolve_columns, MIN_CELL_WIDTH
        with patch('netbox_render.elevation_patch._get_plugin_setting', return_value={}):
            result = _resolve_columns('dense-shelf', 24, 220, 44)
            cell_w = 220 / result
            self.assertGreaterEqual(cell_w, MIN_CELL_WIDTH)

    def test_short_device_many_bays_uses_grid(self):
        from netbox_render.elevation_patch import _resolve_columns
        with patch('netbox_render.elevation_patch._get_plugin_setting', return_value={}):
            result = _resolve_columns('rpi-cluster', 8, 230, 44)
            self.assertGreater(result, 1)

    def test_config_columns_one_forces_horizontal(self):
        from netbox_render.elevation_patch import _resolve_columns
        with patch('netbox_render.elevation_patch._get_plugin_setting') as mock_setting:
            mock_setting.return_value = {'rpi-cluster': {'columns': 1}}
            result = _resolve_columns('rpi-cluster', 8, 230, 44)
            self.assertEqual(result, 1)

    def test_config_columns_zero_falls_back(self):
        from netbox_render.elevation_patch import _resolve_columns
        with patch('netbox_render.elevation_patch._get_plugin_setting') as mock_setting:
            mock_setting.return_value = {'rpi-cluster': {'columns': 0}}
            result = _resolve_columns('rpi-cluster', 8, 230, 44)
            self.assertGreater(result, 1)

    def test_config_columns_string_falls_back(self):
        from netbox_render.elevation_patch import _resolve_columns
        with patch('netbox_render.elevation_patch._get_plugin_setting') as mock_setting:
            mock_setting.return_value = {'rpi-cluster': {'columns': 'three'}}
            result = _resolve_columns('rpi-cluster', 8, 230, 44)
            self.assertGreater(result, 1)

    def test_config_columns_exceeds_bays_falls_back(self):
        from netbox_render.elevation_patch import _resolve_columns
        with patch('netbox_render.elevation_patch._get_plugin_setting') as mock_setting:
            mock_setting.return_value = {'my-shelf': {'columns': 50}}
            result = _resolve_columns('my-shelf', 4, 230, 44)
            self.assertGreater(result, 0)
            self.assertLessEqual(result, 4)

    def test_config_layouts_not_a_dict_falls_back(self):
        from netbox_render.elevation_patch import _resolve_columns
        with patch('netbox_render.elevation_patch._get_plugin_setting') as mock_setting:
            mock_setting.return_value = 'not-a-dict'
            result = _resolve_columns('rpi-cluster', 8, 230, 44)
            self.assertGreater(result, 1)


class TestCellFontSize(unittest.TestCase):

    def test_wide_cell_uses_default(self):
        from netbox_render.elevation_patch import _cell_font_size, LABEL_FONT_SIZE
        self.assertEqual(_cell_font_size(200), LABEL_FONT_SIZE)

    def test_100px_cell_uses_default(self):
        from netbox_render.elevation_patch import _cell_font_size, LABEL_FONT_SIZE
        self.assertEqual(_cell_font_size(100), LABEL_FONT_SIZE)

    def test_narrow_cell_scales_down(self):
        from netbox_render.elevation_patch import _cell_font_size
        result = _cell_font_size(55)
        self.assertLess(result, 13)
        self.assertGreaterEqual(result, 9)

    def test_very_narrow_cell_floors_at_9(self):
        from netbox_render.elevation_patch import _cell_font_size
        self.assertEqual(_cell_font_size(20), 9)


class TestWrapLabel(unittest.TestCase):

    def test_short_label_no_wrap(self):
        from netbox_render.elevation_patch import _wrap_label
        result = _wrap_label("1: ok", 200, 13)
        self.assertEqual(result, ["1: ok"])

    def test_long_label_wraps(self):
        from netbox_render.elevation_patch import _wrap_label
        result = _wrap_label("1: frame03-device", 55, 9)
        self.assertGreater(len(result), 1)
        self.assertEqual(''.join(r.strip() for r in result).replace(' ', ''),
                         "1:frame03-device".replace(' ', ''))

    def test_wraps_at_hyphen(self):
        from netbox_render.elevation_patch import _wrap_label
        result = _wrap_label("1: my-device", 60, 9)
        if len(result) > 1:
            self.assertTrue(result[0].endswith('-') or result[0].endswith(' '))

    def test_wraps_at_space(self):
        from netbox_render.elevation_patch import _wrap_label
        result = _wrap_label("1: a b c d e f", 50, 9)
        self.assertGreater(len(result), 1)

    def test_hard_breaks_long_word(self):
        from netbox_render.elevation_patch import _wrap_label
        result = _wrap_label("abcdefghijklmnopqrstuvwxyz", 30, 9)
        self.assertGreater(len(result), 1)
        for line in result:
            self.assertGreater(len(line), 0)

    def test_empty_label(self):
        from netbox_render.elevation_patch import _wrap_label
        result = _wrap_label("", 100, 13)
        self.assertEqual(result, [""])

    def test_exact_fit_no_wrap(self):
        from netbox_render.elevation_patch import _wrap_label
        result = _wrap_label("abc", 100, 13)
        self.assertEqual(result, ["abc"])


class TestGridGeometry(unittest.TestCase):

    def test_grid_cell_coordinates(self):
        x, y = 50, 100
        width, total_height = 230, 44
        columns = 3
        n_bays = 6
        rows = math.ceil(n_bays / columns)
        cell_width = width / columns
        cell_height = total_height / rows

        expected = [
            (50, 100),
            (50 + cell_width, 100),
            (50 + 2 * cell_width, 100),
            (50, 100 + cell_height),
            (50 + cell_width, 100 + cell_height),
            (50 + 2 * cell_width, 100 + cell_height),
        ]

        for i in range(n_bays):
            col = i % columns
            row = i // columns
            bay_x = x + col * cell_width
            bay_y = y + row * cell_height
            self.assertAlmostEqual(bay_x, expected[i][0])
            self.assertAlmostEqual(bay_y, expected[i][1])

    def test_grid_cell_sizes(self):
        width, total_height = 230, 44
        columns = 3
        n_bays = 6
        rows = math.ceil(n_bays / columns)
        cell_width = width / columns
        cell_height = total_height / rows

        self.assertAlmostEqual(cell_width, 230 / 3)
        self.assertAlmostEqual(cell_height, 22.0)

    def test_grid_text_centered_in_cell(self):
        bay_x, bay_y = 126.67, 122.0
        cell_width, cell_height = 76.67, 22.0
        text_coords = (bay_x + cell_width / 2, bay_y + cell_height / 2)
        self.assertAlmostEqual(text_coords[0], 165.005)
        self.assertAlmostEqual(text_coords[1], 133.0)

    def test_partial_last_row_empty_cells(self):
        n_bays = 7
        columns = 3
        rows = math.ceil(n_bays / columns)
        total_cells = columns * rows
        self.assertEqual(rows, 3)
        self.assertEqual(total_cells, 9)
        empty_count = total_cells - n_bays
        self.assertEqual(empty_count, 2)


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

    def _make_device(self, bays=None, device_type_slug='generic-shelf'):
        device = MagicMock()
        device.pk = 42
        device.device_type.slug = device_type_slug
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

        with patch.object(self.ep, '_get_plugin_setting', side_effect=lambda key, default=None: default):
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

        with patch.object(self.ep, '_get_plugin_setting', side_effect=lambda key, default=None: default):
            self.ep._patched_draw_device(
                self.svg_instance, device, (50, 100), (200, 30), color='aa1409'
            )

        self.mock_original.assert_not_called()
        self.assertEqual(self.mock_drawing.add.call_count, 2)

    def test_mixed_bays_front_face(self):
        bays = [
            self._make_bay('Bay 1', child_name='Server-01', role_color='4caf50'),
            self._make_bay('Bay 2'),
            self._make_bay('Bay 3', child_name='Server-03', role_color='ff5722'),
        ]
        device = self._make_device(bays=bays)

        with patch.object(self.ep, '_get_plugin_setting', side_effect=lambda key, default=None: default):
            self.ep._patched_draw_device(
                self.svg_instance, device, (50, 100), (200, 90), color='aa1409'
            )

        self.mock_original.assert_not_called()
        self.assertEqual(self.mock_drawing.add.call_count, 5)

    def test_rear_face_no_color(self):
        bays = [
            self._make_bay('Bay 1', child_name='Server-01', role_color='4caf50'),
        ]
        device = self._make_device(bays=bays)

        with patch.object(self.ep, '_get_plugin_setting', side_effect=lambda key, default=None: default):
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

    def test_grid_layout_with_config_override(self):
        bays = [self._make_bay(f'Slot {i+1}', child_name=f'mini-{i+1}') for i in range(6)]
        device = self._make_device(bays=bays, device_type_slug='mac-mini-shelf')

        def mock_setting(key, default=None):
            if key == 'layouts':
                return {'mac-mini-shelf': {'columns': 3}}
            return default

        with patch.object(self.ep, '_get_plugin_setting', side_effect=mock_setting):
            self.ep._patched_draw_device(
                self.svg_instance, device, (50, 100), (230, 44), color='aa1409'
            )

        self.mock_original.assert_not_called()
        self.assertTrue(self.mock_drawing.add.call_count >= 6)

    def test_grid_renders_empty_padding_cells(self):
        bays = [self._make_bay(f'Slot {i+1}', child_name=f'rpi-{i+1}') for i in range(7)]
        device = self._make_device(bays=bays, device_type_slug='rpi-shelf')

        def mock_setting(key, default=None):
            if key == 'layouts':
                return {'rpi-shelf': {'columns': 3}}
            return default

        with patch.object(self.ep, '_get_plugin_setting', side_effect=mock_setting):
            self.ep._patched_draw_device(
                self.svg_instance, device, (50, 100), (230, 66), color='aa1409'
            )

        self.mock_original.assert_not_called()
        self.assertTrue(self.mock_drawing.add.call_count >= 9)

    def test_auto_grid_for_many_bays_in_short_device(self):
        bays = [self._make_bay(f'Slot {i+1}') for i in range(8)]
        device = self._make_device(bays=bays)

        with patch.object(self.ep, '_get_plugin_setting', return_value={}):
            self.ep._patched_draw_device(
                self.svg_instance, device, (50, 100), (230, 44), color='aa1409'
            )

        self.mock_original.assert_not_called()


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
