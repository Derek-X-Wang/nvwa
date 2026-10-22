"""Source-order controls, distinct from actual all-row baseline admission."""
import json
import unittest
import current19 as c
from geometry_checks import source_bone_order,source_triangles,topology_order,source_scale_ratios,e


class SourceOrderControls(unittest.TestCase):
    def test_actual_source_axis_dictionary_scale_ratios(self):
        source=e.corpus.diagnose.Source(e.SOURCE)
        cage=e.raw_cage({'torso_length':0,'jaw_drop':0})
        self.assertIs(type(source.axes),dict)
        self.assertEqual(set(source.axes),{0,1,2})
        # Derive expected XYZ rules directly from authenticated real MHCLO text,
        # independent of Source.parse_mapping's integer-keyed dictionary API.
        rules={}
        for line in (e.SOURCE/'garment/female_sportsuit01.mhclo').read_text().splitlines():
            fields=line.split()
            if fields and fields[0] in ('x_scale','y_scale','z_scale'):
                rules[fields[0]]=(int(fields[1]),int(fields[2]),float(fields[3]))
        expected=[]
        for axis,name in enumerate(('x_scale','y_scale','z_scale')):
            lo,hi,reference=rules[name]
            expected.append((cage[hi][axis]-cage[lo][axis])/reference)
        self.assertEqual(source_scale_ratios(source.axes,cage),expected)

    def test_sorted_child_preorder(self):
        rig={'z':{'parent':'root'},'c':{'parent':'a'},'root':{'parent':''},'a':{'parent':'root'}}
        self.assertEqual(source_bone_order(rig),['root','a','c','z'])
    def test_disconnected_cycle_rejects(self):
        with self.assertRaises(ValueError):source_bone_order({'root':{'parent':''},'a':{'parent':'b'},'b':{'parent':'a'}})
    def test_source_face_fans(self):
        faces=[{'source_ids':[3,2,1,0]},{'source_ids':[5,6,7]}]
        self.assertEqual(source_triangles(faces),[[3,2,1],[3,1,0],[5,6,7]])
        self.assertEqual(source_triangles(faces,{5,6,7}),[[3,2,1],[3,1,0]])
    def reference(self,part):
        return {part['name']:{key:{'length':len(part[key]),
                'sha256':c.digest(json.dumps(part[key],separators=(',',':')).encode())}
                for key in ('source_ids','indices')}}
    def test_exact_integer_order(self):
        part={'name':'garment','source_ids':[3,2,1],'indices':[0,1,2]}
        topology_order(part,self.reference(part))
    def test_source_id_reorder_rejects(self):
        part={'name':'garment','source_ids':[3,2,1],'indices':[0,1,2]};ref=self.reference(part)
        part['source_ids'].reverse()
        with self.assertRaises(ValueError):topology_order(part,ref)
    def test_indices_reorder_rejects(self):
        part={'name':'garment','source_ids':[3,2,1],'indices':[0,1,2]};ref=self.reference(part)
        part['indices']=[1,2,0]
        with self.assertRaises(ValueError):topology_order(part,ref)


if __name__=='__main__':unittest.main()
