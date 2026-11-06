"""Exact auxiliary StringPool representations; no fallback pool is constructed."""
from __future__ import annotations
import re
import struct
from scripts.game_data.schemas.named_schema import parse_utf8_json
from scripts.game_data.string_pool import StringPoolDecodeError


def need(check,condition,detail=''):
    if not condition:raise StringPoolDecodeError('StringPoolAux.'+check+':'+str(detail)[:500])


def decode_counting(data:bytes,*,strings,source='StringPool/StringPoolCounting.json'):
    end=data.find(b'\r\n')
    need('reported-size-line',0<end<80)
    match=re.fullmatch(rb'Total Size: (0|[1-9][0-9]*)',data[:end])
    need('reported-size-spelling',match is not None)
    reported=int(match[1]);rows=parse_utf8_json(data[end+2:],source=source,error=StringPoolDecodeError)
    need('list-root',isinstance(rows,list));seen={};total=unique=0
    for i,row in enumerate(rows):
        need('exact-counting-fields',isinstance(row,dict)and set(row)=={'str','repeatCount','size','totalSize'},i)
        text=row['str'];count=row['repeatCount'];size=row['size'];extent=row['totalSize']
        need('typed-counting-values',isinstance(text,str)and all(type(v)is int for v in(count,size,extent))and count>0,i)
        need('utf8-byte-length',size==len(text.encode('utf-8')),i)
        need('repeat-byte-total',extent==size*count,i)
        need('unique-statistic-string',text not in seen,i);seen[text]=i
        total+=extent;unique+=size
    need('saved-repeat-byte-total',reported==total-unique,dict(reported=reported,total=total,unique=unique))
    need('selected-pool-required',strings is not None)
    actual=[strings.resolve(i)for i in range(len(strings))]
    need('exact-selected-pool-membership',len(actual)==len(rows)and len(set(actual))==len(actual)and set(actual)==set(seen))
    return dict(schemaStatus='named_exact',wholeSchemaExact=True,reportedTotalSize=reported,
        statisticMeaning='saved repeated UTF-8 bytes',stringCount=len(rows),values=rows,
        physicalEOF=True,selectedPoolMembershipProved=True,runtimeExecutionProved=False)


def decode_hash_index(data:bytes,*,strings,game_root):
    from scripts.game_data.string_pool_hash_index_native import load_schema
    contract,audit=load_schema(game_root=game_root)
    header=contract['header'];fields=header['fields']
    need('reviewed-header-shape',fields==[['magic','4s'],['version','I'],['jsonKeyCount','I'],['bucketCount','I'],['seed1','Q'],['seed2','Q']]
        and header['encoding']=='little-endian')
    codec=struct.Struct('<'+''.join(fmt for _,fmt in fields));need('complete-header',len(data)>=codec.size)
    values=dict(zip((name for name,_ in fields),codec.unpack_from(data),strict=True))
    need('magic-version',values['magic']==header['magic'].encode('ascii')and values['version']==header['version'])
    count=values['jsonKeyCount'];buckets=values['bucketCount'];need('positive-counts',count>0 and buckets>0)
    offset=codec.size
    for name,length,fmt in contract['arrays']:
        size=values[length];width=struct.calcsize('<'+fmt);need('bounded-'+name,size<=len(data)//width and offset+width*size<=len(data))
        values[name]=list(struct.unpack_from('<'+str(size)+fmt,data,offset));offset+=width*size
    need('physical-EOF',offset==len(data));need('selected-pool-required',strings is not None)
    indices=values['values'];need('unique-pool-indices',len(set(indices))==count)
    need('valid-pool-indices',all(type(i)is int and 0<=i<len(strings)for i in indices))
    algo=contract['hash']
    need('reviewed-hash-algorithm',algo['characterEncoding']=='utf-16-le-code-units'
        and algo['operator']=='xor-then-multiply-mod-2^64'
        and algo['bucket']=='hash1 % bucketCount'
        and algo['slot']=='((hash2 + displacement) mod 2^64) % jsonKeyCount'
        and algo['fingerprint']=='low32(hash1 xor high32(hash1) xor hash2 xor high32(hash2))')
    multiplier=algo['multiplier'];need('uint64-multiplier',type(multiplier)is int and 0<multiplier<1<<64)
    mask=(1<<64)-1
    for slot,index in enumerate(indices):
        text=strings.resolve(index);h1,h2=values['seed1'],values['seed2']
        for(unit,)in struct.iter_unpack('<H',text.encode('utf-16-le')):
            h1=((h1^unit)*multiplier)&mask;h2=((h2^unit)*multiplier)&mask
        actual=((h2+values['displacements'][h1%buckets])&mask)%count
        fingerprint=(h1^(h1>>32)^h2^(h2>>32))&0xffffffff
        need('complete-pool-lookup',actual==slot and fingerprint==values['fingerprints'][slot],
            dict(poolIndex=index,expectedSlot=slot,actualSlot=actual,expectedFingerprint=values['fingerprints'][slot],actualFingerprint=fingerprint))
    values['magic']=values['magic'].decode('ascii')
    return dict(schemaStatus='named_exact',wholeSchemaExact=True,fields=values,physicalEOF=True,
        completeSelectedPoolLookupsChecked=count,nativeAudit=audit,runtimeExecutionProved=False)
