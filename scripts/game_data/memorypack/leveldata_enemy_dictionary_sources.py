"""Enemy string/object dictionary -1/0 under an explicit erased-source condition."""
import json

TYPE='System.Collections.Generic.Dictionary`2<string,object>'
CAP='story-enemy-ai-blackboard-empty'


def require_arguments(carrier):
 if not isinstance(carrier,dict):raise ValueError('storyEnemyDictionary.closed-carrier')
 arguments=carrier.get('classArguments',[])
 if(carrier.get('name')!=TYPE or carrier.get('definition',{}).get('name')!='System.Collections.Generic.Dictionary`2'
  or len(arguments)!=2 or[(a.get('name'),bytes.fromhex(a.get('rawHex',''))[10:12])for a in arguments]!=[('string',b'\x0e\x00'),('object',b'\x1c\x00')]):
  raise ValueError('storyEnemyDictionary.exact-STRING14-OBJECT28-arguments')


def require_source_profiles(source):
 programs=source.get('sourcePrograms',[])if isinstance(source,dict)else[]
 profiles=[p.get('countProfile')if isinstance(p,dict)else None for p in programs]
 if(profiles!=['null','zero']or any(type(p.get('headerBytes'))is not int or p['headerBytes']!=4
  or p.get('normalReturn')is not True for p in programs)):
  raise ValueError('storyEnemyDictionary.full-null-newzero-count-programs:expected=[null,zero]/header4/normal-return:actual='+str(profiles))


def derive(image,pins,*,typed_request,call_target):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext,closed_generic_reference_pointer_extent
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 from scripts.game_data.memorypack.leveldata_empty_dictionary_sources import derive_source_witness
 from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
 from scripts.game_data.memorypack.skill_cost_data_list_sources import _load
 from scripts.game_data.memorypack import scalar_param_native as scalar
 need=lambda k,e,a:scalar.need('storyEnemyDictionary',k,e,a)
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image)
 validate_typed_usage_context(image,typed_request,label='storyEnemyDictionary.actualParent')
 bind_typed_read(image,typed_request,method_name='ReadPackable',argument=TYPE,kind=21,reference=True)
 argument,=image.instantiations.resolve(typed_request['methodSpec'][2]).arguments
 carrier=ContextSymbols(image).type(argument.type_pointer_va);require_arguments(carrier)
 extent=closed_generic_reference_pointer_extent(ctx,argument.type_pointer_va)
 core=_load('npc_runtime_native.json',pins)
 need('literal-actual-parent-source',True,type(call_target)is int and call_target>base)
 need('actual-owned-ReadPackable-helper',base+core['readPackable']['entryRva'],call_target)
 source=derive_source_witness(image,pins)
 need('independent-open-source-witness',['object','object'],source['sourceWitnessClassArguments'])
 need('source-only-no-capability',False,'capability'in source)
 require_source_profiles(source)
 cap=dict(typeName=TYPE,closedDictionaryType=TYPE,keyType='string',valueType='object',allowedCounts=[-1,0],countRange=[-1,0],
  countLimit=0,headerBytes=4,outputBytes=8,nullable=True,positiveCountsAdmitted=False,keyGrammarAdmitted=False,valueGrammarAdmitted=False,
  profileAdmitted=True,wholeGrammarAdmitted=False,closedPointerEquivalenceProved=False,
  actualCallbackEqualsCanonicalRequired=True,sourceWitnessClassArguments=['object','object'],
  typedConstructorAndHelperCompatibilityRequired=True,actualCallbackSelectionObserved=False,providerFactorySelectionObserved=False,
  packableReaderMethodDefinition=typed_request['methodSpec'][0],packableReaderTargetRva=call_target-base,
  parentFieldAdmitted=False,wholeOwnerAdmitted=False)
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-enemy-dictionary-empty-source.v1',status='validated-conditional-empty-dictionary-source',
  nativeInputs=pins,capabilities={CAP:cap},proof=dict(actualTypedRequest=typed_request,closedCarrier=carrier,closedReferenceExtent=extent,sourceWitness=source),
  parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(
   exact='Actual closed Dictionary<string,object> parent context/reference carrier and selected ReadPackable helper, independently authenticated open TK/TV object/object source witness and complete -1/newzero count/output/constructor/provider programs.',
   conditional='Actual selected dictionary callback executes the independently proved erased source under coherent closed string/object contexts, compatible typed constructor/helper/provider/factory choice, initialized metadata and normal disabled collector/allocation effects. No closed pointer equivalence is inferred.',
   unresolved=['positive keys or arbitrary object values','actual closed runtime callback/constructor/provider selection','enclosing Enemy/host framing','whole owner physical EOF/publication']))))
