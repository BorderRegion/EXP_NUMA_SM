"""A changed queued source must not affect an already frozen process."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'tools'))
from frozen_source import freeze

with tempfile.TemporaryDirectory() as directory:
    temp=Path(directory);source=temp/'source';(source/'tools').mkdir(parents=True)
    (source/'config').mkdir()
    (source/'tools/helper.py').write_text('VALUE="original dependency"\n')
    (source/'config/input.json').write_text('{"value": "original input"}')
    entry=source/'tools/entry.py'
    entry.write_text('from helper import VALUE\nfrom pathlib import Path\n'
                    'print(VALUE)\nprint((Path(__file__).parents[1]/"config/input.json").read_text())\n')
    frozen,records=freeze(source,entry,temp/'snapshot')
    entry.write_text('raise RuntimeError("must not execute")\n')
    (source/'tools/helper.py').write_text('VALUE="changed dependency"\n')
    (source/'config/input.json').write_text('{"value": "changed input"}')
    env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
    output=subprocess.check_output([sys.executable,str(frozen)],text=True,env=env)
    assert output=='original dependency\n{"value": "original input"}\n'
    assert all(not ((temp/'snapshot'/r['path']).stat().st_mode & 0o222) for r in records)
    # Cleanup only the temporary test fixture, not any real run snapshot.
    for parent,dirs,files in os.walk(temp/'snapshot'):
        Path(parent).chmod(0o755)
        for name in files:(Path(parent)/name).chmod(0o644)
result=dict(status='CPU_FROZEN_EXECUTION_PASS',entry_and_import_and_input_frozen=True,
            gpu_worker_started=False,old_registry_modified=False)
(ROOT/'reports/frozen_execution_validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
