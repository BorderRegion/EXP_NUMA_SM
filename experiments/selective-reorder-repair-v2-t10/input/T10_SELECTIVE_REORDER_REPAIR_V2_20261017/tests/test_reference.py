import sys, math, json, unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'reference'))
from paired_stats import quartet_contrast,error_card,margin_value,latency_bucket,block_bootstrap_logratios
from relative_policy import ACTIONS,decide,fit_linear,FeatureBank,additive_features,aggregate_pairs,train,export_linear_header

class PairedTests(unittest.TestCase):
    def test_same(self):self.assertAlmostEqual(quartet_contrast('ABBA',[100]*4)['ratio'],1.)
    def test_abba(self):self.assertAlmostEqual(quartet_contrast('ABBA',[100,80,80,100])['ratio'],.8)
    def test_baab(self):self.assertAlmostEqual(quartet_contrast('BAAB',[80,100,100,80])['ratio'],.8)
    def test_signed(self):self.assertGreater(quartet_contrast('ABBA',[100,110,110,100])['delta_us'],0.)
    def test_log_linear_drift(self):
        t=[100*math.exp(.01*i)*(1 if x=='A' else .8) for i,x in enumerate('ABBA')]
        self.assertAlmostEqual(quartet_contrast('ABBA',t)['ratio'],.8)
    def test_bad_order(self):
        with self.assertRaises(ValueError):quartet_contrast('AABB',[1]*4)
    def test_bad_times(self):
        with self.assertRaises(ValueError):quartet_contrast('ABBA',[1,float('nan'),1,1])
    def test_bootstrap_unit(self):
        r=block_bootstrap_logratios([math.log(.9)]*6,draws=100)
        self.assertEqual(r['n_independent_blocks'],6);self.assertAlmostEqual(r['ratio'],.9)

class RiskTests(unittest.TestCase):
    def test_single_sided(self):self.assertEqual(error_card([(100,-.5)]*8)['pooled'],0.)
    def test_small_large_separated(self):
        c=error_card([(100,.02)]*6+[(6000,.8)]*6)
        self.assertAlmostEqual(margin_value(c,100),.02);self.assertAlmostEqual(margin_value(c,6000),.8)
    def test_sparse_fallback_dimensionless(self):
        c=error_card([(100,.02)]*2+[(6000,.3)]*8)
        self.assertEqual(c['buckets']['0']['source'],'pooled_log')
        self.assertAlmostEqual(margin_value(c,100),.3)
    def test_aa_not_added(self):
        c=error_card([(100,.05)]*8)
        self.assertAlmostEqual(margin_value(c,100,.04),.05)
        self.assertAlmostEqual(margin_value(c,100,.06),.06)
    def test_strata(self):self.assertEqual([latency_bucket(x) for x in [249,250,1999,2000]],[0,1,1,2])

class DecisionTests(unittest.TestCase):
    def setUp(self):
        self.z={a:0. for a in ACTIONS};self.setup={a:0. for a in ACTIONS}
        self.q={(a,b):.02 for a in ACTIONS[1:] for b in (('LIB',) if a in ('SINGLE','SPLIT') else ACTIONS[:3])}
    def go(self,**kw):return decide(kw.pop('logs',self.z),kw.pop('margins',self.q),kw.pop('setup_us',self.setup),kw.pop('predicted_lib_us',200),kw.pop('expected_reuse',1024),**kw)
    def test_identity_keeps_lib(self):self.assertEqual(self.go().chosen_action,'LIB')
    def test_small_request_not_absolute_block(self):
        self.z['PC0_0']=math.log(.8);self.q[('PC0_0','LIB')]=.05
        self.assertEqual(self.go(selection_delta_us=1.).chosen_action,'PC0_0')
    def test_large_prediction_risk_rejects(self):
        self.z['PC0_0']=math.log(.9);self.q[('PC0_0','LIB')]=.3
        self.assertEqual(self.go().chosen_action,'LIB')
    def test_common_base(self):
        self.z['SINGLE']=math.log(.7);self.z['PC0_0']=math.log(.8)
        b=self.go(mode='BASE').chosen_action
        self.assertEqual(b,'SINGLE');self.assertEqual(self.go(frozen_base=b).chosen_action,'SINGLE')
    def test_pc_vs_true_base(self):
        self.z['SINGLE']=math.log(.7);self.z['PC0_0']=math.log(.6)
        self.assertEqual(self.go(frozen_base='SINGLE').chosen_action,'PC0_0')
    def test_init_short_long(self):
        self.z['PC0_0']=math.log(.8);self.setup['PC0_0']=1000
        self.assertEqual(self.go(expected_reuse=1).chosen_action,'LIB')
        self.assertEqual(self.go(expected_reuse=1024).chosen_action,'PC0_0')
    def test_unknown_horizon_not_free(self):
        self.z['PC0_0']=math.log(.8);self.setup['PC0_0']=1000
        self.assertEqual(self.go(expected_reuse=None).chosen_action,'LIB')
    def test_missing_setup_not_zero(self):
        self.z['PC0_0']=math.log(.1);self.setup['PC0_0']=None
        self.assertEqual(self.go().chosen_action,'LIB')
    def test_ood_before_model(self):
        self.assertEqual(decide({}, {},{},float('nan'),None,in_envelope=False).chosen_action,'LIB')
    def test_scale_invariance_zero_cost(self):
        self.z['PC0_0']=math.log(.8)
        self.assertEqual(self.go(predicted_lib_us=50).chosen_action,self.go(predicted_lib_us=5000).chosen_action)
    def test_no_force_pc(self):
        self.z.update({a:math.log(1.2) for a in ACTIONS[3:]})
        self.assertEqual(self.go().chosen_action,'LIB')

