import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import build_map_recovery_preview as builder
from scripts.build_map_recovery_preview import (
    BASE_CELL,
    LONG_EDGE,
    MIN_SAMPLES,
    NO_HIT,
    VIEW_ASPECT,
    _alignment_bits,
    _read_cluster,
    cell_size,
    fit_origin,
    grow_surface,
    hillshade,
    plot_bounds,
    raster_size,
    rasterise_depth,
    render_point_cloud,
    smooth_surface,
)


class CellSizeTests(unittest.TestCase):
    def test_cell_size_doubles_per_lod_and_matches_the_hand_derived_hlod1(self):
        self.assertEqual(cell_size(0), 64.0)
        # 128 m for HLOD1 was derived by hand for indie_dg002 before this
        # builder existed, and is the independent check on the doubling rule.
        self.assertEqual(cell_size(1), 128.0)
        self.assertEqual(cell_size(2), 256.0)


class PreviewInputTests(unittest.TestCase):
    def test_missing_asset_map_is_a_nonfatal_degraded_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing-assets.json"
            maps_root = Path(tmp) / "maps"
            output_root = Path(tmp) / "render"
            maps_root.mkdir()
            with mock.patch("sys.argv", [
                "build_map_recovery_preview.py",
                "--asset-map", str(missing),
                "--maps-root", str(maps_root),
                "--output-root", str(output_root),
            ]):
                self.assertEqual(builder.main(), 0)

    def test_exact_positions_render_an_explicit_point_cloud_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = render_point_cloud(
                "test_level",
                [(-10.0, -2.0, 20.0), (30.0, 12.0, -40.0)],
                Path(tmp),
            )
            self.assertEqual(manifest["status"], "inferred_registry_point_cloud_preview")
            self.assertEqual(manifest["render"]["pointCount"], 2)
            self.assertEqual(manifest["render"]["elevationRange"], {"min": -2.0, "max": 12.0})
            self.assertIn("Evidence-only", manifest["boundary"])
            image = Path(tmp, "test_level_registry_point_cloud.png")
            self.assertTrue(image.is_file())
            self.assertEqual(image.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")


class FitOriginTests(unittest.TestCase):
    """The grid origin is recovered from marker occupancy, or not claimed."""

    def _lods(self, cells):
        return {"0": [{"i": i, "j": j, "pathId": 1, "name": "n"} for i, j in cells]}

    def test_origin_is_recovered_from_markers_that_sit_on_occupied_cells(self):
        # Cells (16,16)..(17,17) are occupied; with a -1024 origin and 64 m
        # cells that is world x/z 0..128.
        lods = self._lods([(16, 16), (17, 16), (16, 17), (17, 17)])
        points = [(x, z) for x in range(4, 128, 8) for z in range(4, 128, 16)]
        fit = fit_origin(lods, points)

        self.assertIsNotNone(fit)
        self.assertEqual((fit["originX"], fit["originZ"]), (-1024.0, -1024.0))
        self.assertEqual(fit["coverage"], 1.0)
        self.assertEqual(fit["samplePoints"], len(points))
        self.assertEqual(fit["baseCellSize"], BASE_CELL)

    def test_too_few_markers_leave_the_origin_unclaimed(self):
        lods = self._lods([(16, 16), (17, 17)])
        self.assertIsNone(fit_origin(lods, [(10.0, 10.0)] * (MIN_SAMPLES - 1)))

    def test_alignment_breaks_ties_toward_a_streaming_grid_origin(self):
        # A power-of-two aligned origin divides by two more often, so a stray
        # marker cannot drag the answer one cell off the real grid.
        self.assertGreater(_alignment_bits(-2048), _alignment_bits(-2176))
        self.assertGreater(_alignment_bits(-1024), _alignment_bits(-960))

    def test_lods_must_agree_so_a_coarse_lod_cannot_carry_a_wrong_origin(self):
        # HLOD0 says the content is at world 0..128; HLOD1's single cell covers
        # 0..128 too. Only an origin satisfying both may win.
        lods = {
            "0": [{"i": 16, "j": 16, "pathId": 1, "name": "n"}],
            "1": [{"i": 8, "j": 8, "pathId": 2, "name": "n"}],
        }
        points = [(float(x), float(x)) for x in range(2, 62)]
        fit = fit_origin(lods, points)
        self.assertEqual((fit["originX"], fit["originZ"]), (-1024.0, -1024.0))
        self.assertEqual(fit["coverage"], 1.0)


class RasterTests(unittest.TestCase):
    def test_bounds_are_padded_out_to_the_pages_view_aspect(self):
        bounds = plot_bounds([(0.0, 0.0), (100.0, 100.0)])
        width = bounds["maxX"] - bounds["minX"]
        height = bounds["maxZ"] - bounds["minZ"]
        self.assertAlmostEqual(width / height, VIEW_ASPECT, places=6)
        # The markers stay inside the padded box.
        self.assertLess(bounds["minX"], 0.0)
        self.assertGreater(bounds["maxZ"], 100.0)

    def test_raster_keeps_the_world_aspect_on_a_fixed_long_edge(self):
        tall = raster_size(800.0, 1000.0)
        wide = raster_size(1000.0, 800.0)
        self.assertEqual(tall, (880, 1100))
        self.assertEqual(wide, (1100, 880))
        self.assertEqual(max(tall), LONG_EDGE)


class SurfaceRasterTests(unittest.TestCase):
    """Triangles are rendered as a depth-tested surface, not a point cloud."""

    def _cluster_obj(self, tmp, body):
        path = Path(tmp) / "S_HLOD1_0_0_Cluster_1_p1.obj"
        path.write_text(body, encoding="utf-8")
        return path

    def test_cluster_obj_parses_vertices_and_triangles(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._cluster_obj(tmp, "g c\nv 0 1 0\nv 1 1 0\nv 0 1 1\n"
                                          "vn 0 1 0\nvn 0 1 0\nvn 0 1 0\n"
                                          "vt 0 0\nf 1/1/1 2/2/2 3/3/3\n")
            vertices, faces = _read_cluster(path)

        self.assertEqual(len(vertices), 3)
        # Normals are deliberately not read: shading comes from the smoothed
        # height field, and per-facet normals would only add back the noise.
        self.assertEqual(faces, [(0, 1, 2)])

    def test_a_flat_triangle_fills_pixels_and_records_its_elevation(self):
        bounds = {"minX": 0.0, "maxX": 8.0, "minZ": 0.0, "maxZ": 8.0}
        fit = {"originX": 0.0, "originZ": 0.0}
        with tempfile.TemporaryDirectory() as tmp:
            # A large upward-facing triangle sitting at world Y = 5.
            path = self._cluster_obj(tmp, "g c\nv 60 5 -60\nv -60 5 -60\nv -60 5 60\n"
                                          "f 1 2 3\n")
            clusters = [{"i": 0, "j": 0, "pathId": 1, "name": "S_HLOD1_0_0_Cluster_1"}]
            depth, used, triangles = rasterise_depth(
                clusters, 1, fit, bounds, {"1": path}, 16, 16
            )

        self.assertEqual(triangles, 1)
        self.assertEqual(used[0]["triangles"], 1)
        covered = [value for value in depth if value > NO_HIT]
        self.assertTrue(covered, "the triangle should cover pixels")
        self.assertAlmostEqual(max(covered), 5.0, places=3)

    def test_the_higher_surface_wins_the_depth_test(self):
        bounds = {"minX": 0.0, "maxX": 8.0, "minZ": 0.0, "maxZ": 8.0}
        fit = {"originX": 0.0, "originZ": 0.0}
        with tempfile.TemporaryDirectory() as tmp:
            # Two stacked triangles; only the upper one may reach the image,
            # because the camera looks straight down.
            path = self._cluster_obj(tmp, "g c\n"
                                          "v 60 2 -60\nv -60 2 -60\nv -60 2 60\n"
                                          "v 60 9 -60\nv -60 9 -60\nv -60 9 60\n"
                                          "f 1 2 3\nf 4 5 6\n")
            clusters = [{"i": 0, "j": 0, "pathId": 1, "name": "S_HLOD1_0_0_Cluster_1"}]
            depth, _, triangles = rasterise_depth(
                clusters, 1, fit, bounds, {"1": path}, 16, 16
            )

        self.assertEqual(triangles, 2)
        covered = [value for value in depth if value > NO_HIT]
        self.assertTrue(covered)
        self.assertTrue(all(abs(value - 9.0) < 1e-6 for value in covered))

    def test_a_missing_mesh_file_is_skipped_without_failing_the_render(self):
        bounds = {"minX": 0.0, "maxX": 8.0, "minZ": 0.0, "maxZ": 8.0}
        clusters = [{"i": 0, "j": 0, "pathId": 99, "name": "absent"}]
        depth, used, triangles = rasterise_depth(
            clusters, 1, {"originX": 0.0, "originZ": 0.0}, bounds, {}, 8, 8
        )
        self.assertEqual((used, triangles), ([], 0))
        self.assertTrue(all(value <= NO_HIT for value in depth))


class ReliefShadingTests(unittest.TestCase):
    """Shading works from a grown, smoothed height field, not mesh normals."""

    def test_growing_joins_scattered_props_and_marks_what_was_real(self):
        width = height = 7
        depth = [NO_HIT] * (width * height)
        depth[3 * width + 1] = 10.0  # two isolated props with a gap between
        depth[3 * width + 5] = 20.0
        grown, real = grow_surface(depth, width, height, rounds=2)

        self.assertEqual(sum(1 for value in real if value), 2)
        covered = sum(1 for value in grown if value > NO_HIT)
        self.assertGreater(covered, 2, "the surface should grow outward")
        # Growth interpolates between the props rather than inventing extremes.
        values = [value for value in grown if value > NO_HIT]
        self.assertGreaterEqual(min(values), 10.0)
        self.assertLessEqual(max(values), 20.0)

    def test_growing_stops_after_the_requested_rounds(self):
        width = height = 21
        depth = [NO_HIT] * (width * height)
        depth[10 * width + 10] = 5.0
        grown, _ = grow_surface(depth, width, height, rounds=2)
        # A single seed grows into at most a 5x5 block after two rounds.
        self.assertLessEqual(sum(1 for value in grown if value > NO_HIT), 25)

    def test_smoothing_flattens_a_single_spike_into_its_surroundings(self):
        width = height = 9
        values = [1.0] * (width * height)
        values[4 * width + 4] = 100.0
        mask = [True] * (width * height)
        smoothed = smooth_surface(values, mask, width, height, radius=2, passes=1)

        self.assertLess(smoothed[4 * width + 4], 100.0)
        self.assertGreater(smoothed[4 * width + 3], 1.0)
        # Blurring conserves the field's total, so nothing is invented.
        self.assertAlmostEqual(sum(smoothed), sum(values), delta=1e-6 * sum(values))

    def test_hillshade_lights_a_slope_differently_from_flat_ground(self):
        width = height = 9
        mask = [True] * (width * height)
        flat = [5.0] * (width * height)
        ramp = [float(x) * 3.0 for y in range(height) for x in range(width)]

        flat_shade = hillshade(flat, mask, width, height)
        ramp_shade = hillshade(ramp, mask, width, height)
        centre = 4 * width + 4
        self.assertNotAlmostEqual(flat_shade[centre], ramp_shade[centre], places=3)
        for values in (flat_shade, ramp_shade):
            self.assertTrue(all(0.0 <= value <= 1.0 for value in values))

    def test_uncovered_pixels_are_never_shaded(self):
        width = height = 5
        mask = [False] * (width * height)
        mask[12] = True
        shades = hillshade([1.0] * (width * height), mask, width, height)
        self.assertTrue(all(shades[i] == 0.0 for i in range(len(shades)) if not mask[i]))


if __name__ == "__main__":
    unittest.main()
