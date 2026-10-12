"""Synthetic offline sensitivity controls, never actual browser captures."""
import copy
import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('fixed22',HERE/'check.py')
check=importlib.util.module_from_spec(spec); spec.loader.exec_module(check)

SOURCE={'schema':'offline-control-only'}
RECT=[257,1,222,22]

def fixture(dpr=2, offset=0):
    g={'dpr':dpr, 'viewport':{'width':1209.6,'height':644.8,'visual':None},
       'fixedParent':{'x':0,'y':0,'width':1100,'height':640},
       'parent':{'x':0,'y':0,'width':1100,'height':640},'parentTransform':'none','scroll':{'x':0,'y':0},
       'canvas':{'rect':{'x':0,'y':0,'width':1100,'height':640},
                 'client':{'width':1100,'height':640}, 'backing':{'width':1100*dpr,'height':640*dpr},
                 'css':{'width':'1100px','height':'640px','transform':'none'}},
       'caret':{'rect':{'x':350,'y':21,'width':1,'height':1},'hidden':False},
       'activeElement':'nvwa_text_input','documentFocused':True}
    rows=[{'index':offset,'timeMs':100+offset*1000,'kind':'pointerdown','target':'nvwa','trusted':True,
           'pointerId':1,'client':{'x':350,'y':12},'geometry':copy.deepcopy(g)},
          {'index':offset+1,'timeMs':350+offset*1000,'kind':'settled','after':'pointerdown',
           'originIndex':offset,'originPointerId':1,'originTimeMs':100+offset*1000,'geometry':copy.deepcopy(g)}]
    recorded=offset+2
    first=max(0,recorded-1200)
    prefix=[{'index':i,'timeMs':i*1000,'kind':'offline-control-only','geometry':copy.deepcopy(g)}
            for i in range(first,offset)]
    rows=prefix+rows
    return {'schema':'nvwa-fixed-css-dpr-v1','sessionId':'offline-control-only','source':SOURCE,'stopped':False,
            'collector':{'limit':1200,'pointerCoverage':'all document targets; drag moves only',
                         'timerDelayMs':250,'textRead':False,'viewportAndCanvasSeparate':True},
            'inventory':{'limit':1200,'recorded':recorded,'retained':len(rows),'dropped':first,
                         'firstIndex':first,'lastIndex':offset+1},'rows':rows}

def transition_fixtures(dprs=(2,2.5,2)):
    captures=[]; retained=[]
    for phase,dpr in enumerate(dprs):
        capture=fixture(dpr)
        pair=capture['rows']
        for row in pair:
            row['index']+=phase*2; row['timeMs']+=phase*2000
            if row['kind']=='settled':
                row['originIndex']+=phase*2; row['originTimeMs']+=phase*2000
        retained+=pair
        capture['rows']=copy.deepcopy(retained)
        capture['inventory'].update(recorded=len(retained),retained=len(retained),lastIndex=len(retained)-1)
        captures.append(capture)
    return captures

def args(pointer=0,row=1,dpr=2):
    return SimpleNamespace(pointer=pointer,row=row,expected_dpr=dpr,work_rect=RECT)

