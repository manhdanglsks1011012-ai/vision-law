"""Collect Ubuntu package provenance/notices for every bundled ELF library."""
from pathlib import Path
import subprocess,json,urllib.parse,shutil
ROOT=Path(__file__).resolve().parents[1]
bundle=ROOT/'build-dist/vision-law/_internal'
entries=subprocess.run(['dpkg-query','-S','*.so*'],capture_output=True,text=True,check=True).stdout.splitlines()
byname={}
for line in entries:
    if ': /' not in line:continue
    package,path=line.split(': ',1)
    byname.setdefault(Path(path).name,[]).append((package,path))
items={};unknown=[]
for file in bundle.rglob('*.so*'):
    if not file.is_file():continue
    matches=byname.get(file.name,[])
    if not matches:unknown.append(str(file.relative_to(bundle)));continue
    package=matches[0][0]
    if package not in items:
        raw=subprocess.check_output(['dpkg-query','-W','-f=${binary:Package}\t${Version}\t${source:Package}\t${source:Version}',package],text=True).split('\t')
        binary,version,source,source_version=raw
        doc=Path('/usr/share/doc')/package.split(':')[0]/'copyright'
        items[package]={'binary_package':binary,'version':version,'source_package':source,'source_version':source_version,'source_url':'https://launchpad.net/ubuntu/+source/'+urllib.parse.quote(source,safe='')+'/'+urllib.parse.quote(source_version,safe=''),'copyright_file':str(doc),'bundled_files':[]}
    items[package]['bundled_files'].append(str(file.relative_to(bundle)))
if unknown:raise RuntimeError('Missing source package attribution: '+str(unknown))
result={'distribution':'Ubuntu 26.04 (resolute)','packages':list(items.values())}
(ROOT/'docs/BUNDLED-SOURCES.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
print('Recorded',len(items),'Ubuntu packages; no unassigned shared libraries.')
