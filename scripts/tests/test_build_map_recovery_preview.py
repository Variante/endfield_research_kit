import json
import struct
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
    _is_explicit_overhead_cover,
    _is_detail_prop,
    _is_large_horizontal_triangle,
    _read_cluster,
    _read_textured_mesh,
    cell_size,
    elevation_color,
    fit_origin,
    grow_surface,
    hillshade,
    plot_bounds,
    raster_size,
    rasterise_depth,
    read_png_preview,
    render_depth_surface,
    render_level,
    render_point_cloud,
    render_point_height_mask,
    render_streaming_surface_samples,
    render_water_overlay,
    select_shared_origin,
    streaming_projection_payload,
    smooth_surface,
    water_scene_id,
)


class CellSizeTests(unittest.TestCase):
    def test_art_level_water_uses_owning_world_scene(self):
        self.assertEqual(water_scene_id("map01_lv005"), "map01")
        self.assertEqual(water_scene_id("dung", "map01_lv005"), "map01")
        self.assertEqual(water_scene_id("dung01_wrdg001"), "dung01_wrdg001")

    def test_cell_size_doubles_from_the_native_32_m_base_grid(self):
        self.assertEqual(cell_size(0), 32.0)
        self.assertEqual(cell_size(1), 64.0)
        self.assertEqual(cell_size(2), 128.0)

    def test_material_surface_preserves_source_rgba(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = render_depth_surface(
                "material", [5.0], 1, 1, Path(tmp), "surface",
                material_colors=bytes((120, 80, 40, 191)),
            )
            width, height, pixels = read_png_preview(Path(tmp) / "material_surface.png", 4)

        self.assertIsNotNone(manifest)
        self.assertEqual((width, height), (1, 1))
        self.assertEqual(pixels, bytes((120, 80, 40, 191)))



class PreviewInputTests(unittest.TestCase):
    def test_streaming_hlod_uses_exact_level_lod_hash_material_binding(self):
        binding = {"slot": "_BaseColorMap"}
        instances = [{"meshes": [{
            "name": "S_HLOD1_10_9_Cluster_-7",
            "obj": "export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/Mesh/S_HLOD1_10_9_Cluster_-7_p7.obj",
        }]}]
        with mock.patch.object(builder, "_HLOD_TEXTURE_BINDINGS", {("indie_dg002", 1, -7): binding}), \
                mock.patch.object(builder, "texture_bindings", return_value={}):
            result = builder.streaming_texture_bindings("indie_dg002", instances)

        self.assertEqual(result["StreamingAssets/Mesh/S_HLOD1_10_9_Cluster_-7_p7.obj"], binding)

    def test_map_regions_use_fixed_hlod_grid_origins_without_image_registration(self):
        self.assertEqual(builder.REGION_HLOD_GRID_ORIGINS["map01"], (-1024.0, -1024.0))
        self.assertEqual(builder.REGION_HLOD_GRID_ORIGINS["map02"], (-2048.0, -2048.0))
        self.assertEqual(builder.LEVEL_RENDER_ALIGNMENTS, {})

        frontend = (builder.ROOT / "webui/src/features/map_recovery/index.js").read_text(encoding="utf-8")
        self.assertIn("worldBounds: model.worldBounds", frontend)
        self.assertIn("const revealSelectedMap = (host) =>", frontend)
        self.assertIn("column.scrollTop +=", frontend)
        self.assertIn("function previewMapCoordinates(event)", frontend)
        self.assertIn("projection.maxZ - (canvasY - projection.viewY)", frontend)
        self.assertNotIn("alignment.scaleX", frontend)
        self.assertNotIn("minimapMaskRects", frontend)

    def test_exact_streaming_geometry_supersedes_inferred_hlod_background(self):
        hlod = {"status": "inferred_hlod_textured_preview", "src": "render/level_hlod_surface.png"}
        exact = {
            "status": "recovered_streaming_textured_topdown",
            "src": "render/scene_streaming_textured_topdown.png",
        }
        self.assertIs(builder.preferred_background_preview(exact, hlod), exact)

    def test_registry_points_do_not_supersede_recovered_hlod_surface(self):
        hlod = {"status": "inferred_hlod_grid_preview", "src": "render/level_hlod_surface.png"}
        points = {
            "status": "inferred_registry_point_cloud_preview",
            "src": "render/level_registry_point_cloud.png",
        }
        self.assertIs(builder.preferred_background_preview(points, hlod), hlod)

    def test_only_explicit_roof_or_ceiling_names_are_overhead_covers(self):
        self.assertTrue(_is_explicit_overhead_cover({"entityBase": "P_mod_map02_sfroof+1_001_02"}))
        self.assertTrue(_is_explicit_overhead_cover({"meshes": [{"name": "S_mod_com_ceiling+1_001_01_lod0"}]}))
        self.assertFalse(_is_explicit_overhead_cover({"entityBase": "P_prop_indie_sphub+1_001_04"}))
        self.assertFalse(_is_explicit_overhead_cover({"entityBase": "P_prop_map01_canopy+1_001_01"}))

    def test_detail_scan_excludes_only_large_near_horizontal_triangles(self):
        self.assertTrue(_is_large_horizontal_triangle([(0, 2, 0), (4, 2, 0), (0, 2, 4)]))
        self.assertFalse(_is_large_horizontal_triangle([(0, 2, 0), (0.1, 2, 0), (0, 2, 0.1)]))
        self.assertFalse(_is_large_horizontal_triangle([(0, 0, 0), (0, 4, 0), (0, 0, 4)]))

    def test_dijiang_detail_pass_can_keep_authored_props_without_ship_shells(self):
        self.assertTrue(_is_detail_prop({}, {"name": "S_prop_base01_zmdmachine+1_002_01_lod0"}))
        self.assertTrue(_is_detail_prop({"entityBase": "P_decal_base01_sign+1_001"}, {}))
        self.assertFalse(_is_detail_prop({}, {"name": "S_building_tundra_dijianghao+1_001_05_lod0"}))

    def test_authored_minimap_water_color_publishes_independent_overlay(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            minimap = root / "test_minimap.png"
            builder.write_png(minimap, 2, 2, [
                bytes((38, 110, 115, 255, 127, 127, 255, 255)),
                bytes((20, 20, 20, 255, 0, 0, 0, 0)),
            ])
            with mock.patch.object(builder, "LONG_EDGE", 32):
                overlay = render_water_overlay(
                    "test", "scene", {"minX": 0, "maxX": 128, "minZ": 0, "maxZ": 128},
                    {"scene": [{"i": 0, "j": 0, "pathId": 1, "name": "water"}]},
                    {}, root,
                )
        self.assertIsNotNone(overlay)
        self.assertEqual(overlay["status"], "recovered_authored_minimap_water_color_mask")
        self.assertEqual(overlay["renderedSectorCount"], 0)
        self.assertGreater(overlay["waterPixelRatio"], 0)

    def test_flowmap_without_authored_minimap_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            texture = root / "T_water_sector_flowmap_0_0_p1.png"
            builder.write_png(texture, 1, 1, [bytes((127, 127, 255, 255))])
            overlay = render_water_overlay(
                "test", "scene", {"minX": 0, "maxX": 128, "minZ": 0, "maxZ": 128},
                {"scene": [{"i": 0, "j": 0, "pathId": 1, "name": "water"}]},
                {"1": texture}, root,
            )
        self.assertIsNone(overlay)

    def test_minimap_color_without_water_sectors_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            builder.write_png(root / "test_minimap.png", 1, 1, [bytes((38, 110, 115, 255))])
            overlay = render_water_overlay(
                "test", "scene", {"minX": 0, "maxX": 128, "minZ": 0, "maxZ": 128},
                {}, {}, root,
            )
        self.assertIsNone(overlay)

    def test_point_height_mask_encodes_only_emitted_points(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            depth = [NO_HIT, 10.0, 20.0, NO_HIT]
            mask = render_point_height_mask(
                "test", depth, 2, 2, root, "height_mask", "all"
            )
            decoded = read_png_preview(root / "test_height_mask.png", 2)
        self.assertEqual(mask["encoding"], "uint16_rg_normalized_world_y")
        self.assertEqual(mask["pointPixelCount"], 2)
        self.assertEqual(mask["elevationRange"], {"min": 10.0, "max": 20.0})
        self.assertEqual(decoded[2][3], 0)
        self.assertEqual(decoded[2][7], 255)
        self.assertEqual(decoded[2][11], 255)

    def test_shared_streaming_sidecar_adapts_exact_matrices_and_meshes(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "blackbox01_dg001.json"
            source.write_text(json.dumps({
                "entityBases": [{
                    "entityBase": "P_build_blackbox_floor",
                    "meshes": [{"name": "S_build_blackbox_floor_lod0", "pathId": 9}],
                }],
                "instances": [{
                    "entityId": 7,
                    "entityBase": "P_build_blackbox_floor",
                    "matrixColumnMajor": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 12, 3, -8, 1],
                }],
            }), encoding="utf-8")
            positions, payload = streaming_projection_payload(source)

        self.assertEqual(positions, [(12.0, 3.0, -8.0)])
        instance = payload["markers"][0]["streamingInstance"]
        self.assertEqual(instance["meshes"][0]["pathId"], 9)
        self.assertEqual(instance["matrixColumnMajor"][12:15], [12, 3, -8])

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
            self.assertEqual(manifest["status"], "exact_registry_transform_point_cloud")
            self.assertEqual(manifest["render"]["pointCount"], 2)
            self.assertEqual(manifest["render"]["elevationRange"], {"min": -2.0, "max": 12.0})
            self.assertIn("Evidence-only", manifest["boundary"])
            self.assertEqual(
                manifest["elevationUnderlay"]["method"],
                "exact_registry_transform_grayscale_elevation_points",
            )
            self.assertIn("no growth", manifest["elevationUnderlay"]["boundary"])
            self.assertEqual(manifest["pointCloudOverlay"]["heightMask"]["elevationRange"], {"min": -2.0, "max": 12.0})
            self.assertTrue(Path(tmp, "test_level_registry_height_mask.png").is_file())
            self.assertTrue(Path(tmp, "test_level_registry_elevation_points.png").is_file())
            image = Path(tmp, "test_level_registry_point_cloud.png")
            self.assertTrue(image.is_file())
            self.assertEqual(image.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    def test_streaming_static_meshes_are_rasterized_instead_of_drawn_as_location_points(self):
        payload = {"markers": [{"streamingInstance": {
            "sourceFile": "Data/Streaming/PC/test/Streaming/InitChunkData_0_0_0_0.bytes",
            "meshes": [{
                "name": "S_build_test_lod0",
                "pathId": 42,
                "obj": "export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/Mesh/S_build_test_lod0_p2A.obj",
            }],
        }}]}
        def fake_raster(_streaming, _bounds, width, height, _bindings):
            return {
                "depth": [1.0] * (width * height), "albedo": bytearray(width * height * 4),
                "usedInstances": 1, "texturedInstances": 0, "triangles": 7,
                "texturedTriangles": 0, "vertexSamples": 3, "texturedPixels": 0, "usedTextures": [],
            }

        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
            builder, "rasterise_streaming_depth", side_effect=fake_raster
        ), mock.patch.object(builder, "texture_bindings", return_value={}), mock.patch.object(
            builder, "LONG_EDGE", 32
        ):
            manifest = render_point_cloud("test_level", [(1.0, 2.0, 3.0)], Path(tmp), payload)

        self.assertEqual(manifest["status"], "recovered_streaming_mesh_topdown")
        self.assertEqual(manifest["render"]["method"], "exact_streaming_matrix_obj_depth_pass")
        self.assertEqual(manifest["render"]["pointCount"], 0)
        self.assertEqual(manifest["render"]["renderedTriangleCount"], 7)
        self.assertEqual(manifest["modelScene"]["meshCount"], 1)
        self.assertEqual(manifest["modelScene"]["instanceCount"], 1)
        self.assertEqual(manifest["modelScene"]["meshes"][0]["assetRel"], "StreamingAssets/Mesh/S_build_test_lod0_p2A.obj")
        self.assertIn("static OBJ instances", manifest["boundary"])

    def test_zero_hit_streaming_mesh_falls_back_to_exact_instance_point_height(self):
        payload = {"markers": [{"streamingInstance": {
            "entityBase": "P_build_indie_floor+1_001_01",
            "matrixColumnMajor": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 100, 0, 1],
            "meshes": [{"name": "S_build_indie_floor+1_001_01_lod0", "pathId": 42, "obj": "missing.obj"}],
        }}]}

        def empty_raster(_streaming, _bounds, width, height, _bindings):
            return {
                "depth": [NO_HIT] * (width * height), "albedo": bytearray(width * height * 4),
                "detailDepth": [NO_HIT] * (width * height), "detailAlbedo": bytearray(width * height * 4),
                "usedInstances": 0, "texturedInstances": 0, "triangles": 0,
                "texturedTriangles": 0, "vertexSamples": 0, "texturedPixels": 0, "usedTextures": [],
                "detailTriangles": 0, "excludedDetailTriangles": 2,
            }

        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
            builder, "rasterise_streaming_depth", side_effect=empty_raster
        ), mock.patch.object(builder, "texture_bindings", return_value={}), mock.patch.object(
            builder, "LONG_EDGE", 32
        ):
            manifest = render_point_cloud("test_level", [(0.0, 100.0, 0.0)], Path(tmp), payload)

        self.assertEqual(manifest["status"], "exact_registry_transform_point_cloud")
        self.assertEqual(manifest["pointCloudOverlay"]["heightMask"]["elevationRange"], {"min": 100.0, "max": 100.0})
        self.assertGreater(manifest["pointCloudOverlay"]["heightMask"]["pointPixelCount"], 0)

    def test_exact_hlod_elevation_keeps_floor_but_omits_ceiling(self):
        matrix = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
        payload = {
            "exactHlodMatrices": True,
            "markers": [{"streamingInstance": {
                "entityBase": "P_build_ceiling_001",
                "matrixColumnMajor": matrix,
                "meshes": [{"name": "S_build_ceiling_lod0", "pathId": 42, "obj": "missing.obj"}],
            }}, {"streamingInstance": {
                "entityBase": "P_build_floor_001",
                "matrixColumnMajor": matrix,
                "meshes": [{"name": "S_build_floor_lod0", "pathId": 43, "obj": "missing.obj"}],
            }}],
        }

        def fake_raster(streaming, _bounds, width, height, _bindings):
            self.assertEqual([row["entityBase"] for row in streaming], ["P_build_floor_001"])
            return {
                "depth": [5.0] * (width * height), "albedo": bytearray(width * height * 4),
                "detailDepth": [NO_HIT] * (width * height),
                "detailAlbedo": bytearray(width * height * 4),
                "usedInstances": 1, "texturedInstances": 0, "triangles": 2,
                "texturedTriangles": 0, "vertexSamples": 0, "texturedPixels": 0,
                "usedTextures": [], "detailTriangles": 0, "excludedDetailTriangles": 2,
            }

        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
            builder, "rasterise_streaming_depth", side_effect=fake_raster
        ), mock.patch.object(builder, "texture_bindings", return_value={}), mock.patch.object(
            builder, "render_elevation_underlay", return_value={"src": "full.png"}
        ) as elevation, mock.patch.object(
            builder, "render_streaming_surface_samples", return_value={"src": "points.png"}
        ), mock.patch.object(builder, "LONG_EDGE", 8):
            manifest = render_point_cloud("exact", [(0.0, 0.0, 0.0)], Path(tmp), payload)

        self.assertTrue(elevation.call_args.args[1])
        self.assertTrue(all(value == 5.0 for value in elevation.call_args.args[1]))
        self.assertEqual(elevation.call_args.kwargs["source_label"], "full exact streaming-mesh triangle depth")
        self.assertEqual(manifest["elevationUnderlay"]["src"], "full.png")
        self.assertEqual(manifest["render"]["excludedOverheadCoverInstanceCount"], 1)

    def test_exact_texture_pixels_publish_colored_streaming_contract(self):
        payload = {"markers": [{"streamingInstance": {
            "matrixColumnMajor": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1, 2, 3, 1],
            "meshes": [{
                "name": "S_build_test_lod0",
                "pathId": 42,
                "obj": "export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/Mesh/S_build_test_lod0_p2A.obj",
            }],
        }}]}

        def fake_raster(_streaming, _bounds, width, height, _bindings):
            albedo = bytearray(width * height * 4)
            albedo[:4] = bytes((120, 80, 40, 255))
            return {
                "depth": [1.0] * (width * height), "albedo": albedo,
                "usedInstances": 1, "texturedInstances": 1, "triangles": 7,
                "texturedTriangles": 4, "vertexSamples": 0, "texturedPixels": 1,
                "usedTextures": ["StreamingAssets/convert_by_type/Texture2D/T_test_D.png"],
            }

        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
            builder, "rasterise_streaming_depth", side_effect=fake_raster
        ), mock.patch.object(builder, "texture_bindings", return_value={42: {}}), mock.patch.object(
            builder, "LONG_EDGE", 32
        ):
            manifest = render_point_cloud("colored", [(1.0, 2.0, 3.0)], Path(tmp), payload)
            _width, _height, surface = read_png_preview(Path(tmp) / "colored_streaming_textured_topdown.png", 32)
            _width, _height, elevation = read_png_preview(Path(tmp) / "colored_streaming_elevation.png", 32)
            _width, _height, points = read_png_preview(Path(tmp) / "colored_streaming_points.png", 32)

        self.assertEqual(manifest["status"], "recovered_streaming_textured_topdown")
        self.assertEqual(manifest["src"], "render/colored_streaming_textured_topdown.png")
        self.assertEqual(manifest["render"]["method"], "exact_streaming_matrix_obj_uv_material_texture_depth_pass")
        self.assertEqual(manifest["render"]["baseColorTextureCount"], 1)
        self.assertEqual(manifest["elevationUnderlay"]["method"], "orthographic_depth_pass_grayscale_hillshade")
        self.assertEqual(manifest["pointCloudOverlay"]["method"], "orthographic_exact_depth_material_color_or_elevation_palette_points")
        bounds = manifest["worldBounds"]
        self.assertAlmostEqual(
            _width / _height,
            (bounds["maxX"] - bounds["minX"]) / (bounds["maxZ"] - bounds["minZ"]),
            delta=0.02,
        )
        self.assertTrue(elevation[0] == elevation[1] == elevation[2])
        self.assertEqual(surface[:4], bytes((120, 80, 40, 255)))
        self.assertEqual(points[:3], bytes((120, 80, 40)))

    def test_explicit_roof_instance_is_omitted_before_depth_raster(self):
        base_mesh = {
            "name": "S_build_room_lod0", "pathId": 1,
            "obj": "export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/Mesh/S_build_room_lod0_p1.obj",
        }
        roof_mesh = {
            "name": "S_build_room_roof_lod0", "pathId": 2,
            "obj": "export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/Mesh/S_build_room_roof_lod0_p2.obj",
        }
        matrix = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
        payload = {"markers": [
            {"streamingInstance": {"entityBase": "P_build_room", "matrixColumnMajor": matrix, "meshes": [base_mesh]}},
            {"streamingInstance": {"entityBase": "P_build_room_roof", "matrixColumnMajor": matrix, "meshes": [roof_mesh]}},
        ]}

        def fake_raster(streaming, _bounds, width, height, _bindings):
            self.assertEqual([row["entityBase"] for row in streaming], ["P_build_room"])
            return {
                "depth": [1.0] * (width * height), "albedo": bytearray(width * height * 4),
                "usedInstances": 1, "texturedInstances": 0, "triangles": 1,
                "texturedTriangles": 0, "vertexSamples": 0, "texturedPixels": 0,
                "usedTextures": [],
            }

        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
            builder, "rasterise_streaming_depth", side_effect=fake_raster
        ), mock.patch.object(builder, "texture_bindings", return_value={}), mock.patch.object(
            builder, "LONG_EDGE", 32
        ):
            manifest = render_point_cloud("cutaway", [(0.0, 0.0, 0.0)], Path(tmp), payload)

        self.assertEqual(manifest["render"]["excludedOverheadCoverInstanceCount"], 1)
        self.assertIn("roof/ceiling instances are omitted", manifest["boundary"])

    def test_composite_streaming_instance_publishes_each_mesh_but_counts_one_instance(self):
        meshes = [
            {"name": "tower", "pathId": 3, "obj": "export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/Mesh/tower_p3.obj"},
            {"name": "base", "pathId": 2, "obj": "export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/Mesh/base_p2.obj"},
        ]
        payload = {"markers": [{"streamingInstance": {
            "matrixColumnMajor": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
            "meshes": meshes,
        }}]}
        def fake_raster(_streaming, _bounds, width, height, _bindings):
            return {
                "depth": [1.0] * (width * height), "albedo": bytearray(width * height * 4),
                "usedInstances": 1, "texturedInstances": 0, "triangles": 12,
                "texturedTriangles": 0, "vertexSamples": 0, "texturedPixels": 0, "usedTextures": [],
            }

        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
            builder, "rasterise_streaming_depth", side_effect=fake_raster
        ), mock.patch.object(builder, "texture_bindings", return_value={}), mock.patch.object(
            builder, "LONG_EDGE", 32
        ):
            manifest = render_point_cloud("composite", [(0.0, 0.0, 0.0)], Path(tmp), payload)

        self.assertEqual(manifest["modelScene"]["instanceCount"], 1)
        self.assertEqual(manifest["modelScene"]["meshCount"], 2)


