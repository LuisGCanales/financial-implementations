"""Small synthetic release-gate fixtures; never part of the financial testpaths."""
import base64
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import sys
import tarfile
import tomllib
import zipfile

import pytest

RELEASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RELEASE))
import verify_distribution as distribution
import verify_source_export as source_export
import verify_test_selection as selection
import consumer_smoke as consumer

PREFIX = 'yield_curves-0.1.0.dist-info/'
ROOT = 'yield_curves-0.1.0/'


def wheel_write(path, files, record=True):
    files = dict(files)
    if record:
        rows = []
        for name, data in sorted(files.items()):
            if name.endswith('/RECORD'):
                continue
            value = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode()
            rows.append([name, 'sha256=' + value, str(len(data))])
        rows.append([PREFIX + 'RECORD', '', ''])
        out = io.StringIO()
        csv.writer(out, lineterminator='\n').writerows(rows)
        files[PREFIX + 'RECORD'] = out.getvalue().encode()
    with zipfile.ZipFile(path, 'w') as archive:
        for name, data in files.items():
            archive.writestr(name, data)


def tar_write(path, files):
    with tarfile.open(path, 'w:gz') as archive:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))


@pytest.fixture
def package(tmp_path, monkeypatch):
    source = tmp_path / 'source'
    source.mkdir()
    # Metadata contract from the reviewed project; fixture modules are tiny stubs.
    cfg = (RELEASE.parents[1] / 'pyproject.toml').read_bytes()
    (source / 'pyproject.toml').write_bytes(cfg)
    project = tomllib.loads(cfg.decode())['project']
    for name in distribution.SOURCE_METADATA - {'pyproject.toml'}:
        (source / name).write_bytes((name + '\n').encode())
    modules = ['yield_curves/__init__.py', 'yield_curves/research/__init__.py', 'yield_curves/tooling/__init__.py'] + [f'yield_curves/module_{i}.py' for i in range(35)]
    for name in modules:
        p = source / 'src' / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b'"""Synthetic fixture."""\n')
    monkeypatch.setattr(distribution, 'MODULE_SHA256', {name: hashlib.sha256((source/'src'/name).read_bytes()).hexdigest() for name in modules})
    headers = [('Metadata-Version','2.4'),('Name','yield-curves'),('Version','0.1.0'),('Summary',project['description']),('Author',project['authors'][0]['name']),('License-Expression','MIT'),('License-File','LICENSE'),('Requires-Python','<3.12,>=3.11'),('Description-Content-Type','text/markdown')]
    headers += [('Classifier', v) for v in project['classifiers']]
    headers += [('Project-URL', f'{k}, {v}') for k,v in project['urls'].items()]
    headers += [('Requires-Dist', v) for v in project['dependencies']]
    for extra, requirements in project['optional-dependencies'].items():
        headers += [('Provides-Extra',extra)] + [('Requires-Dist',f'{r}; extra == "{extra}"') for r in requirements]
    headers += [('Keywords', ','.join(project['keywords'])), ('Dynamic', 'license-file')]
    meta = (''.join(f'{k}: {v}\n' for k,v in headers) + '\n').encode() + (source/'README.md').read_bytes()
    wf = {name: (source/'src'/name).read_bytes() for name in modules}
    wf.update({PREFIX+'METADATA':meta, PREFIX+'WHEEL':b'Wheel-Version: 1.0\nGenerator: setuptools (79.0.1)\nRoot-Is-Purelib: true\nTag: py3-none-any\n\n', PREFIX+'top_level.txt':b'yield_curves\n',PREFIX+'licenses/LICENSE':(source/'LICENSE').read_bytes()})
    sf = {name:(source/name).read_bytes() for name in distribution.SOURCE_METADATA | {'src/'+n for n in modules}}
    egg = 'src/yield_curves.egg-info/'
    sf.update({'PKG-INFO':meta, 'setup.cfg':b'[egg_info]\ntag_build = \ntag_date = 0\n\n',egg+'PKG-INFO':meta,egg+'dependency_links.txt':b'\n',egg+'requires.txt':b'numpy>=1.24\nscipy>=1.11.4\n\n[dev]\npytest>=8.0\n\n[plots]\nmatplotlib>=3.7\n',egg+'top_level.txt':b'yield_curves\n'})
    sf[egg+'SOURCES.txt'] = ('\n'.join(sorted((set(sf)-{'PKG-INFO','setup.cfg'}) | {egg+'SOURCES.txt'}))).encode()
    wheel = tmp_path/'yield_curves-0.1.0-py3-none-any.whl'
    sdist = tmp_path/'yield_curves-0.1.0.tar.gz'
    def write():
        wheel_write(wheel,wf)
        tar_write(sdist,{ROOT+k:v for k,v in sf.items()})
    write()
    return source, wheel, sdist, wf, sf, write


