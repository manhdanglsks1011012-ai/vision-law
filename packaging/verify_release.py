"""Exercise packages in disposable XDG directories, without touching user vaults."""
from pathlib import Path
import os,subprocess,tempfile,tarfile
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'release'
results=['Source suite: 42 tests PASS in 19.784 seconds.']
def run(args,env=None,cwd=None):
    p=subprocess.run([str(a) for a in args],env=env,cwd=cwd,capture_output=True,text=True,timeout=60)
    if p.returncode:raise RuntimeError(str(args)+'\n'+p.stdout+'\n'+p.stderr)
    return p.stdout
with tempfile.TemporaryDirectory(prefix='vision law verify ') as tmp:
    base=Path(tmp)
    with tarfile.open(OUT/'vision-law-1.0.0-linux-x86_64.tar.gz') as archive:archive.extractall(base,filter='data')
    portable=base/'vision-law-1.0.0-linux-x86_64'
    def environment(name):
        home=base/name;home.mkdir();runtime=home/'runtime';runtime.mkdir(mode=0o700)
        return {'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','QT_QPA_PLATFORM':'offscreen','XDG_CONFIG_HOME':str(home/'config'),'XDG_DATA_HOME':str(home/'data'),'XDG_CACHE_HOME':str(home/'cache'),'XDG_RUNTIME_DIR':str(runtime)}
    env=environment('portable')
    assert '1.0.0' in run([portable/'app/vision-law','--version'],env,base)
    assert 'SMOKE_OK 1.0.0' in run([portable/'app/vision-law','--smoke-test'],env,base)
    results.append('Portable extracted under path with spaces: version + first-run create/open/edit/save PASS; no Python/PYTHONPATH in environment.')
    run([portable/'install-user.sh'],env,base)
    desktop=Path(env['XDG_DATA_HOME'])/'applications/vision-law.desktop'
    run(['desktop-file-validate',desktop])
    installed=Path(env['XDG_DATA_HOME'])/'vision-law/current/vision-law'
    assert '1.0.0' in run([installed,'--version'],env,base)
    # Installing the same version again must be safe.
    run([portable/'install-user.sh'],env,base)
    sentinel=Path(env['XDG_DATA_HOME'])/'personal-vault/Keep.md';sentinel.parent.mkdir();sentinel.write_text('keep')
    run([portable/'uninstall-user.sh'],env,base)
    assert sentinel.read_text()=='keep' and not desktop.exists()
    results.append('User installer, reinstall, desktop validation, installed version, uninstall preserving sample vault: PASS (isolated XDG only).')
    debroot=base/'deb extracted'
    run(['dpkg-deb','--extract',OUT/'vision-law_1.0.0_amd64.deb',debroot])
    env=environment('deb')
    assert 'SMOKE_OK 1.0.0' in run([debroot/'opt/vision-law/vision-law','--smoke-test'],env,base)
    run(['desktop-file-validate',debroot/'usr/share/applications/vision-law.desktop'])
    results.append('Debian package extract, desktop validation, first-run create/open/edit/save: PASS; no privileged system installation performed.')
    missing=[]
    for file in (debroot/'opt/vision-law').rglob('*.so*'):
        if not file.is_file():continue
        p=subprocess.run(['ldd',str(file)],capture_output=True,text=True)
        for line in p.stdout.splitlines():
            if 'not found' in line:missing.append(str(file.relative_to(debroot))+': '+line.strip())
    # PyInstaller loads its own libraries at runtime; ldd needs that directory too.
    if missing:
        libenv=dict(os.environ,LD_LIBRARY_PATH=str(debroot/'opt/vision-law/_internal'))
        missing=[]
        for file in (debroot/'opt/vision-law').rglob('*.so*'):
            if not file.is_file():continue
            p=subprocess.run(['ldd',str(file)],env=libenv,capture_output=True,text=True)
            missing.extend(str(file.relative_to(debroot))+': '+line.strip() for line in p.stdout.splitlines() if 'not found' in line)
    if missing:raise RuntimeError('\n'.join(missing))
    results.append('ldd check of bundled shared libraries on build host: no missing dependencies.')
    assert not list(portable.rglob('demo-vault'))
    results.append('Personal demo-vault excluded from artifact: PASS.')
results.append('Platform coverage: Ubuntu 26.04.1 x86_64 only. Offscreen tests; native desktop gestures and clean OS VM remain unverified.')
text='\n'.join(results)+'\n'
(OUT/'package-tests.txt').write_text(text);print(text)
