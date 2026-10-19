"""Source-level panel layout regression; no browser/focus-recovery claim."""
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest


class PanelDocument(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.panels = {}
        self.details = []
        self.styles = []
        self.in_style = False
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        if tag == 'style':
            self.in_style = True
        if tag == 'details':
            identifier = dict(attrs).get('id')
            self.panels[identifier] = {'tag': tag, 'parent': self.details[-1] if self.details else None}
            self.details.append(identifier)

    def handle_endtag(self, tag):
        if tag == 'style':
            self.in_style = False
        if tag == 'details':
            self.details.pop()

    def handle_data(self, data):
        if self.in_style:
            self.styles.append(data)


def require_panel_flow(source):
    """Apply authored position declarations to actual panel IDs/tag selectors."""
    doc = PanelDocument(source)
    if set(doc.panels) != {'controls', 'wire'} or doc.panels['wire']['parent'] != 'controls':
        raise AssertionError('actual nested controls/wire details required')
    positions = {name: ('static', (-1, -1)) for name in doc.panels}
    for order, (selectors, declarations) in enumerate(re.findall(r'([^{}]+)\{([^{}]*)\}', ''.join(doc.styles))):
        properties = dict(item.split(':', 1) for item in declarations.split(';') if ':' in item)
        properties = {key.strip(): value.strip() for key, value in properties.items()}
        if 'position' not in properties:
            continue
        for selector in selectors.split(','):
            selector = selector.strip()
            if not re.fullmatch(r'#[\w-]+|[a-z]+', selector):
                raise AssertionError('unsupported position selector in bounded panel regression: '+selector)
            for name, node in doc.panels.items():
                if selector not in ('#'+name, node['tag']):
                    continue
                priority = (1 if selector.startswith('#') else 0, order)
                if priority >= positions[name][1]:
                    positions[name] = properties['position'], priority
    if positions['controls'][0] != 'fixed':
        raise AssertionError('outer controls must retain fixed panel positioning')
    if positions['wire'][0] != 'static':
        raise AssertionError('nested wire must stay in normal panel flow; shared fixed viewport positioning overlaps summaries')
    return {name: value[0] for name, value in positions.items()}


class PanelLayout(unittest.TestCase):
    def test_actual_nested_wire_remains_in_panel_flow(self):
        source = Path(__file__).with_name('index.html').read_text()
        self.assertEqual(require_panel_flow(source), {'controls': 'fixed', 'wire': 'static'})

    def test_original_global_details_selector_is_rejected(self):
        source = Path(__file__).with_name('index.html').read_text()
        self.assertEqual(source.count('#controls{position:fixed;'), 1)
        original_defect = source.replace('#controls{position:fixed;', 'details{position:fixed;', 1)
        with self.assertRaisesRegex(AssertionError, 'nested wire must stay in normal panel flow'):
            require_panel_flow(original_defect)


if __name__ == '__main__':
    unittest.main()
