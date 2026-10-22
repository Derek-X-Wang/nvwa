"""Semantic current19 adapter around immutable experiment84 position score math.

This file requires a future author/scoring execution freeze. It is intentionally
outside the immutable baseline capture execution closure. No CLI score entry yet.
"""
import current19 as c
from geometry_checks import e


def default_roi_gate(result):
    """Keep new raw identity and explicitly require original strict default benefit."""
    c.need(result['case'] in c.CASES,'unknown current19 scoring slot')
    if result['case']==c.ANCHOR:
        roi=result['fixed_default_ROI']
        before,after=roi['baseline']['body_first'],roi['candidate']['body_first']
        c.need(type(before) is int and type(after) is int and 0<=before<=400 and 0<=after<=400,
               'invalid semantic default ROI count')
        if after>=before:
            result['failures'].append('no_measurable_default_ROI_benefit')
    return result


def score_case(case,snapshot,candidate,affected,maximum,scales,cam,fr):
    # Unchanged crossing/degeneracy/winding/body-probe/ray math and thresholds.
    # The old function's historical-name gate does not cover the new anchor ID.
    result=e.score_case(case,snapshot,candidate,affected,maximum,scales,cam,fr)
    return default_roi_gate(result)
