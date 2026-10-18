from worker import *
run('S1_aa_1',[PYTHON,ROOT/'src/aa.py','{OUT}','1'])
for b in range(3):
 run(f'S2_pairs_{b}',[PYTHON,ROOT/'src/pair_suite.py','{OUT}','CALIBRATION',str(b)])
 run(f'S2_card_{b}',[PYTHON,ROOT/'src/card_v2.py','{OUT}',str(b)])
run('S2_setup',[PYTHON,ROOT/'src/setup_costs.py','{OUT}'])
