"""Conditional face evidence under stored or repeatedly observed current poses.

Callers own capture/native/source authentication. Stored creation poses and
separately timed current poses keep their own conditions; numerical comparisons
do not recover a geometry pointer, prove lifetime or classify solver contacts.
"""
from __future__ import annotations

import math
import struct


def _vector(value, width):
    if len(value) != width or any(type(x) not in (int,float) or not math.isfinite(x) for x in value):
        raise ValueError('collision geometry finite vector width:' + str(width))
    return tuple(value)


def _sub(a,b):return tuple(x-y for x,y in zip(a,b))
def _dot(a,b):return sum(x*y for x,y in zip(a,b))
def _cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])


def _rotate(v,q):
    uv=_cross(q[:3],v);uuv=_cross(q[:3],uv)
    return tuple(v[i]+2*(q[3]*uv[i]+uuv[i]) for i in range(3))


def world_vertices(vertices, descriptor, actor):
    """Apply recorded local scale/rotation/translation, then the source actor pose.

    Zero scale or a nonunit quaternion leaves this comparison unavailable.
    No source value is silently normalized, clamped or filled from runtime data.
    """
    scale=_vector(descriptor['scale'],3)
    local_rotation=_vector(descriptor.get('rotation',(0,0,0,1)),4)
    local_position=_vector(descriptor.get('position',(0,0,0)),3)
    actor_rotation=_vector(actor['rotation'],4);actor_position=_vector(actor['position'],3)
    if any(x==0 for x in scale) or any(abs(_dot(q,q)-1)>1e-5 for q in (local_rotation,actor_rotation)):
        raise ValueError('collision geometry unavailable source pose:zero scale/nonunit quaternion')
    result=[]
    for value in vertices:
        v=_vector(value,3)
        local=_rotate(tuple(v[i]*scale[i] for i in range(3)),local_rotation)
        local=tuple(local[i]+local_position[i] for i in range(3))
        world=_rotate(local,actor_rotation)
        result.append(tuple(world[i]+actor_position[i] for i in range(3)))
    return result


def face_metrics(mesh, vertices, hit):
    """Keep all remap aliases and report plane/normal/barycentric measurements."""
    face_id=hit['faceId'];point=_vector(hit['point'],3);observed=_vector(hit['normal'],3)
    if type(face_id) is not int or not 0<=face_id<1<<32:
        raise ValueError('collision geometry face ID width')
    remap=mesh.metadata['faceRemap']
    faces=[i for i,value in enumerate(remap) if value==face_id] if remap else [face_id]
    results=[]
    for face in faces:
        if not 0<=face<len(mesh.geometry.triangles):continue
        a,b,c=(_vector(vertices[i],3) for i in mesh.geometry.triangles[face])
        ab,ac=_sub(b,a),_sub(c,a);normal=_cross(ab,ac)
        length=math.sqrt(_dot(normal,normal));observed_length=math.sqrt(_dot(observed,observed))
        aa,cc,bb=_dot(ab,ab),_dot(ac,ac),_dot(ab,ac);den=aa*cc-bb*bb
        if length==0 or observed_length==0 or den<=0:
            results.append(dict(cookedFace=face,status='degenerate_face_or_normal'));continue
        normal=tuple(v/length for v in normal);p=_sub(point,a)
        u=(cc*_dot(p,ab)-bb*_dot(p,ac))/den;v=(aa*_dot(p,ac)-bb*_dot(p,ab))/den
        results.append(dict(cookedFace=face,status='conditional_face_metrics',planeDistance=_dot(p,normal),
                            normalDot=_dot(normal,observed)/observed_length,barycentric=[1-u-v,u,v]))
    return results


def source_surface_evidence(mesh, projection, slots, hit, scale_hex, *, vertex_cache=None, cache_key=None, point_eligible=True):
    """Retain each aliased source pose and its numerical face measurements."""
    actor = {name: projection[name] for name in ('position', 'rotation')}
    candidates = []
    for descriptor in projection['records']:
        if descriptor.get('meshSlot') not in slots or descriptor['kind'] not in ('mesh', 'triangleMesh'):
            continue
        row = dict(meshSlot=descriptor['meshSlot'], offset=descriptor['offset'],
                   scaleBitsMatch=struct.pack('<3f', *descriptor['scale']).hex() == scale_hex)
        if not point_eligible:
            row.update(status='unavailable_zero_distance_sweep_point',faceMetrics=[])
            candidates.append(row)
            continue
        key = (cache_key, descriptor['offset'])
        try:
            vertices = vertex_cache.get(key) if vertex_cache is not None else None
            if vertices is None:
                vertices = world_vertices(mesh.geometry.vertices, descriptor, actor)
                if vertex_cache is not None:
                    vertex_cache[key] = vertices
            row['faceMetrics'] = face_metrics(mesh, vertices, hit)
            row['status'] = 'conditional_source_surface' if row['faceMetrics'] else 'face_not_in_stored_remap'
        except ValueError as error:
            row.update(status='unavailable_source_pose', diagnostic=str(error))
        candidates.append(row)
    return dict(actorSourcePose=actor, candidates=candidates,
                queryPointEligibility='positive_distance_or_non_sweep' if point_eligible else 'zero_distance_sweep_needs_native_validity_flags',
                boundary='conditional: complete stored geometry transformed by observed creation-source poses. Numerical agreement is not current shape pose, attachment history, runtime array equality or solver contact.')


