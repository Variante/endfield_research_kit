"""Selected metadata-default source paths; lookup and live globals stay conditional."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def unsigned_conversion(regions,entry,*,image_base):
 g=BytesPath(regions,entry)
 g.take('48895c2408','48896c2418','4889742420','57','4154','4155','4156','4157','4883ec50','8d42fe','498bf1','498bf8','488be9','3dfd000000');g.branch('0f87',False)
 g.take('8d42fe')
 if g.relative('488d0d')!=image_base:raise ValueError('metadataDefault.image-base')
 g.take('4863d0','0fb68411');selectors=int.from_bytes(g.read(4),'little');g.take('8b9481');targets=int.from_bytes(g.read(4),'little');g.take('4803d1','ffe2')
 # Incoming EDX is the ordinary selected UInt32 kind9, hence index7.
 try:index=g.bytes[image_base+selectors+7];target=image_base+int.from_bytes(bytes(g.bytes[image_base+targets+index*4+i]for i in range(4)),'little')
 except KeyError as error:raise ValueError('metadataDefault.unowned-dispatch-table')from error
 g.at=target;g.take('488bcf');reader=g.relative('e8');g.take('8906');g.jump('e9')
 g.take('b001','4c8d5c2450','498b5b30','498b6b40','498b7348','498be3','415f','415e','415d','415c','5f','c3')
 return dict(typeKind=9,selectorRva=selectors,targetTableRva=targets,index=index,target=target,reader=reader,resultBits=32,output='original compressed UInt32 result unchanged',selectedBytes=g.seen,condition='Incoming ordinary kind9; valid stable disjoint cursor/output/frame and normal selected reader return. Other type cases excluded.')


def compressed_uint_f0(regions,entry):
 g=BytesPath(regions,entry)
 g.take('488b01','440fb610','4c8d5801','4c8919','4584d2');g.branch('78',True,1)
 g.take('410fb6c2','24c0','3c80');g.branch('75',True,1)
 g.take('410fb6c2','24e0','3cc0');g.branch('75',True,1)
 g.take('4180faf0');g.branch('75',False,1)
 g.take('418b03','498d5304','488911','c3')
 return dict(prefix=240,payloadBytes=4,byteOrder='little',cursorDelta=5,resultBits=32,selectedBytes=g.seen,condition='Prefix exactlyF0; five valid source bytes, valid disjoint writable cursor storage, no overflow. No other compressed forms admitted by this source model.')


def default_data_pointer(regions,entry):
 proofs=[]
 for absent in(False,True):
  g=BytesPath(regions,entry);g.take('83f9ff');g.branch('75',not absent,1)
  if absent:g.take('33c0','c3')
  else:
   header=g.relative('488b05');g.take('48635048');source=g.relative('480315');g.take('8bc1','4803c2','c3')
  proofs.append(g.seen)
 seen={at+i for rows in proofs for at,raw in rows for i in range(len(bytes.fromhex(raw)))};expected={at+i for at,raw in regions for i in range(len(raw))}
 if seen!=expected:raise ValueError('metadataDefault.complete-data-leaf')
 return dict(headerCell=header,metadataCell=source,sectionOffsetField=72,dataIndexBits=32,nullSentinel=-1,selectedBytes=proofs,condition='Initialized matching metadata/header globals, selected UInt32 data index or null sentinel, valid stable storage and no pointer overflow. Global initialization and record lookup are separate.')


def literal_forward(regions,entry):
 g=BytesPath(regions,entry)
 g.take('48895c2410','4889742418','57','4883ec30','488bf2','488bf9','33db');lookup=g.relative('e8')
 g.take('4c8bc8','4885c0');g.branch('74',False,1)
 g.take('4c634004','4183f8ff');g.branch('74',False,1)
 registration=g.relative('488b05');g.take('488b4838','4a8b1cc1','418b4908');data=g.relative('e8')
 g.take('488b4f10','4c8d442440','0fbe530a','4c8bce','4889442440','c644242001','488b09');convert=g.relative('e8')
 g.take('488b5c2448','488b742450','4883c430','5f','c3')
 return dict(lookup=lookup,data=data,convert=convert,registrationCell=registration,typeTableOffset=56,defaultTypeIndexOffset=4,defaultDataIndexOffset=8,typeKindOffset=10,selectedBytes=g.seen,condition='The selected metadata field lookup returns its existing default record with nonnegative type/data indexes; initialized matching registration/header globals and owner, original ordinary UInt32 type; valid disjoint output/frame and normal ABI-preserving callees. Lookup/initialization/live object selection remain unproved.')


def literal_export(regions,entry):
 g=BytesPath(regions,entry)
 g.take('48895c2410','48896c2418','56','57','4154','4156','4157','4883ec20','488bfa','488be9','488b4910');initialize=g.relative('e8')
 g.take('33f6','448bf6','837d18ff');g.branch('75',True,1)
 g.take('488b4508','f6400840');g.branch('74',False,1)
 g.take('488bd7','488bcd');literal=g.relative('e8');g.jump('e9')
 g.take('488b5c2458','488b6c2460','4883c420','415f','415e','415c','5f','5e','c3')
 return dict(initialize=initialize,literal=literal,literalAttributeMask=64,typePointerOffset=8,selectedBytes=g.seen,condition='Original selected FieldInfo, normal owner initialization, field offset not thread-static sentinel, literal flag set. Other class/field branches and runtime lookup are excluded.')
