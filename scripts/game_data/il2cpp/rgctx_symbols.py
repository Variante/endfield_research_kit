"""Decode static RGCTX symbols without substituting runtime generic arguments.

The caller authenticates the NativeImage. Reciprocal parameter ownership and
referenced declarations are checked; initialized runtime slots are not observed.
"""
from __future__ import annotations

from .context import method_parameter_owner, type_parameter_owner, method_spec_record, select_rgctx_range, rgctx_range_entries
from .protocol import runtime_type_name


class ContextSymbols:
    def __init__(self, image):
        self.image = image
        self.type_containers = [t.generic_container_index for t in image.metadata.types]
        self.method_containers = [m.generic_container_index for m in image.metadata.methods]

    def type(self, pointer, trail=()):
        image = self.image; pe = image.pe; md = image.metadata
        if pointer in trail or len(trail) >= 16:raise ValueError('rgctxSymbol.type: cyclic or excessive nesting')
        raw = pe.bytes_at_va(pointer,16)
        if len(raw)!=16:raise ValueError('rgctxSymbol.type: incomplete native record')
        result = {'name':runtime_type_name(pe,md,pointer),'typePointerVa':pointer,'rawHex':raw.hex().upper()}
        kind = raw[10]; index = int.from_bytes(raw[:8],'little')
        if kind in (0x13,0x1e):
            owner = (type_parameter_owner if kind==0x13 else method_parameter_owner)(md.buf,index,
                self.type_containers if kind==0x13 else self.method_containers,source=str(image.metadata_path))
            definition = md.methods[owner['methodIndex']].declaring_type if kind==0x1e else owner['typeIndex']
            owner['typeName'] = image.type_name(definition)
            if kind==0x1e:owner['methodName'] = md.string(md.methods[owner['methodIndex']].name_index)
            result['parameterOwner'] = owner
        elif kind==0x15:
            definition = pe.u64_at_va(index)
            instance = image.instantiations.resolve_pointer(pe.u64_at_va(index+8))
            result['definition'] = {'name':runtime_type_name(pe,md,definition),'typePointerVa':definition,
                                    'rawHex':pe.bytes_at_va(definition,16).hex().upper()}
            result['classInstantiationIndex'] = instance.index
            result['classArguments'] = [self.type(a.type_pointer_va,(*trail,pointer)) for a in instance.arguments]
        return result

    def arguments(self, index):
        return [] if index<0 else [self.type(a.type_pointer_va) for a in self.image.instantiations.resolve(index).arguments]

    def context(self, definition, *, is_method=False):
        image = self.image; pe = image.pe; md = image.metadata
        owners = md.methods if is_method else md.types
        if type(is_method) is not bool or type(definition) is not int or not 0<=definition<len(owners):raise ValueError('rgctxSymbol.owner: invalid owner kind or index')
        owner = owners[definition]; type_index = owner.declaring_type if is_method else definition
        image_name = md.string(md.images[image.owners[type_index]].name_index); module = image.modules[image_name]
        range_count,entry_count = pe.u32_at_va(module+0x40),pe.u32_at_va(module+0x50)
        if not 0<=range_count<=1_000_000 or not 0<=entry_count<=1_000_000:raise ValueError('rgctxSymbol.module: unbounded directory')
        ranges,entries = pe.u64_at_va(module+0x48),pe.u64_at_va(module+0x58)
        start,count = select_rgctx_range(pe.bytes_at_va(ranges,range_count*12),entry_count,owner.token,source=str(image.gameassembly),offset=ranges)
        result = {'definition':definition,'isMethod':is_method,'token':owner.token,'image':image_name,
                  'typeName':image.type_name(type_index),'methodName':md.string(owner.name_index) if is_method else None,
                  'start':start,'count':count,'entries':[]}
        raw = pe.bytes_at_va(entries+start*16,count*16)
        decoded = rgctx_range_entries(raw,0,count,source=str(image.gameassembly),offset=entries+start*16)
        for item in decoded:
            kind = item['kindRaw']; index = pe.u32_at_va(item['dataPointerVa'])
            if item['opaquePaddingHex']!='00000000' or kind not in (1,2,3):raise ValueError('rgctxSymbol.entry: unsupported kind or padding')
            row = {'relativeSlot':item['relativeIndex'],'moduleEntryIndex':start+item['relativeIndex'],
                   'entryVa':item['entryVa'],'rawHex':item['rawHex'],'kind':kind,'index':index}
            if kind in (1,2):
                if not 0<=index<image.registration['typesCount']:raise ValueError('rgctxSymbol.type: index outside selected table')
                pointer = pe.u64_at_va(int(image.registration['types'],16)+index*8)
                row['type'] = self.type(pointer); row['typeName'] = row['type']['name']
            else:
                if not 0<=index<image.registration['methodSpecsCount']:raise ValueError('rgctxSymbol.method: index outside selected table')
                address = int(image.registration['methodSpecs'],16)+index*12
                spec = method_spec_record(pe.bytes_at_va(address,12),len(md.methods),image.registration['genericInstsCount'],source=str(image.gameassembly),offset=address)
                method = md.methods[spec[0]]
                row.update(methodSpec=list(spec),typeName=image.type_name(method.declaring_type),methodName=md.string(method.name_index),
                           classArguments=self.arguments(spec[1]),methodArguments=self.arguments(spec[2]))
            result['entries'].append(row)
        return result


def validate_claims(expected, actual, *, label):
    """Authenticate every declared symbol, while permitting narrower fact rows."""
    if isinstance(expected,dict):
        if not isinstance(actual,dict):raise ValueError(f'{label}: expected object')
        for key,value in expected.items():
            if key not in actual:raise ValueError(f'{label}.{key}: unknown symbol claim')
            validate_claims(value,actual[key],label=label+'.'+key)
    elif isinstance(expected,list):
        if not isinstance(actual,list) or len(expected)!=len(actual):
            size=len(actual) if isinstance(actual,(list,tuple,dict,str,bytes)) else 'unavailable'
            raise ValueError(f'{label}: incomplete symbol sequence: expected=list(length={len(expected)}) actual={type(actual).__name__}(length={size})')
        for index,(left,right) in enumerate(zip(expected,actual)):validate_claims(left,right,label=f'{label}[{index}]')
    elif type(expected) is not type(actual) or expected!=actual:
        raise ValueError(f'{label}: expected={str(expected)[:200]} actual={str(actual)[:200]}')
