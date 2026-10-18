"""Controls for the actual offline fitting/weight/LBS seams; no asset/source mutation."""
from pathlib import Path
import tempfile
import unittest
import fit

HERE=Path(__file__).resolve().parent
(HERE/'.work').mkdir(exist_ok=True)
IDENTITY=[1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.]


class FittingControls(unittest.TestCase):
    def test_complete_cage_and_exact_split_duplicates(self):
        part={'source_ids':[0,1,0],'rest_positions':[[1.,2.,3.],[4.,5.,6.],[1.,2.,3.]]}
        cage,dup=fit.source_cage(part,count=2)
        self.assertEqual(len(cage),2);self.assertEqual(dup,1)
        part['rest_positions'][2][0]+=1e-10
        with self.assertRaisesRegex(ValueError,'conflicting'):fit.source_cage(part,count=2)

    def test_missing_or_wrong_source_ids_reject(self):
        for ids in ([0],[0,2],[0,-1],[0,True]):
            with self.subTest(ids=ids),self.assertRaises(ValueError):
                fit.source_cage({'source_ids':ids,'rest_positions':[[0.,0.,0.] for _ in ids]},count=2)

    def test_signed_reference_offset_units_without_abs_or_double_conversion(self):
        mapping={'rules':{a:{'helpers':[0,1],'reference_m':2*.1} for a in range(3)},'rows':[{'helpers':[0],'coefficients':[1.],'offset_m':[.2*.1]*3}]}
        points,scales=fit.fit_rest(mapping,{0:[0.,0.,0.],1:[-.4,.4,.2]})
        self.assertEqual(scales,{0:-2.,1:2.,2:1.})
        self.assertEqual(points,[[-.04000000000000001,.04000000000000001,.020000000000000004]])

    def test_mapping_wrong_id_coefficients_reference_and_mask_reject(self):
        header='obj_file x.obj\nx_scale 0 1 1\ny_scale 0 1 1\nz_scale 0 1 1\nverts 0\n'
        with tempfile.TemporaryDirectory(dir=HERE/'.work') as tmp:
            p=Path(tmp)/'mapping.mhclo'
            for bad in [header+'19158\n',header+'0 1 2 0 0 0 0 0 0\n',header+'0 1 2 nan 1 1 0 0 0\n',header+'0\ndelete_verts\n1\n',header.replace('x_scale 0 1 1','x_scale 0 1 0')+'0\n']:
                p.write_text(bad)
                with self.assertRaises(ValueError):fit.parse_mapping(p,.1)
            p.write_text(header+'0 1 2 -0.5 1.0 0.5 0.1 0.2 0.3\n')
            row=fit.parse_mapping(p,.1)['rows'][0]
            self.assertEqual(row['coefficients'],[-.5,1.,.5])
            self.assertEqual(row['raw_coefficients'],[-.5,1.,.5])

    def test_signed_final_aggregation_keeps_all_positive_not_signed_clamp(self):
        names=['head','neck']
        mapping={'rows':[{'helpers':[0,1],'coefficients':[-.5,1.5]}]}
        rows,stats=fit.transfer(mapping,{'head':{0:1.,1:.5},'neck':{0:0.,1:.5}},names)
        self.assertEqual(rows,[[[0,.25],[1,.75]]])
        # Clamping source coefficients would give head=.5, a different result.
        self.assertNotEqual(rows[0][0][1],.5)
        rows,stats=fit.transfer(mapping,{'head':{0:1.},'neck':{1:1.}},names)
        self.assertEqual(rows,[[[1,1.]]]);self.assertEqual(stats['negative_final_aggregates_omitted'],1)
        with self.assertRaises(ValueError):fit.transfer(mapping,{'head':{},'neck':{}},names)

    def test_full_five_influence_lbs_and_invalid_rows(self):
        bones=[]
        for j in range(53):
            m=list(IDENTITY);m[12]=j;bones.append({'skin':m})
        row=[[j,w] for j,w in enumerate([.125,.125,.25,.25,.25])]
        self.assertEqual(fit.lbs([[1.,2.,3.]],[row],bones),[[3.375,2.,3.]])
        for invalid in [[],[[0,-1.]],[[53,1.]],[[0,float('nan')]],[[0,.5],[0,.5]],[[0,.9]]]:
            with self.subTest(row=invalid),self.assertRaises(ValueError):fit.lbs([[1.,2.,3.]],[invalid],bones)

    def test_stage_transform_once_and_no_source_root_reapplication(self):
        display=list(IDENTITY);display[13]=10.
        self.assertEqual(fit.point(display,[1.,2.,3.]),[1.,12.,3.])
        self.assertNotEqual(fit.point(display,fit.point(display,[1.,2.,3.])),[1.,12.,3.])

    def test_obj_uv_seams_preserved_and_wrong_uv_or_missing_source_reject(self):
        with tempfile.TemporaryDirectory(dir=HERE/'.work') as tmp:
            p=Path(tmp)/'x.obj'
            header='v 1 2 3\nv 4 5 6\nv 7 8 9\nvt 0 0\nvt 1 0\nvt 1 1\nvt 0 1\n'
            p.write_text(header+'f 1/1 2/2 3/3\nf 1/4 2/2 3/3\n')
            mesh=fit.obj_mesh(p,3)
            self.assertIn((0,0),mesh['render_source_uv_pairs']);self.assertIn((0,3),mesh['render_source_uv_pairs'])
            self.assertEqual(mesh['uv_bevy_v_flipped'][0],[0.,1.])
            for face in ['f 1/5 2/2 3/3\n','f 1/1 2/2 4/3\n','f 1/1 1/2 1/3\n','f 1 2 3\n']:
                p.write_text(header+face)
                with self.assertRaises(ValueError):fit.obj_mesh(p,3)


if __name__=='__main__':unittest.main(verbosity=2)
