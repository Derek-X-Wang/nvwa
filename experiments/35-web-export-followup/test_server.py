import unittest
from server import Handler, body_for, members

class ExactMapTests(unittest.TestCase):
    def test_foreign_host_and_origin_rejected_before_file_access(self):
        class Request:
            def __init__(self, headers):
                self.headers = headers
                self.codes = []
            def send_error(self, code):
                self.codes.append(code)
        for headers in ({'Host':'foreign.invalid'}, {'Host':'127.0.0.1:9206','Origin':'https://foreign.invalid'}):
            request = Request(headers)
            Handler.do_GET(request)
            self.assertEqual(request.codes, [403])

    def test_no_traversal_listing_or_arbitrary_file(self):
        for path in ('/', '/case-1/', '/case-1/../Cargo.lock', '/case-1/%2e%2e/Cargo.lock', '/etc/passwd'):
            self.assertIsNone(body_for(path))

    def test_only_observer_insertion_changes_original_page(self):
        original = members()['/case-1/index.html'][0].read_bytes()
        served = body_for('/case-1/index.html')[0]
        self.assertEqual(served.replace(b'  <script src="./observer.js"></script>\n', b''), original)

    def test_payloads_are_original_bytes(self):
        for path, (filename, _) in members().items():
            if not path.endswith('index.html'):
                self.assertEqual(body_for(path)[0], filename.read_bytes())

    def test_second_case_changes_only_observer_and_pre_init_delay(self):
        original = members()['/case-2/index.html'][0].read_bytes()
        served = body_for('/case-2/index.html')[0]
        restored = served.replace(b'  <script src="./observer.js"></script>\n', b'').replace(b'\n    await new Promise(resolve => setTimeout(resolve, 5000));', b'')
        self.assertEqual(restored, original)

if __name__ == '__main__':
    unittest.main()
