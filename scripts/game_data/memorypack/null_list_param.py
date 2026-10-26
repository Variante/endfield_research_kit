"""Selected null List constants; the parent keeps its independent typed proof."""
import json
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import scalar_param_native as scalar,utf8_source_helper
from scripts.game_data.memorypack.reference_param import derive_reference_parameter
LABEL='nullListParam'


def derive(image,pins,profile,value_type):
 if not value_type.startswith('System.Collections.Generic.List`1<') or not value_type.endswith('>'):raise ValueError(LABEL+'.listType')
 element=value_type[len('System.Collections.Generic.List`1<'):-1];base=image.pe.image_base;md=image.metadata
 parent,ctx,owned,calls=derive_reference_parameter(image,pins,profile,value_type,reader_method='ReadPackable');at,raw=parent['ownedMethods']['set___path__']['instructions'][7];barrier=at+5+int.from_bytes(bytes.fromhex(raw)[1:],'little',signed=True)
 td=ctx.index.types['MemoryPack.Formatters.ListFormatter`1'];method,=[m for m in md.methods_for(td) if md.string(m.name_index)=='Deserialize'];entry=GenericEntries(image).resolve(method.index,[element],[]);source=owned(entry['pointer'])
 header_target=calls(source)[0];headers=utf8_source_helper._contract();scalar.need(LABEL,'headerNativeInputs',pins,headers['nativeInputs']);scalar.need(LABEL,'selectedCollectionHeader',headers['bodies']['header']['entryRva'],header_target-base);header_proof=utf8_source_helper._validate_native(image,headers)
 null_program=null_list_program(source['regions'],source['pointer'],header_target,base+barrier)
 return json.loads(json.dumps(dict(**parent,listRegistration=entry,listCodeWindows=source['windows'],collectionHeader=header_proof,nullListProgram=null_program,evidenceBoundary=dict(direct='Typed four-member Param and selected reference ReadPackable clone, owned fields/factory/null parent, two Int32 bindings and pooled path; concrete ListFormatter<T> consumes the signed null collection header and writes a null List reference.',conditional='Initialized coherent closed contexts and matching normal generated Param wrapper and ListFormatter<T> route; sufficient contiguous input, disjoint storage and ordinary helper/allocation/barrier ABI.',unresolved=['every nonnull list count and element','live provider default/cache/override selection','cold refill or malformed paths','enclosing owner execution']))))

def null_list_program(regions,entry,header,barrier):
 g=BytesPath(regions,entry)
 if bytes(g.bytes.get(entry+i,0) for i in range(3))==bytes.fromhex('4c8bdc'):
  g.take('4c8bdc','53','55','56','57','4881eca8000000','488bf2','0f57c0','33c0','498d5310','0f11442440','33db','488bce','0f11442450','49894398','498be9','498bf8','41895b10');g.call(header);g.take('84c0');g.branch('75',False,1)
  g.take('488bcf','48891f');g.call(barrier);g.take('4881c4a8000000','5f','5e','5d','5b','c3')
 else:
  g=BytesPath(regions,entry);g.take('4053','55','4154','4157','4883ec48','488bda','33c0','4533e4','4889442420','488bcb','4489642478','488d542478','89442428','498be9','4d8bf8');g.call(header);g.take('84c0');g.branch('0f84',True)
  g.take('498bcf','4d8927');g.call(barrier);g.take('4883c448','415f','415c','5d','5b','c3')
 return dict(selectedBytes=g.seen,wireBytes=4,collectionCount=-1,returnedReference=0)
