import unittest
from verify import EVIDENCE,png_info

class PNGReceiptNegativeControls(unittest.TestCase):
    def test_corrupted_actual_download_fails_crc(self):
        original=(EVIDENCE/'case-2-auto.png').read_bytes()
        corrupt=bytearray(original)
        corrupt[29]^=1
        with self.assertRaisesRegex(AssertionError,'PNG CRC'):
            png_info(bytes(corrupt))

    def test_truncated_actual_download_cannot_pass(self):
        original=(EVIDENCE/'case-1-explicit.png').read_bytes()
        with self.assertRaises(AssertionError):
            png_info(original[:-12])

if __name__=='__main__':
    unittest.main()
