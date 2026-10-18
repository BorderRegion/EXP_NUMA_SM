from common import ROOT,REPO,PYTHON,UUID,sha,write,utc
from pathlib import Path
import os,json
INPUT=ROOT/'input/T10_NUMA_FROZEN_RULE_FOLLOWUP_20261016'
def runroot():
 configured=os.environ.get('FROZEN_RUN')
 return Path(configured if configured else (ROOT/'FROZEN_CURRENT_RUN.txt').read_text().strip())
