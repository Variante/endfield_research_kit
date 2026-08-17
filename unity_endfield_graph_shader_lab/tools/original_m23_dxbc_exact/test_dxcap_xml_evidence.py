"""Bounded tests for DXCap XML state tracking and the fail-closed M23 gate."""

import importlib.util
import io
from pathlib import Path
import unittest


MODULE = Path(__file__).with_name("dxcap_xml_evidence.py")
SPEC = importlib.util.spec_from_file_location("m23_dxcap_xml_evidence", MODULE)
assert SPEC and SPEC.loader
EVIDENCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EVIDENCE)


class DxcapEvidenceTests(unittest.TestCase):
    def test_streaming_fixture_tracks_state_and_m23_candidate(self):
        fixture = MODULE.with_name("fixtures") / "dxcap_m23_bounded.xml"
        report = EVIDENCE.parse_dxcap(fixture)
        self.assertEqual(report["schema"], EVIDENCE.SCHEMA)
        self.assertEqual(len(report["draw_calls"]), 1)
        draw = report["draw_calls"][0]
        self.assertEqual(draw["moment"], 4242)
        self.assertEqual(draw["draw_type"], "DrawIndexed")
        self.assertEqual(draw["parameters"]["index_count"], 36)
        self.assertEqual(draw["vs_handle"], "vs-m23")
        self.assertEqual(draw["ps_handle"], "ps-m23")
        self.assertEqual(draw["ia_vertex_buffers"][0]["stride"], 136)
        self.assertEqual(draw["index_buffer"]["format"], "R16_UINT")
        self.assertEqual(draw["topology"], "D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST")
        self.assertEqual(draw["viewport"]["width"], 1280)
        self.assertTrue(draw["m23_candidate"]["exact_m23_candidate"])
        self.assertFalse(draw["m23_candidate"]["byte_hashes_available"])
        self.assertFalse(report["byte_hashes_available"])

    def test_wrong_stride_cannot_claim_candidate(self):
        xml = """<Capture><Call name='CreateVertexShader'><Arg name='BytecodeLength'>10720</Arg><Arg name='ppVertexShader'>vs</Arg></Call><Call name='CreatePixelShader'><Arg name='BytecodeLength'>8100</Arg><Arg name='ppPixelShader'>ps</Arg></Call><Call name='VSSetShader'><Arg name='shader'>vs</Arg></Call><Call name='PSSetShader'><Arg name='shader'>ps</Arg></Call><Call name='IASetVertexBuffers'><Buffer slot='0' stride='135' handle='vb'/></Call><Call name='Draw'/></Capture>"""
        draw = EVIDENCE.parse_dxcap(io.StringIO(xml))["draw_calls"][0]
        self.assertFalse(draw["m23_candidate"]["exact_m23_candidate"])
        self.assertFalse(draw["m23_candidate"]["checks"]["ia_stride_136"])

    def test_windows_dxcap_fragment_schema(self):
        xml = """<Moment value='90'/>
<Method name='CreateVertexShader'><Parameter name='BytecodeLength' value='10720'/><Parameter name='ppVertexShader' handle='vs'/></Method>
<Method name='CreatePixelShader'><Parameter name='BytecodeLength' value='8100'/><Parameter name='ppPixelShader' handle='ps'/></Method>
<Method name='IASetVertexBuffers'><Parameter name='StartSlot' value='0'/><Parameter name='ppVertexBuffers'><Element handle='vb'/></Parameter><Parameter name='pStrides'><Element value='136'/></Parameter><Parameter name='pOffsets'><Element value='0'/></Parameter></Method>
<Method name='VSSetShader'><Parameter name='pVertexShader' handle='vs'/></Method>
<Method name='PSSetShader'><Parameter name='pPixelShader' handle='ps'/></Method>
<Method name='VSSetConstantBuffers'><Parameter name='StartSlot' value='0'/><Parameter name='ppConstantBuffers'><Element handle='b0'/><Element handle='b1'/><Element handle='b2'/><Element handle='b3'/><Element handle='b4'/></Parameter></Method>
<Moment value='99'/><Method name='Draw'><Parameter name='VertexCount' value='3'/><Parameter name='StartVertexLocation' value='0'/></Method>"""
        report = EVIDENCE.parse_dxcap(io.StringIO(xml))
        draw = report["draw_calls"][0]
        self.assertEqual(draw["moment"], 99)
        self.assertEqual(draw["ia_vertex_buffers"], [{"handle": "vb", "slot": 0, "stride": 136, "offset": 0}])
        self.assertEqual([row["handle"] for row in draw["vs_constant_buffers"]], ["b0", "b1", "b2", "b3", "b4"])
        self.assertTrue(draw["m23_candidate"]["exact_m23_candidate"])

    def test_malformed_xml_fails_closed(self):
        with self.assertRaises(EVIDENCE.EvidenceParseError):
            EVIDENCE.parse_dxcap(io.StringIO("<Capture><Call name='Draw'>"))

    def test_partial_slot_updates_preserve_unaffected_bindings(self):
        xml = """<Method Name='VSSetConstantBuffers'><Parameter Name='StartSlot' value='0'/><Parameter Name='ppConstantBuffers'><Element handle='b0'/><Element handle='b1'/><Element handle='b2'/><Element handle='old-b3'/><Element handle='b4'/></Parameter></Method>
<Method Name='VSSetConstantBuffers'><Parameter Name='StartSlot' value='3'/><Parameter Name='ppConstantBuffers'><Element handle='new-b3'/></Parameter></Method>
<Method Name='Draw'><Parameter Name='VertexCount' value='3'/></Method>"""
        draw = EVIDENCE.parse_dxcap(io.StringIO(xml))["draw_calls"][0]
        self.assertEqual(
            [row["handle"] for row in draw["vs_constant_buffers"]],
            ["b0", "b1", "b2", "new-b3", "b4"],
        )

    def test_generic_size_and_id_do_not_create_shader_identity(self):
        xml = """<Method Name='CreateVertexShader'><Parameter Name='size' value='10720'/><Parameter Name='id' handle='vs'/></Method>
<Method Name='VSSetShader'><Parameter Name='pVertexShader' handle='vs'/></Method><Method Name='Draw'><Parameter Name='VertexCount' value='3'/></Method>"""
        report = EVIDENCE.parse_dxcap(io.StringIO(xml))
        self.assertEqual(report["shader_creates"], [])
        self.assertFalse(report["draw_calls"][0]["m23_candidate"]["checks"]["vs_handle_known"])


if __name__ == "__main__":
    unittest.main()
