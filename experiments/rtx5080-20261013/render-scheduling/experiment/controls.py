from common import *
import random
j=json.loads((ROOT/'experiment/POLICY_FREEZE.json').read_text())
for block in range(2):
    for si,scene in enumerate(['train','bonsai']):
        values=[j['settings'][str(p)] for p in [5,6,7,8]]
        random.Random(50802026+si).shuffle(values)
        if block:values=values[::-1]
        settings=','.join(':'.join(map(str,v)) for v in values)
        bench(f'controls_{block}_{scene}',scene,'calib',settings,128,256,2,'calib',phase='controls')