class FitOriginTests(unittest.TestCase):
    """The grid origin is recovered from marker occupancy, or not claimed."""

    def _lods(self, cells):
        return {"0": [{"i": i, "j": j, "pathId": 1, "name": "n"} for i, j in cells]}

    def test_origin_is_recovered_from_markers_that_sit_on_occupied_cells(self):
        # Cells (32,32)..(35,35) are occupied; with a -1024 origin and 32 m
        # cells that is world x/z 0..128.
        lods = self._lods([(i, j) for i in range(32, 36) for j in range(32, 36)])
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

    def test_region_origin_uses_marker_weighted_member_agreement(self):
        fits = [
            {"originX": -2048, "originZ": -2048, "samplePoints": 1500},
            {"originX": -2048, "originZ": -2048, "samplePoints": 1000},
            {"originX": -2048, "originZ": -1920, "samplePoints": 1017},
        ]
        self.assertEqual(select_shared_origin(fits), (-2048.0, -2048.0))

    def test_lods_must_agree_so_a_coarse_lod_cannot_carry_a_wrong_origin(self):
        # HLOD0 and HLOD1 describe the same world cell with adjacent 32/64 m
        # grids. Only an origin satisfying both may win.
        lods = {
            "0": [{"i": 32, "j": 32, "pathId": 1, "name": "n"}],
            "1": [{"i": 16, "j": 16, "pathId": 2, "name": "n"}],
        }
        points = [(float(x), float(x)) for x in range(2, 30)] * 2
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

    def test_exact_surface_sampling_density_is_world_area_based_and_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mesh = root / "export_full/recovered/mesh.obj"
            mesh.parent.mkdir(parents=True)
            # OBJ X is mirrored by AnimeStudio; after undoing that mirror this
            # is a 4x4 right triangle in Unity world X/Z.
            mesh.write_text("v 0 2 0\nv -4 6 0\nv 0 2 4\nf 1 2 3\n", encoding="utf-8")
            streaming = [{
                "matrixColumnMajor": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
                "meshes": [{"obj": "export_full/recovered/mesh.obj", "pathId": 1}],
            }]
            bounds = {"minX": 0.0, "maxX": 4.0, "minZ": 0.0, "maxZ": 4.0}
            with mock.patch.object(builder, "ROOT", root):
                sparse = render_streaming_surface_samples(
                    "sparse", streaming, bounds, 8, 8, root / "out", 0.25, {}
                )
                dense = render_streaming_surface_samples(
                    "dense", streaming, bounds, 8, 8, root / "out", 1.0, {}
                )

        self.assertEqual(sparse["method"], "exact_matrix_world_surface_area_samples")
        self.assertEqual(sparse["sourceSampleCount"], 3)
        self.assertEqual(dense["sourceSampleCount"], 10)
        self.assertEqual(sparse["densityPerSquareMeter"], 0.25)
        self.assertEqual(sparse["spacingMeters"], 2.0)

    def test_exact_surface_sampling_excludes_floor_and_ceiling_surfaces(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            floor = root / "export_full/recovered/floor.obj"
            ceiling = root / "export_full/recovered/ceiling.obj"
            floor.parent.mkdir(parents=True)
            floor.write_text("v 0 2 0\nv -4 2 0\nv 0 2 4\nf 1 2 3\n", encoding="utf-8")
            # A named ceiling is excluded even when its triangle is vertical.
            ceiling.write_text("v 0 0 0\nv 0 4 0\nv 0 0 4\nf 1 2 3\n", encoding="utf-8")
            matrix = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
            streaming = [{
                "entityBase": "P_build_platform_001",
                "matrixColumnMajor": matrix,
                "meshes": [{"obj": "export_full/recovered/floor.obj", "pathId": 1}],
            }, {
                "entityBase": "P_build_ceiling_001",
                "matrixColumnMajor": matrix,
                "meshes": [{"obj": "export_full/recovered/ceiling.obj", "pathId": 2}],
            }]
            bounds = {"minX": 0.0, "maxX": 4.0, "minZ": 0.0, "maxZ": 4.0}
            with mock.patch.object(builder, "ROOT", root):
                result = render_streaming_surface_samples(
                    "structural", streaming, bounds, 8, 8, root / "out", 0.25, {}
                )

        self.assertIsNone(result)

    def test_streaming_floor_fills_surface_depth_but_not_detail_depth(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mesh = root / "export_full/recovered/floor.obj"
            mesh.parent.mkdir(parents=True)
            mesh.write_text("v 0 2 0\nv -4 2 0\nv 0 2 4\nf 1 2 3\n", encoding="utf-8")
            streaming = [{
                "entityBase": "P_build_indie_floor_001",
                "matrixColumnMajor": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
                "meshes": [{
                    "name": "S_build_indie_floor_lod0",
                    "obj": "export_full/recovered/floor.obj",
                    "pathId": 1,
                }],
            }]
            bounds = {"minX": 0.0, "maxX": 4.0, "minZ": 0.0, "maxZ": 4.0}
            with mock.patch.object(builder, "ROOT", root):
                raster = builder.rasterise_streaming_depth(streaming, bounds, 8, 8, {})

        self.assertTrue(any(value > NO_HIT for value in raster["depth"]))
        self.assertTrue(all(value <= NO_HIT for value in raster["detailDepth"]))
        self.assertEqual(raster["triangles"], 1)
        self.assertEqual(raster["excludedDetailTriangles"], 1)

    def test_streaming_obj_preserves_triangle_uv_indices(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._cluster_obj(
                tmp, "v 0 1 0\nv 1 1 0\nv 0 1 1\nvt 0.1 0.2\nvt 0.8 0.2\nvt 0.1 0.9\nf 1/1 2/2 3/3\n"
            )
            vertices, texcoords, faces = _read_textured_mesh(path)
        self.assertEqual(len(vertices), 3)
        self.assertEqual(texcoords[1], (0.8, 0.2))
        self.assertEqual(faces, [((0, 1, 2), (0, 1, 2))])

    def test_hlod_binding_requires_exact_level_lod_and_signed_suffix(self):
        with tempfile.TemporaryDirectory(dir=builder.ROOT / "tmp") as tmp:
            root = Path(tmp)
            (root / "materials/Material").mkdir(parents=True)
            (root / "textures/Texture2D").mkdir(parents=True)
            material_name = "M_auto_generated_HLOD0_indie_dg002_art_-1142725418_pA.json"
            texture_name = "T_auto_generated_HLOD0_indie_dg002_art_1_D_pB.png"
            (root / "materials/Material" / material_name).write_text("{}", encoding="utf-8")
            builder.write_png(root / "textures/Texture2D" / texture_name, 1, 1, [bytes((120, 80, 40, 255))])
            index = {
                "sourceRoots": {
                    "StreamingAssets-materials": str(root / "materials"),
                    "StreamingAssets": str(root / "textures"),
                },
                "relations": {
                    f"StreamingAssets-materials/Material/{material_name}": {
                        "textures": [{
                            "slot": "_BaseColorMap",
                            "rel": f"StreamingAssets/Texture2D/{texture_name}",
                        }],
                    },
                },
            }
            index_path = root / "index.json"
            index_path.write_text(json.dumps(index), encoding="utf-8")
            clusters = [{
                "name": "S_HLOD0_16_20_Cluster_-1142725418",
                "pathId": 7,
            }]
            with mock.patch.object(builder, "ASSET_INDEX", index_path), mock.patch.object(
                builder, "_TEXTURE_BINDINGS", None
            ), mock.patch.object(builder, "_HLOD_TEXTURE_BINDINGS", None):
                exact = builder.hlod_texture_bindings("indie_dg002", 0, clusters)
                wrong_level = builder.hlod_texture_bindings("indie_dg003", 0, clusters)

        self.assertEqual(set(exact), {7})
        self.assertEqual(exact[7]["mappingMethod"], "exact_hlod_level_lod_signed_suffix_to_generated_material")
        self.assertEqual(wrong_level, {})

    def test_hlod_depth_samples_exact_bound_base_color(self):
        bounds = {"minX": 0.0, "maxX": 8.0, "minZ": 0.0, "maxZ": 8.0}
        fit = {"originX": 0.0, "originZ": 0.0}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self._cluster_obj(
                tmp,
                "v 60 5 -60\nv -60 5 -60\nv -60 5 60\n"
                "vt 0 0\nvt 1 0\nvt 0 1\nf 1/1 2/2 3/3\n",
            )
            texture = root / "texture.png"
            material = root / "material.json"
            builder.write_png(texture, 1, 1, [bytes((120, 80, 40, 255))])
            material.write_text("{}", encoding="utf-8")
            colors = bytearray(16 * 16 * 4)
            depth, used, _triangles = rasterise_depth(
                [{"i": 0, "j": 0, "pathId": 1, "name": "S_HLOD1_0_0_Cluster_1"}],
                1, fit, bounds, {"1": path}, 16, 16,
                bindings={1: {
                    "slot": "_BaseColorMap", "textureRel": "texture.png",
                    "texturePath": texture, "materialRel": "material.json",
                    "materialPath": material,
                }},
                material_colors=colors,
            )

        self.assertTrue(any(value > NO_HIT for value in depth))
        self.assertTrue(used[0]["materialColor"])
        colored = [bytes(colors[index:index + 4]) for index in range(0, len(colors), 4) if colors[index + 3]]
        self.assertTrue(colored)
        self.assertEqual(set(colored), {bytes((120, 80, 40, 255))})

    def test_hlod_duplicate_material_key_fails_closed_even_if_one_texture_is_missing(self):
        with tempfile.TemporaryDirectory(dir=builder.ROOT / "tmp") as tmp:
            root = Path(tmp)
            material_root = root / "materials/Material"
            texture_root = root / "textures/Texture2D"
            material_root.mkdir(parents=True)
            texture_root.mkdir(parents=True)
            invalid = "M_auto_generated_HLOD1_map01_lv001_art_-9_pA.json"
            valid = "M_auto_generated_HLOD1_map01_lv001_art_-9_pB.json"
            for name in (invalid, valid):
                (material_root / name).write_text("{}", encoding="utf-8")
            builder.write_png(texture_root / "valid.png", 1, 1, [bytes((1, 2, 3, 255))])
            index = {
                "sourceRoots": {
                    "StreamingAssets-materials": str(root / "materials"),
                    "StreamingAssets": str(root / "textures"),
                },
                "relations": {
                    f"StreamingAssets-materials/Material/{invalid}": {
                        "textures": [{"slot": "_BaseColorMap", "rel": "StreamingAssets/Texture2D/missing.png"}],
                    },
                    f"StreamingAssets-materials/Material/{valid}": {
                        "textures": [{"slot": "_BaseColorMap", "rel": "StreamingAssets/Texture2D/valid.png"}],
                    },
                },
            }
            index_path = root / "index.json"
            index_path.write_text(json.dumps(index), encoding="utf-8")
            clusters = [{"name": "S_HLOD1_0_0_Cluster_-9", "pathId": 9}]
            with mock.patch.object(builder, "ASSET_INDEX", index_path), mock.patch.object(
                builder, "_TEXTURE_BINDINGS", None
            ), mock.patch.object(builder, "_HLOD_TEXTURE_BINDINGS", None):
                bindings = builder.hlod_texture_bindings("map01_lv001", 1, clusters)

        self.assertEqual(bindings, {})

    def test_material_alpha_uses_render_state_not_an_opaque_default_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            material = Path(tmp) / "material.json"
            binding = {"materialPath": material, "slot": "_BaseColorMap"}
            base = {
                "m_CustomRenderQueue": 2000,
                "m_StringTagMap": {"RenderType": "Opaque"},
                "m_ValidKeywords": [],
                "m_SavedProperties": {
                    "m_TexEnvs": {"_BaseColorMap": {}},
                    "m_Floats": {"_AlphaClipThreshold": 0.5},
                },
            }
            material.write_text(json.dumps(base), encoding="utf-8")
            builder._MATERIAL_PARAMS.clear()
            opaque = builder._material_render_params(binding)
            texture = {**opaque, "width": 1, "height": 1, "pixels": bytes((20, 40, 60, 0))}
            self.assertEqual(builder._sample_texture(texture, 0.0, 0.0), (20, 40, 60, 255))

            base["m_ValidKeywords"] = ["_ALPHATEST_ON"]
            material.write_text(json.dumps(base), encoding="utf-8")
            builder._MATERIAL_PARAMS.clear()
            cutout = builder._material_render_params(binding)
            self.assertIsNone(builder._sample_texture({**texture, **cutout}, 0.0, 0.0))

            base["m_ValidKeywords"] = []
            base["m_CustomRenderQueue"] = 3000
            base["m_StringTagMap"]["RenderType"] = "Transparent"
            material.write_text(json.dumps(base), encoding="utf-8")
            builder._MATERIAL_PARAMS.clear()
            transparent = builder._material_render_params(binding)
            self.assertEqual(builder._sample_texture({**texture, **transparent}, 0.0, 0.0), (20, 40, 60, 0))

    def test_exported_rgba_png_preview_round_trips_color(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "texture.png"
            builder.write_png(path, 2, 2, [
                bytes((255, 0, 0, 255, 0, 255, 0, 255)),
                bytes((0, 0, 255, 255, 255, 255, 0, 255)),
            ])
            width, height, pixels = read_png_preview(path, 2)
        self.assertEqual((width, height), (2, 2))
        self.assertEqual(pixels[:4], bytes((255, 0, 0, 255)))

    def test_a_flat_triangle_fills_pixels_and_records_its_elevation(self):
        bounds = {"minX": 0.0, "maxX": 8.0, "minZ": 0.0, "maxZ": 8.0}
        fit = {"originX": 0.0, "originZ": 0.0}
        with tempfile.TemporaryDirectory() as tmp:
            # A large upward-facing triangle sitting at world Y = 5.
            path = self._cluster_obj(tmp, "g c\nv 30 5 -30\nv -30 5 -30\nv -30 5 30\n"
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
                                          "v 30 2 -30\nv -30 2 -30\nv -30 2 30\n"
                                          "v 30 9 -30\nv -30 9 -30\nv -30 9 30\n"
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

    def test_hlod_preview_publishes_black_point_density(self):
        bounds = {"minX": 0.0, "maxX": 8.0, "minZ": 0.0, "maxZ": 8.0}
        fit = {"originX": 0.0, "originZ": 0.0}
        with tempfile.TemporaryDirectory() as tmp:
            path = self._cluster_obj(tmp, "g c\nv 30 5 -30\nv -30 5 -30\nv -30 5 30\nf 1 2 3\n")
            clusters = [{"i": 0, "j": 0, "pathId": 1, "name": "S_HLOD1_0_0_Cluster_1"}]
            with mock.patch.object(builder, "raster_size", return_value=(16, 16)):
                manifest = render_level(clusters=clusters, level_id="test", lod=1, fit=fit,
                                        bounds=bounds, mesh_files={"1": path}, output_root=Path(tmp))

        self.assertEqual(manifest["render"]["method"], "orthographic_hlod_depth_black_point_density")
        self.assertEqual(manifest["render"]["pointDensity"], 8 / 11)
        self.assertEqual(manifest["render"]["coveredPixelRatio"], manifest["render"]["realPixelRatio"])
        self.assertEqual(manifest["src"], "render/test_hlod_surface.png")
        self.assertEqual(manifest["pointCloudOverlay"]["src"], "render/test_hlod_vertex_points.png")
        self.assertEqual(manifest["pointCloudOverlay"]["sampleSet"]["encoding"],
                         "mrps_v1_le_u32_pixel_f32_height_rgba8")
        self.assertIsNotNone(manifest["elevationUnderlay"])

    def test_layered_point_samples_reveal_a_lower_coprojecting_vertex(self):
        bounds = {"minX": -1.0, "maxX": 1.0, "minZ": -1.0, "maxZ": 1.0}
        fit = {"originX": 0.0, "originZ": 0.0}
        with tempfile.TemporaryDirectory() as tmp:
            path = self._cluster_obj(tmp, "g c\nv 32 10 -32\nv 32 20 -32\n")
            clusters = [{"i": 0, "j": 0, "pathId": 1, "name": "S_HLOD1_0_0_Cluster_1"}]
            overlay = builder.render_hlod_point_samples(
                "stacked", clusters, 1, fit, bounds, {"1": path}, 8, 8, Path(tmp)
            )
            payload = (Path(tmp) / "stacked_hlod_vertex_points.samples").read_bytes()

        self.assertEqual(payload[:4], b"MRPS")
        version, record_size, width, height = struct.unpack_from("<HHII", payload, 4)
        self.assertEqual((version, record_size, width, height), (1, 12, 8, 8))
        records = [struct.unpack_from("<IfBBBB", payload, offset)
                   for offset in range(16, len(payload), record_size)]
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0][0], records[1][0])
        self.assertEqual([row[1] for row in records], [10.0, 20.0])
        self.assertEqual(overlay["sampleSet"]["recordCount"], 2)
        self.assertEqual(overlay["sampleSet"]["pixelCount"], 1)

    def test_dg002_uses_irregular_mesh_vertex_scan_without_coordinate_echo(self):
        bounds = {"minX": 0.0, "maxX": 8.0, "minZ": 0.0, "maxZ": 8.0}
        fit = {"originX": 0.0, "originZ": 0.0}
        with tempfile.TemporaryDirectory() as tmp:
            path = self._cluster_obj(tmp, "g c\nv 30 1 -30\nv -30 9 -30\nv -30 1 30\nf 1 2 3\n")
            clusters = [{"i": 0, "j": 0, "pathId": 1, "name": "S_HLOD1_0_0_Cluster_1"}]
            with mock.patch.object(builder, "raster_size", return_value=(32, 32)):
                manifest = render_level(clusters=clusters, level_id="indie_dg002", lod=1, fit=fit,
                                        bounds=bounds, mesh_files={"1": path}, output_root=Path(tmp))

        self.assertEqual(manifest["render"]["method"], "orthographic_hlod_mesh_vertex_scan")
        self.assertFalse(manifest["render"]["heightEcho"]["enabled"])
        self.assertEqual(manifest["worldBounds"], bounds)
        self.assertEqual(manifest["elevationUnderlay"]["method"], "orthographic_depth_pass_grayscale_hillshade")
        self.assertEqual(manifest["elevationUnderlay"]["src"], "render/indie_dg002_hlod_elevation.png")

    def test_hlod_palette_is_colored_and_changes_with_height(self):
        low = elevation_color(0.0)
        high = elevation_color(1.0)
        self.assertNotEqual(low, high)
        self.assertFalse(low[0] == low[1] == low[2])
        self.assertFalse(high[0] == high[1] == high[2])


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