def verify(package):
    return distribution.verify(*package[:3], '0.1.0')


def test_valid_synthetic_package(package):
    assert verify(package)['status'] == 'PASS'


@pytest.mark.parametrize('change', ['missing-module','extra-member','license-omission','source-hash','metadata-version','metadata-python','metadata-dependency','entrypoint'])
def test_wheel_rejections(package, change):
    _,_,_,wf,_,write=package
    module='yield_curves/module_0.py'
    if change=='missing-module': del wf[module]
    elif change=='extra-member': wf['tests/private.json']=b'private'
    elif change=='license-omission': del wf[PREFIX+'licenses/LICENSE']
    elif change=='source-hash': wf[module]=b'changed'
    elif change=='entrypoint': wf[PREFIX+'entry_points.txt']=b'[console_scripts]'
    else:
        before,after={'metadata-version':(b'Version: 0.1.0',b'Version: 9.9.9'),'metadata-python':(b'<3.12,>=3.11',b'>=3.11'),'metadata-dependency':(b'numpy>=1.24',b'numpy>=1.0')}[change]
        wf[PREFIX+'METADATA']=wf[PREFIX+'METADATA'].replace(before,after)
    write()
    with pytest.raises(ValueError): verify(package)


@pytest.mark.parametrize('change', ['missing-module','extra-member','license-omission','source-hash','stale-metadata','stale-sources','unknown-backend','machine-dependency'])
def test_sdist_rejections(package,change):
    _,_,_,_,sf,write=package
    module='src/yield_curves/module_0.py'
    if change=='missing-module': del sf[module]
    elif change=='extra-member': sf['data/private.csv']=b'private'
    elif change=='license-omission': del sf['LICENSE']
    elif change=='source-hash': sf[module]=b'changed'
    elif change=='stale-metadata': sf['src/yield_curves.egg-info/PKG-INFO']=b'stale'
    elif change=='stale-sources': sf['src/yield_curves.egg-info/SOURCES.txt']+=b'\nsrc/yield_curves/deleted.py'
    elif change=='unknown-backend': sf['src/yield_curves.egg-info/new.txt']=b'unknown'
    elif change=='machine-dependency': sf['PKG-INFO']=sf['PKG-INFO'].replace(b'numpy>=1.24',b'numpy @ file:///private/numpy.whl')
    write()
    with pytest.raises(ValueError): verify(package)


def test_corrupt_record(package):
    source,wheel,sdist,wf,_,_=package
    wheel_write(wheel,dict(wf,**{PREFIX+'RECORD':b'broken,sha256=bad,0\n'}),record=False)
    with pytest.raises(ValueError,match='RECORD'): verify(package)


@pytest.mark.parametrize('name',['../escape.py','/absolute.py','x/../escape.py','x//escape.py','x/./escape.py','C:/escape.py','x\\escape.py'])
@pytest.mark.parametrize('kind',['wheel','tar'])
def test_unsafe_archive_paths(tmp_path,name,kind):
    path=tmp_path/'archive'
    if kind=='wheel':
        wheel_write(path,{name:b'x'},record=False)
        read=distribution.read_wheel
    else:
        tar_write(path,{name:b'x'})
        read=source_export.read_tar
    with pytest.raises(ValueError): read(path)


