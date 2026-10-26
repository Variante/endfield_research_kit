"""Authenticate bounded current FMV source/name programs and their typed joins.

This proves selected static transfers under the returned conditions. It does
not establish live cache/iFix/gender/VFS selection, activation or playback.
"""
import collections,itertools,json,struct
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.string_source_instructions import decode_string_source_instructions
from scripts.game_data.il2cpp.text_source_instructions import decode_text_instruction
from scripts.game_data.il2cpp import fmv_string_sources as programs,protocol
from scripts.game_data.memorypack import pooled_source_helper
from scripts.game_data.levelscript_string_param_native import validate_string_param_native_contract,CONTRACT_PATH as STRING_PARAM_CONTRACT
from scripts.game_data.memory_copy_bounded_native import validate as validate_bounded_copy,CONTRACT_PATH as COPY_CONTRACT

CONTRACT_PATH=CONTRACTS_DIR/'levelscript_fmv_video_native.json'
SCHEMA='endfield.levelscript-fmv-video-native-contract.v2'
LABEL='levelscriptFmvVideoNative'
PROGRAMS=dict(forwarding=2,parse_token=5,constant_value=1,zero_alignment=1,fixed_format=3,append_string=2,cached_builder=1,final_string=1,cached_string=1,format_result=2,array_data=1,char_copy=1,concat=1,ordinary_concat=1,video_root=2,action_tail=2,play_name_probe=1,do_play_name=1,exists=1,check_can_play=1,resolve_path=1,gender_id=8,cutscene_subpath=1,video_asset_path=2)

def _same(expected,actual,role):
 if json.loads(json.dumps(expected))!=json.loads(json.dumps(actual)):
  from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
  validate_claims(expected,actual,label=LABEL+'.native:'+role);validate_claims(actual,expected,label=LABEL+'.native:'+role)
  raise ValueError(LABEL+'.native:'+role)

def method_record(image,index):
 ctx=NativeReferenceContext(image);symbols=ContextSymbols(image);m=image.metadata.methods[index]
 return dict(methodIndex=index,owner=image.type_name(m.declaring_type),name=image.metadata.string(m.name_index),flags=m.flags,parameters=[dict(name=image.metadata.string(p.name_index),type=symbols.type(ctx.type_pointer(p.type_index)))for p in image.metadata.parameters_for(m)],returned=symbols.type(ctx.type_pointer(m.return_type)),pointer=image.method_pointer_va(m))

def type_record(image,name):
 ctx=NativeReferenceContext(image);symbols=ContextSymbols(image);td=ctx.index.types[name]
 offsets=protocol.runtime_type_field_offsets(image.metadata,image.pe,image.registration,td.index)if td.field_count else{}
 sizes=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
 return dict(name=name,parent=ctx.type_name(td.parent_index)if td.parent_index>=0 else'',valueType=ctx.is_value_type(name),sizes=[image.pe.u32_at_va(sizes),image.pe.u32_at_va(sizes+4)],fields=[dict(name=image.metadata.string(f.name_index),type=symbols.type(ctx.type_pointer(f.type_index)),attributes=ctx.field_attributes(f.type_index),offset=offsets[image.metadata.string(f.name_index)])for f in image.metadata.fields_for(td)])

def literal_record(image,cell):
 raw=image.pe.bytes_at_va(cell,8);word=int.from_bytes(raw,'little')
 if word>0xffffffff or not word&1 or word>>29!=5:raise ValueError(LABEL+'.native:literal-tag')
 index=(word>>1)&0xfffffff;ls=image.metadata.sections['stringLiteral'];ds=image.metadata.sections['stringLiteralData']
 if index>=ls.size//8:raise ValueError(LABEL+'.native:literal-index')
 n,at=struct.unpack_from('<ii',image.metadata.buf,ls.offset+index*8)
 if not 0<=at<=at+n<=ds.size:raise ValueError(LABEL+'.native:literal-range')
 data=image.metadata.buf[ds.offset+at:ds.offset+at+n]
 return dict(cellRva=cell-image.pe.image_base,rawHex=raw.hex(),index=index,dataStart=at,dataLength=n,utf8Hex=data.hex(),value=data.decode('utf-8'))

