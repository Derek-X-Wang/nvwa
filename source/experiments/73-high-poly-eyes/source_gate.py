"""Lightweight, fresh-process entry for exact frozen source admission."""
import json
from pathlib import Path
import sys

from frozen_context import SourceInputRejected, validate_source_inputs


def main():
    if sys.argv[1:]:
        sys.stderr.write('usage: source_gate.py (no arguments)\n')
        return 64
    exp = Path(__file__).resolve().parent
    try:
        context = validate_source_inputs(exp.parents[1], exp)
    except SourceInputRejected as error:
        record = {'protocol': 'nvwa73-source-gate-v1', 'outcome': 'rejected',
                  'message': str(error)}
        code = 2
    else:
        record = {'protocol': 'nvwa73-source-gate-v1', 'outcome': 'accepted',
                  'context': context}
        code = 0
    print(json.dumps(record, ensure_ascii=True, separators=(',', ':')))
    return code


if __name__ == '__main__':
    sys.exit(main())
