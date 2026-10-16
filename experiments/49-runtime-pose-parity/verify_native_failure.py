"""Check retained native failure evidence; this does not launch the app."""
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'offline'))
from compare import SCHEDULE, compare
from evaluator import Rejected


def verify():
    results = HERE / 'probe/results'
    for name, code in [('native', '0'), ('native-visual', '0'),
                       ('native-negative', '1')]:
        if (results / (name + '-exit-code.txt')).read_text().strip() != code:
            raise Rejected(name + ': wrong retained process exit code')
    raw = json.loads((results / 'native-negative.json').read_text())
    if (type(raw.get('schema_version')) is not int or
            raw['schema_version'] != 1 or raw.get('platform') != 'native' or
            raw.get('schedule') != SCHEDULE or raw.get('status') != 'failed' or
            raw.get('error') != 'wrong Work/profile' or raw.get('samples') != []):
        raise Rejected('wrong retained failure condition')
    try:
        compare(raw)
    except Rejected as error:
        if str(error) != 'capture completed without error':
            raise Rejected('comparator rejected for an unexpected reason') from error
    else:
        raise Rejected('failed capture was incorrectly accepted')
    print('PASS retained native positive exits 0; wrong-Work launch exit 1; failed capture rejected. No new runtime collected.')


if __name__ == '__main__':
    verify()
