"""Selected native declarations behind reviewed self-describing JSON schemas.

JSON names, value shapes and cross-field relations are checked independently
by the named schema reader. This lane authenticates their declared native
types and inheritance; it does not infer a live consumer from a file name.
"""
from __future__ import annotations

import json
import struct
from pathlib import Path

from scripts.common import check_installed_native_inputs, resolve_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.memorypack.wrapper_members import _Deriver
from scripts.game_data.memorypack.derived_schema import _split_generic_arguments
from scripts.game_data.il2cpp.protocol import field_defaults, native_enum_members

CONTRACT_PATH=CONTRACTS_DIR/'jsondata_text_native.json'
SCHEMA='endfield.jsondata-text-native-declarations.v1'
INTEGER_TYPES={'byte':(0,255),'sbyte':(-128,127),'short':(-32768,32767),'ushort':(0,65535),
               'int':(-(1<<31),(1<<31)-1),'uint':(0,(1<<32)-1),
               'long':(-(1<<63),(1<<63)-1),'ulong':(0,(1<<64)-1)}
DICTIONARIES=('System.Collections.Generic.Dictionary`2','Beyond.SerializeFieldDictionary`2')


def need(check,condition,detail=''):
    if not condition:raise ValueError('jsondataTextNative.'+check+':'+str(detail)[:1000])


class NativeJsonTypes:
    def __init__(self,image,contract=None):
        self.image=image;self.md=image.metadata;self.deriver=_Deriver(image)
        self.contract=contract;self.used={};self.enums={};self._defaults=None

    def declaration(self,name):
        if name in self.used:return self.used[name]
        types=self.image.named_type_definitions.get(name,())
        need('one-selected-native-type',len(types)==1,name);td=types[0]
        parent=self.deriver._declared_type_name(td.parent_index)
        fields=[]
        for f in self.md.fields_for(td):
            attrs=self.deriver._field_attributes(f.type_index)
            need('native-field-attributes',attrs is not None,(name,f.index))
            if attrs&16:continue
            fields.append(dict(name=self.md.string(f.name_index),type=self.deriver._declared_type_name(f.type_index)))
        properties=[]
        for m in self.md.methods_for(td):
            n=self.md.string(m.name_index)
            if n.startswith('get_')and m.parameter_count==0 and not m.flags&16:
                properties.append(dict(name=n[4:],type=self.deriver._declared_type_name(m.return_type),
                                       getter=[m.index,name,n]))
        interfaces=[]
        if td.interfaces_count:
            start=self.md.sections['interfaces'].offset+td.interfaces_start*4
            for i in range(td.interfaces_count):
                index=struct.unpack_from('<i',self.md.buf,start+i*4)[0]
                interfaces.append(self.deriver._declared_type_name(index))
        result=dict(typeName=name,typeDefinition=td.index,parent=parent,interfaces=interfaces,fields=fields,properties=properties)
        if self.contract is not None:
            need('reviewed-selected-native-declaration',self.contract['declarations'].get(name)==result,name)
        self.used[name]=result
        return result

    def members(self,name,stack=()):
        need('acyclic-native-parent',name not in stack,name)
        row=self.declaration(name);members={}
        if row['parent'] not in (None,'object','System.ValueType','System.Enum'):
            members.update(self.members(row['parent'],(*stack,name)))
        members.update({f['name']:f['type']for f in row['fields']})
        for p in row['properties']:members.setdefault(p['name'],p['type'])
        return members

    def enum(self,name):
        if name not in self.enums:
            row=self.declaration(name);need('enum-parent',row['parent']=='System.Enum',name)
            if self._defaults is None:self._defaults=field_defaults(self.md)
            self.enums[name]={r['name']:r['id']for r in native_enum_members(self.md,self._defaults,
                self.image.pe,self.image.registration,name)}
        return self.enums[name]

    def dictionary(self,name):
        if '<'in name:
            head,args=name.split('<',1)
            if head in DICTIONARIES:
                parts=_split_generic_arguments(args[:-1]);need('dictionary-two-type-arguments',len(parts)==2,name)
                return tuple(parts)
        if name in self.image.named_type_definitions:
            parent=self.declaration(name)['parent']
            if parent and any(parent.startswith(p+'<')for p in DICTIONARIES):return self.dictionary(parent)
        return None

    def key(self,key,kind,path):
        need('JSON-dictionary-string-key',type(key)is str,path)
        if kind=='string':return
        if kind in INTEGER_TYPES:
            need('integer-dictionary-key-spelling',key=='0'or key.lstrip('-').isdigit()and not key.lstrip('-').startswith('0'),(path,key))
            value=int(key);low,high=INTEGER_TYPES[kind];need('integer-dictionary-key-range',low<=value<=high,(path,key));return
        need('native-enum-dictionary-key',key in self.enum(kind),(path,kind,key))

    def validate(self,value,name,path='$',depth=0):
        need('bounded-JSON-native-depth',depth<=128,path)
        if value is None:
            nullable=name=='string'or name.endswith('[]')or name.startswith(('System.Collections.Generic.List`1<',*tuple(p+'<'for p in DICTIONARIES)))
            if not nullable and name not in (*INTEGER_TYPES,'float','double','bool'):
                nullable=self.declaration(name)['parent']not in('System.ValueType','System.Enum')
            need('nullable-native-JSON-value',nullable,(path,name));return
        if name=='string':need('native-string',type(value)is str,(path,name));return
        if name=='bool':need('native-Boolean',type(value)is bool,(path,name));return
        if name in INTEGER_TYPES:
            low,high=INTEGER_TYPES[name];need('native-integer-range',type(value)is int and low<=value<=high,(path,name,value));return
        if name in ('float','double'):
            import math
            need('native-finite-number',type(value)in(int,float)and math.isfinite(value),(path,name,value));return
        if name.endswith('[]'):
            need('native-array',type(value)is list,(path,name))
            for i,v in enumerate(value):self.validate(v,name[:-2],f'{path}[{i}]',depth+1)
            return
        if name.startswith('System.Collections.Generic.List`1<'):
            return self.validate(value,name[len('System.Collections.Generic.List`1<'):-1]+'[]',path,depth)
        if name=='UnityEngine.AnimationCurve':
            # The reviewed textual codec stores keyframe property words. The
            # named schema owns their exact JSON field set and scalar shapes.
            return self.validate(value,'UnityEngine.Keyframe[]',path,depth+1)
        dictionary=self.dictionary(name)
        if dictionary is not None:
            need('native-dictionary-object',type(value)is dict,(path,name))
            for k,v in value.items():
                self.key(k,dictionary[0],path);self.validate(v,dictionary[1],f'{path}[{k!r}]',depth+1)
            return
        declaration=self.declaration(name)
        if declaration['parent']and declaration['parent'].startswith('System.Collections.Generic.List`1<'):
            return self.validate(value,declaration['parent'],path,depth+1)
        if declaration['parent']=='System.Enum':
            fields=declaration['fields'];need('one-native-enum-backing',len(fields)==1 and fields[0]['name']=='value__',name)
            return self.validate(value,fields[0]['type'],path,depth+1)
        need('native-record-object',type(value)is dict,(path,name))
        tag=value.get('$type')
        if tag is not None:
            need('native-tag-string',type(tag)is str,path)
            concrete=tag.split(',',1)[0];lineage=[];pending=[concrete]
            while pending:
                cursor=pending.pop()
                if cursor in (None,'object')or cursor in lineage:continue
                lineage.append(cursor);decl=self.declaration(cursor)
                pending.extend([decl['parent'],*decl['interfaces']])
            need('native-tagged-assignability',name in lineage,(path,name,concrete));name=concrete
        members=self.members(name)
        for key,child in value.items():
            if key=='$type':continue
            need('JSON-field-has-native-declaration',key in members,(path,name,key))
            self.validate(child,members[key],path+'.'+key,depth+1)


