"""Recreate the ignored source archive before rebuilding a sample Docker image."""
import json,subprocess,tarfile,tempfile
from pathlib import Path
R=Path(__file__).resolve().parent
cfg=json.loads((R/'source.json').read_text())
tag=cfg.get('base_image_tag')
if tag and subprocess.run(['docker','image','inspect',tag],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
 subprocess.run(['docker','pull','--platform',cfg['platform'],cfg['base_image_digest']],check=True)
 subprocess.run(['docker','tag',cfg['base_image_digest'],tag],check=True)
with tempfile.TemporaryDirectory() as temporary:
 p=Path(temporary)/'repo';p.mkdir()
 def git(*args):subprocess.run(['git','-C',str(p),*args],check=True)
 git('init');git('remote','add','origin','https://github.com/'+cfg['repository']+'.git')
 git('fetch','--depth=2','origin',cfg['patch_commit']);git('checkout','--detach',cfg['patch_commit']);git('cat-file','-e',cfg['base_commit']+'^{commit}')
 with tarfile.open(R/'source.tar.gz','w:gz') as archive:archive.add(p,arcname='.')
print('Prepared',R/'source.tar.gz')
