"""Compare declared Animator Mesh renderers with exported FBX instances.

This is a source-declaration audit, not runtime visibility, shader deformation
or a full vertex/skin equivalence proof. Mesh targets are retained as exact
referring CAB/external-slot/PathID tuples; a missing mesh target is not empty.


Evidence and admission boundary
-------------------------------
Exact attachment comparison requires reciprocal source GameObject/Transform,
MeshFilter and renderer declarations against FBX geometry attachments; external
Mesh identities retain referring CAB, external slot and PathID. Count equality
proves attachment coverage only. A selected independent sheep Mesh-body/FBX
comparison matched vertices and triangles after X reflection/winding reversal:
its horns are present despite bright preview emission and weapon-style names.
That result does not prove other Animator payloads or final game appearance.

Dependency closure can cross VFS layers, offsets within one physical chunk and
loose built-in Resources. The selected-layer CAB map wins; fallback fills only
absent names. Built-ins participate in cache/freshness inputs. Dependencies bypass
source-object filters without becoming export targets; root offset filters do
not narrow transitive closure. Duplicate sibling names require exact ImportedFrame
identity for attachment; legacy producers retain path lookup, without implying
new animation/morph/bone rules. Missing parsed Mesh targets warn by exact pointer.
Remaining door CAB targets are absent from both current layer indexes and the
saved previous indexes/Mesh PathIDs: partial exports must not invent geometry.
"""


def index_directory(directory):
    objects={row['pathId']:row for row in directory['objects']}
    classes={row['pathId']:row['classId'] for row in directory['classNames']}
    class_names={row['pathId']:row.get('typeName',str(row['classId'])) for row in directory['classNames']}
    if len(objects)!=len(directory['objects']) or len(classes)!=directory['objectCount']:
        raise ValueError('source directory object identities duplicate or census differs')
    if any(classes.get(pid)!=row['classId'] for pid,row in objects.items()):
        raise ValueError('source body class differs from complete directory')
    return dict(directory=directory,objects=objects,classes=classes,class_names=class_names)


def declared_renderers(directory, animator_path_id, *, index=None):
    index=index if index is not None else index_directory(directory)
    if index['directory'] is not directory:raise ValueError('source directory index belongs to another directory')
    objects=index['objects'];classes=index['classes'];class_names=index['class_names']
    observed=[];unknown=[];seen=set()

    def target(pointer,expected=None):
        if not isinstance(pointer,dict) or type(pointer.get('m_FileID'))!=int or type(pointer.get('m_PathID'))!=int:
            raise ValueError('invalid source PPtr')
        if pointer['m_FileID']!=0:raise ValueError('external source hierarchy requires another complete directory')
        row=objects.get(pointer['m_PathID'])
        if row is None or expected is not None and row['classId'] not in expected:
            raise ValueError(f'source hierarchy target unavailable or wrong class: PathID={pointer["m_PathID"]}; expected={expected}')
        return row

    def mesh_ref(pointer):
        if not isinstance(pointer,dict) or type(pointer.get('m_FileID'))!=int or type(pointer.get('m_PathID'))!=int:
            raise ValueError('invalid renderer Mesh PPtr')
        slot=pointer['m_FileID'];pid=pointer['m_PathID']
        if not 0<=slot<=len(directory['externals']):raise ValueError('renderer Mesh external slot exceeds referring directory')
        return dict(fileId=slot,pathId=pid,targetCab=directory['externals'][slot-1].replace('\\','/').rsplit('/',1)[-1] if slot else directory['cab'])

    animator=objects.get(animator_path_id)
    if animator is None or animator['classId']!=95:raise ValueError('selected Animator is absent from source directory')
    root=target(animator['body']['m_GameObject'],{1})
    pending=[(root,[],None)]
    while pending:
        game_object,parent_path,parent_transform=pending.pop()
        pid=game_object['pathId']
        if pid in seen:raise ValueError('source hierarchy cycles or shares a child')
        if len(parent_path)>512:raise ValueError('source hierarchy exceeds depth bound')
        seen.add(pid);body=game_object['body'];path=parent_path+[body['m_Name']]
        components=[]
        component_ids=set()
        for item in body['m_Component']:
            pointer=item['component'];component_id=pointer['m_PathID']
            if component_id in component_ids:raise ValueError('duplicate GameObject component pointer')
            component_ids.add(component_id)
            if pointer['m_FileID']!=0 or component_id not in classes:raise ValueError('GameObject component identity unavailable')
            if classes[component_id] in (4,23,33,95,137,224):components.append(target(pointer))
            else:unknown.append(dict(path=path,pathId=component_id,classId=classes[component_id],typeName=class_names[component_id]))
        transforms=[row for row in components if row['classId'] in (4,224)]
        if len(transforms)!=1:raise ValueError('GameObject must have one source Transform')
        transform=transforms[0]
        if target(transform['body']['m_GameObject'],{1})['pathId']!=pid:raise ValueError('Transform/GameObject link is not reciprocal')
        if parent_transform is not None and target(transform['body']['m_Father'],{4,224})['pathId']!=parent_transform:
            raise ValueError('Transform parent/child link is not reciprocal')
        filters=[row for row in components if row['classId']==33]
        if len(filters)>1:raise ValueError('multiple MeshFilters on one source GameObject')
        if filters and target(filters[0]['body']['m_GameObject'],{1})['pathId']!=pid:
            raise ValueError('MeshFilter/GameObject link is not reciprocal')
        for renderer in (r for r in components if r['classId'] in (23,137)):
            rbody=renderer['body']
            if target(rbody['m_GameObject'],{1})['pathId']!=pid:raise ValueError('Renderer/GameObject link is not reciprocal')
            pointer=rbody.get('m_Mesh') if renderer['classId']==137 else filters[0]['body']['m_Mesh'] if filters else None
            if pointer is None:
                observed.append(dict(path=path,rendererPathId=renderer['pathId'],status='missing_mesh_filter'))
            else:
                mesh=mesh_ref(pointer)
                observed.append(dict(path=path,rendererPathId=renderer['pathId'],classId=renderer['classId'],mesh=mesh,
                                     status='declared_mesh' if mesh['pathId'] else 'null_mesh'))
        for pointer in reversed(transform['body']['m_Children']):
            child=target(pointer,{4,224});pending.append((target(child['body']['m_GameObject'],{1}),path,transform['pathId']))
    return dict(renderers=observed,declaredMeshes=sum(r['status']=='declared_mesh' for r in observed),
                otherRendererComponents=[r for r in unknown if 'renderer' in r['typeName'].lower()],
                otherComponents=unknown,gameObjects=len(seen))


