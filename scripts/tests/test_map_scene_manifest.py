import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import build_map_recovery_preview as builder


class MapSceneManifestTests(unittest.TestCase):
    def test_render_level_publishes_optional_model_scene_without_replacing_png(self):
        image_exists = False
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mesh = root / "export_full" / "recovered" / "AnimeStudio-cli" / "StreamingAssets" / "convert_by_type" / "Mesh" / "cluster_p1.obj"
            mesh.parent.mkdir(parents=True)
            mesh.write_text("v 0 1 0\nv 1 1 0\nv 0 1 1\nf 1 2 3\n", encoding="utf-8")
            with mock.patch.object(builder, "ROOT", root):
                manifest = builder.render_level(
                    "test_level",
                    [{"i": 0, "j": 0, "pathId": 1, "name": "S_HLOD1_0_0_Cluster_deadbeef"}],
                    1,
                    {"originX": 0.0, "originZ": 0.0},
                    {"minX": 0.0, "maxX": 128.0, "minZ": 0.0, "maxZ": 128.0},
                    {"1": mesh},
                    root / "render",
                )
                image_exists = (root / "render" / "test_level_hlod_grid_inferred.png").exists()

        self.assertIsNotNone(manifest)
        self.assertTrue(image_exists)
        self.assertEqual(manifest["modelScene"]["status"], "obj_cluster_subset")
        self.assertEqual(manifest["modelScene"]["meshes"][0]["assetRel"], "StreamingAssets/Mesh/cluster_p1.obj")

    def test_scene_manifest_reuses_cluster_transform_and_axis_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            export = root / "export_full" / "recovered" / "AnimeStudio-cli"
            mesh = export / "StreamingAssets" / "convert_by_type" / "Mesh" / "cluster_p1.obj"
            mesh.parent.mkdir(parents=True)
            mesh.write_text("", encoding="utf-8")
            with mock.patch.object(builder, "ROOT", root):
                rows = builder._scene_meshes(
                    [{"name": "S_HLOD1_2_-3_Cluster_deadbeef", "pathId": 1, "triangles": 17}],
                    {"1": mesh},
                    lod=1,
                    fit={"originX": -1024.0, "originZ": 2048.0},
                )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["src"], "/export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/Mesh/cluster_p1.obj")
        self.assertEqual(rows[0]["assetRel"], "StreamingAssets/Mesh/cluster_p1.obj")
        self.assertEqual(rows[0]["gridIndex"], {"i": 2, "j": -3})
        self.assertEqual(rows[0]["translation"], {"x": -704.0, "y": 0.0, "z": 1728.0})

    def test_scene_manifest_fails_closed_for_meshes_outside_export_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outside = root / "scratch" / "cluster.obj"
            outside.parent.mkdir(parents=True)
            outside.write_text("", encoding="utf-8")
            with mock.patch.object(builder, "ROOT", root):
                rows = builder._scene_meshes(
                    [{"name": "S_HLOD1_0_0_Cluster_deadbeef", "pathId": 1, "triangles": 1}],
                    {"1": outside},
                    lod=1,
                    fit={"originX": 0.0, "originZ": 0.0},
                )

        self.assertEqual(rows, [])

    def test_scene_manifest_is_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mesh_root = root / "export_full" / "Mesh"
            mesh_root.mkdir(parents=True)
            files = {}
            used = []
            for path_id in range(builder.MAX_SCENE_MESHES + 5):
                path = mesh_root / f"cluster_{path_id:x}.obj"
                path.write_text("", encoding="utf-8")
                files[f"{path_id:X}"] = path
                used.append({
                    "name": f"S_HLOD1_{path_id}_0_Cluster_{path_id:x}",
                    "pathId": path_id,
                    "triangles": 1,
                })
            with mock.patch.object(builder, "ROOT", root):
                rows = builder._scene_meshes(
                    used, files, lod=1, fit={"originX": 0.0, "originZ": 0.0}
                )

        self.assertEqual(len(rows), builder.MAX_SCENE_MESHES)


if __name__ == "__main__":
    unittest.main()
