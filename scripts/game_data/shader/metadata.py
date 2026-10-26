"""Join stored pass/keyword/parameter indices to their D3D program records."""
import hashlib
import json
from scripts.game_data.shader.materials import material_parameters
from scripts.game_data.shader.material_instructions import material_instruction_reads

STAGES=('Vertex','Fragment','Geometry','Hull','Domain','RayTracing')


def analyze_shader(body,parsed):
    form=body['m_ParsedForm'];names=form['m_KeywordNames'];declarations=form['m_PropInfo']['m_Props']
    if len(names)!=len(set(names)):raise ValueError('shader keyword names duplicate')
    if len(form['m_KeywordFlags'])!=len(names):raise ValueError('shader keyword flags/name census differs')
    if len({p['m_Name'] for p in declarations})!=len(declarations):raise ValueError('shader property names duplicate')
    layouts={};variants=[];passes=[];gaps=[]
    for lod in parsed['lods']:
        platform=next((p for p in lod['platforms'] if p['platform']==4),None)
        if platform is None:continue
        records={r['index']:r for r in platform['records']}
        for subindex,sub in enumerate(form['m_SubShaders']):
            if sub['m_LOD']!=lod['lod']:continue
            for passindex,p in enumerate(sub['m_Passes']):
                pass_name=p['m_State']['m_Name'] or p['m_Name']
                context=dict(shaderLOD=lod['lod'],subShaderOrdinal=subindex,passOrdinal=passindex,passName=pass_name)
                passes.append(dict(context,programMask=p['m_ProgramMask'],tags=p['m_Tags']))
                for stage in STAGES:
                    program=p['prog'+stage];groups=program['m_PlayerSubPrograms'];parameters=program['m_ParameterBlobIndices']
                    if program['m_SubPrograms']:raise ValueError('shader non-player variant layout remains unsupported')
                    if len(groups)!=len(parameters):raise ValueError('shader player/parameter group census differs')
                    for gi,group in enumerate(groups):
                        if len(group)!=len(parameters[gi]):raise ValueError('shader player/parameter row census differs')
                        for vi,row in enumerate(group):
                            if row['m_GpuProgramType']!=33:continue
                            pointer=row['m_BlobIndex'];parameter_index=parameters[gi][vi];code=records.get(pointer);parameter=records.get(parameter_index)
                            indices=row['m_KeywordIndices']
                            if len(indices)!=len(set(indices)) or any(type(i)!=int or not 0<=i<len(names) for i in indices):raise ValueError('shader keyword index outside name table or duplicates')
                            keywords=[names[i] for i in indices]
                            if code is None or parameter is None:
                                gaps.append(dict(context,serializedStage=stage.lower(),codeIndex=pointer,parameterIndex=parameter_index,reason='record outside selected stored shader LOD'));continue
                            if code['status']!='complete_dxbc_code':raise ValueError('D3D variant does not point to a decoded D3D code record')
                            if set(keywords)!=set(code['code']['keywords']):raise ValueError('serialized/native code keyword sets differ')
                            layout_id=None
                            if parameter['status']=='complete_parameter_tables':
                                raw=json.dumps(parameter['parameters'],sort_keys=True,separators=(',',':')).encode();layout_id=hashlib.sha256(raw).hexdigest()
                                layouts[layout_id]=parameter['parameters']
                            else:gaps.append(dict(context,parameterIndex=parameter_index,reason='parameter table layout unavailable'))
                            variants.append(dict(context,serializedStage=stage.lower(),groupOrdinal=gi,variantOrdinal=vi,
                                codeIndex=pointer,codeSha256=code['sha256'],parameterIndex=parameter_index,parameterSha256=parameter['sha256'],
                                layoutId=layout_id,keywords=keywords,shaderRequirements=row['m_ShaderRequirements'],
                                decodedStages=[s['stage'] for s in code['code']['snippets']],
                                snippets=[{k:v for k,v in s.items() if k not in ('bytecode','chunks')} for s in code['code']['snippets']]))
    return dict(schema='endfield.stored-shader-analysis.v1',name=parsed['name'],declarations=declarations,
        keywordNames=names,keywordFlags=form['m_KeywordFlags'],passes=passes,variants=variants,parameterLayouts=layouts,gaps=gaps,
        evidenceBoundary='Exact stored Shader LOD/pass/player indices, native record keywords, parsed parameter tables and token-encoded DXBC stages. Serialized stage names are carriers and may contain multiple executable stages. Stored declarations do not prove runtime PSO/keyword selection, uploaded constants or bound textures/samplers.')


def material_shader_info(material,shader):
    names=set(shader['keywordNames']);valid=material['m_ValidKeywords'];unknown=[k for k in valid if k not in names]
    # Conditional shortlist only. Other engine/global keywords are allowed;
    # this never chooses a runtime variant or treats persisted strings as calls.
    wanted=set(valid)&names;candidates=[v for v in shader['variants'] if wanted.issubset(v['keywords'])] if not unknown else []
    property_names={p['m_Name'] for p in shader['declarations']}
    return dict(schema='endfield.stored-material-shader-info.v3',name=shader['name'],validKeywords=valid,invalidKeywords=material['m_InvalidKeywords'],
        undeclaredValidKeywords=unknown,conditionalCandidateCount=len(candidates),compiledVariantCount=len(shader['variants']),
        passNames=list(dict.fromkeys(p['passName'] for p in shader['passes'])),
        candidatePassNames=list(dict.fromkeys(v['passName'] for v in candidates)),
        parameters=material_parameters(material,shader,candidates),
        instructions=material_instruction_reads(candidates),
        undeclaredTextureProperties=[p['Key'] for p in material['m_SavedProperties']['m_TexEnvs'] if int(p['Value']['m_Texture']['m_PathID']) and p['Key'] not in property_names],
        evidenceBoundary='Conditional stored keyword-superset shortlist, allowing additional engine/global keywords. No runtime variant, pass execution, sampler application or material appearance selection.')
