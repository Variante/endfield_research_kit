"""MC4/FF Param and raw unsigned64 elements under its own fresh source gate."""
import struct
from scripts.game_data.levelscript_positive_ulong_lists_native import validate
from scripts.game_data.memorypack.operation_native_validation import validate_native
from scripts.game_data.string_pool import resolve_string_pool_index


def decode_param(data,offset,*,strings=None,game_root=None):
 audit=validate_native(validate,game_root=game_root)
 expected=dict(status='validated',codecKind='Param<List<ulong>>',memberCount=4,countLimit=4096,wireCountBytes=4,
  elementWireBytes=8,elementEncoding='raw-uint64',initiallyNullListProved=True,pathEncoding='int32-pool-index',positiveCountsAdmitted=True)
 if any(type(audit.get(k))is not type(v)or audit.get(k)!=v for k,v in expected.items()):
  raise ValueError('positiveUlongList.native:status='+str(audit.get('status'))+',detail='+str(audit.get('detail',''))[:500])
 if type(offset)is not int or not 0<=offset<len(data):raise ValueError('positiveUlongList.Param:truncated')
 marker=data[offset];offset+=1
 if marker==255:return None,offset
 if marker!=4:raise ValueError('positiveUlongList.Param:member-count='+str(marker))
 if offset>len(data)-4:raise ValueError('positiveUlongList.count:truncated')
 count,=struct.unpack_from('<i',data,offset);offset+=4
 if count < -1 or count>audit['countLimit']:raise ValueError('positiveUlongList.count:unproved='+str(count))
 if count>(len(data)-offset-12)//8:raise ValueError('positiveUlongList.elements-or-tail:truncated')
 value=None if count==-1 else[struct.unpack_from('<Q',data,offset+8*i)[0]for i in range(count)]
 offset+=8*max(count,0)
 if offset>len(data)-12:raise ValueError('positiveUlongList.Param:tail-truncated')
 id_ref,param_source,index=struct.unpack_from('<iii',data,offset)
 path=resolve_string_pool_index(index,strings,'positiveUlongList.Param.path')
 return dict(value=value,idRef=id_ref,paramSource=param_source,path=path),offset+12
