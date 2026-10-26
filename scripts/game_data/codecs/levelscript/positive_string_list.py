"""Bounded pooled STRING lists; literal and MC4 Param framing remain distinct."""
import struct
from scripts.game_data.levelscript_positive_string_lists_native import validate
from scripts.game_data.memorypack.operation_native_validation import validate_native
from scripts.game_data.string_pool import resolve_string_pool_index


def _audit(kind,root):
 audit=validate_native(validate,codec_kind=kind,game_root=root)
 expected=dict(status='validated',codecKind=kind,countLimit=4096,wireCountBytes=4,
  elementWireBytes=4,stringEncoding='int32-pool-index',positiveCountsAdmitted=True)
 if any(type(audit.get(k))is not type(v)or audit.get(k)!=v for k,v in expected.items()):
  raise ValueError('positiveStringList.native:status='+str(audit.get('status'))+',detail='+str(audit.get('detail',''))[:500])
 return audit


def _list(data,offset,strings,limit):
 if type(offset)is not int or not 0<=offset<=len(data)-4:raise ValueError('positiveStringList.count:truncated')
 count,=struct.unpack_from('<i',data,offset);offset+=4
 if count < -1 or count>limit:raise ValueError('positiveStringList.count:unproved='+str(count))
 if count==-1:return None,offset
 if count>(len(data)-offset)//4:raise ValueError('positiveStringList.elements:truncated')
 values=[resolve_string_pool_index(struct.unpack_from('<i',data,offset+4*i)[0],strings,f'stringList[{i}]')for i in range(count)]
 return values,offset+4*count


def decode_literal(data,offset,*,strings=None,game_root=None):
 audit=_audit('List<string>',game_root)
 return _list(data,offset,strings,audit['countLimit'])


def decode_param(data,offset,*,strings=None,game_root=None):
 audit=_audit('Param<List<string>>',game_root)
 if type(offset)is not int or not 0<=offset<len(data):raise ValueError('positiveStringList.Param:truncated')
 marker=data[offset];offset+=1
 if marker==255:return None,offset
 if marker!=4:raise ValueError('positiveStringList.Param:member-count='+str(marker))
 value,offset=_list(data,offset,strings,audit['countLimit'])
 if offset>len(data)-12:raise ValueError('positiveStringList.Param:tail-truncated')
 id_ref,param_source,index=struct.unpack_from('<iii',data,offset)
 path=resolve_string_pool_index(index,strings,'positiveStringList.Param.path')
 return dict(value=value,idRef=id_ref,paramSource=param_source,path=path),offset+12