@pytest.mark.parametrize('names',[['same','same'],['Name','name'],['café','café'],['file','file/child']])
@pytest.mark.parametrize('kind',['wheel','tar'])
def test_duplicate_alias_collisions(tmp_path,names,kind):
    path=tmp_path/'archive'
    if kind=='wheel':
        with zipfile.ZipFile(path,'w') as z:
            for name in names: z.writestr(name,b'x')
        read=distribution.read_wheel
    else:
        with tarfile.open(path,'w') as z:
            for name in names:
                info=tarfile.TarInfo(name);info.size=1;z.addfile(info,io.BytesIO(b'x'))
        read=source_export.read_tar
    with pytest.raises(ValueError):read(path)


@pytest.mark.parametrize('kind',[tarfile.SYMTYPE,tarfile.LNKTYPE,tarfile.CHRTYPE,tarfile.BLKTYPE,tarfile.FIFOTYPE])
def test_tar_nonregular(tmp_path,kind):
    path=tmp_path/'archive.tar'
    with tarfile.open(path,'w') as z:
        info=tarfile.TarInfo('member');info.type=kind;info.linkname='target';z.addfile(info)
    with pytest.raises(ValueError):source_export.read_tar(path)


@pytest.mark.parametrize('file_type',[stat.S_IFLNK,stat.S_IFCHR,stat.S_IFBLK,stat.S_IFIFO,stat.S_IFSOCK])
def test_zip_nonregular(tmp_path,file_type):
    path=tmp_path/'archive.whl'
    with zipfile.ZipFile(path,'w') as z:
        info=zipfile.ZipInfo('member');info.external_attr=(file_type|0o777)<<16;z.writestr(info,b'target')
    with pytest.raises(ValueError):distribution.read_wheel(path)


def test_editable_origin(tmp_path):
    with pytest.raises(ValueError,match='origin'):
        consumer.verify_origin(tmp_path/'checkout/src/yield_curves/baseline.py',tmp_path/'env',[])


@pytest.mark.parametrize('kind',['missing','substituted','skip','xfail','error','incomplete-teardown','nonzero'])
def test_outcome_rejections(kind):
    selected=['tests/test_a.py::test_a','tests/test_b.py::test_b']
    phases={n:[dict(when=w,outcome='passed',xfail=False) for w in ('setup','call','teardown')] for n in selected}
    code=0
    if kind=='missing':del phases[selected[0]]
    elif kind=='substituted':phases['tests/test_c.py::test_c']=phases.pop(selected[0])
    elif kind=='skip':phases[selected[0]][1]['outcome']='skipped'
    elif kind=='xfail':phases[selected[0]][1]['xfail']=True
    elif kind=='error':phases[selected[0]][2]['outcome']='failed'
    elif kind=='incomplete-teardown':phases[selected[0]].pop()
    elif kind=='nonzero':code=1
    with pytest.raises(ValueError):selection.validate_outcomes(selected,phases,code)


def test_outcomes_complete():
    phases={'a':[dict(when=w,outcome='passed',xfail=False) for w in ('setup','call','teardown')]}
    selection.validate_outcomes(['a'],phases,0)


def test_junit_substitution(tmp_path):
    path=tmp_path/'junit.xml'
    path.write_text('<testsuites><testsuite><testcase classname="tests.test_other" name="test_other"/></testsuite></testsuites>')
    with pytest.raises(ValueError):selection.validate_junit(path,['tests/test_a.py::test_a'])


def test_directory_modification(tmp_path):
    (tmp_path/'source.py').write_bytes(b'changed')
    with pytest.raises(ValueError):source_export.verify_directory(tmp_path,{'source.py':b'original'})


@pytest.mark.parametrize('kind',['missing','substituted','no-teardown','interrupted','skipped','failed'])
def test_attempt_classification(kind):
    phases={'a':[dict(when=w,outcome='passed',xfail=False) for w in ('setup','call','teardown')]}
    code=1
    expected='INCOMPLETE'
    if kind=='missing':phases={}
    elif kind=='substituted':phases={'b':phases['a']}
    elif kind=='no-teardown':phases['a'].pop()
    elif kind=='interrupted':code=2
    elif kind=='skipped':
        phases['a'][1]['outcome']='skipped';expected='FAIL'
    elif kind=='failed':
        phases['a'][1]['outcome']='failed';expected='FAIL'
    assert selection.classify_attempt(['a'],phases,code)==expected


