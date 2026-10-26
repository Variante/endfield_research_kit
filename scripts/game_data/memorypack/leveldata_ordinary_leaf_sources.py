"""Finite ordinary Story leaves; parents, lists and owner authority stay separate."""
import json

PLANS={
 'Beyond.Gameplay.AI.Config.EnemyAIOverrideAttr':(
  ('innerCircleRange','float','float32-bits'),('longSightRange','float','float32-bits'),('shortSightRange','float','float32-bits')),
 'Beyond.Gameplay.LevelFactoryRegionBusData':(
  ('arcPosition','UnityEngine.Vector3','unity-vector3-raw12'),('hasArc','bool','bool-byte'),('instKey','string','byte-payload'),
  ('templateId','string','byte-payload'),('worldPosition','UnityEngine.Vector3','unity-vector3-raw12'),
  ('worldRotation','UnityEngine.Vector3','unity-vector3-raw12')),
}


def bind_program(name,source,compiled,pending):
 plan=PLANS.get(name)
 if (plan is None or pending or source.get('wrappedType')!=name
   or [(r['fieldName'],r['declaredType'])for r in source.get('orderedSourceReads',[])]!=[(n,t)for n,t,k in plan]
   or not isinstance(compiled,dict)or type(compiled.get('memberCount'))is not int or compiled['memberCount']!=len(plan)
   or [(r['fieldName'],r['kind'])for r in compiled.get('reads',[])]!=[(n,k)for n,t,k in plan]
   or compiled.get('requiredCapabilities')!=(['byte-payload']if any(k=='byte-payload'for n,t,k in plan)else[])
   or compiled.get('childBindings')!=[]):
  raise ValueError('storyOrdinaryLeaf.exact-finite-program:'+str(name))


def derive(image,pins,*,type_names=None):
 """Fresh full sources and ordinary adapters for only these explicit leaves."""
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.memorypack import scalar_param_native as scalar,generated_reader_sources,pooled_source_helper
 from scripts.game_data.memorypack.generated_record_components import compile_member_program
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 from scripts.game_data.memorypack.reference_object_sources import derive_adapter
 need=lambda k,e,a:scalar.need('storyOrdinaryLeaf',k,e,a)
 _publication_gate(image,pins)
 names=list(PLANS)if type_names is None else type_names
 need('finite-explicit-type-selection',True,isinstance(names,list)and bool(names)and all(type(n)is str and n in PLANS for n in names)and len(names)==len(set(names)))
 wrappers={w.wrapped_type:w for w in image.memorypack_wrappers.values()if w.wrapped_type in names}
 need('exact-nominal-wrapper-set',set(names),set(wrappers));base=image.pe.image_base
 result=generated_reader_sources.derive_many(image,pins,[wrappers[name].name for name in names]);records={};caps={}
 for name,row in zip(names,result['owners'],strict=True):
  need('complete-generated-source:'+name,'complete-reader-source-proved',row['status']if row['status']=='complete-reader-source-proved'else row)
  source=row['proof'];compiled,pending=compile_member_program(source,pins,wrapper_name=wrappers[name].name,type_name=name,value4={})
  bind_program(name,source,compiled,pending)
  pair=derive_pair(image,name);adapter=derive_adapter(image,pins,pair,wrappers[name])
  need('complete-original-GetValue',True,source['lifecycle']['GetValue']['program'].get('fullReferenceOutput'))
  need('same-actual-GetValue',source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
  need('same-concrete-formatter',source['lifecycle']['concreteFormatter']['method'][0],pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
  strings={str(read['memberIndex']):pooled_source_helper.validate_on_image(image,base+read['sourceTargetRva'],pins)
   for read in source['orderedSourceReads']if read['kind']=='byte-payload'}
  records[name]=dict(source=source,compiled=compiled,pair=pair,adapter=adapter,pooled=strings)
  caps[name]=dict(typeName=name,memberCount=len(PLANS[name]),program=compiled,nullAdmitted=True,positiveAdmitted=True,
   ordinaryAdapterAdmitted=True,finiteFloatProfile=True,profileAdmitted=True,actualCallbackEqualsProvedChildRequired=True,
   wholeGrammarAdmitted=False,liveFormatterSelectionObserved=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False)
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-ordinary-leaf-components.v1',status='validated-conditional-finite-ordinary-leaves',
  nativeInputs=pins,records=records,capabilities=caps,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
  evidenceBoundary=dict(exact='Each explicitly named complete ordinary wrapper source, new/existing/FF frame, own nominal field stores, canonical original adapter/GetValue and independently checked pooled targets. No child namespace or storage width selects another record.',
   conditional='Ready coherent owned contexts and matching canonical callbacks/providers, normal allocation/collector/helper effects and disjoint contiguous finite input. Float projections reject nonfinite values.',
   unresolved=['actual enclosing field and collection callbacks/counts','runtime selection or use','whole owner/physical EOF/publication']))))
