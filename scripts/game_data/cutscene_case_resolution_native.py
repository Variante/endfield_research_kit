"""Current conditional GenderSelect native/Lua association; runtime lookup unresolved."""
import hashlib,json,re
from pathlib import Path
from scripts.common import check_installed_native_inputs,repo_path
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.il2cpp.gender_select_sources import derive
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs,reader_input_changes
from scripts.game_data.memorypack.pooled_source_helper import check_unity_input
from scripts.source_paths import ExportLayout

SCHEMA='cutsceneCaseResolutionNativeContract.v5'
AUDIT_SCHEMA='cutsceneCaseResolutionNativeContractAudit.v3'
DEFAULT_CONTRACT=CONTRACTS_DIR/'cutscene_case_resolution.json'
MATCH_FIELDS=('module','sourceSha256','line','method','resolvedLiteral','canonicalStoryKey','registryStatus')


def _contained(root,name):
    path=(Path(root)/name).resolve()
    if not path.is_relative_to(Path(root).resolve()):raise ValueError('genderSelect.source-outside-selected-root')
    return path


def _installed_lua(root,contract):
    rows=contract['installedLuaInputs'];selection=contract['installedLuaSelection']
    if not rows or not selection:raise ValueError('genderSelect.missing-installed-Lua-inputs')
    for row in rows:
        path=_contained(root,row['path'])
        with path.open('rb')as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest().upper()
        if path.stat().st_size!=row['length']or digest!=row['sha256']:raise ValueError('genderSelect.installed-Lua-input:'+str(path))
    for row in selection:
        if _contained(root,row['path']).is_file()!=row['exists']:raise ValueError('genderSelect.installed-Lua-overlay-selection')


def _lua_sources(root,contract):
    sources=contract['luaSources']
    if len(sources)!=2:raise ValueError('genderSelect.Lua-source-set')
    data={}
    for row in sources:
        path=_contained(root,row['sourceFile']);raw=path.read_bytes()
        if len(raw)!=row['length']or hashlib.sha256(raw).hexdigest().upper()!=row['sha256']:raise ValueError('genderSelect.Lua-export-source:'+str(path))
        data[row['sourceFile']]=raw
    playback=contract['luaPlayback'];key=contract['nativeFacts']['programs']['keyField']['name'];phase=data['game/Lua/Data/LuaScripts/'+playback['module']].decode('utf-8');messages=data['game/Lua/Data/LuaScripts/Const/MessageConst.lua'].decode('utf-8')
    def one(pattern,text):
        found=list(re.finditer(pattern,text,re.MULTILINE|re.DOTALL))
        if len(found)!=1:raise ValueError('genderSelect.Lua-clause:'+pattern[:100])
        return found[0]
    literal=one(r'^local EnterCutsceneId = "([^"\r\n]+)"$',phase).group(1)
    one(r"\[MessageConst\."+re.escape(key)+r"\] = \{ 'OnGenderSelectStart', false \}",phase)
    one(r'PhaseGenderSelect\.OnGenderSelectStart = HL\.StaticMethod\(HL\.Any\) << function\(onFinishGenderSelect\)\s+logger\.info\([^\n]+\)\s+PhaseManager:OpenPhaseFast\(PhaseId\.GenderSelect, onFinishGenderSelect\)\s+end',phase)
    activated=one(r'PhaseGenderSelect\._OnActivated = HL\.Override\(\) << function\(self\)(.*?)\nend\n',phase).group(1)
    guarded=one(r'if self\.m_firstActive then(.*?)\n    end\n\s+self\.m_firstActive = false',activated).group(1)
    call=one(r'GameAction\.PlayCutsceneAndGetHandle\(EnterCutsceneId, function\(\)\s+self:OnNotificationActive\(\)\s+end\)',phase)
    if call.group(0)not in guarded or literal!=playback['resolvedLiteral']or phase[:call.start()].count('\n')+1!=playback['line']:raise ValueError('genderSelect.Lua-first-active-playback')
    one(r'^    "'+re.escape(key)+r'",$',messages)
    # These are source associations; executing the message registry and matching its native key remains conditional.
    for clause in ('local msgs = {}','group = GlobalMsg,','for _, msg in pairs(v.group) do','msgs[msg] = id','return res'):
        if messages.count(clause)!=1:raise ValueError('genderSelect.Lua-message-registry-clause')
    return data


