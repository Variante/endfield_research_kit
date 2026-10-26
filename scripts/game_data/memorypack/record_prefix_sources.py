"""Initialized cached-holder prefix only; cold paths and the enclosing owner stay separate."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

def initialized_cached_prefix(regions,entry,offsets,fields,count):
 if type(count)is not int or not 4<=count<255 or len(fields)!=4 or any(type(n)is not int or not 0<=n<128 for n in fields):raise ValueError('recordPrefix.declared-shape')
 g=BytesPath(regions,entry);g.take('488bc4','53','55','56','57','4156','4881ec80000000');flags=[]
 def flag():
  g.take('803d');at=g.at+5+int.from_bytes(g.read(4),'little',signed=True);g.take('00');flags.append(at)
 flag();imagebase=g.relative('4c8d35');g.take('488bfa','488be9');g.branch('0f85',True);g.take('488b37','4885f6');g.branch('0f84',False);flag();g.branch('0f85',True);g.take('48837e2000');g.branch('75',True,1)
 current,remaining,advanced,consumed=(offsets[k] for k in ('currentPtr','bufferLength','advancedCount','consumed'))
 g.take('837d'+bytes((remaining,1)).hex());g.branch('7d',True,1);g.take('488b45'+bytes((current,)).hex(),'0fb630','8b5d'+bytes((remaining,)).hex(),'83eb01');g.branch('79',True,1)
 for prefix,key in [('48ff45',current),('ff45',advanced),('ff45',consumed)]:g.take(prefix+bytes((key,)).hex())
 g.take('895d'+bytes((remaining,)).hex(),'4080feff');g.branch('0f84',False);g.take('48833f00');g.branch('75',True,1);header=g.at;g.take('4080fe'+bytes((count,)).hex());g.branch('0f85',False);children=[];nulls=[]
 for i,offset in enumerate(fields):
  g.take(*(('488b1f','488bcd') if i==0 else ('488bcd','488b1f')));call=g.at;target=g.relative('e8');g.take('4885db');nulls.append(g.relative('0f84'))
  g.take('4c8b4310' if i==3 else '488b4b10','4d85c0' if i==3 else '4885c9');nulls.append(g.relative('0f84'))
  if i==3:
   g.take('833d');collector=g.at+5+int.from_bytes(g.read(4),'little',signed=True);g.take('00')
  store=g.at;g.take(('498940' if i==3 else '8941' if i==1 else '8841')+bytes((offset,)).hex());children.append(dict(call=call,target=target,store=store))
  if i==3:g.branch('74',True,1)
 if len(set(nulls))!=1 or any(at not in g.bytes for at in nulls) or children[0]['target']!=children[2]['target']:raise ValueError('recordPrefix.guard-or-Boolean-source')
 return dict(selectedBytes=g.seen,header=header,imageBaseReference=imagebase,initializerFlags=flags,collectorFlag=collector,nullTarget=nulls[0],children=children,prefixOnly=True,wholeOwnerAdmitted=False,condition='Both metadata flags initialized; existing matching nonnull wrapper/original and nonnull cached instance; contiguous nonoverflowing reader, exact nonnull root count; disabled collector and normal scalar/string helper returns. Cold initialization, missing/cached instance selection, allocation, subsequent members and complete owner are unproved.')

def selected_initialized_prefix(build,wrapper):
 from scripts.game_data.il2cpp.reference_field_programs import _setter_metadata
 from scripts.game_data.il2cpp.type_data_initialization_instructions import decode_type_data_initialization_instructions
 from scripts.game_data.memorypack.scalar_param_native import reader_offsets
 image=build.image;base=image.pe.image_base;body=image.body_index.body(wrapper.name,'Deserialize');regions=[];rows=[]
 for part in image.unwind_index.family(body.pointer-base)['ranges']:
  a,z=part['runtimeTriple'][:2];raw=image.pe.bytes_at_va(base+a,z-a);regions.append((base+a,raw));rows+=decode_type_data_initialization_instructions(image.mapper,raw,base+a)
 fields=[_setter_metadata(image,build.wrappers,m)[4] for m in wrapper.members[:4]];proof=initialized_cached_prefix(regions,body.pointer,reader_offsets(image,'recordPrefix'),fields,len(wrapper.members))
 if proof['imageBaseReference']!=base:raise ValueError('recordPrefix.selected-image-base')
 selected={a+i:b for a,h in proof['selectedBytes'] for i,b in enumerate(bytes.fromhex(h))};chosen=[]
 for row in rows:
  at=int(row['va'],16);raw=bytes.fromhex(row['bytes'])
  if at not in selected:continue
  if any(selected.get(at+i)!=b for i,b in enumerate(raw)):raise ValueError('recordPrefix.complete-selected-instruction')
  chosen.append(row)
 chosen.sort(key=lambda r:next(i for i,(a,h) in enumerate(proof['selectedBytes']) if a<=int(r['va'],16)<a+len(bytes.fromhex(h))))
 if sum(len(bytes.fromhex(r['bytes']))for r in chosen)!=len(selected):raise ValueError('recordPrefix.selected-byte-partition')
 trap=[r for r in rows if int(r['va'],16)>=proof['nullTarget']][:2]
 if len(trap)!=2 or int(trap[0]['va'],16)!=proof['nullTarget']:raise ValueError('recordPrefix.owned-null-target')
 return chosen+trap,proof