def _joins(cases,copy_entry):
 rows=collections.defaultdict(list)
 for case in cases:rows[case['program']].append(case['arguments'])
 def one(kind,**selection):
  found=[r for r in rows[kind]if all(r.get(k)==v for k,v in selection.items())]
  if not found or any(r!=found[0]for r in found):raise ValueError(LABEL+'.contract:ambiguous-component:'+kind)
  return found[0]
 def equal(*values):
  if any(v!=values[0]for v in values[1:]):raise ValueError(LABEL+'.contract:component-transfer-join')
 cv=one('constant_value');alloc=one('cached_string');string=one('final_string');zero=one('zero_alignment');cat=one('concat');rootcat=one('ordinary_concat');play=one('play_name_probe');exists=one('exists');check=one('check_can_play');resolve=one('resolve_path');sub=one('cutscene_subpath');builder=one('cached_builder')
 genders=rows['gender_id'];assets=rows['video_asset_path']
 equal(*[r['entry']for r in genders],play['gender'],one('do_play_name')['gender'])
 equal(*[r['s']for r in genders]);gender=genders[0]
 equal(*[r['entry']for r in assets],resolve['asset']);equal(*[r['s']for r in assets]);asset=assets[0]
 equal(gender['s']['concat'],cat['entry']);equal(gender['s']['exists'],exists['entry'])
 equal(play['subpath'],exists['subpath'],sub['entry']);equal(play['check'],check['entry']);equal(check['resolve'],exists['resolve'],resolve['entry'])
 equal(cat['allocate'],string['allocate'],rootcat['allocate'],alloc['entry']);equal(cat['array_data'],one('array_data')['entry']);equal(cat['char_copy'],one('char_copy')['entry'])
 equal(cat['append'],one('append_string',substring=False)['entry'])
 for action in rows['action_tail']:equal(action['get'],cv['get_entry']);equal(action['play'],play['entry'])
 for arity in(1,2):
  forward=one('forwarding',arity=arity);result=one('format_result',arity=arity);loops=[r for r in rows['fixed_format']if r['arity']==arity]
  equal(sub['s']['format']if arity==1 else asset['s']['format'],forward['entry']);equal(forward['tail'],result['entry']);equal(result['construct'],builder['entry']);equal(result['string'],string['entry'])
  for loop in loops:
   equal(result['append'],loop['entry']);equal(loop['internal'],zero['entry']);equal(loop['substring'],one('append_string',substring=True)['entry']);equal(loop['parser'],*[r['entry']for r in rows['parse_token']])
 for root in rows['video_root']:equal(root['concat'],rootcat['entry'])
 for kind in('zero_alignment','append_string','final_string','ordinary_concat','char_copy'):
  for r in rows[kind]:equal(r['copy_target'],copy_entry)
 def domain(kind,keys,expected):
  actual=[tuple(r[k]for k in keys)for r in rows[kind]]
  if collections.Counter(actual)!=collections.Counter(expected):raise ValueError(LABEL+'.contract:complete-selected-domain:'+kind)
 domain('action_tail',['wait'],[(False,),(True,)])
 domain('video_root',['receiver_present'],[(False,),(True,)])
 domain('video_asset_path',['has_suffix'],[(False,),(True,)])
 domain('gender_id',['query_gender','female','exists'],list(itertools.product((False,True),repeat=3)))
 domain('fixed_format',['arity','text'],[(1,'Narrative/Cutscene/{0}'),(2,'{0}/{1}'),(2,'{0}/{1}.usm')])
 domain('parse_token',['length','start','index'],[(len(text),text.index('{'+str(n)+'}'),n)for text in('Narrative/Cutscene/{0}','{0}/{1}.usm','{0}/{1}')for n in(0,1)if'{'+str(n)+'}'in text])