class Controls(unittest.TestCase):
    def reject(self,mutate):
        capture=fixture(); mutate(capture)
        with self.assertRaises((AssertionError,KeyError,TypeError,ValueError)):
            check.geometry(capture,args(),SOURCE)

    def test_green(self):
        self.assertEqual(check.geometry(fixture(),args(),SOURCE)['origin_index'],0)
    def test_wrong_timer_origin(self):
        self.reject(lambda c:c['rows'][1].update(originIndex=9))
    def test_wrong_pointer_id(self):
        self.reject(lambda c:c['rows'][1].update(originPointerId=2))
    def test_wrong_timer_time(self):
        self.reject(lambda c:c['rows'][1].update(originTimeMs=99))
    def test_stale_settled(self):
        self.reject(lambda c:c['rows'][1].update(timeMs=2100))
    def test_dpr_changed_mid_interval(self):
        self.reject(lambda c:c['rows'][1]['geometry'].update(dpr=2.5))
    def test_backing_does_not_follow(self):
        self.reject(lambda c:[r['geometry']['canvas']['backing'].update(width=1100,height=640)
                              for r in c['rows']] or None)
    def test_fixed_parent_changed(self):
        self.reject(lambda c:c['rows'][1]['geometry']['fixedParent'].update(width=1099))
    def test_fixed_canvas_changed(self):
        self.reject(lambda c:[r['geometry']['canvas']['rect'].update(width=1099.5) for r in c['rows']])
    def test_viewport_phase_change(self):
        self.reject(lambda c:c['rows'][1]['geometry']['viewport'].update(width=1200))
    def test_clipped_canvas(self):
        self.reject(lambda c:[r['geometry']['viewport'].update(height=639) for r in c['rows']])
    def test_caret_outside(self):
        self.reject(lambda c:c['rows'][1]['geometry']['caret']['rect'].update(x=1000))
    def test_untrusted_pointer(self):
        self.reject(lambda c:c['rows'][0].update(trusted=False))
    def test_external_focus(self):
        self.reject(lambda c:c['rows'][1]['geometry'].update(activeElement='other'))
    def test_wrong_source(self):
        self.reject(lambda c:c.update(source={'schema':'different'}))
    def test_drop_inventory_mismatch(self):
        self.reject(lambda c:c['inventory'].update(dropped=1))
    def test_gap(self):
        self.reject(lambda c:c['rows'][1].update(index=2))
    def test_scroll_changed(self):
        self.reject(lambda c:c['rows'][1]['geometry']['scroll'].update(x=1))
    def test_stop_state_mismatch(self):
        self.reject(lambda c:c.update(stopped=True))
    def test_parent_transformed(self):
        self.reject(lambda c:[r['geometry'].update(parentTransform='matrix(1,0,0,1,0,0)') for r in c['rows']])
    def test_second_pointer(self):
        capture=fixture()
        middle=copy.deepcopy(capture['rows'][0]); middle.update(index=1,timeMs=150,target='other')
        capture['rows'][1]['index']=2; capture['rows'].insert(1,middle)
        capture['inventory'].update(recorded=3,retained=3,lastIndex=2)
        with self.assertRaises(AssertionError): check.geometry(capture,args(row=2),SOURCE)
    def test_drop_inventory_honest_retained_pair(self):
        capture=fixture(offset=1200)
        self.assertEqual(len(capture['rows']),1200)
        result=check.geometry(capture,args(pointer=1200,row=1201),SOURCE)
        self.assertTrue(result['inventory']['prefix_truncated'])
        self.assertFalse(result['inventory']['whole_session_proof'])
    def test_fabricated_two_row_tail(self):
        capture=fixture(offset=1200)
        capture['rows']=capture['rows'][-2:]
        capture['inventory'].update(retained=2,dropped=1200,firstIndex=1200)
        with self.assertRaises(AssertionError):
            check.geometry(capture,args(pointer=1200,row=1201),SOURCE)
    def test_transition_green(self):
        result=check.transition(transition_fixtures(),
                               [0,2,4],[1,3,5],[2,2.5,2],[RECT]*3,SOURCE)
        self.assertEqual(result['actual_dprs'],[2,2.5,2])
    def test_transition_missing_scale(self):
        with self.assertRaises(AssertionError):
            check.transition(transition_fixtures((2,2,2)),
                             [0,2,4],[1,3,5],[2,2,2],[RECT]*3,SOURCE)
    def test_whole_work_real_historical_positive_and_mutants(self):
        evidence=check.ROOT/'docs/evidence/viewport'
        base=check.read(evidence/'viewport-base.nvwa.json')
        drag=check.read(evidence/'viewport-drag.nvwa.json')
        undo=check.read(evidence/'viewport-undo.nvwa.json')
        check.old.check_work(base,drag,undo,'jaw_width',.05)
        for mutation in ('missing_delta','collateral','extra_commit','incomplete_undo'):
            changed=copy.deepcopy(drag); restored=copy.deepcopy(undo)
            if mutation=='missing_delta': changed['character']['parameters']['jaw_width']=base['character']['parameters']['jaw_width']
            elif mutation=='collateral': changed['character']['parameters']['smile']=.123
            elif mutation=='extra_commit': changed['revision']+=1
            else: restored['character']['parameters']['jaw_width']=changed['character']['parameters']['jaw_width']
            with self.subTest(mutation=mutation), self.assertRaises(AssertionError):
                check.old.check_work(base,changed,restored,'jaw_width',.05)

if __name__=='__main__': unittest.main()