def compare_inventory(source, inventory):
    """Count difference is a recovery candidate, not a missing-target proof."""
    expected=source['declaredMeshes'];actual=inventory['geometryInstances']
    return dict(status='renderer_count_matches' if expected==actual else 'fewer_exported_meshes' if expected>actual else 'more_exported_meshes',
                declaredMeshes=expected,exportedGeometryInstances=actual,
                missingMeshFilters=sum(r['status']=='missing_mesh_filter' for r in source['renderers']))


def compare_facts(facts, inventories):
    """Join recorded declarations and structural reads, retaining every gap."""
    from collections import Counter
    indexed = {row['name']: row for row in inventories}
    counts = Counter(); differences = []; collisions = []; found = set()
    for row in facts:
        name = row['output']; source = row['source']
        if name in found:
            raise ValueError('duplicate source declaration: '+name)
        found.add(name)
        existing = indexed.get(name)
        if existing:
            comparison = compare_inventory(source, existing['inventory'])
        else:
            comparison = dict(status='empty_with_declared_mesh' if source['declaredMeshes'] else 'empty_without_declared_mesh',
                declaredMeshes=source['declaredMeshes'], exportedGeometryInstances=0)
        counts[comparison['status']] += 1
        if comparison['status'] not in ('renderer_count_matches', 'empty_without_declared_mesh'):
            differences.append(dict(row, comparison=comparison))
        paths = Counter(tuple(renderer['path']) for renderer in source['renderers'] if renderer['status']=='declared_mesh')
        duplicates = [list(path) for path, count in paths.items() if count>1]
        if duplicates:
            collisions.append(dict(row, duplicatePaths=duplicates))
    return dict(schema='endfield.animator-geometry-coverage.v1', counts=dict(counts), differences=differences,
        rendererPathCollisions=collisions, unmatchedFbx=sorted(indexed.keys()-found),
        evidenceBoundary='Conditional comparison of selected recorded source declarations and FBX structure. Count equality is not vertex/skin or appearance parity; source freshness belongs to the declaration producer and repair source gate.')


def main():
    import argparse
    import json
    from pathlib import Path
    from scripts.common import write_json,sha256_file
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--facts', type=Path, required=True, help='Recorded source-renderer facts JSONL')
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    inventory = json.loads(args.inventory.read_bytes())
    if inventory.get('schema') != 'endfield.fbx-structural-inventory.v1' or inventory.get('errors'):
        raise ValueError('complete successful FBX inventory is required')
    with args.facts.open(encoding='utf8') as stream:
        result = compare_facts((json.loads(line) for line in stream), inventory['rows'])
    result['inputs'] = dict(facts=dict(path=str(args.facts),sha256=sha256_file(args.facts)),
        inventory=dict(path=str(args.inventory),sha256=sha256_file(args.inventory)))
    write_json(args.report, result)
    print(dict(counts=result['counts'], differences=len(result['differences']), unmatchedFbx=len(result['unmatchedFbx'])))
    if result['unmatchedFbx']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
