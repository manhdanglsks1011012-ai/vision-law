"""Package an already-built PyInstaller onedir; never includes personal vaults."""
from pathlib import Path
import shutil,subprocess,tarfile,hashlib,json,platform
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'release'; VERSION='1.0.0'
NAME=f'vision-law-{VERSION}-linux-x86_64'
def copy(a,b):
    b.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(a,b)
stage=OUT/NAME
stage.mkdir(parents=True,exist_ok=True)
shutil.copytree(ROOT/'build-dist/vision-law',stage/'app',dirs_exist_ok=True)
for name in ('install-user.sh','uninstall-user.sh'):copy(ROOT/'packaging'/name,stage/name)
shutil.copytree(ROOT/'docs',stage/'docs',dirs_exist_ok=True)
notices=stage/'THIRD-PARTY';notices.mkdir(exist_ok=True)
for name in ('python3-pyqt6','libqt6core6t64','libqt6gui6','libqt6widgets6'):
    source=Path('/usr/share/doc')/name/'copyright'
    if source.exists():copy(source,notices/(name+'-copyright'))
for name in ('GPL-3','LGPL-3','LGPL-2.1','GPL-2'):
    source=Path('/usr/share/common-licenses')/name
    if source.exists():copy(source,notices/name)
for folder in (ROOT/'.build-venv/lib').glob('python*/site-packages/*dist-info'):
    for file in folder.rglob('*'):
        if file.is_file() and ('license' in file.name.lower() or file.name=='COPYING.txt'):
            copy(file,notices/folder.name/file.relative_to(folder))
copy(Path('/usr/share/doc/python3.14/copyright'),notices/'python-copyright')
manifest={'version':VERSION,'platform':platform.platform(),'python':platform.python_version(),'PyQt6':'6.10.2','Qt':'6.10.2','PyInstaller':'6.22.3','architecture':'x86_64'}
(stage/'BUILD-INFO.json').write_text(json.dumps(manifest,indent=2)+'\n')
source=OUT/f'vision-law-{VERSION}-source.tar.gz'
files=subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines()
with tarfile.open(source,'w:gz') as archive:
    for name in files:archive.add(ROOT/name,arcname=f'vision-law-{VERSION}-source/'+name)
copy(source,stage/source.name)
portable=OUT/(NAME+'.tar.gz')
with tarfile.open(portable,'w:gz') as archive:archive.add(stage,arcname=NAME)
debroot=OUT/'deb-root';debroot.mkdir(exist_ok=True)
shutil.copytree(stage/'app',debroot/'opt/vision-law',dirs_exist_ok=True)
copy(ROOT/'packaging/vision-law.desktop',debroot/'usr/share/applications/vision-law.desktop')
copy(ROOT/'assets/vision-law.svg',debroot/'usr/share/icons/hicolor/scalable/apps/vision-law.svg')
shutil.copytree(stage/'docs',debroot/'usr/share/doc/vision-law',dirs_exist_ok=True)
shutil.copytree(notices,debroot/'usr/share/doc/vision-law/THIRD-PARTY',dirs_exist_ok=True)
control=debroot/'DEBIAN/control';control.parent.mkdir(exist_ok=True)
control.write_text(f'''Package: vision-law
Version: {VERSION}
Section: editors
Priority: optional
Architecture: amd64
Maintainer: Vision law <vision-law@localhost>
Depends: libc6 (>= 2.43), libgl1, libegl1, libxkbcommon0, libfontconfig1, libx11-6
Description: Local Markdown notes and knowledge circuit boards
 Desktop application with independent Markdown vaults and named boards.
''')
deb=OUT/f'vision-law_{VERSION}_amd64.deb'
subprocess.run(['dpkg-deb','--build','--root-owner-group',str(debroot),str(deb)],check=True)
with (OUT/'SHA256SUMS').open('w') as f:
    for file in (portable,deb,source):f.write(hashlib.sha256(file.read_bytes()).hexdigest()+'  '+file.name+'\n')
print('Built:',portable,deb,source,sep='\n')
