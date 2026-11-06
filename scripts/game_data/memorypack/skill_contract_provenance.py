"""Compact native provenance without admitting a schema or hashing proof JSON.

Every nontrace semantic field is retained in a deterministic, structurally
interned acyclic node table. Component schemas/status/scopes, actual typed
member/call/MethodSpec identities and conditions therefore remain lossless.
Only decoded rows, copied raw regions, ordered native instruction traces and
non-native contract/source digests are omitted. Full traces belong in reports.

Existing native window hashes are deduplicated by exact RVA range, refusing a
conflicting hash. Selected trace slices covered by those windows are omitted;
uncovered slices retain exact bytes and explicitly based or unresolved addresses,
without inventing a whole-method extent or a digest. Named metadata
method rows have their own deduplicated catalog. Structural JSON keys are used
only for interning, never as hashes or integrity checks. This pure projection
grants no native or grammar admission; the owner freshly derives full proofs.
"""
import copy
import bisect
import json
import math
import re

SCHEMA='endfield.skill-contract-provenance.v1'
TRACE_KEYS={'selectedBytes','selectedProgram','instructions','program','entryInstructions','entryProgram','selectedInstructions','rawProgram'}
ROW_TRACE_KEYS={'rows','ordinarySourceRows'}
REGION_TRACE_KEYS={'regions','ordinarySourceRegions','callerRegions'}
HEX=re.compile(r'[0-9a-fA-F]+')
LABEL='skillContractProvenance'


def contract_json_bytes(fact):
    """Keep each interned catalog row on one reviewable line.

    The complete current contract has many small graph nodes. Indenting every
    member of every node multiplies its size without exposing more evidence.
    Semantic fields keep ordinary indentation; only the four flat provenance
    catalogs use one complete JSON value per line. No data is omitted or hashed.
    """
    _need('serialized-contract-object',type(fact)is dict and type(fact.get('proof'))is dict
        and fact['proof'].get('schema')==SCHEMA)
    def member(key,value,indent,*,catalog=False):
        prefix=' '*indent+json.dumps(key)+': '
        if catalog:
            _need('serialized-provenance-catalog',type(value)is list)
            if not value:return [prefix+'[]']
            rows=[prefix+'[']
            for index,item in enumerate(value):
                rows.append(' '*(indent+2)+json.dumps(item,separators=(',',':'),ensure_ascii=True,allow_nan=False)+(','if index+1<len(value)else''))
            rows.append(' '*indent+']');return rows
        rows=json.dumps(value,indent=2,ensure_ascii=True,allow_nan=False).splitlines()
        return [prefix+rows[0]]+[' '*indent+row for row in rows[1:]]
    result=['{'];items=list(fact.items())
    for index,(key,value)in enumerate(items):
        if key=='proof':
            result.append('  "proof": {');proof_items=list(value.items())
            for ordinal,(name,item)in enumerate(proof_items):
                rows=member(name,item,4,catalog=name in('nodes','nativeCodeWindows','metadataMethods','nativeCodeSlices'))
                if ordinal+1<len(proof_items):rows[-1]+=','
                result.extend(rows)
            result.append('  }')
        else:result.extend(member(key,value,2))
        if index+1<len(items):result[-1]+=','
    result.append('}')
    return ('\n'.join(result)+'\n').encode('utf-8')


def _need(check,valid):
    if not valid:raise ValueError(LABEL+'.'+check)


def _key(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)


def _window(value):
    if not isinstance(value,dict)or not {'startRva','endRva','sha256'}<=value.keys():return None
    _need('native-window-fields',set(value)<={'startRva','endRva','sha256','boundary'})
    a,z,h=value['startRva'],value['endRva'],value['sha256']
    _need('native-window-range',type(a)is int and type(z)is int and 0<=a<z<=1<<32)
    _need('native-window-hash',isinstance(h,str)and len(h)==64 and HEX.fullmatch(h)is not None)
    _need('native-window-boundary','boundary'not in value or isinstance(value['boundary'],str))
    return a,z,h.upper()


def _method(value,role):
    return(isinstance(value,list)and 3<=len(value)<=6 and 'method'in role.lower()
        and type(value[0])is int and value[0]>=0 and isinstance(value[1],str)and '.'in value[1]
        and isinstance(value[2],str)and bool(value[2])and not any(c.isspace()for c in value[2])
        and all(item is None or type(item)in(str,int,bool)for item in value[3:]))


def _slice(value):
    if not isinstance(value,(list,tuple))or len(value)!=2 or type(value[0])is not int or value[0]<0 or not isinstance(value[1],str):return None
    raw=value[1].replace(' ','')
    if not raw or len(raw)%2 or HEX.fullmatch(raw)is None:return None
    return value[0],raw.upper()