def test_same_count_substituted_collection():
    rows=[dict(nodeid=f'tests/test_substituted.py::test_{i}',slow=i<27) for i in range(1035)]
    with pytest.raises(ValueError,match='selection mismatch'):selection.validate_selection(rows)


@pytest.mark.parametrize('member',['.venv/pyvenv.cfg','src/yield_curves.egg-info/SOURCES.txt','src/yield_curves.dist-info/METADATA'])
def test_inherited_export_metadata(monkeypatch,member):
    tree='a'*40
    responses={('rev-parse','--verify','b'*40+'^{commit}'):('b'*40+'\n').encode(),
               ('rev-parse','b'*40+':project'):(tree+'\n').encode(),
               ('ls-tree','-rz',tree):b'100644 blob '+b'c'*40+b'\t'+member.encode()+b'\0'}
    monkeypatch.setattr(source_export,'git',lambda repo,*args:responses[args])
    with pytest.raises(ValueError,match='inherited'):source_export.tracked('repo','b'*40,'project',tree)


@pytest.mark.parametrize('malicious',['../escape.py','/absolute.py','same','content-mismatch'])
def test_export_rejects_before_writing(tmp_path,monkeypatch,malicious):
    archive=tmp_path/'source.tar'; destination=tmp_path/'destination'
    expected={'source.py':b'approved'}
    if malicious=='content-mismatch':files={'source.py':b'tampered'}
    else:files={malicious:b'tampered'}
    tar_write(archive,files)
    monkeypatch.setattr(source_export,'tracked',lambda *args:expected)
    with pytest.raises(ValueError):source_export.export('repo','a'*40,'project','b'*40,archive,destination,tmp_path/'receipt.json')
    assert not destination.exists()


def test_noncanonical_clean_export(tmp_path,monkeypatch):
    archive=tmp_path/'source.tar';destination=tmp_path/'destination'
    with tarfile.open(archive,'w') as z:
        info=tarfile.TarInfo('source.py');info.size=8;z.addfile(info,io.BytesIO(b'approved'))
    monkeypatch.setattr(source_export,'tracked',lambda *args:{'source.py':b'approved'})
    other=tmp_path/'other.tar'
    with tarfile.open(other,'w') as z:
        info=tarfile.TarInfo('source.py');info.size=8;info.mode=0o777;z.addfile(info,io.BytesIO(b'approved'))
    monkeypatch.setattr(source_export,'git',lambda *args:other.read_bytes())
    with pytest.raises(ValueError,match='clean Git archive'):
        source_export.export('repo','a'*40,'project','b'*40,archive,destination,tmp_path/'receipt.json')
    assert not destination.exists()


def test_export_rejects_trailing_bytes(tmp_path,monkeypatch):
    archive=tmp_path/'source.tar';canonical=tmp_path/'canonical.tar';destination=tmp_path/'destination'
    for path in (archive,canonical):
        with tarfile.open(path,'w') as z:
            info=tarfile.TarInfo('source.py');info.size=8;z.addfile(info,io.BytesIO(b'approved'))
    archive.write_bytes(archive.read_bytes()+b'private trailing content')
    monkeypatch.setattr(source_export,'tracked',lambda *args:{'source.py':b'approved'})
    monkeypatch.setattr(source_export,'git',lambda *args:canonical.read_bytes())
    with pytest.raises(ValueError,match='(?:clean Git archive|trailing tar payload)'):
        source_export.export('repo','a'*40,'project','b'*40,archive,destination,tmp_path/'receipt.json')
    assert not destination.exists()


@pytest.mark.parametrize('kind',['tar','wheel'])
def test_archive_trailing_payload(tmp_path,kind):
    path=tmp_path/'archive'
    if kind=='tar':
        with tarfile.open(path,'w') as z:
            info=tarfile.TarInfo('member');info.size=1;z.addfile(info,io.BytesIO(b'x'))
        read=source_export.read_tar
    else:
        wheel_write(path,{'member':b'x'},record=False)
        read=distribution.read_wheel
    path.write_bytes(path.read_bytes()+b'private trailing bytes')
    with pytest.raises(ValueError):read(path)