def validate_text_native(root,relative,*,game_root=None):
    contract=json.loads(CONTRACT_PATH.read_bytes())
    need('reviewed-contract',contract.get('schema')==SCHEMA and contract.get('status')=='reviewed')
    name=contract['roots'].get(relative)
    if name is None:return None
    from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs
    from scripts.game_data.memorypack.pooled_source_helper import check_unity_input
    before=snapshot_complete_reader_inputs()
    if game_root is not None:
        root_path=Path(game_root).resolve();assembly=root_path.parent/'GameAssembly.dll'
        metadata=root_path/'il2cpp_data/Metadata/global-metadata.dat'
    else:assembly,metadata=resolve_installed_native_inputs()
    pins=contract['nativeInputs']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],
        gameassembly=assembly,metadata=metadata)
    need('selected-native-pair',gate.status=='validated',gate.detail)
    need('selected-Unity-input',check_unity_input(assembly,pins)is None)
    image=open_native_image(assembly,metadata);types=NativeJsonTypes(image,contract)
    types.validate(root,name)
    claims=[]
    if 'UnityEngine.Keyframe'in types.used:
        from scripts.game_data.il2cpp.body_claims import BodyIndex,evaluate
        claims,failures=evaluate(BodyIndex(image),contract['methods'])
        need('native-keyframe-JSON-converter-claims',not failures,failures)
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],
        gameassembly=assembly,metadata=metadata)
    need('selected-native-pair-exit',after.status=='validated',after.detail)
    need('selected-Unity-input-exit',check_unity_input(assembly,pins)is None)
    need('complete-reader-source-exit',before==snapshot_complete_reader_inputs())
    return dict(status='validated',declarationsChecked=len(types.used),converterClaims=claims,
                evidenceBoundary='direct native declaration and assignability; exact JSON shape is independently reviewed; no runtime consumption claim')
