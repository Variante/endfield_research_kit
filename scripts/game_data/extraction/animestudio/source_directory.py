"""Build/run a bounded serialized-directory sidecar against an admitted CLI.

Outputs and compilation intermediates live in the caller's ignored work root.
The CLI binaries are referenced, never rebuilt or modified by this sidecar.
"""
from pathlib import Path
import subprocess
from scripts.game_data.extraction.animestudio.managed_sidecar import build_sidecar
from scripts.game_data.extraction.animestudio.setup_dotnet9 import dotnet_environment
from scripts.game_data.cooked_collision_corpus import _decoder_closure
from scripts.repo_paths import REPO_ROOT


def build_helper(cli,work):
    project=REPO_ROOT/'scripts/game_data/extraction/animestudio/source_directory/SourceDirectory.csproj'
    # GameManager initializes UnityCN keys even for Endfield. Supply the
    # admitted configuration before recording the closure; do not accept a
    # first-run warning or let the library generate an unrecorded file.
    return build_sidecar(cli,work,project=project,binary_name='SourceDirectory.dll',unitycn_keys=True)


def extract(helper,cli,selection,output,classes):
    args=[helper['sdk'],helper['binary'],str(cli.parent.resolve()),str(selection.resolve()),str(output.resolve()),
          ','.join(map(str,sorted(classes)))]
    log=output.parent/(output.name+'.log')
    with log.open('wb') as stream:
        result=subprocess.run(args,stdout=stream,stderr=subprocess.STDOUT,env=dotnet_environment(Path(helper['sdk']).parent))
    if result.returncode or log.stat().st_size:
        raise ValueError(f'serialized directory sidecar failed/diagnosed: exit={result.returncode}; log={log}; '
                         +log.read_text('utf-8',errors='replace')[:1600])
    if _decoder_closure(Path(helper['binary']))!=helper['closure']:
        raise ValueError('serialized directory sidecar output closure changed during extraction')
    return dict(command=args,log=str(log))
