#!/usr/bin/env python3
"""Apply the user-authorized 100 W cap; retain all fan/emergency logic.

Default is read-only preparation. --apply and --rollback need local root rights.
Only the known controller revision is accepted; no password is read or stored.
"""
import argparse
import datetime
import difflib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
GPU = 'GPU-8cfbc08d-0090-bc29-db9a-b2a2f7261ca5'
SCRIPT = Path('/usr/local/sbin/t10_quiet_fan.py')
DROPIN = Path('/etc/systemd/system/t10-quiet-power.service.d/90-op-fused-fixed100.conf')
LOCK = HERE.parents[2]/'environment/gpu_worker.lock'
POWER_UNIT = Path('/etc/systemd/system/t10-quiet-power.service')
DROPIN_TEXT = '''[Service]
ExecStart=
ExecStart=/usr/bin/nvidia-smi -i GPU-8cfbc08d-0090-bc29-db9a-b2a2f7261ca5 -pm 1
ExecStart=/usr/bin/nvidia-smi -i GPU-8cfbc08d-0090-bc29-db9a-b2a2f7261ca5 -pl 100
'''

def replacement(source):
    assert source.count('125000') == 1, 'Unexpected recovery cap occurrences'
    assert source.count('Protection recovered; quiet cap 125 W restored') == 1
    result=source.replace('125000','100000').replace(
        'Protection recovered; quiet cap 125 W restored',
        'Protection recovered; fixed cap 100 W retained')
    compile(result,str(SCRIPT),'exec')
    return result

def command(*args):
    return subprocess.check_output(args,text=True,stderr=subprocess.STDOUT).strip()

def atomic_write(path, data, mode):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.'+path.name)
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(data);f.flush();os.fsync(f.fileno())
        os.chmod(tmp,mode);os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def restart():
    command('systemctl','daemon-reload')
    command('systemctl','restart','t10-quiet-power.service')
    command('systemctl','restart','t10-quiet-fan.service')
    assert command('systemctl','is-active','t10-quiet-fan.service')=='active'

def restore(backup):
    backup=backup.resolve()
    assert backup.parent==Path('/var/lib') and backup.name.startswith('t10-fixed100-backup-')
    old=(backup/'t10_quiet_fan.py').read_bytes()
    info=json.loads((backup/'manifest.json').read_text())
    assert hashlib.sha256(old).hexdigest()==info['controller_sha256']
    atomic_write(SCRIPT,old,0o755)
    if DROPIN.exists():
        assert DROPIN.read_text()==DROPIN_TEXT, 'Refuse to delete unrelated drop-in changes'
        DROPIN.unlink()
    restart()
    print('Restored previous 125/100 W policy from',backup)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    group=p.add_mutually_exclusive_group()
    group.add_argument('--apply',action='store_true')
    group.add_argument('--rollback',type=Path)
    a=p.parse_args()
    if a.apply or a.rollback:
        if os.geteuid()!=0: p.error('Root required: run this exact script locally with sudo; do not send passwords.')
    if a.rollback:
        with LOCK.open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            restore(a.rollback)
        return
    old=(HERE/'t10_quiet_fan.before.py').read_text()
    new=replacement(old)
    assert POWER_UNIT.read_bytes()==(HERE/'t10-quiet-power.before.service').read_bytes(), 'Power service changed'
    if SCRIPT.read_text()==new and DROPIN.exists() and DROPIN.read_text()==DROPIN_TEXT:
        print('Configuration already applied; current cap:',command('nvidia-smi','-i',GPU,
            '--query-gpu=power.limit','--format=csv,noheader,nounits'))
        return
    assert SCRIPT.read_text()==old, 'Controller changed; stop for review'
    assert not DROPIN.exists(), 'Drop-in already exists; stop for review'
    if not a.apply:
        print(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),
              fromfile=str(SCRIPT),tofile=str(SCRIPT)+' (proposed)')))
        print(str(DROPIN)+'\n'+DROPIN_TEXT)
        print('READ_ONLY_PREPARATION: no system settings changed')
        return
    with LOCK.open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        compute=command('nvidia-smi','-i',GPU,'--query-compute-apps=pid,process_name','--format=csv,noheader')
        active=[line for line in compute.splitlines() if line.strip() and
                line.split(', ',1)[-1] not in ('/usr/libexec/gnome-remote-desktop-daemon',)]
        assert not active, 'Compute processes active: '+repr(active)
        stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        backup=Path('/var/lib')/('t10-fixed100-backup-'+stamp)
        backup.mkdir(mode=0o700)
        shutil.copy2(SCRIPT,backup/'t10_quiet_fan.py')
        shutil.copy2(POWER_UNIT,backup/'t10-quiet-power.service')
        info=dict(time_utc=stamp,controller_sha256=hashlib.sha256(old.encode()).hexdigest(),
                  requested_cap_w=100,gpu=GPU,fan_and_emergency_logic='UNCHANGED')
        (backup/'manifest.json').write_text(json.dumps(info,indent=2)+'\n')
        try:
            atomic_write(SCRIPT,new.encode(),0o755)
            atomic_write(DROPIN,DROPIN_TEXT.encode(),0o644)
            restart()
            cap=float(command('nvidia-smi','-i',GPU,'--query-gpu=power.limit','--format=csv,noheader,nounits'))
            assert cap==100, f'Unexpected cap {cap}'
            print(json.dumps(dict(status='APPLIED_AND_READ_BACK',power_limit_w=cap,
                  backup=str(backup),fan_service='active',rollback_command=
                  f'sudo python3 "{Path(__file__).resolve()}" --rollback "{backup}"'),indent=2))
        except BaseException:
            restore(backup)
            raise

if __name__=='__main__': main()
