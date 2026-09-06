"""Native profile rejects code, usage, MethodSpec and generic-carrier drift."""
import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts.game_data.il2cpp_context import ContextError
from scripts.game_data.il2cpp_context_audit import buff_action_read_order


class BuffEcNativeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'contract.json'
        self.base=0x180000000
        ins=b'\x48\x8b\x15'+struct.pack('<i',0x200-0x100-7)
        usage=struct.pack('<Q',(6<<29)|(2<<1)|1)
        arg=struct.pack('<QII',3,0x120000,0)
        self.parts={self.base+0x10:b'\x48\x89\xd9\xc3',self.base+0x100:ins,
                    self.base+0x200:usage,0x1000+2*12:struct.pack('<iii',7,-1,4)}
        self.argument=SimpleNamespace(raw_type_record_hex=arg.hex().upper(),type_pointer_va=0x3000)
        self.instance=SimpleNamespace(arguments=[self.argument])
        self.table=SimpleNamespace(resolve=lambda index:self.instance if index==4 else None)
        self.pe=SimpleNamespace(image_base=self.base,bytes_at_va=lambda va,n:self.parts[va])
        self.names={3:'Fixture.Nested'}
        self.md=SimpleNamespace(methods=[None]*8,types=list(range(10)),type_full_name=lambda t:self.names[t])
        self.reg={'methodSpecsCount':3,'methodSpecs':'0x1000','genericInstsCount':5}
        self.contract={'schemaVersion':1,'methods':[],
            'codeWindows':[{'startRva':0x10,'endRva':0x14,
                            'sha256':hashlib.sha256(self.parts[self.base+0x10]).hexdigest().upper()}],
            'nestedContexts':[{'instructionRva':0x100,'instructionHex':ins.hex().upper(),
                'cellVa':self.base+0x200,'usageRawHex':usage.hex().upper(),'methodSpecIndex':2,
                'methodSpec':[7,-1,4],'argumentRawHex':arg.hex().upper(),
                'typeDefinition':3,'typeName':'Fixture.Nested','generic':None}],
            'anonymousReadOrder':{'fixture':['byte']},'boundary':'fixture'}

    def decode(self):
        self.path.write_text(json.dumps(self.contract),encoding='utf8')
        with patch('scripts.game_data.il2cpp_context_audit.module_methods',return_value=[]) as methods:
            result=buff_action_read_order(self.pe,self.md,self.reg,self.table,{},[],source='selected.dll',contract_path=self.path)
            methods.assert_called_once_with(self.pe,self.md,{},[],[],source='selected.dll',expected_image='MemoryPack.Beyond.dll')
            return result

    def test_normal_static_context(self):
        row=self.decode()
        self.assertEqual(row['nestedContexts'][0]['typeName'],'Fixture.Nested')
        self.assertEqual(row['contractSha256'],hashlib.sha256(self.path.read_bytes()).hexdigest().upper())

    def test_truncated_trailing_and_corrupt_native_windows(self):
        for va,good in list(self.parts.items()):
            for bad in (good[:-1],good+b'x',bytes(len(good))):
                self.parts[va]=bad
                with self.subTest(va=va,length=len(bad)),self.assertRaises(ContextError) as caught:self.decode()
                d=caught.exception.diagnostics
                self.assertEqual(d['source'],'selected.dll')
                self.assertIn('expected',d);self.assertIn('actual',d);self.assertIn('offset',d)
            self.parts[va]=good

    def test_wrong_native_type_and_argument_count(self):
        self.names[3]='Fixture.Other'
        with self.assertRaises(ContextError):self.decode()
        self.names[3]='Fixture.Nested'
        self.instance.arguments.append(self.argument)
        with self.assertRaises(ContextError):self.decode()

    def test_methodspec_count_gate(self):
        self.reg['methodSpecsCount']=2
        with self.assertRaises(ContextError) as caught:self.decode()
        self.assertEqual(caught.exception.diagnostics['source'],'selected.dll')

    def test_generic_carrier_and_nested_argument_drift(self):
        row=self.contract['nestedContexts'][0]
        arg=struct.pack('<QII',0x4000,0x150000,0)
        cr=struct.pack('<QQQQ',0x5000,0x6000,0,0)
        br=struct.pack('<QII',8,0x120000,0)
        row.update(argumentRawHex=arg.hex().upper(),typeDefinition=8,typeName='Fixture.List',
                   generic={'carrierRawHex':cr.hex().upper(),'baseRawHex':br.hex().upper(),
                            'elementInstantiationIndex':1,'elementArguments':['03000000000000000000120000000000']})
        self.argument.raw_type_record_hex=arg.hex().upper()
        self.parts.update({0x4000:cr,0x5000:br});self.names[8]='Fixture.List'
        nested=SimpleNamespace(index=1,arguments=[SimpleNamespace(raw_type_record_hex=row['generic']['elementArguments'][0])])
        self.table.resolve_pointer=lambda pointer:nested if pointer==0x6000 else None
        self.decode()
        for va in (0x4000,0x5000):
            good=self.parts[va];self.parts[va]=good[:-1]
            with self.assertRaises(ContextError):self.decode()
            self.parts[va]=good
        nested.index=2
        with self.assertRaises(ContextError):self.decode()
        nested.index=1;nested.arguments=[]
        with self.assertRaises(ContextError):self.decode()


if __name__=='__main__':unittest.main()
