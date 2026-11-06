"""Complete named stored DynamicStreaming main payloads.

FlatBuffer allocations, every reached inline struct and native zero padding
must close. Descriptor tables require their own positive grammar; a nonempty
descriptor vector is refused, never replaced by an empty result.
"""
from __future__ import annotations

import hashlib
import math
import struct

from scripts.game_data.dynamic_component_programs import SCALARS, expected_writes
from scripts.game_data.dynamic_streaming import (
    _bounded_vector, _field_span, _root_layout, _table_layout,
    _validate_string_vector, parse_dynamic_file,
)


SCHEMA='endfield.complete-dynamic-main-frame.v1'


def need(check,condition,detail=''):
    if not condition:raise ValueError('dynamicComponents.frame.'+check+': '+str(detail)[:1000])


def _zero(data,start,end,label):
    need('native-zero-Pad',0<=start<=end<=len(data)and not any(data[start:end]),(label,start,end))


def _record(data,start,record,records):
    end=start+record['width'];need('bounded-struct',0<=start<end<=len(data),record['type'])
    values={};words={}
    for field in record['fields']:
        at=start+field['offset'];kind=field['type'];name=field['name']
        if kind in SCALARS:
            fmt,width=SCALARS[kind];raw=data[at:at+width]
            need('complete-field-word',len(raw)==width,(record['type'],name,at))
            value=struct.unpack(fmt,raw)[0]
            if kind=='System.Boolean':need('canonical-bool',value in (0,1),(record['type'],name,at,value))
            if kind=='System.Single':
                words[name]={'byteOffset':at,'rawHex':raw.hex().upper()}
                if not math.isfinite(value):
                    value={'float32BitsHex':f'{struct.unpack("<I",raw)[0]:08X}','special':'nan'if math.isnan(value)else'negativeInfinity'if value<0 else'positiveInfinity'}
            values[name]=value
        else:
            values[name],child_words=_record(data,at,records[kind],records)
            words.update({name+'.'+k:v for k,v in child_words.items()})
    for a,b,kind in expected_writes(record,records):
        if kind=='padding':_zero(data,start+a,start+b,record['type'])
    return values,words


def _table_bytes(data,table,fields,label):
    """Close field extents and each minimal Prep inside a table object."""
    parts=[(table['tableOffset'],table['tableOffset']+4,4,'vtable back offset')]
    for index,(width,alignment)in fields.items():
        address=_field_span(data,table,index,width)
        if address is not None:parts.append((address,address+width,alignment,f'{label} field {index}'))
    parts.sort();finish=table['tableOffset']+table['objectSize'];out=[]
    for i,(start,end,alignment,name)in enumerate(parts):
        right=parts[i+1][0]if i+1<len(parts)else finish
        need('nonoverlapping-table-fields',start<end<=right<=finish,(name,start,end,right))
        padding=(-(len(data)-right+(end-start)))&(alignment-1)
        need('minimal-native-table-Prep',right-end==padding,(name,end,right,padding))
        _zero(data,end,right,name)
        if padding:out.append(dict(startOffset=end,endOffset=right,bytes=padding,source='table-Prep'))
    return out


def _allocations(data,allocations):
    """Close minimal native reverse-builder pads, including Finish and EOF."""
    unique={}
    for row in allocations:
        start,end,alignment,additional,kind,label=row
        need('allocation-bounds',0<=start<end<=len(data),(label,start,end))
        previous=unique.get((start,end))
        if previous is not None:
            need('only-native-shared-allocations',kind in ('vtable','string')and previous==row,(label,previous))
        else:unique[start,end]=row
    ordered=sorted(unique.values());pads=[];owned=0
    for i,(start,end,alignment,additional,kind,label)in enumerate(ordered):
        right=ordered[i+1][0]if i+1<len(ordered)else len(data)
        need('allocation-nonoverlap',end<=right,(label,end,right))
        if kind=='root offset':
            # Finish Prep(minAlign, sizeof(root offset)); root Version is an
            # actually present UInt64, so native minAlign is at least eight.
            expected=(-(len(data)-right+4))&7
        elif kind in ('vector','string'):
            expected=(-(len(data)-right+additional))&(alignment-1)
        else:expected=0
        need('minimal-native-allocation-Prep',right-end==expected,(label,end,right,expected))
        _zero(data,end,right,label)
        if expected:pads.append(dict(startOffset=end,endOffset=right,bytes=expected,source='Finish-Prep'if kind=='root offset'else kind+'-Prep'))
        owned+=end-start
    need('physical-EOF-byte-closure',ordered and ordered[0][0]==0 and owned+sum(p['bytes']for p in pads)==len(data))
    return dict(ownedAllocationBytes=owned,nativePaddingBytes=sum(p['bytes']for p in pads),
                allocationCount=len(ordered),padding=pads,allBytesAccounted=True,physicalEOF=True)


