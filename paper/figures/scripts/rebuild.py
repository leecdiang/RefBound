"""Rebuild the accepted figures and native tables from frozen inputs, CPU/offline.

Five generators, font/vector checks, and bounded saved-value/mark checks run.
The historical #276 mechanical preview and incomplete raw-archive audit do not.
"""

if not __debug__:
    raise SystemExit("Optimized Python is unsupported: verification must remain enabled.")

import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import zlib
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
MAIN = ['f01_obligations','f02_local_lowering','f07_confirmation','f04_few_column',
        'f05_prefill','f06_b570','f03_transaction','f08_c4_initial']
IDS = ['1','2','3','4','5','6','S1','S2']
ALTS = ['f02_layered','f03_alternate','f05_prompt_length']
PACKAGES = ['numpy','matplotlib','Pillow','pypdfium2','fonttools','pdfminer.six','PyMuPDF']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def emit(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n')


def freeze():
    checked = []
    for name, info in json.loads((ROOT/'provenance/INPUT_BYTES.json').read_text()).items():
        path = ROOT/'inputs'/name
        assert path.is_file(), f'Missing frozen input: {path.relative_to(ROOT)}'
        assert path.stat().st_size == info['bytes'] and sha(path) == info['sha256'], name
        checked.append(dict(path='inputs/'+name, bytes=path.stat().st_size, sha256=sha(path)))
    data_root = (ROOT/'inputs/scientific_data').resolve()
    with ZipFile(ROOT/'inputs/scientific_data.zip') as archive:
        rows = json.loads(archive.read('MANIFEST.json'))['files']
        for item in rows:
            member_bytes = archive.read(item['member'])
            if (len(member_bytes) != item['bytes'] or
                hashlib.sha256(member_bytes).hexdigest() != item['sha256'] or
                f'{zlib.crc32(member_bytes) & 0xffffffff:08x}' != item['crc32'] or
                archive.getinfo(item['member']).CRC != zlib.crc32(member_bytes) & 0xffffffff):
                raise ValueError('Member metadata mismatch: ' + item['member'])
        expected = {item['member']: item['sha256'] for item in rows}
        for name in [*expected, 'MANIFEST.json']:
            value = archive.read(name)
            if name in expected:
                assert hashlib.sha256(value).hexdigest() == expected[name], name
            dest = (data_root/name).resolve()
            assert data_root in dest.parents, name
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                assert dest.read_bytes() == value, f'Existing frozen member differs: {name}'
            else:
                dest.write_bytes(value)
    return checked


def sync_inventory():
    caps, owners = {}, {}
    for directory in ('method','results','tail'):
        items = json.loads((ROOT/directory/'captions.json').read_text())
        caps.update(items)
        owners.update({stem:directory+'/captions.json' for stem in items})
    assert set(caps) == set(MAIN+ALTS)
    emit(ROOT/'captions/alternatives.json', {stem:caps[stem] for stem in ALTS})
    baseline = json.loads((ROOT/'provenance/EXHIBIT_INVENTORY_BASELINE277.json').read_text())
    ledger = json.loads((ROOT/'table_design/table_ledger.json').read_text())
    table_caps = json.loads((ROOT/'table_design/captions.json').read_text())
    assert [x['table'] for x in ledger['tables']] == [str(i) for i in range(1,8)]+[f'S{i}' for i in range(1,21)]
    inventory = {}
    for stem, number in zip(MAIN, IDS):
        inventory[stem] = dict(id=number,kind='figure',label=baseline[stem]['label'],
            asset=f'figures/{stem}.pdf',svg=f'figures/{stem}.svg',caption_source=owners[stem],
            caption=caps[stem]['caption'],description=caps[stem]['description'],status='selected formal figure')
    for stem in ALTS:
        inventory[stem] = dict(id=None,kind='alternative',asset=f'alternatives/{stem}.pdf',
            svg=f'alternatives/{stem}.svg',caption_source=owners[stem],caption=caps[stem]['caption'],
            description=caps[stem]['description'],status='editable diagnostic attachment; no formal number')
    for item in ledger['tables']:
        path = ROOT/item['output']
        assert sha(path) == item['sha256'], item['output']
        inventory[path.stem] = dict(id=item['table'],kind='table',label=item['label'],asset=item['output'],
            caption_source='table_design/captions.json',caption=table_caps[path.stem],status='selected native LaTeX table')
    assert len(inventory) == 38
    emit(ROOT/'provenance/EXHIBIT_INVENTORY.json', inventory)
    return inventory


def main():
    inputs = freeze()
    work = ROOT/'.build'
    work.mkdir(exist_ok=True)
    stages = []
    with tempfile.TemporaryDirectory(prefix='integrated-font-cache-',dir=work) as cache:
        env = dict(os.environ,SOURCE_DATE_EPOCH='1794960000',FORCE_SOURCE_DATE='1',TZ='UTC',
                   MPLBACKEND='Agg',MPLCONFIGDIR=cache,PYTHONDONTWRITEBYTECODE='1')
        def run(relative,*args):
            print('Build:',relative,*args,flush=True)
            subprocess.run([sys.executable,str(ROOT/relative),*args],cwd=ROOT,env=env,check=True)
            stages.append(dict(script=relative,args=list(args),exit_code=0))
        for script in ('method_figures.py','results_figures.py','tail_figures.py',
                       'prompt_length_alternate.py','build_tables.py'):
            run('scripts/'+script)
        inventory = sync_inventory()
        run('scripts/caption_packet.py')
        run('scripts/access.py','--no-sim')
        run('tail/check_mark_sources.py')
        run('results/verify_encoding.py')
    assert {p.stem for p in (ROOT/'figures').glob('*.pdf')} == set(MAIN)
    assert {p.stem for p in (ROOT/'alternatives').glob('*.pdf')} == set(ALTS)
    assert len(list((ROOT/'tables').glob('*.tex'))) == 27
    outputs = []
    for item in inventory.values():
        for key in ('asset','svg'):
            if key in item:
                path = ROOT/item[key]
                outputs.append(dict(path=item[key],bytes=path.stat().st_size,sha256=sha(path)))
    emit(ROOT/'proof/REBUILD_REPORT.json',dict(
        scope='Offline CPU regeneration/checks of saved evidence; no model/GPU execution, network, TeX preview, or new intervals',
        status='PASS',executed_stages=stages,frozen_inputs=inputs,formal_figures=8,editable_alternatives=3,
        native_tables=27,caption_entries=len(inventory),export_files=outputs,python=platform.python_version(),
        packages={package:metadata.version(package) for package in PACKAGES},
        not_executed=['scripts/audit_values.py (optional raw archives incomplete)',
                      'scripts/press.py (historical mechanical #276 preview)',
                      'color-vision simulation or human accessibility testing','GPU/model replay']))
    print('PASS: regenerated 8 formal + 3 alternative PDF/SVG pairs and 27 native tables; bounded checks passed.')


if __name__ == '__main__':
    main()