def _trace(value,role):
    if role in ROW_TRACE_KEYS and isinstance(value,list)and value:
        def decoded(row):
            if not isinstance(row,dict)or not {'va','bytes','text'}<=row.keys()or not isinstance(row['text'],str):return False
            address=row['va']
            if isinstance(address,str)and re.fullmatch(r'0x[0-9a-fA-F]+',address):address=int(address,16)
            return _slice([address,row['bytes']])is not None
        if all(decoded(row)for row in value):return 'decoded-rows'
    if role in REGION_TRACE_KEYS and isinstance(value,list)and value and all(_slice(row)is not None for row in value):return 'raw-regions'
    if role in TRACE_KEYS and isinstance(value,list)and value and all(_slice(row)is not None for row in value):return 'selected-code-slices'
    return None


def _forbidden_digest(role):
    low=role.lower()
    return(('contract'in low or 'declaration'in low or 'proofjson'in low or 'readersource'in low or 'scriptsource'in low)
        and('sha256'in low or low.endswith('hash')))



def _normalize_json_graph(value):
    """JSON-equivalent plain graph normalization, preserving container aliases.

    Tuples become lists. Ordinary Int32/RVA-style integer keys become decimal
    strings, preserving JSON duplicate-key overwrite and insertion ordering.
    Exotic values/keys, nonfinite numbers, cycles or recursion fallback to the
    entire original JSON roundtrip rather than silently widening admission.
    """
    class Fallback(Exception):pass
    memo={};active=set()
    def clone(item):
        kind=type(item)
        if kind in(dict,list,tuple):
            identity=id(item)
            if identity in active:raise Fallback()
            if identity in memo:return memo[identity]
            active.add(identity)
            if kind is dict:
                result={};memo[identity]=result
                for key,child in item.items():
                    if type(key)is str:normalized=key
                    elif type(key)is int:normalized=str(key)
                    else:raise Fallback()
                    result[normalized]=clone(child)
            else:
                result=[];memo[identity]=result
                result.extend(clone(child)for child in item)
            active.remove(identity);return result
        if item is None or kind in(str,bool):return item
        if kind is int:
            # Respect the interpreter's integer-to-JSON digit limit too.
            str(item);return item
        if kind is float:
            if not math.isfinite(item):raise Fallback()
            return item
        raise Fallback()
    try:return clone(value)
    except(Fallback,RecursionError):return json.loads(json.dumps(value))