def decode_complete_main(data,*,native,source):
    """Decode one VFS-authenticated source with a fresh complete native layout."""
    path=source['path'];actual_md5=hashlib.md5(data).hexdigest().upper()
    need('authenticated-VFS-byte-join',len(data)==source['declaredBytes']and actual_md5==source['fileDataMd5'].upper(),
         (path,len(data),source['declaredBytes'],actual_md5,source['fileDataMd5']))
    main=native['main'];records=native['records'];vectors={r['fieldIndex']:r for r in main['vectors']}
    widths={index:r['elementWidth']for index,r in vectors.items()}
    framed=parse_dynamic_file('main',data,main_vector_widths=widths)
    root=_root_layout(data);total=len(data)
    need('native-Finish-alignment',total%8==0,(path,total))
    allocations=[(0,4,8,4,'root offset','root offset')];table_pads=[]
    def table_allocation(table,label):
        a=table['tableOffset'];allocations.append((a,a+table['objectSize'],1,0,'table',label))
        a=table['vtableOffset'];allocations.append((a,a+table['vtableSize'],1,0,'vtable','shared vtable'))
    def vector(table,index,width,alignment,label):
        a,n,end=_bounded_vector(data,table,index,width)
        if a:
            need('native-vector-body-alignment',(total-a)%alignment==0,(label,a,alignment))
            allocations.append((a-4,end,max(4,alignment),n*width,'vector',label))
        return a,n,end
    table_allocation(root,'root')
    table_pads.extend(_table_bytes(data,root,{0:(8,8),1:(4,4),2:(4,4),3:(4,4),4:(4,4)},'root'))
    string_body,string_count,_=vector(root,4,4,4,'TotalStr')
    string_spans=_validate_string_vector(data,string_body,string_count);strings=[]
    for start,end,label in string_spans:
        allocations.append((start,end,4,end-start-4,'string','shared string'))
        strings.append(dict(byteOffset=start,text=data[start+4:end-1].decode('utf-8'),utf8Bytes=end-start-5))
    grid_body,grid_count,_=vector(root,3,4,4,'Grids');grids=[];components=[];by_type={}
    for ordinal in range(grid_count):
        slot=grid_body+ordinal*4;target=slot+struct.unpack_from('<I',data,slot)[0]
        grid=_table_layout(data,target);table_allocation(grid,'SingleGrid['+str(ordinal)+']')
        uid_at=_field_span(data,grid,0,4);mask_at=_field_span(data,grid,60,8)
        need('selected-grid-scalar-fields',uid_at is not None and mask_at is not None,(path,ordinal))
        uid=struct.unpack_from('<I',data,uid_at)[0];mask=struct.unpack_from('<Q',data,mask_at)[0]
        table_pads.extend(_table_bytes(data,grid,{0:(4,4),60:(8,8),**{i:(4,4)for i in vectors}},'SingleGrid['+str(ordinal)+']'))
        fields=[dict(index=0,name='UniqueId',type='System.UInt32',byteOffset=uid_at,value=uid)]
        for index,row in vectors.items():
            label=f'SingleGrid[{ordinal}].{row["name"]}'
            a,count,_=vector(grid,index,row['elementWidth'],row['elementAlignment'],label)
            field=dict(index=index,name=row['name'],elementType=row['elementType'],
                       present=index in grid['presentFields'],count=count,bodyOffset=a if a else None)
            if row['elementKind']=='scalar32':
                field['values']=list(struct.unpack_from('<'+str(count)+'i',data,a))if count else[]
            elif row['elementKind']=='struct':
                definition=records[row['elementType']];entries=[]
                for item in range(count):
                    at=a+item*row['elementWidth'];values,words=_record(data,at,definition,records)
                    entries.append(len(components))
                    components.append(dict(name=row['name'],type=row['elementType'],gridOrdinal=ordinal,
                        uniqueId=uid,ordinal=item,byteOffset=at,bytes=row['elementWidth'],values=values,float32Words=words,
                        stringReferences={},authoredOwners=[]))
                field['componentIndexes']=entries;by_type[row['name']]=by_type.get(row['name'],0)+count
            else:
                need('descriptor-table-positive-grammar-required',count==0,(path,label,count))
                field['values']=[]
            fields.append(field)
        fields.append(dict(index=60,name='DataMask',type='System.UInt64',byteOffset=mask_at,value=mask))
        need('all-sixty-one-named-grid-fields',[f['index']for f in fields]==list(range(61)))
        grids.append(dict(ordinal=ordinal,uniqueId=uid,fields=fields))
    closure=_allocations(data,allocations);closure['tablePadding']=table_pads
    layouts={}
    def retain_layout(kind):
        if kind in layouts:return
        row=records[kind]
        layouts[kind]=dict(type=kind,width=row['width'],alignment=row['alignment'],
            fields=[{k:field[k]for k in ('name','type','offset')}for field in row['fields']])
        for field in row['fields']:
            if field['type']not in SCALARS:retain_layout(field['type'])
    for component in components:retain_layout(component['type'])
    return dict(schema=SCHEMA,schemaStatus='named_exact',wholeSchemaExact=True,physicalEOF=True,
        bytesConsumed=total,rootFieldCount=5,gridFieldCount=61,
        fields=[dict(index=i,name=name,value=value)for i,(name,value)in enumerate([
            ('Version',framed['Version']),('StreamingVersion',framed['StreamingVersion']),
            ('UniqueId',framed['UniqueId']),('Grids',grids),('TotalStr',strings)])],
        components=components,componentLayouts=list(layouts.values()),byType=by_type,byteClosure=closure,
        sourceMd5=actual_md5,sourceSha256=hashlib.sha256(data).hexdigest().upper(),
        evidenceBoundary={'storedLayout':'exact','DataMaskMeaning':'unresolved','runtimeActivation':'unresolved'})
