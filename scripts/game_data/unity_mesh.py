"""Stored Endfield Mesh framing and bounded render vertex/index projections."""
import base64
import math
import struct

from scripts.game_data.unity_type_tree import decode_object


def decode_mesh(nodes,raw):
    if not nodes or nodes[0]['type']!='Mesh':raise ValueError('Endfield Mesh requires a Mesh type-tree root')
    # The Endfield dedicated reader and generic TypeTreeHelper both select this
    # branch from the preceding raw boolean. Never borrow the flag from JSON.
    return decode_object(nodes,raw,omit_when={'m_CompressedMesh':('m_CollisionMeshBaked','bool',True)})


def _bytes(value):
    if isinstance(value,str):return base64.b64decode(value,validate=True)
    if isinstance(value,list) and all(type(v)==int and 0<=v<=255 for v in value):return bytes(value)
    raise ValueError('Mesh byte buffer is neither declared bytes nor base64')


def packed_normal(packed):
    """Decode Endfield's selected signed-10 octahedral normal direction.

    Tangent angle and handedness remain retained in the source packed word;
    this surface projection does not reconstruct a runtime tangent frame.
    """
    if not packed&0x40000000:raise ValueError('Endfield packed normal lacks the bit-30 selector')
    def signed10(shift):
        value=(packed>>shift)&1023
        return value-1024 if value>=512 else value
    x,y=signed10(0)/511.,signed10(10)/511.;z=1.-abs(x)-abs(y)
    if z<0:
        x,y=(1.-abs(y))*(1. if x>=0 else -1.),(1.-abs(x))*(1. if y>=0 else -1.)
    length=math.sqrt(x*x+y*y+z*z)
    if not math.isfinite(length) or length==0:raise ValueError('Endfield packed normal has invalid length')
    return (x/length,y/length,z/length)


