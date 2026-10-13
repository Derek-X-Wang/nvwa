import json
import unittest
from reconcile_native import reconcile

class BoundaryControls(unittest.TestCase):
    def line(self, row): return 'NVWA_METAL_PROBE '+json.dumps({'pid':123,**row})
    def gpu(self, **changes):
        return {'event':'command_completed','gpu_start_host_seconds':10.,'gpu_end_host_seconds':10.002,'status_raw':4,'valid_completed_gpu_span':True,**changes}
    def present(self, **changes):
        return {'event':'drawable_presented_callback','index':1,'presented_host_seconds':10.,'valid_presented_time':True,'ca_host_seconds':10.01,'callback_monotonic_before_ns':20_000_000_000,'callback_monotonic_after_ns':20_000_000_100,**changes}
    def test_real_boundary_duration_and_calibration_arithmetic(self):
        result=reconcile(self.line(self.gpu())+'\n'+self.line(self.present()),123)
        self.assertAlmostEqual(result['valid_gpu_command_samples'][0]['duration_ms'],2.)
        interval=result['first_observed_valid_drawable']['converted_CLOCK_MONOTONIC_interval_ns']
        self.assertAlmostEqual(interval[0],19_990_000_000,places=3)
        self.assertEqual(interval[1]-interval[0],100)
        self.assertTrue(result['first_registered_drawable_callback_valid'])
        self.assertIn('NOT-RUN',result['first_character_pixels'])
    def test_zero_and_failed_GPU_never_count(self):
        a=self.gpu(gpu_start_host_seconds=0.,gpu_end_host_seconds=0.,valid_completed_gpu_span=False)
        b=self.gpu(status_raw=5,valid_completed_gpu_span=False)
        result=reconcile(self.line(a)+'\n'+self.line(b),123)
        self.assertEqual(result['valid_gpu_command_samples'],[])
        self.assertEqual(len(result['invalid_gpu_command_samples']),2)
    def test_skipped_drawable_is_not_display(self):
        result=reconcile(self.line(self.present(presented_host_seconds=0.,valid_presented_time=False)),123)
        self.assertIsNone(result['first_observed_valid_drawable'])
        self.assertFalse(result['first_registered_drawable_callback_valid'])
    def test_invalid_flags_and_PID_fail_closed(self):
        with self.assertRaises(AssertionError): reconcile(self.line(self.gpu(status_raw=5)),123)
        with self.assertRaises(AssertionError): reconcile(self.line(self.present()),124)
    def test_negative_duration_and_bad_calibration_rejected(self):
        with self.assertRaises(AssertionError): reconcile(self.line(self.gpu(gpu_end_host_seconds=9.)),123)
        with self.assertRaises(AssertionError): reconcile(self.line(self.present(callback_monotonic_after_ns=1)),123)

if __name__=='__main__': unittest.main()
