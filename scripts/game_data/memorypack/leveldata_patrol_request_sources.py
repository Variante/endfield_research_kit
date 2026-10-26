"""Atomic selected cached resource-request effects below handle construction.

All selected direct children are independently replayed. Existing manifest/cache
hits, literal state two, ready callbacks, bounded stable storage and spare pools
remain conditions; no actual loaded asset or controller invocation is observed.
"""
from scripts.game_data.memorypack import leveldata_patrol_request_load_sources as loading
from scripts.game_data.memorypack import leveldata_patrol_string_scope_sources as strings
from scripts.game_data.memorypack import leveldata_patrol_bundle_cache_sources as cache
from scripts.game_data.memorypack import leveldata_patrol_resource_validity_sources as packets

SCHEMA='endfield.story-patrol-cached-resource-request-sources.v1'


def need(check,condition):
 if not condition:raise ValueError('patrolCachedRequest.'+check)


def _check(load,scope,cached,pins):
 loading.validate(load,pins);strings.validate(scope,pins);cache.validate(cached,pins)
 l=load['proof'];s=scope['proof'];c=cached['proof'];manifest=l['manifestSource'];m=manifest['proof'];b=l['imageBase']
 need('same-native-image-base',b==s['imageBase']==c['imageBase'])
 need('same-fresh-actual-request-parent',m['resourceHandleSource']==s['resourceHandleSource']and m['helpers']['request']==s['helpers']['request'])
 call=next(x for x in l['programs']['load']['calls']if x['role']=='getOrCreate')
 need('actual-LoadAsset-cache-E8',call['targetVa']==b+c['helpers']['caller']['entryRva'])
 need('same-replacement-root',m['programs']['request']['replacementRootCellVa']==l['programs']['load']['replacementRootCellVa']==c['programs']['caller']['replacementRootCellVa'])
 need('same-disabled-collector',c['programs']['caller']['collectorFlagVa']==s['programs']['scope']['collectorDisabledFlagVa'])
 need('literal-state-two-survives-outer-branches',l['programs']['process']['selectedProxyStateLiteral']==2
  and l['programs']['load']['excludedProxyStateLiteral']==4 and m['programs']['request']['selectedProxyStateNotEqualLiteral']==3)
 return dict(actualRequestAndManifestOutput=True,exactGetOrCreateActualE8=True,sameTemporaryStringScope=True,
  sameDisabledCollectorAndReplacementRoot=True,literalTwoSameProxyReturnThroughAllFrames=True,
  allSelectedDirectCalleeEffectsJoined=True,actualCacheOrAssetObserved=False)


def compose(load,scope,cached,pins):
 joins=_check(load,scope,cached,pins)
 return packets.norm(dict(schema=SCHEMA,status='validated-conditional-cached-resource-request-effects',nativeInputs=pins,
  proof=dict(loadSource=load,stringScopeSource=scope,cacheSource=cached,sourceJoins=joins),
  selectedCachedRequestAndAllDirectChildrenEffectsProved=True,sameRequestedProxyAndFullFramesProved=True,
  liveAssetOrCacheHitObserved=False,resourceLoadSchedulingOrCompletionProved=False,runtimeInvocationObserved=False,playbackProved=False,
  conditions=load['conditions']+load['proof']['manifestSource']['conditions']+scope['conditions']+cached['conditions']+[
   'The same requested raw path hash selects a valid manifest record and the independent seeded Type/key cache returns an existing nonnull proxy. Its inherited literal state is2 throughout the selected LoadAsset/request return; the source neither creates/schedules a proxy nor observes an actual cache hit or successful asset load.']))


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 _publication_gate(image,pins);value=compose(loading.derive(image,pins),strings.derive(image,pins),cache.derive(image,pins),pins)
 validate(value,pins);_publication_gate(image,pins);return value


def validate(value,pins):
 need('envelope',value.get('schema')==SCHEMA and value.get('status')=='validated-conditional-cached-resource-request-effects'and value.get('nativeInputs')==pins
  and all(value.get(k)is True for k in('selectedCachedRequestAndAllDirectChildrenEffectsProved','sameRequestedProxyAndFullFramesProved'))
  and all(value.get(k)is False for k in('liveAssetOrCacheHitObserved','resourceLoadSchedulingOrCompletionProved','runtimeInvocationObserved','playbackProved')))
 p=value['proof'];need('exact-atomic-joins',p['sourceJoins']==_check(p['loadSource'],p['stringScopeSource'],p['cacheSource'],pins))
 return value
