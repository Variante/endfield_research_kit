import importlib.util
from pathlib import Path
import unittest
P=Path(__file__).with_name("validate_m23_exact_source_substitution.py"); S=importlib.util.spec_from_file_location("m",P); M=importlib.util.module_from_spec(S); S.loader.exec_module(M)
def runtime(): return {"status":"pass","exactIdentityClosed":True,"noBakeMeshContract":True,"noProxyContract":True,"activeVertexStreamIds":[0,1,3,4,5,34]}
def sub(): return {"schema":"endfield.lizhiyan-m23-exact-source-substitution.v1","status":"pass","callback_count":2,"shell_input_observed_count":2,"vertex_swap_count":1,"pixel_swap_count":1,"failure_count":0,"last_hresult":0}
def evidence(index=3456, stride=60, variant="blob1277_non_instanced", vs=10720, ps=8100, exact=False):
 return {"draw_calls":[{"parameters":{"index_count":index},"ia_vertex_buffers":[{"slot":0,"stride":stride}],"m23_candidate":{"exact_m23_candidate":exact,"variant":variant,"vs_bytecode_length":vs,"ps_bytecode_length":ps}}]}
class Tests(unittest.TestCase):
 def test_observed_exact_shader_source_stride_boundary_passes(self):
  r=M.validate(runtime(),sub(),evidence()); self.assertEqual(r["status"],"pass"); self.assertTrue(r["classification"]["automaticParticleRendererDrawAdmission"]); self.assertEqual(r["classification"]["sourceIaStride"],60); self.assertFalse(r["classification"]["stride136ProducerResolved"])
 def test_missing_target_draw_fails_closed(self):
  r=M.validate(runtime(),sub(),evidence(6)); self.assertEqual(r["status"],"fail"); self.assertEqual(r["summary"]["firstFailure"],"dxcap.single_target_draw")
 def test_shell_shader_at_target_draw_fails_closed(self):
  r=M.validate(runtime(),sub(),evidence(variant=None,vs=3036,ps=3956)); self.assertEqual(r["status"],"fail"); self.assertEqual(r["summary"]["firstFailure"],"dxcap.exact_shader_on_source_stride")
 def test_stride136_does_not_overclaim_source_result(self):
  r=M.validate(runtime(),sub(),evidence(stride=136,exact=True)); self.assertEqual(r["status"],"fail")
 def test_replacement_counter_drift_fails(self):
  s=sub();s["vertex_swap_count"]=0; self.assertEqual(M.validate(runtime(),s,evidence())["summary"]["firstFailure"],"substitution.shader_objects")
if __name__=="__main__": unittest.main()
