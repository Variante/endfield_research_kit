"""Finite cursors for source-owned Npc tag and Forbid phase constants."""
from scripts.game_data.memorypack.levelscript_action_nominal_param_sources import NPC,FORBID,PHASE,SCHEMA,RECORD_SCHEMA


def need(check,value):
 if not value:raise ValueError('currentNominalActionParam.'+check)


def _records(records):
 need('exact-finite-record-domain',type(records)is dict and set(records)=={FORBID,PHASE})
 allowed={'bool':'bool-byte','byte':'byte','int':'scalar32','uint':'scalar32','long':'scalar64-bits','ulong':'scalar64-bits',
  'float':'float32-bits','double':'float64-bits','string':'byte-payload',PHASE:'actionmap-nominal-record'}
 for name,cap in records.items():
  need('complete-nominal-record',type(cap)is dict and cap.get('schema')==RECORD_SCHEMA and cap.get('typeName')==name
   and type(cap.get('wrapperName'))is str and cap['wrapperName']
   and type(cap.get('memberCount'))is int and 0<=cap['memberCount']<250
   and all(cap.get(k)is True for k in('ordinaryOriginalReadValueAdmitted','wholeGrammarAdmitted','actualCallbackEqualsProvedChildRequired'))
   and cap.get('liveFormatterSelectionObserved')is False
   and type(cap.get('referenceReaderMethodDefinition'))is int and cap['referenceReaderMethodDefinition']>=0
   and all(type(cap.get(k))is int and cap[k]>0 for k in('referenceReaderTargetRva','canonicalAdapterTargetRva')))
  fields=cap.get('fields');program=cap.get('program');need('owned-record-program',type(program)is dict);reads=program.get('reads');enums={}
  for e in cap.get('enumBackings',[]):
   need('unique-owned-enum-backing',type(e)is dict and type(e.get('typeName'))is str and e['typeName']not in enums
    and type(e.get('typeDefinition'))is int and e['typeDefinition']>=0 and e.get('backingType')in('int','uint','long','ulong','byte'))
   raw=bytes.fromhex(e.get('backingTypeRawHex',''));kind={'int':8,'uint':9,'long':10,'ulong':11,'byte':5}[e['backingType']]
   need('ordinary-enum-backing-record',len(raw)==16 and raw[10]==kind and raw[11]&127==0)
   enums[e['typeName']]=allowed[e['backingType']]
  need('complete-ordered-fields',type(fields)is list and type(reads)is list and len(fields)==len(reads)==cap['memberCount']==program.get('memberCount')
   and all(type(f)is dict and type(f.get('memberIndex'))is int and type(f.get('fieldName'))is str and f['fieldName']and type(f.get('declaredType'))is str for f in fields)
   and [f['memberIndex']for f in fields]==list(range(len(fields)))and len({f['fieldName']for f in fields})==len(fields))
  required=set();bindings=[]
  for field,read in zip(fields,reads,strict=True):
   typ=field['declaredType'];kind=allowed.get(typ,enums.get(typ));child=read.get('childCapability')
   need('exact-source-compiled-record-operation',kind is not None and read.get('kind')==kind
    and(read.get('memberIndex'),read.get('fieldName'))==(field['memberIndex'],field['fieldName']))
   if kind=='actionmap-nominal-record':
    need('only-root-to-Phase-child',name==FORBID and typ==PHASE and child==PHASE);required.add(PHASE);bindings.append(field)
   elif kind=='byte-payload':need('pooled-string-child',child=='byte-payload');required.add('byte-payload')
   else:need('atomic-operation-no-child',child is None)
  need('exact-record-child-set',program.get('requiredCapabilities')==sorted(required))
  actual=program.get('childBindings');need('exact-record-child-binding-count',type(actual)is list and len(actual)==len(bindings))
  for field,binding in zip(bindings,actual,strict=True):
   child=records[PHASE]
   need('exact-record-child-reader-binding',(binding.get('fieldName'),binding.get('typeName'),binding.get('capability'))==(field['fieldName'],PHASE,PHASE)
    and binding.get('readerMethodDefinition')==child['referenceReaderMethodDefinition']and type(binding.get('readerMethodDefinition'))is int
    and binding.get('sourceTargetRva')==child['referenceReaderTargetRva']and type(binding.get('sourceTargetRva'))is int)
 root=records[FORBID]
 need('exact-Forbid-root-order',[(f['fieldName'],f['declaredType'])for f in root['fields']]==[('forbidPhaseParams',PHASE),('phaseName','string')])


def validate_constant(cap,value_type):
 need('own-nominal-source',type(cap)is dict and cap.get('schema')==SCHEMA and cap.get('valueType')==value_type and value_type in(NPC,FORBID))
 need('complete-independent-source-flags',all(cap.get(k)is True for k in('constantSourceProved','fullParamSourceProved','actualCallbackEqualsProvedChildRequired'))
  and all(cap.get(k)is False for k in('liveFormatterSelectionObserved','runtimeValueEvaluationAdmitted','wholeOwnerAdmitted')))
 if value_type==NPC:
  need('exact-Npc-raw4-grammar',cap.get('wireKind')=='npc-behavior-tag-raw4'and type(cap.get('wireBytes'))is int and cap['wireBytes']==4
   and cap.get('fieldOrder')==['tag']and cap.get('rawBitsPreserved')is True and cap.get('wrapperFramingUsed')is False and cap.get('firstFFIsRawData')is True)
 else:
  need('own-Forbid-record-grammar',cap.get('wireKind')=='forbid-phase-record'and cap.get('rootRecord')==FORBID)
  _records(cap.get('records'))
 return cap


def read_constant(reader,field,cap,value_type):
 validate_constant(cap,value_type)
 if value_type==NPC:
  bits=reader.number('<I',field+'.tag');return dict(tagBits=bits,rawHex=bits.to_bytes(4,'little').hex().upper())
 from scripts.game_data.codecs.levelscript.current_generated_action_route import _float
 def record(name,path):
  selected=cap['records'][name];at=reader.offset;marker=reader.number('<B',path+'.memberCount')
  if marker==255:return None
  if marker!=selected['memberCount']:raise ValueError(path+':nominal-record-member-count')
  fields={};spans={}
  for declaration,read in zip(selected['fields'],selected['program']['reads'],strict=True):
   key=declaration['fieldName'];part=path+'.'+key;start=reader.offset;kind=read['kind']
   if kind=='actionmap-nominal-record':value=record(PHASE,part)
   elif kind=='byte-payload':value=reader.string(part)
   elif kind=='bool-byte':byte=reader.number('<B',part);value=dict(value=bool(byte),rawByte=byte)
   elif kind=='byte':value=reader.number('<B',part)
   elif kind in('scalar32','scalar64-bits'):
    width=4 if kind=='scalar32'else 8;bits=reader.number('<I'if width==4 else'<Q',part)
    value=dict(unsignedBits=bits,rawHex=bits.to_bytes(width,'little').hex().upper())
   elif kind in('float32-bits','float64-bits'):value=_float(reader,part,4 if kind=='float32-bits'else 8)
   else:raise ValueError(part+':unproved-nominal-operation')
   fields[key]=value;spans[key]=[start,reader.offset]
  return dict(typeName=name,startOffset=at,endOffset=reader.offset,fields=fields,fieldRanges=spans)
 return record(FORBID,field)
