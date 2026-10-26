"""Freshly compose explicit Param selections through their independent owners."""
import json

from scripts.game_data.memorypack.levelscript_condition_param_sources import PREFIX,CAP_PREFIX,need

SCHEMA='endfield.story-condition-selected-params.v1'


def partition(parameter_types):
 from scripts.game_data.memorypack.levelscript_condition_param_sources import PRIMITIVES
 from scripts.game_data.memorypack.levelscript_condition_storage_param_components import TYPES as STORAGE
 from scripts.game_data.memorypack.levelscript_condition_list_param_sources import TYPES as LISTS
 from scripts.game_data.memorypack.levelscript_int2_param_sources import VALUE as INT2
 from scripts.game_data.memorypack.levelscript_script_task_param_sources import VALUE as TASK
 need('explicit-distinct-selected-Param-types',isinstance(parameter_types,(list,tuple))and 0<len(parameter_types)<=256
  and all(type(n)is str and n.startswith(PREFIX)and n.endswith('>')for n in parameter_types)
  and len(set(parameter_types))==len(parameter_types))
 selected={k:[]for k in('primitive','storage','list','int2','task','enum')}
 for name in parameter_types:
  value=name[len(PREFIX):-1]
  family='primitive'if value in PRIMITIVES else'storage'if value in STORAGE else'list'if value in LISTS else'int2'if value==INT2 else'task'if value==TASK else'enum'
  # "enum" is only a candidate queue: its owner independently proves the
  # actual carrier, sole enum declaration, backing and native source.
  selected[family].append(name if family=='enum'else value)
 return selected


def derive(image,pins,*,parameter_types):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.memorypack import levelscript_condition_param_sources as primitive
 from scripts.game_data.memorypack import levelscript_condition_storage_param_components as storage
 from scripts.game_data.memorypack import levelscript_condition_list_param_components as listing
 from scripts.game_data.memorypack import levelscript_condition_enum_param_components as enum
 from scripts.game_data.memorypack import levelscript_int2_param_sources as int2,levelscript_script_task_param_sources as task
 from scripts.game_data.memorypack.levelscript_condition_param_bindings import _validate_capability
 selected=partition(parameter_types);_publication_gate(image,pins);components=[];caps={};owners=[]
 operations={
  'primitive':lambda names:primitive.derive_many(image,pins,names),
  'storage':lambda names:storage.derive_many(image,pins,names),
  'list':lambda names:listing.derive_many(image,pins,element_types=[n[len(listing.LIST):-1]for n in names]),
  'int2':lambda names:int2.derive(image,pins),'task':lambda names:task.derive(image,pins),
  'enum':lambda names:enum.derive_many(image,pins,names)}
 for family,names in selected.items():
  if not names:continue
  try:component=operations[family](names)
  except(ValueError,KeyError,IndexError,TypeError)as error:
   import traceback
   sites=[dict(function=f.name,line=f.lineno,source=f.filename.replace('\\','/').split('/scripts/',1)[-1])
    for f in traceback.extract_tb(error.__traceback__)[-8:]]
   owners.extend(dict(status='pendingReview',typeName=n if family=='enum'else PREFIX+n+'>',reason=str(error)[:2200],
    diagnostic=dict(validator='storyConditionSelectedParams',family=family,failedGate=str(error).split(':',1)[0],sourceCallSites=sites),
    parentFieldAdmitted=False,wholeOwnerAdmitted=False)for n in names)
   continue
  need('same-selected-Param-family-native-inputs',component.get('nativeInputs')==pins)
  for key,cap in component.get('capabilities',{}).items():
   _validate_capability(component,key)
   need('no-overlapping-or-unrequested-Param-child',key not in caps and key==CAP_PREFIX+cap['typeName']and cap['typeName']in parameter_types)
   caps[key]=cap
  owners.extend(component['owners']);components.append(component)
 complete={c['typeName']for c in caps.values()}==set(parameter_types)
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,nativeInputs=pins,selectedTypes=list(parameter_types),components=components,
  capabilities=caps,owners=owners,selectedChildDomainComplete=complete,parentFieldAdmitted=False,
  recursiveGrammarAdmitted=False,wholeOwnerAdmitted=False)))
