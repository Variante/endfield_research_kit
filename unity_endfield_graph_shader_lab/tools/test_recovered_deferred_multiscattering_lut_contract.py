import ctypes
import hashlib
import importlib.util
import json
import math
import struct
import sys
import unittest
from pathlib import Path


LAB = Path(__file__).resolve().parents[1]
RUNTIME = (
    LAB / "Assets" / "EndfieldGraphShaderLab" / "Runtime" / "Rendering"
)
EXPECTED_LUT_SHA256 = (
    "1a15afe25b25e7aa64dcf17d74f5375dd1b692b3805cd00aa4f531ad289f030e"
)
EXPECTED_GAMEASSEMBLY_SHA256 = (
    "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
)
EXPECTED_METADATA_SHA256 = (
    "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
)
EXPECTED_METHOD_VA = 0x189BC8C9C
EXPECTED_METHOD_SIZE = 0x324
EXPECTED_METHOD_SHA256 = (
    "490bfd6a788aecfa6f9a192a85e1eb44cbbde9c426bca5977472bcb6acaa1c93"
)
CONTRACT = (
    LAB
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Generated"
    / "OriginalData"
    / "CharInfoPresentation"
    / "deferred_resolver_binding_contract.json"
)
REPO = LAB.parent


def f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


def build_native_order_lut() -> bytes:
    ucrt = ctypes.CDLL("ucrtbase")
    ucrt.powf.argtypes = [ctypes.c_float, ctypes.c_float]
    ucrt.powf.restype = ctypes.c_float
    output = bytearray()

    for roughness_index in range(32):
        roughness = f32(f32(roughness_index) / f32(31.0))
        roughness2 = f32(roughness * roughness)
        roughness4 = f32(roughness2 * roughness2)
        roughness3 = f32(roughness2 * roughness)
        s_b = f32(roughness * f32(4.0798502))
        s_c = f32(roughness2 * f32(-11.5295))
        s_d = f32(roughness3 * f32(18.4961))
        s_e = f32(roughness4 * f32(-9.23618))
        t_b = f32(roughness * f32(3.1434))
        t_c = f32(roughness2 * f32(-7.47567))
        t_d = f32(roughness3 * f32(13.0482))
        t_e = f32(roughness4 * f32(-7.0401))

        for n_dot_v_index in range(32):
            n_dot_v = f32(f32(n_dot_v_index) / f32(31.0))
            s = f32(f32(math.sqrt(n_dot_v)) * f32(-0.170718))
            for term in (s_b, s_c, s_d, s_e):
                s = f32(s + term)
            t = f32(n_dot_v * f32(0.0632331))
            for term in (t_b, t_c, t_d, t_e):
                t = f32(t + term)
            s2 = f32(s * s)
            t2 = f32(t * t)
            s6 = f32(f32(s2 * s2) * s2)
            t6 = f32(f32(t2 * t2) * t2)
            numerator = f32(
                f32(ucrt.powf(n_dot_v, f32(0.75))) * s6
            )
            denominator = f32(t6 + f32(n_dot_v * n_dot_v))
            value = (
                f32(numerator / denominator)
                if denominator != 0.0
                else float("nan")
            )
            if math.isfinite(value):
                value = min(max(value, 0.0), 1.0)
                quantized = int(f32(value * f32(65535.0)))
            else:
                quantized = -(1 << 31)
            output.extend(struct.pack("<H", quantized & 0xFFFF))

    return bytes(output)


class RecoveredDeferredMultiscatteringLutContractTests(unittest.TestCase):
    def test_native_producer_formula_rebuilds_exact_payload(self) -> None:
        payload = build_native_order_lut()
        self.assertEqual(len(payload), 2048)
        self.assertEqual(hashlib.sha256(payload).hexdigest(), EXPECTED_LUT_SHA256)

    def test_generated_contract_pins_the_exact_installed_method_body(self) -> None:
        sys.path.insert(0, str(REPO))
        try:
            from scripts import common
        finally:
            sys.path.pop(0)

        gate = common.check_installed_native_inputs(
            EXPECTED_GAMEASSEMBLY_SHA256,
            EXPECTED_METADATA_SHA256,
        )
        if gate.status == common.NATIVE_EVIDENCE_MISSING:
            self.skipTest(gate.detail)
        self.assertTrue(gate.validated, gate.detail)

        mapper_path = (
            REPO
            / "tools"
            / "endfield-il2cpp"
            / "map_body_targets_to_gameassembly.py"
        )
        spec = importlib.util.spec_from_file_location(
            "endfield_multiscattering_native_mapper",
            mapper_path,
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        mapper = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mapper
        spec.loader.exec_module(mapper)
        image = mapper.PeImage(gate.gameassembly)
        method_body = image.bytes_at_va(
            EXPECTED_METHOD_VA,
            EXPECTED_METHOD_SIZE,
        )
        self.assertEqual(len(method_body), EXPECTED_METHOD_SIZE)
        self.assertEqual(
            hashlib.sha256(method_body).hexdigest(),
            EXPECTED_METHOD_SHA256,
        )

        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        validation = contract[
            "deferred_resolver_source_texture_transport"
        ]["validation"]
        self.assertEqual(
            validation["multiscattering_source_method_body_sha256"],
            EXPECTED_METHOD_SHA256,
        )

    def test_exact_consumer_uses_the_source_producer(self) -> None:
        producer = (RUNTIME / "EndfieldRecoveredMultiscatteringLut.cs").read_text(
            encoding="utf-8"
        )
        consumer = (
            RUNTIME / "EndfieldRecoveredDeferredExactConsumer.cs"
        ).read_text(encoding="utf-8")
        self.assertIn("GraphicsFormat.R16_UNorm", producer)
        self.assertIn("FilterMode.Bilinear", producer)
        self.assertIn("TextureWrapMode.Clamp", producer)
        self.assertIn("float s = Sa * Mathf.Sqrt(nDotV);", producer)
        self.assertIn("Mathf.Pow(nDotV, 0.75f)", producer)
        self.assertIn("EndfieldRecoveredMultiscatteringLut.Create()", consumer)
        self.assertNotIn("neutral multiscattering LUT", consumer)

    def test_directional_b4_uses_the_serialized_divide_pi_formula(self) -> None:
        source = (
            RUNTIME / "EndfieldRecoveredDeferredLightDataContract.cs"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "SourceDirectIntensity / Mathf.PI;",
            source,
        )
        directional_write = source.split(
            "destination[DirectionalColorVector]", 1
        )[1].split("float softRadiusRadians", 1)[0]
        self.assertEqual(
            directional_write.count("SourceDirectIntensityDividePi"),
            4,
        )
        self.assertNotIn("* SourceDirectIntensity,", directional_write)
        self.assertEqual(
            struct.pack("<f", f32(f32(8.631674) / f32(math.pi))),
            struct.pack("<f", f32(2.7475471)),
        )


if __name__ == "__main__":
    unittest.main()
