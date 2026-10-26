"""Compile an offline managed helper without modifying its admitted CLI."""
from pathlib import Path
import shutil
import subprocess

from scripts.game_data.extraction.animestudio.rebuild import find_dotnet
from scripts.game_data.extraction.animestudio.setup_dotnet9 import dotnet_environment
from scripts.game_data.cooked_collision_corpus import _decoder_closure


def build_sidecar(cli,work,*,project,binary_name,unitycn_keys=False):
    sdk=find_dotnet(False);env=dotnet_environment(sdk.parent)
    work.mkdir(parents=True,exist_ok=True);work=work.resolve()
    args=[str(sdk),'build',str(project),'-c','Release','--nologo',
          '-p:AnimeStudioCliRoot='+str(cli.parent.resolve()),'-p:BaseIntermediateOutputPath='+str(work/'obj')+'/',
          '-p:OutputPath='+str(work/'bin')+'/','-p:RestoreIgnoreFailedSources=true','-p:NuGetAudit=false']
    log=work/'build.log'
    with log.open('wb') as output:result=subprocess.run(args,stdout=output,stderr=subprocess.STDOUT,env=env)
    if result.returncode:raise ValueError(f'managed offline sidecar build failed: {log}; '+log.read_text('utf-8',errors='replace')[-1500:])
    binary=work/'bin'/binary_name
    if not binary.is_file():raise ValueError(f'managed offline sidecar output missing: {binary}')
    if unitycn_keys:
        keys=cli.parent/'CNKeys.json'
        if not keys.is_file():raise ValueError('admitted CLI UnityCN configuration is missing')
        shutil.copyfile(keys,binary.parent/'CNKeys.json')
    return dict(sdk=str(sdk),binary=str(binary),closure=_decoder_closure(binary),buildCommand=args,buildLog=str(log))