def _resolution(fact,results):
 def selected(kind,**selection):return next(out for row,out in results if row['program']==kind and all(row['arguments'].get(k)==v for k,v in selection.items()))
 def literal(cell):return next(r['value']for r in fact['literals']if r['cellRva']==cell-fact['imageBase'])
 gender=selected('gender_id');sub=selected('cutscene_subpath');plain=selected('video_asset_path',has_suffix=True);suffix=selected('video_asset_path',has_suffix=False);root=selected('video_root')
 prefixes=[literal(gender['literalCells'][k])for k in('male','female')];templates=[literal(p['formatLiteralCell'])for p in(plain,suffix)];subpath=literal(sub['formatLiteralCell']);base_path=literal(root['prefixLiteralCell'])+literal(root['platformLiteralCell']);extension=literal(suffix['suffixCell'])
 maximum=128-len(base_path.encode('utf-16-le'))//2-1-len(subpath.replace('{0}','').encode('utf-16-le'))//2-max(len(p.encode('utf-16-le'))//2 for p in prefixes)-len(extension.encode('utf-16-le'))//2
 _same(fact['resolution'],dict(action='PlayFmvAction',field='_moviePath',source=0,encoding='int32-pool-index',genderPrefixes=prefixes,subpathTemplate=subpath,root=base_path,templates=templates,maxIntermediateUtf16Chars=128,maxSourceUtf16Chars=maximum),'literal-derived-resolution-recipe')
 def field(owner,name):return next(f for t in fact['types']if t['name']==owner for f in t['fields']if f['name']==name)
 movie=field('Beyond.Gameplay.Actions.PlayFmvAction','_moviePath');root_field=field('Beyond.VFS.VFSDefine','BLOCK_VIDEO_PATH')
 if movie['type']['name']!='Beyond.Gameplay.Actions.Param`1<string>'or movie['attributes']&16 or any(r['arguments']['movie_slot']!=movie['offset']for r in fact['programs']if r['program']=='action_tail')or root_field['type']['name']!='string'or root_field['attributes']!=54 or root_field['offset']!=root['videoPathFieldOffset']or root_field['offset']!=plain['storedBasePathOffset']:raise ValueError(LABEL+'.native:owned-source-field-layout-joins')
 usages={r['usageCellRva']:r for r in fact['usages']}
 for proof in(root,plain,suffix):
  if usages[proof['sourceTypeCell']-fact['imageBase']]['typeName']!='Beyond.VFS.VFSDefine':raise ValueError(LABEL+'.native:owned-video-root-class')

