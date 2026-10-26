"""Join bit-preserving stored objects/structs to source-named child receipts.

The caller authenticates the native declaration and logical source. Metadata
plans alone never admit a record: every nonnull stored object and headerless
struct matches independent complete ordered fields and every supplied raw value.
"""
from __future__ import annotations
from .stored_plan_values import encode_stored_node


def bind_source_named_tree(receipt: dict, tree: dict) -> dict:
    if not isinstance(receipt,dict) or receipt.get('recursiveStoredSchemaExact') is not True:
        raise ValueError('sourceBoundStoredTree:complete-source-receipt-required')
    objects=[]
    def coordinates(fields):
        if not isinstance(fields,list) or any(not isinstance(field,dict)
                or not isinstance(field.get('fieldName',field.get('name')),str)
                or not field.get('fieldName',field.get('name'))
                or type(field.get('start')) is not int or type(field.get('end')) is not int
                or not 0<=field['start']<field['end']<1<<64 for field in fields):
            raise ValueError('sourceBoundStoredTree:field-coordinates')
        return [(field.get('fieldName',field.get('name')),field['start'],field['end']) for field in fields]
    def nodes(value,depth=0):
        if depth>256:raise ValueError('sourceBoundStoredTree:tree-depth')
        if isinstance(value,dict):
            if (value.get('kind')=='object' and not value.get('null')) or value.get('kind')=='struct':
                coordinates(value.get('members'))
                objects.append(value)
            for child in value.values():nodes(child,depth+1)
        elif isinstance(value,list):
            for child in value:nodes(child,depth+1)
    nodes(tree)
    covered=set();matched=0
    def receipts(value,depth=0):
        nonlocal matched
        if depth>256:raise ValueError('sourceBoundStoredTree:receipt-depth')
        if isinstance(value,dict):
            fields=next((value.get(key) for key in ('namedMembers','namedFields','fields')
                if isinstance(value.get(key),list) and value[key]),None)
            if fields and all(isinstance(field,dict) and ('fieldName' in field or 'name' in field)
                    and 'start' in field and 'end' in field for field in fields):
                expected=coordinates(fields)
                matches=[(index,node) for index,node in enumerate(objects)
                    if [(m['fieldName'],m['start'],m['end']) for m in node['members']]==expected]
                if len(matches)!=1:
                    raise ValueError(f'sourceBoundStoredTree:ordered-field-boundaries:expected=1,actual={len(matches)}')
                index,node=matches[0]
                for field,member in zip(fields,node['members'],strict=True):
                    wire=encode_stored_node(member['value'])
                    raw=field.get('rawHex',field.get('rawBitsHex'))
                    if raw is not None and wire.hex().upper()!=raw.upper():
                        raise ValueError('sourceBoundStoredTree:raw-word-value')
                    if 'rawByte' in field and wire!=bytes((field['rawByte'],)):
                        raise ValueError('sourceBoundStoredTree:raw-byte-value')
                    if 'rawPayloadHex' in field:
                        stored=member['value']
                        payload=None if stored.get('byteLength')==-1 else stored.get('payloadHex')
                        if stored.get('kind')!='string' or payload!=field['rawPayloadHex']:
                            raise ValueError('sourceBoundStoredTree:raw-string-value')
                covered.add(index);matched+=1
            for child in value.values():receipts(child,depth+1)
        elif isinstance(value,list):
            for child in value:receipts(child,depth+1)
    receipts(receipt)
    structs = sum(node['kind'] == 'struct' for node in objects)
    if len(covered)!=len(objects):
        label = 'unbound-stored-records' if structs else 'unbound-stored-objects'
        raise ValueError(f'sourceBoundStoredTree:{label}:expected={len(objects)},actual={len(covered)}')
    return {'status':'all-nonnull-stored-objects-source-field-bound',
        'storedNonNullObjects':len(objects)-structs,'matchedSourceFieldReceipts':matched,
        'metadataOnlyAdmission':False,'runtimeExecutionKnown':False,
        **({'storedHeaderlessStructs': structs} if structs else {})}