class ModelTests(unittest.TestCase):
    def test_linear_is_log_ratio_not_exp_time(self):
        m=fit_linear([[0],[1],[2]],[math.log(.8)]*3)
        self.assertAlmostEqual(m.predict([1.5]),math.log(.8))
    def test_additive_effect_zero(self):
        s={'matrix_us':[[100+i*10+j for j in range(4)] for i in range(4)],'P_us':[20]*4,'R_us':[2]*4}
        for part in range(3):
            for pi in range(2):self.assertAlmostEqual(additive_features(s,part,pi)[2],0.)
    def test_consistent_rename(self):
        s={'matrix_us':[[100+2*i+3*j+(i==j)*-3 for j in range(4)] for i in range(4)],'P_us':[10,11,13,17],'R_us':[1,2,3,4]}
        ids=[2,0,3,1];p={'matrix_us':np.asarray(s['matrix_us'])[np.ix_(ids,ids)].tolist(),'P_us':np.asarray(s['P_us'])[ids].tolist(),'R_us':np.asarray(s['R_us'])[ids].tolist()}
        np.testing.assert_allclose(additive_features(s,0,0),additive_features(p,1,0),atol=1e-14)
    def test_train_leakage_rejected(self):
        row=dict(case_id='V01',action='SINGLE',block=0,round=0,protocol_id='p',state_epoch='s',cohort='new_confirmation',log_ratio=0.,reference_geomean_us=100)
        with self.assertRaises(ValueError):aggregate_pairs([row])
    def test_epoch_mixing_rejected(self):
        r=dict(case_id='D01',action='SINGLE',block=0,round=0,protocol_id='p',state_epoch='s',cohort='development_remeasured',log_ratio=0.,reference_geomean_us=100)
        with self.assertRaises(ValueError):aggregate_pairs([r,dict(r,state_epoch='other',round=1)])
    def test_toy_fit_shape_units_and_self_card(self):
        cases=json.loads((ROOT/'plans/cases.json').read_text())[:8]
        bins=json.loads((ROOT/'plans/legacy_action_recipes.json').read_text())
        card={'representatives':[]}
        for c in cases[:4]:
            sample={'matrix_us':[[100+2*i+3*j-(2 if i==j else 0) for j in range(4)] for i in range(4)],'P_us':[80,82,83,81],'R_us':[5,6,5,6]}
            card['representatives'].append(dict(case=c['id'],shape=[c[q] for q in ('M','N','K')],samples=[sample,dict(sample)]))
        rows=[]
        for i,c in enumerate(cases):
            for b in range(2):
                for ai,a in enumerate(ACTIONS[1:]):
                    rows.append(dict(case_id=c['id'],action=a,block=b,round=0,protocol_id='TOY_ONLY',state_epoch='TOY',cohort='development_remeasured',log_ratio=math.log(.9+.01*ai),reference_geomean_us=100+10*i))
        model=train(dict(cases=cases,bins=bins,card=card,pairs=rows))
        self.assertEqual(model['n_independent_shapes'],8);self.assertTrue(model['card_self_excluded_in_loso'])
        self.assertEqual(model['models']['SHAPE']['SINGLE'],model['models']['RESOURCE']['SINGLE'])
        self.assertIn('inline double SHAPE_SINGLE',export_linear_header(model))

if __name__=='__main__':unittest.main()
