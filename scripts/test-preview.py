"""Focused transfer/identity controls; no claim of actual rendering."""
import base64
import importlib.util
from http.server import BaseHTTPRequestHandler
from pathlib import Path
import socket
import struct
import time
import unittest
import zlib

spec = importlib.util.spec_from_file_location('preview', Path(__file__).with_name('preview.py'))
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)


def chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)


def png(width=1280, height=720):
    return (preview.PNG_SIGNATURE + chunk(b'IHDR', struct.pack('>IIBBBBB',width,height,8,6,0,0,0))
            + chunk(b'IDAT',zlib.compress((b'\0'+b'\0'*(width*4))*height)) + chunk(b'IEND',b''))


class TransferControls(unittest.TestCase):
    def setUp(self):
        self.request = {'seconds':2.0,'effective_seconds':2.0,'work_sha256':'request-sha',
                        'document_revision':7,'camera':{'distance':4.4},
                        'foot_clearance_required':True,
                        'effective_camera':{'distance':preview.f32(4.4)}}
        self.payload = {'status':'rendered','runtime':{
            'schema_version':1,'status':'rendered',**self.request,'camera':self.request['effective_camera'],
            'foot_clearance':{'unit':'cm','method':'b1_visible_body_foot_min_stage_y',
                              'floor_stage_y_m':0,'left_cm':-0.5,'right_cm':4.0},
            'playing':False,'capture_callback':True},
            'png_data_url':'data:image/png;base64,'+base64.b64encode(png()).decode()}

    def test_complete_transfer(self):
        raw, runtime = preview.accept_result(self.payload,self.request)
        self.assertEqual(preview.png_dimensions(raw),(1280,720))
        self.assertEqual(runtime['foot_clearance']['left_cm'],-0.5)

    def test_motion_rejects_missing_or_invalid_clearance(self):
        runtime = self.payload['runtime']
        original = runtime['foot_clearance']
        for invalid in (None, dict(original, unit='m'), dict(original, left_cm=True),
                        dict(original, right_cm=float('nan')), dict(original, floor_stage_y_m=1)):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ValueError,'clearance'):
                runtime['foot_clearance'] = invalid
                preview.accept_result(self.payload,self.request)
        del runtime['foot_clearance']
        with self.assertRaisesRegex(ValueError,'clearance'):
            preview.accept_result(self.payload,self.request)

    def test_static_clearance_is_explicitly_unavailable(self):
        self.request['foot_clearance_required'] = False
        with self.assertRaisesRegex(ValueError,'Static'):
            preview.accept_result(self.payload,self.request)
        self.payload['runtime']['foot_clearance'] = None
        preview.accept_result(self.payload,self.request)

    def test_missing_or_truncated_pixels_are_rejected(self):
        for raw in (b'',png()[:-1],preview.PNG_SIGNATURE,png()+b'extra'):
            with self.subTest(length=len(raw)), self.assertRaises(ValueError):
                preview.png_dimensions(raw)

    def test_corrupt_pixels_are_rejected(self):
        raw = bytearray(png())
        raw[50] ^= 1
        with self.assertRaisesRegex(ValueError,'CRC'):
            preview.png_dimensions(bytes(raw))

    def test_wrong_dimensions_are_rejected(self):
        self.payload['png_data_url'] = 'data:image/png;base64,'+base64.b64encode(png(64,64)).decode()
        with self.assertRaisesRegex(ValueError,'1280x720'):
            preview.accept_result(self.payload,self.request)

    def test_wrong_work_revision_camera_or_readiness_is_rejected(self):
        for key, bad in [('work_sha256','old-sha'),('document_revision',6),('camera',{'distance':5}),
                         ('capture_callback',False),('playing',True),('status','loading')]:
            with self.subTest(key=key):
                old = self.payload['runtime'][key]
                self.payload['runtime'][key] = bad
                with self.assertRaises(ValueError):
                    preview.accept_result(self.payload,self.request)
                self.payload['runtime'][key] = old
        preview.accept_result(self.payload,self.request)

    def test_wrong_nonfinite_or_boolean_time_is_rejected(self):
        for seconds in (0,1.99,float('nan'),float('inf'),True,None,'2'):
            with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                self.payload['runtime']['seconds'] = seconds
                preview.accept_result(self.payload,self.request)

    def test_reported_failure_is_not_a_success_image(self):
        self.payload['status'] = 'failed'
        self.payload['error'] = 'WebGPU adapter unavailable'
        with self.assertRaisesRegex(ValueError,'WebGPU adapter unavailable'):
            preview.accept_result(self.payload,self.request)

    def test_invalid_encoding_is_rejected(self):
        self.payload['png_data_url'] = 'data:image/png;base64,%%%'
        with self.assertRaisesRegex(ValueError,'encoding'):
            preview.accept_result(self.payload,self.request)

    def test_short_decimal_and_promoted_f32_use_the_same_exact_camera(self):
        self.assertEqual(preview.f32(3.8),3.799999952316284)
        self.assertEqual(preview.f32(0.95),0.949999988079071)
        self.assertEqual(self.request['camera']['distance'],4.4)
        self.assertNotEqual(self.request['camera'],self.request['effective_camera'])
        preview.accept_result(self.payload,self.request)

    def test_adjacent_f32_camera_or_time_still_fails_exactly(self):
        def next_f32(value):
            bits = struct.unpack('>I',struct.pack('>f',value))[0]
            return struct.unpack('>f',struct.pack('>I',bits+1))[0]
        old = self.payload['runtime']['camera']
        self.payload['runtime']['camera'] = {'distance':next_f32(4.4)}
        with self.assertRaisesRegex(ValueError,'identity'):
            preview.accept_result(self.payload,self.request)
        self.payload['runtime']['camera'] = old
        self.payload['runtime']['seconds'] = next_f32(2.0)
        with self.assertRaisesRegex(ValueError,'time differs'):
            preview.accept_result(self.payload,self.request)

    def test_f32_overflow_and_nonfinite_values_fail(self):
        for value in (1e300,float('inf'),float('nan')):
            with self.subTest(value=value), self.assertRaises(ValueError):
                preview.f32(value)

    def test_wrong_result_shapes_are_explicit_failures(self):
        for payload in ([],None,{'status':'rendered','runtime':[]}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                preview.accept_result(payload,self.request)

    def test_idle_preconnection_does_not_block_owner_deadline(self):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass
        deadline = time.monotonic()+0.3
        server = preview.PreviewServer(('127.0.0.1',0),Handler,deadline)
        server.timeout = 0.05
        client = socket.create_connection(server.server_address)
        started = time.monotonic()
        try:
            while time.monotonic() < deadline:
                server.handle_request()
            server.server_close()
            self.assertLess(time.monotonic()-started,1.0)
        finally:
            client.close()
            server.server_close()


if __name__ == '__main__':
    unittest.main()
