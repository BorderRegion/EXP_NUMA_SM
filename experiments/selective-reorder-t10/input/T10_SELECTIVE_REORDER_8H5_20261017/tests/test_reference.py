from pathlib import Path
import sys,unittest,math,json,tempfile,subprocess,shutil
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'reference'))
from selection_math import *
from train_rules import train

class TestSelection(unittest.TestCase):
 def test_base_setup_is_priced(self):
  self.assertEqual(choose_base({'LIB':100,'SPLIT':70},{'SPLIT':200},{'SPLIT':1},1),'LIB')
  self.assertEqual(choose_base({'LIB':100,'SPLIT':70},{'SPLIT':200},{'SPLIT':1},100),'SPLIT')
 def test_preselected_base_is_respected(self):
  d=choose_plan({'LIB':100,'SPLIT':90,'PC0_0':95},{'PC0_0':0},{'PC0_0':0},1000,frozen_base_action='LIB')
  self.assertEqual(d.base_action,'LIB')
 def test_default_keeps_best_base(self):
  d=choose_plan({'LIB':100,'SINGLE':95,'SPLIT':90,'PC0_0':89},{'PC0_0':0},{'PC0_0':2},1000)
  self.assertEqual(d.chosen_action,'SPLIT')
 def test_large_margin_can_intervene(self):
  d=choose_plan({'LIB':100,'SPLIT':90,'PC1_0':70},{'PC1_0':100},{'PC1_0':3},100)
  self.assertEqual(d.chosen_action,'PC1_0')
 def test_short_life_returns_base(self):
  p={'LIB':100,'SPLIT':90,'PC1_0':70};cost={'PC1_0':1000};err={'PC1_0':3}
  self.assertEqual(choose_plan(p,cost,err,1).chosen_action,'SPLIT')
  self.assertEqual(choose_plan(p,cost,err,1000).chosen_action,'PC1_0')
 def test_unknown_life_does_not_amortize(self):
  d=choose_plan({'LIB':100,'PC0_0':80},{'PC0_0':500},{'PC0_0':1},None)
  self.assertEqual(d.chosen_action,'LIB');self.assertIsNone(d.expected_reuse)
 def test_ood_goes_direct_lib(self):
  d=choose_plan({'LIB':100,'SPLIT':10,'PC0_0':1},{'PC0_0':0},{'PC0_0':0},1000,in_envelope=False)
  self.assertEqual(d.chosen_action,'LIB')
 def test_missing_cost_is_not_free(self):
  self.assertEqual(choose_plan({'LIB':100,'PC0_0':1},{},{'PC0_0':0},1000).chosen_action,'LIB')
 def test_no_negative_costs(self):
  with self.assertRaises(ValueError):choose_plan({'LIB':100,'PC0_0':1},{'PC0_0':-1},{'PC0_0':0},1000)
 def test_allowed_actions(self):
  self.assertEqual(choose_plan({'LIB':100,'PC0_0':1},{'PC0_0':0},{'PC0_0':0},1000,allowed_actions=['LIB']).chosen_action,'LIB')
 def test_lifecycle(self):
  self.assertEqual(amortized_total_us(10,100,20),300)

class TestMath(unittest.TestCase):
 def test_additive_main_effects_vanish(self):
  a=[[10+i+2*j for j in range(4)] for i in range(4)]
  self.assertLess(max(abs(x) for row in additive_pc(a) for x in row),1e-12)
 def test_pair_direction(self):
  a=[[8 if (i<2)==(j<2) else 12 for j in range(4)] for i in range(4)]
  x=pc_features(a,[10]*4,[2]*4,0,0,0)
  y=pc_features(a,[10]*4,[2]*4,0,1,0)
  self.assertLess(x[2],0);self.assertGreater(y[2],0)
 def test_bad_matrix(self):
  with self.assertRaises(ValueError):additive_pc([[1,2],[3]])
 def test_opaque_split(self):
  a=log_shape_features(1,1024,4096,32,64,None)
  b=log_shape_features(1,1024,4096,32,64,1)
  self.assertEqual(a[-1],0);self.assertEqual(b[-1],1)
  self.assertEqual(a[5],0);self.assertGreater(b[5],0)
 def test_ridge_constant(self):
  m=fit_ridge([[1,2],[1,2],[1,2]],[5,5,5])
  self.assertAlmostEqual(m.predict_us([1,2]),5,places=9)
 def test_quantile(self):self.assertAlmostEqual(quantile([1,2,3,4],.5),2.5)

class TestTraining(unittest.TestCase):
 def data(self):
  return [dict(cohort='development',case_id=f'D{i}',action=a,cpu_ready_us=(10+i)*f,
      shape_features=[math.log2(i+1),i],resource_features=[0.1*i,0.2])
      for i in range(6) for a,f in [('LIB',1),('SINGLE',1.1),('PC0_0',.9)] for rep in range(2)]
 def test_fit_and_shared_base(self):
  models,out=train(self.data())
  self.assertEqual(models['SHAPE']['LIB'].to_dict(),models['RESOURCE']['LIB'].to_dict())
  self.assertEqual(len(out['loso']['SHAPE']),18)
  self.assertIn('PC0_0',out['paired_error_margin_us']['RESOURCE'])
 def test_forbid_test_training(self):
  d=self.data();d[0]['cohort']='confirmation'
  with self.assertRaises(ValueError):train(d)
 def test_whole_shape_card_freeze(self):
  d=self.data();d[1]['resource_features']=[5,8]
  with self.assertRaises(ValueError):train(d)
 def test_missing_action(self):
  d=[r for r in self.data() if not(r['case_id']=='D0' and r['action']=='PC0_0')]
  with self.assertRaises(ValueError):train(d)

class TestCompiledHost(unittest.TestCase):
 @unittest.skipUnless(shutil.which('g++'),'g++ not installed')
 def test_cpp_predictions_and_bypass(self):
  m=fit_ridge([[0,1],[1,2],[2,1],[3,0]],[10,12,14,16])
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);(p/'model.hpp').write_text(compile_ridge_header({'LIB':m}))
   (p/'test.cpp').write_text(r'''
#include "model.hpp"
#include "binding_skeleton.hpp"
#include <iostream>
#include <iomanip>
#include <cassert>
using namespace selective_binding;
struct P:Plan { P(Action a){action=a;partition=-1;} void enqueue(const void*,void*) override {} };
struct F:Factory {int n=0,g=0;std::unique_ptr<Plan> native_plan(Action a) override {n++;return std::make_unique<P>(a);} std::unique_ptr<Plan> placement_plan(Action a) override {g++;return std::make_unique<P>(a);} };
int main(){F f; auto p=bind(Action::Lib,f); assert(f.n==1&&f.g==0);auto q=bind(Action::Pc10,f);assert(f.g==1);double x[2]={1.5,1.0};std::cout<<std::setprecision(17)<<selective_generated::predict_LIB(x);}
''')
   subprocess.run(['g++','-std=c++17','-O2','-I',str(R/'reference'),str(p/'test.cpp'),'-o',str(p/'test')],check=True,capture_output=True)
   y=float(subprocess.check_output([str(p/'test')]).decode())
   self.assertAlmostEqual(y,m.predict_us([1.5,1.0]),places=10)

if __name__=='__main__':unittest.main(verbosity=2)
