"""Retire an exact helper-header byte before a separately proved Int3 spill.

The header owner supplies its actual result-load marker. This component checks
the selected bytes, stable stack and absence of intervening header access. The
source VM and frame owner must independently prove the replacement value's
complete field transfer and disjoint live frame; no wire grammar is inferred.
"""
import re

from scripts.game_data.memorypack import buff_ec_profiles_native as ec


def need(key,condition):
    if not condition:raise ValueError('generatedHeaderLifetime.'+key)


def prove(path,*,base,header_local,result_load,reuse_store):
    need('literal-owned-inputs',isinstance(path,list)and type(base)is int and type(header_local)is int and 32<=header_local<128)
    indices={ec.va(r):i for i,r in enumerate(path)}
    need('unique-selected-boundaries',len(indices)==len(path))
    for marker in(result_load,reuse_store):
        need('literal-current-marker',isinstance(marker,list)and len(marker)==2 and type(marker[0])is int
            and base+marker[0]in indices and ec.site(path[indices[base+marker[0]]],base)==marker)
    start,end=(indices[base+m[0]]for m in(result_load,reuse_store));load=path[start];store=path[end]
    need('header-result-precedes-replacement',start<end)
    zero=load.get('byteMemoryZeroExtensionOperation',{});address=zero.get('sourceAddress',{})
    need('exact-helper-header-byte-reload',ec.raw(load)==bytes.fromhex('0fb67424')+bytes((header_local,))
        and load['text']==f'movzx esi, byte [rsp+{header_local:#x}]'and zero.get('destinationRegister')=='esi'
        and zero.get('destinationBits')==32 and zero.get('sourceBits')==8 and zero.get('memoryReadBytes')==1
        and zero.get('zeroExtendsTo64')is True and zero.get('writesMemory')is False and zero.get('writesFlags')is False
        and address.get('base')=='rsp'and address.get('index')is None and address.get('displacement')==header_local
        and address.get('ripRelative')is False)
    need('exact-subsequent-low-eight-replacement',ec.raw(store)==bytes.fromhex('f20f114424')+bytes((header_local,))
        and store['text']==f'movsd [rsp+{header_local:#x}], xmm0')
    for row in path[start+1:end]:
        text=row['text']
        need('unchanged-selected-stack-between-header-and-reuse',not text.startswith(('push ','pop ','sub rsp, ','add rsp, ','mov rsp, '))
            and re.fullmatch(r'mov \w+, rsp',text)is None)
        for key,address_key,width_key in(('memoryOperation','address','memoryBytes'),
            ('byteMemoryZeroExtensionOperation','sourceAddress','memoryReadBytes'),
            ('memoryImmediateComparisonOperation','sourceAddress','memoryBytes'),
            ('memoryRegisterComparisonOperation','sourceAddress','memoryBytes')):
            operation=row.get(key,{});address=operation.get(address_key,{})
            if address.get('base')!='rsp':continue
            width=operation.get(width_key)
            if width is None:width=operation.get('bits',0)//8
            need('bounded-ordinary-stack-access',address.get('index')is None and not address.get('ripRelative')
                and type(width)is int and width>0 and type(address.get('displacement'))is int)
            offset=address['displacement'];need('no-intervening-header-memory-access',not offset<=header_local<offset+width)
        lea=re.fullmatch(r'lea \w+, \[rsp\+0x([0-9a-f]+)\]',text)
        need('no-intervening-header-address-escape',lea is None or int(lea[1],16)!=header_local)
    return dict(headerResultLoad=result_load,replacementStore=reuse_store,headerLocalDisplacement=header_local,
        headerBytes=1,replacementBytes=8,headerValueCopiedBeforeReplacement=True,
        noInterveningHeaderMemoryAccess=True,selectedStackStable=True,
        completeIndependentReplacementSourceFlowRequired=True,childGrammarAdmitted=False)
