"""Public stored Module cursor selected only by its complete current graph."""
from scripts.game_data.memorypack import levelscript_module_graph_sources as source
from scripts.game_data.codecs.levelscript import current_module_graph as codec
from scripts.game_data.codecs.levelscript.param_graph import Reader


def require_component(component,pins):
 if(not isinstance(component,dict)or component.get('schema')!=source.SCHEMA
    or component.get('status')!='validated-conditional-current-module-graph'or component.get('nativeInputs')!=pins
    or component.get('holds')!=[]or set(component.get('capabilities',{}))!={source.CAPABILITY}
    or component.get('parentFieldAdmitted')is not False or component.get('wholeOwnerAdmitted')is not False):
  holds=component.get('holds',[])if isinstance(component,dict)else[]
  raise ValueError('currentModulePublic.complete-current-graph:'+str(holds)[:2400])
 cap=component['capabilities'][source.CAPABILITY];codec.validate(cap);return cap


def conditional_sources(cap):
 codec.validate(cap)
 return [dict(typeName=cap['typeName'],sourceWitnessClassArguments=['ulong','object'],
  countLimit=cap['dictionary']['countLimit'],initiallyNullOutputRequired=True,
  actualKeyCallbackEqualsProvedUInt64Required=True,actualValueCallbackEqualsProvedModuleRequired=True,
  typedConstructorAndHelperCompatibilityRequired=True,closedPointerEquivalenceProved=False,
  duplicateAndHashBehaviorAdmitted=False,actualRuntimeSelectionObserved=False),
  dict(typeName=source.BASE,admittedRouteTags=sorted(int(k)for k in cap['routes']),
   initiallyNullOutputRequired=True,actualWrapperCallbackEqualsProvedConcreteRequired=True,
   allPositiveChildDomainsAdmitted=True,runtimeModuleBehaviorAdmitted=False),
  *[dict(typeName=child.get('typeName',child.get('closedListType')),countLimit=child['countLimit'],
    initiallyNullOutputRequired=True,actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False)
   for child in cap['capabilities'].values()if child.get('positiveCountsAdmitted')is True
   and child.get('headerBytes')==4 and type(child.get('countLimit'))is int]]


def decode(data,offset,*,strings,capability):
 codec.validate(capability)
 if type(offset)is not int or not 0<=offset<=len(data):raise ValueError('currentModulePublic.literal-input-offset')
 reader=Reader(data,offset,strings,'modules');value=codec.read(reader,'modules',capability)
 count=value['count'];value.update(status='null'if count==-1 else'present',count=None if count==-1 else count,
  parseStatus='decoded',conditionalChildSources=conditional_sources(capability),storedModuleGrammarAdmitted=True)
 return value,reader.offset