def project_proof(proof,*,image_base=None):
    """Retain all nontrace semantics; catalogs contain native evidence only."""
    _need('proof-object',isinstance(proof,dict))
    _need('selected-image-base',image_base is None or type(image_base)is int and image_base>=0)
    windows={};boundaries={};methods={};slices={};active=set();inspect_memo={}
    def inspect(value,role='',depth=0):
        _need('bounded-json-depth',depth<=256)
        if not isinstance(value,(dict,list)):
            if _forbidden_digest(role):return(0,{},False)
            _need('json-scalar',value is None or type(value)in(str,int,float,bool))
            if(type(value)is float and not math.isfinite(value))or(type(value)is int and value.bit_length()>64):
                _key(value)
            return(0,{},False)
        container=True;cache_key=(id(value),role)
        if cache_key in inspect_memo:
            height,traces,recursive=inspect_memo[cache_key]
            if recursive:_need('acyclic-json',id(value)not in active)
            _need('bounded-json-depth',depth+height<=256)
            return height,traces,recursive
        def finish(height=0,traces=None,recursive=False):
            result=(height,{}if traces is None else traces,recursive)
            if cache_key is not None:inspect_memo[cache_key]=result
            return result
        if _forbidden_digest(role):return finish()
        trace=_trace(value,role)
        if trace:
            if trace=='selected-code-slices':
                for row in value:
                    pair=_slice(row);slices[pair]=None
            return finish(traces={trace:1})
        window=_window(value)
        if window is not None:
            a,z,h=window;_need('conflicting-native-window-hash',(a,z)not in windows or windows[a,z]==h)
            windows[a,z]=h
            if 'boundary'in value:boundaries.setdefault((a,z),set()).add(value['boundary'])
            return finish()
        if _method(value,role):methods[_key(value)]=copy.deepcopy(value);return finish()
        if container:
            _need('acyclic-json',id(value)not in active);active.add(id(value))
            if isinstance(value,dict):
                _need('string-object-keys',all(isinstance(k,str)for k in value))
                children=(inspect(value[key],key,depth+1)for key in sorted(value))
            else:children=(inspect(item,role,depth+1)for item in value)
            height=0;traces={}
            for child_height,child_traces,_ in children:
                height=max(height,child_height+1)
                for kind,count in child_traces.items():traces[kind]=traces.get(kind,0)+count
            active.remove(id(value));return finish(height,traces,True)
        _need('json-scalar',value is None or type(value)in(str,int,float,bool))
        _key(value);return finish()
    omitted=inspect(proof)[1]
    window_keys=sorted(windows);window_ids={key:i for i,key in enumerate(window_keys)}
    method_keys=sorted(methods);method_ids={key:i for i,key in enumerate(method_keys)}
    covered=[]
    for a,z in window_keys:
        if covered and a<=covered[-1][1]:covered[-1]=(covered[-1][0],max(z,covered[-1][1]))
        else:covered.append((a,z))
    starts=[a for a,z in covered]
    def slice_fact(pair):
        a,h=pair
        if a<1<<32:basis='rva';reason='no-native-window-covers-complete-slice'
        elif image_base is not None and image_base<=a<image_base+(1<<32):
            a-=image_base;basis='rva';reason='no-native-window-covers-complete-slice'
        else:
            basis='unresolved-as-recorded'
            reason='selected-image-base-not-supplied'if image_base is None else'outside-selected-32bit-rva-range'
        z=a+len(h)//2
        index=bisect.bisect_right(starts,a)-1
        if basis=='rva'and z<=1<<32 and index>=0 and z<=covered[index][1]:return None
        if basis=='rva'and z>1<<32:basis='unresolved-as-recorded';reason='slice-crosses-32bit-rva-range';a=pair[0]
        return a,h,basis,reason
    normalized={pair:slice_fact(pair)for pair in slices}
    slice_keys=sorted({fact for fact in normalized.values()if fact is not None});slice_ids={key:i for i,key in enumerate(slice_keys)}
    nodes=[];intern={};encode_memo={}
    def encode(value,role=''):
        if not isinstance(value,(dict,list)):
            return {'$omittedNonNativeDigest':True}if _forbidden_digest(role)else value
        cache_key=(id(value),role)
        if cache_key in encode_memo:return encode_memo[cache_key]
        result=encode_uncached(value,role)
        if cache_key is not None:encode_memo[cache_key]=result
        return result
    def encode_uncached(value,role=''):
        if _forbidden_digest(role):return {'$omittedNonNativeDigest':True}
        trace=_trace(value,role)
        if trace:
            result={'$omittedTrace':trace,'itemCount':len(value)}
            if trace=='selected-code-slices':
                facts=[normalized[_slice(row)]for row in value]
                result['selectedSliceIds']=sorted({slice_ids[fact]for fact in facts if fact is not None})
                result['windowCoveredItemCount']=sum(fact is None for fact in facts)
            return result
        window=_window(value)
        if window is not None:
            result={'$window':window_ids[window[:2]]}
            if 'boundary'in value:result['boundary']=value['boundary']
            return result
        if _method(value,role):return {'$method':method_ids[_key(value)]}
        if isinstance(value,dict):node={'kind':'object','members':[[key,encode(value[key],key)]for key in sorted(value)]}
        elif isinstance(value,list):node={'kind':'array','items':[encode(item,role)for item in value]}
        else:return value
        key=_key(node)
        if key not in intern:intern[key]=len(nodes);nodes.append(node)
        return {'$node':intern[key]}
    root=encode(proof)
    return dict(schema=SCHEMA,nativeAdmissionGranted=False,fullInstructionTracesRetained=False,
        selectedImageBase=image_base,root=root,nodes=nodes,
        nativeCodeWindows=[dict(startRva=a,endRva=z,sha256=windows[a,z],boundaries=sorted(boundaries.get((a,z),())))for a,z in window_keys],
        metadataMethods=[methods[key]for key in method_keys],
        nativeCodeSlices=[dict(address=a,rawHex=h,addressBasis=b,coverageReason=r,wholeMethodExtentProved=False)for a,h,b,r in slice_keys],
        omittedTraceCounts={key:omitted[key]for key in sorted(omitted)},
        evidenceBoundary='Lossless nontrace proof semantics with unique existing native byte-window hashes and named metadata methods. Selected trace slices covered by those exact native windows are omitted. Only uncovered or explicitly unresolved observed slices remain; VA normalization uses the explicit selected image base and 32-bit RVA range. Graph references are structural indices, never digests. Ordered traces remain report-only; no native/grammar admission follows.')


