"""Stdlib adversarial controls exercise the packer's actual authenticate/decode/publish seams."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile
import zlib

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('pack_assets', HERE.parent/'tools/pack_assets.py')
pack = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pack)


def archive(entries):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, data, mode in entries:
            info = zipfile.ZipInfo(name)
            info.create_system = 3
            info.external_attr = mode << 16
            z.writestr(info, data)
    return stream.getvalue()


def authenticated(data, selected):
    return pack.authenticate(io.BytesIO(data), (len(data), pack.digest(data)), selected)


def chunk(kind, data):
    return struct.pack('>I', len(data))+kind+data+struct.pack('>I', zlib.crc32(kind+data)&0xffffffff)


def png(raw, w=2, h=1, color=6, depth=8, interlace=0, compressed=None):
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,depth,color,0,0,interlace))+chunk(b'IDAT',zlib.compress(raw) if compressed is None else compressed)+chunk(b'IEND',b'')


class ArchiveControls(unittest.TestCase):
    def setUp(self):
        self.data = b'authenticated fixture'
        self.selected = {'chosen/file.txt': (len(self.data), pack.digest(self.data))}
        self.good = archive([('chosen/file.txt', self.data, stat.S_IFREG|0o644), ('other.txt', b'not extracted', stat.S_IFREG|0o644)])

    def test_exact_allowlist_only(self):
        self.assertEqual(authenticated(self.good, self.selected), {'chosen/file.txt': self.data})

    def test_wrong_archive_hash_and_size(self):
        for identity in [(len(self.good), '0'*64), (len(self.good)+1, pack.digest(self.good))]:
            with self.assertRaisesRegex(ValueError, 'archive .* mismatch'):
                pack.authenticate(io.BytesIO(self.good), identity, self.selected)

    def test_wrong_member_hash_and_size(self):
        for identity in [(len(self.data), '0'*64), (len(self.data)+1, pack.digest(self.data))]:
            with self.assertRaises(ValueError):
                authenticated(self.good, {'chosen/file.txt': identity})

    def test_missing_truncated_duplicate_traversal_and_symlink(self):
        bads = [archive([('other', b'x', stat.S_IFREG|0o644)]), self.good[:-12],
                archive([('chosen/file.txt', self.data, stat.S_IFREG|0o644), ('../outside', b'x', stat.S_IFREG|0o644)]),
                archive([('chosen/file.txt', self.data, stat.S_IFLNK|0o777)])]
        # Duplicate names are invalid even if the selected bytes/hash agree.
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            bads.append(archive([('chosen/file.txt',self.data,stat.S_IFREG|0o644)]*2))
        for bad in bads:
            with self.subTest(size=len(bad)), self.assertRaises((ValueError,zipfile.BadZipFile)):
                authenticated(bad, self.selected)

    def test_safe_name_rejects_windows_absolute_and_dot_components(self):
        for name in ['../x','/x','a/../b','a/./b','a//b','C:/x','a\\x','']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                pack.safe_name(name)

    def test_real_cli_rejection_creates_no_output(self):
        with tempfile.TemporaryDirectory(dir=HERE) as temp:
            root = Path(temp)
            source = root/'wrong.zip'
            source.write_bytes(self.good)
            result = subprocess.run([sys.executable,'-B',str(HERE.parent/'tools/pack_assets.py'),'--archive',str(source),'--output',str(root/'output')],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('archive size mismatch',result.stderr)
            self.assertFalse((root/'output').exists())
            link = root/'archive-link.zip'
            link.symlink_to(source)
            with self.assertRaises(OSError):
                pack.prepare(link)


class PNGControls(unittest.TestCase):
    def test_all_five_filters_decode_known_pixels(self):
        # Independent hand-authored encoded rows for two RGB pixels. Every
        # row should reconstruct [10,20,30,40,50,60], including prior-row use.
        rows = bytes([0,10,20,30,40,50,60,
                      1,10,20,30,30,30,30,
                      2,0,0,0,0,0,0,
                      3,5,10,15,15,15,15,
                      4,0,0,0,0,0,0])
        result = pack.inspect_png(png(rows,h=5,color=2),(2,5,2))
        self.assertEqual(result['decoded_sha256'],pack.digest(bytes([10,20,30,40,50,60])*5))
        self.assertEqual(result['row_filters'],{0:1,1:1,2:1,3:1,4:1})
        self.assertEqual(result['alpha']['opaque_pixels'],10)

    def test_rgba_alpha_statistics(self):
        result = pack.inspect_png(png(bytes([0,11,22,33,0,44,55,66,128])),(2,1,6))
        self.assertEqual(result['alpha']['zero_pixels'],1)
        self.assertEqual(result['alpha']['partial_pixels'],1)
        self.assertEqual(result['alpha']['at_or_above_128_pixels'],1)
        self.assertEqual(result['alpha']['opaque_pixels'],0)

    def test_crc_truncation_size_format_and_bomb_rejections(self):
        good = png(bytes([0])+bytes(8))
        corrupted = bytearray(good);corrupted[29] ^= 1
        bads = [bytes(corrupted),good[:-1],good+b'x',
                png(bytes([0])+bytes(8),depth=16),png(bytes([0])+bytes(8),interlace=1),
                png(bytes([5])+bytes(8)),png(bytes([0])+bytes(7)),png(bytes([0])+bytes(9)),
                png(b'',compressed=zlib.compress(bytes(1024*1024))),
                png(b'',compressed=zlib.compress(bytes(9))[:-1]),
                png(b'',compressed=zlib.compress(bytes(9))+b'trailing')]
        for i,bad in enumerate(bads):
            with self.subTest(case=i),self.assertRaises((ValueError,zlib.error)):
                pack.inspect_png(bad,(2,1,6))
        with self.assertRaisesRegex(ValueError,'dimensions'):
            pack.inspect_png(good,(2048,2048,6))


class PublishControls(unittest.TestCase):
    def test_deterministic_outputs_and_existing_or_symlink_destination(self):
        with tempfile.TemporaryDirectory(dir=HERE) as temp:
            root = Path(temp)
            payload = {'one/file':b'one','two/file':b'two'}
            pack.publish(root/'a',payload);pack.publish(root/'b',payload)
            pack.verify_existing(root/'a',payload)
            self.assertEqual({str(p.relative_to(root/'a')):p.read_bytes() for p in (root/'a').rglob('*') if p.is_file()},payload)
            self.assertEqual((root/'a/one/file').read_bytes(),(root/'b/one/file').read_bytes())
            with self.assertRaises(ValueError):pack.publish(root/'a',payload)
            (root/'link').symlink_to(root/'a',target_is_directory=True)
            with self.assertRaises(ValueError):pack.publish(root/'link/child',payload)
            self.assertFalse((root/'a/child').exists())
            with self.assertRaises(ValueError):pack.publish(root/'bad',{'../escape':b'x'})
            self.assertFalse((root/'escape').exists())
            self.assertFalse((root/'bad').exists())
            (root/'a/extra').write_bytes(b'extra')
            with self.assertRaises(ValueError):pack.verify_existing(root/'a',payload)
            (root/'a/extra').unlink()
            (root/'a/one/file').write_bytes(b'bad')
            with self.assertRaises(ValueError):pack.verify_existing(root/'a',payload)
            (root/'a/one/file').unlink()
            (root/'a/one/file').symlink_to(root/'b/one/file')
            with self.assertRaises(ValueError):pack.verify_existing(root/'a',payload)

    def test_actual_extracted_manifest_and_all_bytes(self):
        root = HERE.parent/'assets'
        receipt = json.loads((root/'asset-manifest.json').read_bytes())
        expected = set(receipt['outputs']) | {'asset-manifest.json'}
        self.assertEqual({str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()},expected)
        self.assertEqual(len(pack.MEMBERS),10)
        for name,identity in receipt['outputs'].items():
            data = (root/name).read_bytes()
            self.assertEqual((len(data),pack.digest(data)),(identity['size'],identity['sha256']))
        self.assertEqual(sum(identity[0] for identity in pack.MEMBERS.values()),6769409)
        for name,expected in pack.PNG_EXPECTED.items():
            self.assertEqual(tuple(receipt['png'][name][k] for k in ('width','height','color_type')),expected)
        for name,identity in pack.MEMBERS.items():
            self.assertEqual((root/name).stat().st_size,identity[0])
            self.assertEqual(pack.digest((root/name).read_bytes()),identity[1])


if __name__ == '__main__':
    unittest.main(verbosity=2)
