from common import *
import numpy as np

def main():
 for fn in ['EXECUTION_SHA256.json','TUNING_EXECUTION_SHA256.json']:
  for rel,dig in read(ROOT/'freeze'/fn).items():assert sha(ROOT/rel)==dig,rel
 from select_geometry import compute as geometry
 a=geometry();b=read(ROOT/'freeze/SELECTED_GEOMETRY.json');b.pop('frozen_utc');assert a==b
 from select_recipes import compute as recipes
 a=recipes();b=read(ROOT/'freeze/TUNED_RECIPES.json');b.pop('frozen_utc');assert a==b
 from analyze import main as first
 from analyze_tuning import main as second
 from audit_confirmation import main as audit
 first();second();audit();print('ALL_RAW_MAPS_SELECTIONS_AND_RESULTS_RECOMPUTED_PASS')
if __name__=='__main__':main()