def load_cutscene_case_resolution_contract(contract_path=DEFAULT_CONTRACT,*,gameassembly=None,metadata=None,game_root=None,export_root=None):
    """Fresh source proof, never a runtime key-resolution or whole-owner receipt."""
    path=Path(contract_path);source_file=repo_path(path)
    try:
        raw=path.read_bytes();contract=json.loads(raw);reader=snapshot_complete_reader_inputs();pins=contract['nativeInputs']
        if contract['schema']!=SCHEMA or contract['status']!='validated'or set(pins)!={'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'}:raise ValueError('genderSelect.contract-shape')
        if contract['conclusion']!={'runtimeCaseResolution':'unresolved','literalResolvesToCanonicalKey':None}:raise ValueError('genderSelect.runtime-case-boundary')
        if contract['sources']!={'gameAssemblySha256':pins['GameAssembly.dll'],'metadataSha256':pins['global-metadata.dat']}:raise ValueError('genderSelect.source-native-pin-join')
        bridge=contract['genderSelectBridge']
        if bridge['status']!='conditional'or bridge['actionType']!=contract['nativeFacts']['programs']['callback']['owner']or bridge['storyKey']!=contract['luaPlayback']['canonicalStoryKey']or bridge['conditionalPlayback']is not True or bridge['suppliesMissionOrQuestOwnership']is not False:raise ValueError('genderSelect.conditional-bridge-boundary')
        if(gameassembly is None)!=(metadata is None):raise ValueError('genderSelect.both-native-paths-required')
        root=Path(game_root)if game_root is not None else None
        gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly if gameassembly is not None else root.parent/'GameAssembly.dll'if root else None,metadata=metadata if metadata is not None else root/'il2cpp_data/Metadata/global-metadata.dat'if root else None)
        if gate.status!='validated':return dict(schema=AUDIT_SCHEMA,status=gate.status,sourceFile=source_file,nativeContract={},validationFailures=[dict(gate='installed_native_inputs',actual=gate.detail)])
        selected_root=Path(gate.metadata).resolve().parents[2]
        if root is not None and root.resolve()!=selected_root:raise ValueError('genderSelect.selected-native-root')
        failed=check_unity_input(gate.gameassembly,pins)
        if failed:raise ValueError('genderSelect.UnityPlayer:'+str(failed))
        root=selected_root;export=Path(export_root)if export_root is not None else ExportLayout.configured().root
        _installed_lua(root,contract);lua=_lua_sources(export,contract)
        actual=derive(open_native_image(gate.gameassembly,gate.metadata))
        if actual!=contract['nativeFacts']:raise ValueError('genderSelect.reviewed-native-source-facts')
        association=contract['recoveryAssociationPolicy'];playback=contract['luaPlayback'];literal=playback['resolvedLiteral'];canonical=playback['canonicalStoryKey']
        if not literal.isascii()or not canonical.isascii()or literal==canonical or literal.lower()!=canonical.lower()or association!={'comparison':'ascii_case_insensitive','requiresUniqueCanonicalStoryKey':True,'literalAssociatesToCanonicalKey':True,'graphAction':'associate_casefolded_playback_reference','suppliesMissionOrQuestOwnership':False,'suppliesSpatialEvidence':False}:raise ValueError('genderSelect.association-policy')
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
        if after.status!='validated':raise ValueError('genderSelect.native-input-drift:'+after.detail)
        failed=check_unity_input(gate.gameassembly,pins)
        if failed:raise ValueError('genderSelect.UnityPlayer-drift:'+str(failed))
        _installed_lua(root,contract)
        if raw!=path.read_bytes()or lua!=_lua_sources(export,contract):raise ValueError('genderSelect.contract-or-Lua-drift')
        fresh=snapshot_complete_reader_inputs()
        if fresh!=reader:raise ValueError('genderSelect.reader-input-drift:'+str(reader_input_changes(reader,fresh))[:1000])
        return dict(schema=AUDIT_SCHEMA,status='validated',sourceFile=source_file,sourceSha256=hashlib.sha256(raw).hexdigest().upper(),nativeContract=contract,matchFields=MATCH_FIELDS,validationFailures=[],runtimeCaseResolution='unresolved',wholeOwnerAdmitted=False,nativeSources={'GameAssembly.dll':str(gate.gameassembly),'global-metadata.dat':str(gate.metadata)},evidenceBoundary=contract['evidenceBoundary'])
    except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError)as error:
        failed=native_validation_failure(error,label='genderSelectNative',source_path=path)
        return dict(failed,schema=AUDIT_SCHEMA,sourceFile=source_file,nativeContract={},validationFailures=[dict(gate='genderSelect_source',actual=str(error)[:1000])])


def matches_reviewed_lua_playback(row,audit):
    if audit.get('status')!='validated':return False
    expected=(audit.get('nativeContract')or{}).get('luaPlayback')or{}
    return all(str(row.get(k,'')).upper()==str(expected.get(k,'')).upper()if k=='sourceSha256'else row.get(k)==expected.get(k)for k in MATCH_FIELDS)


def unique_ascii_story_key(literal,keys):
    if not isinstance(literal,str)or not literal.isascii():return None
    matches={key for key in keys if isinstance(key,str)and key.isascii()and key.lower()==literal.lower()}
    return next(iter(matches))if len(matches)==1 else None


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    for name in('contract','game-root','gameassembly','metadata','export-root'):parser.add_argument('--'+name,type=Path,default=DEFAULT_CONTRACT if name=='contract'else None)
    args=parser.parse_args();audit=load_cutscene_case_resolution_contract(args.contract,game_root=args.game_root,gameassembly=args.gameassembly,metadata=args.metadata,export_root=args.export_root);print(json.dumps({k:audit.get(k)for k in('status','runtimeCaseResolution','validationFailures')},indent=2));raise SystemExit(0 if audit['status']=='validated'else 2)