def current_surface_evidence(mesh, pose, hit, scale, scale_rotation, native_hit, *, point_eligible=True):
    """Compare stored faces under repeated current poses; keep timing conditions."""
    result=dict(status='unavailable_current_pose',faceMetrics=[],
                boundary='conditional numerical surface comparison using separately timed repeated current actor/shape poses and original getter scale; no atomic query snapshot, continuous lifetime or solver-contact claim')
    native_face=native_hit['nativeFaceIndex'] if native_hit and native_hit['stableInput'] and native_hit['outputConsumedFieldsEqual'] else None
    remap=mesh.metadata['faceRemap'];expected=remap[native_face] if native_face is not None and 0<=native_face<len(remap) else native_face if not remap else None
    result.update(nativeFaceIndex=native_face,storedFaceRemapEqualsConvertedFace=expected==hit['faceId'] if expected is not None else None,
                  faceRemapBoundary='original native face index and converted face field versus authenticated stored remap, independent of point validity')
    if not pose or not pose['validatedCurrentPose']:return result
    if not point_eligible:
        result['status']='unavailable_nonpositive_distance_sweep_point';return result
    if tuple(_vector(scale_rotation,4))!=(0.,0.,0.,1.):
        result['status']='unavailable_nonidentity_mesh_scale_orientation';return result
    p=pose['after']
    actor=dict(position=p['actorPosition'],rotation=p['actorRotation'])
    shape=dict(position=p['shapePosition'],rotation=p['shapeRotation'],scale=scale)
    try:
        vertices=world_vertices(mesh.geometry.vertices,shape,actor)
        metrics=face_metrics(mesh,vertices,hit)
    except ValueError as error:
        result.update(status='unavailable_current_transform',diagnostic=str(error));return result
    result.update(status='conditional_current_surface' if metrics else 'face_not_in_stored_remap',
                  faceMetrics=metrics,actorCurrentPose=actor,shapeCurrentPose=shape,
                  nativeFaceInCandidates=any(m['cookedFace']==native_face for m in metrics) if native_face is not None else None)
    return result


def sweep_feature_metrics(request, hit):
    """Compare a sweep normal with its recorded sphere/capsule support feature.

    Edge hits need not have a triangle's face normal. This uses the recorded
    direction without normalization and reports residuals, not a native branch.
    Initial-overlap results are retained as a separate, unavailable comparison.
    """
    kind=request['kind']
    if kind not in ('query_sphere_results', 'query_sphere_single', 'query_capsule_results'):
        return dict(status='not_sphere_or_capsule_sweep')
    radius=request['radius'];distance=hit['distance']
    if not math.isfinite(radius) or radius<=0 or not math.isfinite(distance):
        return dict(status='unavailable_radius_or_distance')
    if distance<=0:
        return dict(status='initial_overlap_or_nonpositive_distance',distance=distance)
    values=_vector(request['argumentVectors'],9 if kind=='query_capsule_results' else 6)
    point=_vector(hit['point'],3);normal=_vector(hit['normal'],3)
    direction=values[-3:];a=tuple(values[i]+direction[i]*distance for i in range(3))
    parameter=None
    if kind=='query_capsule_results':
        b=tuple(values[i+3]+direction[i]*distance for i in range(3));segment=_sub(b,a);length2=_dot(segment,segment)
        parameter=max(0.,min(1.,_dot(_sub(point,a),segment)/length2)) if length2 else 0.
        support=tuple(a[i]+parameter*segment[i] for i in range(3))
    else:
        support=a
    radial=_sub(support,point);length=math.sqrt(_dot(radial,radial));normal_length=math.sqrt(_dot(normal,normal))
    if not length or not normal_length:
        return dict(status='unavailable_zero_radial_or_normal')
    return dict(status='conditional_sweep_feature_metrics',supportPoint=list(support),radius=radius,
                radiusResidual=length-radius,normalDot=_dot(radial,normal)/(length*normal_length),
                recordedDirectionLength=math.sqrt(_dot(direction,direction)),capsuleSegmentParameter=parameter,
                boundary='conditional numerical support-feature comparison at recorded query distance; no native feature branch, current pose or solver-contact claim')
