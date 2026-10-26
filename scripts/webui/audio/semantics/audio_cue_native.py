"""Current AudioCue metadata labels through the independent selected-name gate."""
from scripts.webui.audio.semantics.rtpc_contract import selected_static_names


def exact_native_audio_cue_contract(native_context):
 audit=selected_static_names(native_context)
 result={k:audit[k]for k in('status','detail','metadataSha256','gameAssemblySha256')if k in audit}
 result.update(reason=audit.get('detail','current selected Audio metadata declarations'),expressionTypes={},operatorTypes={})
 if audit['status']=='validated':result.update(audit['enums'],evidence='exactCurrentBuildAudioCueEnumDefinitions')
 return result
