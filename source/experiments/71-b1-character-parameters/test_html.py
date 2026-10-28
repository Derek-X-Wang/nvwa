"""Static DOM presentation controls only; no browser stall or runtime proof."""
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest

EXPORTS = {'acceptance-report', 'acceptance-frame', 'acceptance-work'}


class Textareas(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items = []

    def handle_starttag(self, tag, attrs):
        if tag == 'textarea':
            self.items.append(dict(attrs))


def validate_exports(raw):
    parser = Textareas()
    parser.feed(raw)
    readonly = [attrs for attrs in parser.items if 'readonly' in attrs]
    if len(readonly) != len(EXPORTS) or {a.get('id') for a in readonly} != EXPORTS:
        raise ValueError('exactly three visible read-only JSON exports required')
    for attrs in readonly:
        if attrs.get('wrap') != 'off' or 'hidden' in attrs:
            raise ValueError('read-only JSON exports must be visible with wrap off')
    commands = [a for a in parser.items if a.get('id') == 'acceptance-command']
    if len(commands) != 1 or 'readonly' in commands[0]:
        raise ValueError('typed command input must remain editable')


class HtmlExports(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = Path(__file__).with_name('index.html').read_text()

    def test_actual_visible_readonly_json_exports_have_wrap_off(self):
        validate_exports(self.raw)

    def test_each_export_rejects_missing_or_soft_wrap(self):
        for identity in sorted(EXPORTS):
            opening = re.search(r'<textarea\b[^>]*id="' + identity + r'"[^>]*>', self.raw).group()
            for replacement in ('', 'soft'):
                changed = re.sub(r' wrap="[^"]*"', '', opening)
                if replacement:
                    changed = changed.replace('>', f' wrap="{replacement}">')
                bad = self.raw.replace(opening, changed)
                with self.subTest(identity=identity, wrap=replacement):
                    with self.assertRaises(ValueError):
                        validate_exports(bad)

    def test_css_prevents_large_json_soft_wrapping(self):
        compact = ''.join(self.raw.split())
        self.assertIn('textarea[readonly]{white-space:pre;word-break:normal;overflow-wrap:normal;overflow:auto}', compact)


if __name__ == '__main__':
    unittest.main()