def _validate_native(image,fact,copy_entry):
 if image.pe.image_base!=fact['imageBase']or collections.Counter(r['program']for r in fact['programs'])!=PROGRAMS:raise ValueError(LABEL+'.contract:program-set')
 _joins(fact['programs'],copy_entry);ctx=NativeReferenceContext(image);symbols=ContextSymbols(image);groups={};rows={};base=image.pe.image_base
 class Mapper:
  def decode_one_x64(self,raw,offset,at):return decode_text_instruction(raw,offset,at)or image.mapper.decode_one_x64(raw,offset,at)
 for group in fact['groups']:
  expected=[[w['startRva'],w['endRva']]for w in group['windows']]
  _same(expected,[p['runtimeTriple'][:2]for p in image.unwind_index.family(expected[0][0])['ranges']],'complete-owned-window-set')
  image.check_windows(group['windows'],label=LABEL);groups[group['id']]=[(base+w['startRva'],image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva']))for w in group['windows']]
 for r in fact['methods']:_same(r,method_record(image,r['methodIndex']),'method-signature-and-entry')
 endpoints={r['role']:next(m for m in fact['methods']if m['methodIndex']==r['methodIndex'])for r in fact['ordinaryEndpoints']}
 if set(endpoints)!={'genderQuery','typeHandle','stringCtor','actionCtor'}:raise ValueError(LABEL+'.contract:typed-ordinary-endpoint-set')
 for case in fact['programs']:
  kind,args=case['program'],case['arguments'];role,key=('genderQuery',None)if kind=='gender_id'else('typeHandle','type_handle')if kind=='concat'else('stringCtor','entry')if kind=='final_string'else('actionCtor','callback')if kind=='action_tail'and args['wait']else(None,None)
  if role and endpoints[role]['pointer']!=(args['s']['gender']if key is None else args[key]):raise ValueError(LABEL+'.native:typed-ordinary-endpoint-transfer:'+role)
 for r in fact['types']:_same(r,type_record(image,r['name']),'type-fields-layout-and-abi')
 for r in fact['contexts']:_same(r,symbols.context(r['definition'],is_method=r['isMethod'],slots=[e['relativeSlot']for e in r['entries']]),'typed-generic-context')
 for r in fact['usages']:_same(r,derive_typed_usage_context(image,r['instructionRva'],label=LABEL),'typed-usage')
 for r in fact['literals']:_same(r,literal_record(image,base+r['cellRva']),'metadata-string-literal')
 for r in fact['registrations']:_same(r['proof'],GenericEntries(image).resolve(r['definition'],r['classArguments'],r['methodArguments']),'canonical-registration')
 for r in fact['enums']:_same(r['members'],protocol.native_enum_members(image.metadata,protocol.field_defaults(image.metadata),image.pe,image.registration,r['type']),'enum-members')
 def argument(value):
  if isinstance(value,dict):
   if set(value)=={'$regions'}:return groups[value['$regions']]
   if set(value)=={'$rows'}:
    key=value['$rows']
    if key not in rows:rows[key]=[r for start,raw in groups[key]for r in decode_string_source_instructions(Mapper(),raw,start)]
    return rows[key]
   return {k:argument(v)for k,v in value.items()}
  return [argument(v)for v in value]if isinstance(value,list)else value
 proved=0;results=[]
 for case in fact['programs']:
  keys=list(case.get('sweep',{}));domain=case.get('sweep',{})
  if case['program']=='cached_string'and domain!={'mode':[0,3],'count':list(range(1,129))}:raise ValueError(LABEL+'.contract:complete-allocator-domain')
  for values in itertools.product(*(domain[k]for k in keys)):
   proof=getattr(programs,case['program'])(**argument(case['arguments']),**dict(zip(keys,values)));results.append((case,proof));proved+=1
 _resolution(fact,results)
 return proved

def validate(*,game_root=None,contract_path=CONTRACT_PATH,gameassembly=None,metadata=None):
 try:
  path=Path(contract_path);raw=path.read_bytes();fact=json.loads(raw)
  if(fact['schema'],fact['status'],fact['evidenceBoundary'])!=(SCHEMA,'exact-current-build','conditional')or set(fact['nativeInputs'])!={'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'}:raise ValueError(LABEL+'.contract:schema')
  if(gameassembly is None)!=(metadata is None):raise ValueError(LABEL+'.native:both-paths-required')
  root=Path(game_root)if game_root is not None else None;pins=fact['nativeInputs'];gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly if gameassembly is not None else root.parent/'GameAssembly.dll'if root else None,metadata=metadata if metadata is not None else root/'il2cpp_data/Metadata/global-metadata.dat'if root else None)
  if gate.status!='validated':return dict(status=gate.status,failedGate='installed_native_inputs',detail=gate.detail)
  failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if failed:return failed
  dependencies=[Path(STRING_PARAM_CONTRACT),Path(COPY_CONTRACT)];dependency_bytes=[p.read_bytes()for p in dependencies]
  audit=validate_string_param_native_contract(gameassembly=gate.gameassembly,metadata=gate.metadata)
  if audit['status']!='validated':return dict(status=audit['status'],failedGate='stringParam',detail=audit)
  slots=json.loads(dependency_bytes[0])['proof']['parameter']['ownedFieldSlots'];constant=next(r['arguments']for r in fact['programs']if r['program']=='constant_value');_same([slots['paramSource'],slots['constValue']],[constant['source_slot'],constant['constant_slot']],'independent-source-owned-slots')
  audit=validate_bounded_copy(game_root=Path(gate.metadata).parents[2])
  if audit['status']!='validated':return dict(status=audit['status'],failedGate='boundedCopy',detail=audit)
  image=open_native_image(gate.gameassembly,gate.metadata);proved=_validate_native(image,fact,image.pe.image_base+audit['entryRva'])
  after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
  if after.status!='validated':return dict(status=after.status,failedGate='native_bookend',detail=after.detail)
  failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if failed:return failed
  if raw!=path.read_bytes()or dependency_bytes!=[p.read_bytes()for p in dependencies]:raise ValueError(LABEL+'.contract:changed-during-validation')
  return dict(status='validated',nativeInputs=pins,layout=fact['resolution'],evidenceBoundary='conditional',conditions=fact['conditions'],programCases=proved)
 except StopIteration:return native_validation_failure(ValueError(LABEL+'.contract:missing-reviewed-component'),label=LABEL,source_path=contract_path)
 except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError)as error:return native_validation_failure(error,label=LABEL,source_path=contract_path)