def read_surface(body,stream_bytes=None):
    """Project complete stored triangle submeshes; preserve material slot ranges.

    Position/normal/UV channels follow the declared uncompressed vertex streams.
    Coordinates remain Unity source coordinates. Packed compression and other
    topologies stay explicit unsupported cases, not empty successful surfaces.
    """
    vertex_data=body['m_VertexData'];count=vertex_data['m_VertexCount']
    if type(count)!=int or count<=0:raise ValueError('Mesh has no stored render vertices')
    if body['m_MeshCompression']!=0:raise ValueError('packed Mesh compression is outside this surface reader')
    data=_bytes(vertex_data['m_DataSize']);descriptor=body['m_StreamData']
    if descriptor['size']:
        if stream_bytes is None or len(stream_bytes)!=descriptor['size']:raise ValueError('Mesh owner archive vertex span is unavailable or incomplete')
        data=stream_bytes
    channels=vertex_data['m_Channels']
    if len(channels)!=14:raise ValueError(f'Mesh vertex channel count differs: {len(channels)}/14')
    # Unity 2021+ serialized VertexFormat; the Mesh helper uses these same
    # widths and normalizations. Unknown format values never select a width.
    formats={0:('f',4,None),1:('e',2,None),2:('B',1,255),3:('b',1,127),
             4:('H',2,65535),5:('h',2,32767),6:('B',1,None),7:('b',1,None),
             8:('H',2,None),9:('h',2,None),10:('I',4,None),11:('i',4,None)}
    streams={}
    for channel in channels:
        dimension=channel['dimension']&15
        if not dimension:continue
        if not 1<=dimension<=4 or channel['format'] not in formats or not 0<=channel['stream']<=31:
            raise ValueError('Mesh active vertex channel dimension/format/stream is unsupported')
        _,width,_=formats[channel['format']]
        start,end=channel['offset'],channel['offset']+dimension*width
        spans=streams.setdefault(channel['stream'],[])
        if start<0 or any(a<end and start<b for a,b in spans):raise ValueError('Mesh vertex channels overlap within a stream')
        spans.append((start,end))
    if not streams or set(streams)!=set(range(max(streams)+1)):raise ValueError('Mesh active streams have a gap')
    bases={};offset=0;strides={}
    for stream,spans in sorted(streams.items()):
        spans.sort();stride=sum(b-a for a,b in spans)
        if spans[0][0]!=0 or spans[-1][1]!=stride:raise ValueError('Mesh vertex stream has undeclared channel padding')
        bases[stream]=offset;strides[stream]=stride
        end=offset+count*stride
        if end>len(data):raise ValueError('Mesh vertex stream exceeds complete buffer')
        offset=(end+15)&~15
    tail=data[end:]
    if len(tail)>15 or any(tail):raise ValueError('Mesh vertex buffer has an unaccounted tail')

    def vectors(index,min_dimension):
        channel=channels[index];dimension=channel['dimension']&15
        if dimension==0:return None
        if dimension<min_dimension:raise ValueError(f'Mesh channel {index} lacks required dimensions')
        fmt,width,normalizer=formats[channel['format']];stream=channel['stream']
        start=bases[stream]+channel['offset'];stride=strides[stream];values=[]
        for vertex in range(count):
            row=struct.unpack_from('<'+fmt*dimension,data,start+vertex*stride)
            if normalizer:row=tuple(max(-1.,v/normalizer) for v in row)
            if not all(math.isfinite(v) for v in row):raise ValueError(f'Mesh channel {index} contains non-finite coordinates')
            values.append(tuple(row[:min_dimension]))
        return values

    positions=vectors(0,3)
    if positions is None:raise ValueError('Mesh position channel is absent')
    normal=channels[1]
    if normal['dimension']==0x31:
        if normal['format']!=0:raise ValueError('Endfield packed normal requires Float-format storage')
        stream=normal['stream'];start=bases[stream]+normal['offset'];stride=strides[stream]
        normals=[packed_normal(struct.unpack_from('<I',data,start+i*stride)[0]) for i in range(count)]
    else:
        normals=vectors(1,3)
    uv0=vectors(4,2);uv1=vectors(5,2)
    indices=_bytes(body['m_IndexBuffer']);index_format=body['m_IndexFormat']
    if index_format not in (0,1):raise ValueError('Mesh index format is unsupported')
    width=2 if index_format==0 else 4;fmt='H' if width==2 else 'I'
    if len(indices)%width:raise ValueError('Mesh index buffer is not aligned to its declared format')
    submeshes=[];ranges=[]
    for slot,sub in enumerate(body['m_SubMeshes']):
        start=sub['firstByte'];length=sub['indexCount']*width
        if (sub['topology']!=0 or sub['indexCount']%3 or start%width or start<0 or start+length>len(indices)):
            raise ValueError(f'Mesh submesh {slot} topology/index range is unsupported or invalid')
        if any(a<start+length and start<b for a,b in ranges):raise ValueError('Mesh submesh index ranges overlap')
        ranges.append((start,start+length));faces=[]
        for at in range(start,start+length,width*3):
            face=tuple(i+sub['baseVertex'] for i in struct.unpack_from('<'+fmt*3,indices,at))
            if any(i<0 or i>=count for i in face):raise ValueError(f'Mesh submesh {slot} index exceeds vertex buffer')
            faces.append(face)
        submeshes.append(dict(slot=slot,faces=faces))
    if not any(s['faces'] for s in submeshes):raise ValueError('Mesh has no stored triangle faces')
    return dict(vertices=positions,normals=normals,uv0=uv0,uv1=uv1,submeshes=submeshes,
                vertexCount=count,triangleCount=sum(len(s['faces']) for s in submeshes),
                evidenceBoundary='Complete selected uncompressed vertex/resource and triangle submesh buffers in Unity source coordinates. Stored UV0/UV1 are retained separately; runtime transforms, vertex streams, deformation and material/shader selection remain unresolved.')