def _validate_proof(projection, *, materialize):
    """Share every admission rule between expansion and compact validation."""
    _need('projection-object',isinstance(projection,dict))
    _need('projection-shape',set(projection)=={'schema','nativeAdmissionGranted','fullInstructionTracesRetained','selectedImageBase',
        'root','nodes','nativeCodeWindows','metadataMethods','nativeCodeSlices','omittedTraceCounts','evidenceBoundary'})
    _need('projection-schema',projection.get('schema')==SCHEMA and projection.get('nativeAdmissionGranted')is False
        and projection.get('fullInstructionTracesRetained')is False)
    base=projection['selectedImageBase'];_need('selected-image-base',base is None or type(base)is int and base>=0)
    _need('projection-boundary',isinstance(projection['evidenceBoundary'],str)and bool(projection['evidenceBoundary']))
    counts=projection['omittedTraceCounts'];_need('trace-counts',isinstance(counts,dict)
        and set(counts)<={'decoded-rows','raw-regions','selected-code-slices'}
        and all(type(n)is int and n>0 for n in counts.values()))
    nodes=projection['nodes'];windows=projection['nativeCodeWindows'];methods=projection['metadataMethods'];slices=projection['nativeCodeSlices']
    _need('catalog-arrays',all(isinstance(a,list)for a in(nodes,windows,methods,slices)))
    seen={}
    for row in windows:
        _need('window-catalog-shape',isinstance(row,dict)and set(row)=={'startRva','endRva','sha256','boundaries'})
        value=_window({k:row[k]for k in('startRva','endRva','sha256')});a,z,h=value
        _need('unique-window-catalog',(a,z)not in seen);seen[a,z]=h
        _need('window-boundary-catalog',isinstance(row['boundaries'],list)and all(isinstance(s,str)for s in row['boundaries'])
            and row['boundaries']==sorted(set(row['boundaries'])))
    _need('unique-method-catalog',len({_key(row)for row in methods})==len(methods)
        and all(_method(row,'method')for row in methods))
    _need('sorted-window-catalog',[(r['startRva'],r['endRva'])for r in windows]==sorted(seen))
    _need('sorted-method-catalog',[_key(row)for row in methods]==sorted(_key(row)for row in methods))
    for row in slices:
        _need('bounded-native-slice',isinstance(row,dict)and set(row)=={'address','rawHex','addressBasis','coverageReason','wholeMethodExtentProved'}
            and _slice([row['address'],row['rawHex']])is not None
            and row['wholeMethodExtentProved']is False)
        if row['addressBasis']=='rva':
            _need('uncovered-rva-slice',row['address']+len(row['rawHex'])//2<=1<<32
                and row['coverageReason']=='no-native-window-covers-complete-slice')
            start=row['address'];end=start+len(row['rawHex'])//2
            for window in windows:
                if window['startRva']>start:break
                if window['endRva']>start:start=window['endRva']
                if start>=end:break
            _need('slice-not-already-window-covered',start<end)
        else:_need('unresolved-slice',row['addressBasis']=='unresolved-as-recorded'
            and row['coverageReason']in('selected-image-base-not-supplied','outside-selected-32bit-rva-range','slice-crosses-32bit-rva-range'))
    slice_keys=[(r['address'],r['rawHex'],r['addressBasis'],r['coverageReason'])for r in slices]
    _need('unique-sorted-slice-catalog',slice_keys==sorted(set(slice_keys)))
    _need('root-node-reference',isinstance(projection['root'],dict)and set(projection['root'])=={'$node'})
    _need('unique-semantic-nodes',len({_key(node)for node in nodes})==len(nodes))
    used_nodes=set();used_windows=set();used_methods=set();used_slices=set();actual_counts={}
    # A structural DAG can encode exponentially many expanded paths. Validate
    # each node once, retaining its longest remaining depth and trace counts.
    # Counts are summed for every incoming occurrence (not just unique nodes);
    # cached depth is checked at every reference, including deeper later paths.
    # Catalog use is a set union, so visiting each reachable node once suffices.
    summaries={}
    def summary(children, *, object_root=False):
        height=0; traces={}
        for child_height, child_traces, _ in children:
            height=max(height,child_height+1)
            for kind,count in child_traces.items():traces[kind]=traces.get(kind,0)+count
        return height,traces,object_root
    def index(value,array):
        _need('literal-catalog-reference',type(value)is int and 0<=value<len(array));return value
    def decode(value,parent=None,depth=0):
        _need('bounded-graph-depth',depth<=256)
        if not isinstance(value,dict):
            _need('encoded-json-scalar',value is None or type(value)in(str,int,float,bool));_key(value);return value if materialize else (0,{},False)
        if '$node'in value:
            _need('node-reference-shape',set(value)=={'$node'});i=index(value['$node'],nodes)
            _need('acyclic-node-order',parent is None or i<parent)
            if not materialize and i in summaries:
                cached=summaries[i]
                _need('bounded-graph-depth',depth+cached[0]<=256)
                return cached
            node=nodes[i];used_nodes.add(i)
            _need('semantic-node-object',isinstance(node,dict))
            if node.get('kind')=='object':
                _need('object-node-shape',set(node)=={'kind','members'}and isinstance(node['members'],list)
                    and all(isinstance(pair,list)and len(pair)==2 and isinstance(pair[0],str)for pair in node['members']))
                keys=[pair[0]for pair in node['members']];_need('ordered-distinct-object-keys',keys==sorted(set(keys)))
                if materialize:return {key:decode(item,i,depth+1)for key,item in node['members']}
                result=summary((decode(item,i,depth+1)for key,item in node['members']),object_root=True)
                summaries[i]=result;return result
            _need('array-node-shape',set(node)=={'kind','items'}and node['kind']=='array'and isinstance(node['items'],list))
            if materialize:return [decode(item,i,depth+1)for item in node['items']]
            result=summary(decode(item,i,depth+1)for item in node['items'])
            summaries[i]=result;return result
        if '$window'in value:
            _need('window-reference-shape',set(value)<={'$window','boundary'})
            i=index(value['$window'],windows);used_windows.add(i);row=windows[i];out={k:row[k]for k in('startRva','endRva','sha256')}
            if 'boundary'in value:_need('selected-window-boundary',value['boundary']in row['boundaries']);out['boundary']=value['boundary']
            return out if materialize else (0,{},True)
        if '$method'in value:
            _need('method-reference-shape',set(value)=={'$method'});i=index(value['$method'],methods);used_methods.add(i);return copy.deepcopy(methods[i]) if materialize else (0,{},False)
        if '$omittedTrace'in value:
            kind=value['$omittedTrace'];_need('omitted-trace-shape',kind in('decoded-rows','raw-regions','selected-code-slices')
                and set(value)==({'$omittedTrace','itemCount','selectedSliceIds','windowCoveredItemCount'}if kind=='selected-code-slices'else{'$omittedTrace','itemCount'})
                and type(value['itemCount'])is int and value['itemCount']>=0)
            actual_counts[kind]=actual_counts.get(kind,0)+1
            if kind=='selected-code-slices':
                ids=value['selectedSliceIds'];_need('selected-slice-reference',isinstance(ids,list)
                    and all(type(i)is int for i in ids)and ids==sorted(set(ids)))
                _need('window-covered-trace-count',type(value['windowCoveredItemCount'])is int
                    and 0<=value['windowCoveredItemCount']<=value['itemCount']
                    and len(ids)<=value['itemCount']-value['windowCoveredItemCount'])
                for i in ids:used_slices.add(index(i,slices))
            return copy.deepcopy(value) if materialize else (0,{kind:1},True)
        _need('omitted-digest-shape',set(value)=={'$omittedNonNativeDigest'}and value['$omittedNonNativeDigest']is True);return dict(value) if materialize else (0,{},True)
    result=decode(projection['root'])
    if not materialize:actual_counts=result[1]
    _need('proof-root-object',isinstance(result,dict) if materialize else result[2])
    _need('no-orphan-semantic-nodes',used_nodes==set(range(len(nodes))))
    _need('no-orphan-native-windows',used_windows==set(range(len(windows))))
    _need('no-orphan-methods',used_methods==set(range(len(methods))))
    _need('no-orphan-slices',used_slices==set(range(len(slices))))
    _need('exact-trace-counts',actual_counts==counts)
    return result


def expand_proof(projection):
    """Validate and expand semantic nodes; omitted traces stay explicit markers."""
    return _validate_proof(projection,materialize=True)


def project_contract(contract,*,image_base=None):
    """Leave all normative top-level programs/caps/requirements unchanged."""
    _need('contract-proof',isinstance(contract,dict)and isinstance(contract.get('proof'),dict))
    result=copy.deepcopy({key:value for key,value in contract.items()if key!='proof'})
    result['proof']=project_proof(contract['proof'],image_base=image_base);return result


def validate_projection(projection):
    """Validate complete graph/catalog closure; this grants no native admission."""
    _validate_proof(projection,materialize=False)
    return dict(schema=SCHEMA,status='validated-structural-projection',nativeAdmissionGranted=False,
        semanticNodes=len(projection['nodes']),nativeCodeWindows=len(projection['nativeCodeWindows']),
        metadataMethods=len(projection['metadataMethods']),nativeCodeSlices=len(projection['nativeCodeSlices']))
