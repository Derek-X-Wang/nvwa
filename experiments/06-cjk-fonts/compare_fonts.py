#!/usr/bin/env python3
"""Pinned, offline-capable full-cmap CJK font comparison. No application runtime dependency.

Run from any directory. Requires existing fontTools 4.60.2 for derivation only.
Downloads are opt-in; all generated binaries remain under .work/cjk-fonts/.
"""
import argparse
import gzip
import hashlib
import json
import pathlib
import sys
import urllib.request

import fontTools
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

REPO = pathlib.Path(__file__).resolve().parents[2]
WORK = REPO / ".work/cjk-fonts"
EXPERIMENT = pathlib.Path(__file__).resolve().parent
GF_COMMIT = "a85815a42757630ce188fdad368c2dfc444d4773"
NOTO_COMMIT = "523d033d6cb47f4a80c58a35753646f5c3608a78"
STATIC_SHA256 = "902150f57c7bdd221323aad3697d0f78edd015a5fe1af39675e918a8959d51ea"
GF_BASE = f"https://raw.githubusercontent.com/google/fonts/{GF_COMMIT}/ofl/notosanssc/"
NOTO_BASE = f"https://raw.githubusercontent.com/notofonts/noto-cjk/{NOTO_COMMIT}/"
SOURCES = {
    "NotoSansSC[wght].ttf": (GF_BASE + "NotoSansSC%5Bwght%5D.ttf", "a3041811a78c361b1de50f953c805e0244951c21c5bd412f7232ef0d899af0da"),
    "OFL.txt": (GF_BASE + "OFL.txt", "1c05c68c34f9708415aada51f17e1b0092d2cea709bf4a94cd38114f9e73d7d9"),
    "METADATA.pb": (GF_BASE + "METADATA.pb", "c6c4bdb785793b2de1da177caeeffcd0c90d7680bdab2de8f88ab45007bc59bc"),
    "upstream_info.md": (GF_BASE + "upstream_info.md", "9a10facde2dc3ded9d6314b4a595c0a7f3e421fc2f3840104d2d67f4d542b918"),
    "DESCRIPTION.en_us.html": (GF_BASE + "DESCRIPTION.en_us.html", "05ef1b6673b1ec826b56691be57bd5b189e96d014e32134c3c5dddd819396142"),
    "noto-cjk-LICENSE.txt": (NOTO_BASE + "LICENSE", "6a73f9541c2de74158c0e7cf6b0a58ef774f5a780bf191f2d7ec9cc53efe2bf2"),
    "NotoSansSC-upstream-VF.ttf": (NOTO_BASE + "Sans/Variable/TTF/Subset/NotoSansSC-VF.ttf", "d68bafcb48a2707749396aa12bbbd833cb70401f3a9a689fd2902c7e0d295964"),
}
# Fixed block slots, not a claim that all slots have assigned characters.
BLOCKS = {
    "Basic Latin printable": (0x20, 0x7E),
    "CJK Symbols and Punctuation": (0x3000, 0x303F),
    "CJK Unified Ideographs Extension A": (0x3400, 0x4DBF),
    "CJK Unified Ideographs": (0x4E00, 0x9FFF),
    "CJK Compatibility Ideographs": (0xF900, 0xFAFF),
    "Halfwidth and Fullwidth Forms": (0xFF00, 0xFFEF),
    "CJK Unified Ideographs Extension B": (0x20000, 0x2A6DF),
    "CJK Unified Ideographs Extension C": (0x2A700, 0x2B73F),
    "CJK Unified Ideographs Extension D": (0x2B740, 0x2B81F),
    "CJK Unified Ideographs Extension E": (0x2B820, 0x2CEAF),
    "CJK Unified Ideographs Extension F": (0x2CEB0, 0x2EBEF),
    "CJK Unified Ideographs Extension I": (0x2EBF0, 0x2EE5F),
    "CJK Unified Ideographs Extension G": (0x30000, 0x3134F),
    "CJK Unified Ideographs Extension H": (0x31350, 0x323AF),
    "CJK Unified Ideographs Extension J": (0x323B0, 0x3347F),
    "CJK Compatibility Ideographs Supplement": (0x2F800, 0x2FA1F),
    "Bopomofo": (0x3100, 0x312F),
    "Bopomofo Extended": (0x31A0, 0x31BF),
    "Hiragana": (0x3040, 0x309F),
    "Katakana": (0x30A0, 0x30FF),
    "Hangul Syllables": (0xAC00, 0xD7AF),
}
SAMPLES = {
    "simplified_ui_and_filenames": "女娲 工程 打开 保存 另存为 导入 导出 撤销 重做 角色 骨骼 动作 场景 资源 动画 时间轴 姿态 旋转 缩放 移动 播放 暂停 停止 加载 失败 错误 文件路径 请先选择模型 客户张伟/龙年春节/角色模型_最终版（修订二）.glb 上海小笼包_测试.nvwa 重庆音乐会 绿茶 你好世界",
    "traditional_filenames": "女媧 專案 開啟 儲存 檔案 路徑 動畫 骨骼 臺灣 臺北 龍年春節/角色模型_最終版（修訂二）.glb 廣東話 測試資料夾 龜灣鬱鬱",
    "mixed_latin_digits_punctuation": "Alice_角色_2026-10-10_v2.0（draft）.nvwa 中文，。！？：；、【】《》「」『』￥ＡＢＣ１２３ +−×÷ →←↑↓ ✓ ✗",
    "rare_chinese_limit_probe": "龘 靐 齉 𠮷 𠀀 𰻞 𱁬",
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def verify_sources(download):
    source_dir = WORK / "upstream"
    source_dir.mkdir(parents=True, exist_ok=True)
    for name, (url, expected) in SOURCES.items():
        path = source_dir / name
        if not path.exists():
            if not download:
                raise RuntimeError(f"Missing {path}; use --download for pinned official sources")
            with urllib.request.urlopen(url, timeout=60) as response:
                data = response.read(32 * 1024 * 1024 + 1)
            if len(data) > 32 * 1024 * 1024 or sha256(data) != expected:
                raise RuntimeError(f"Source size/hash mismatch: {name}")
            path.write_bytes(data)
        if sha256(path.read_bytes()) != expected:
            raise RuntimeError(f"Source hash mismatch: {name}")
    return source_dir


def compact_ranges(points):
    ranges = []
    for point in sorted(points):
        if ranges and point == ranges[-1][1] + 1:
            ranges[-1][1] = point
        else:
            ranges.append([point, point])
    return [f"U+{a:04X}" if a == b else f"U+{a:04X}–U+{b:04X}" for a, b in ranges]


def cmap_entries(font):
    return {point: glyph for point, glyph in font.getBestCmap().items() if font.getGlyphID(glyph) != 0}


def cmap_snapshot(font):
    return [{"platform": table.platformID, "encoding": table.platEncID, "format": table.format, "language": table.language, "cmap": sorted(getattr(table, 'cmap', {}).items()), "variation_selectors": sorted(getattr(table, 'uvsDict', {}).items())} for table in font['cmap'].tables]


def measure(path):
    data = path.read_bytes()
    with TTFont(path, recalcTimestamp=False) as font:
        cmap = cmap_entries(font)
        points = set(cmap)
        blocks = {}
        for name, (start, end) in BLOCKS.items():
            slots = set(range(start, end + 1))
            blocks[name] = {"start": f"U+{start:04X}", "end": f"U+{end:04X}", "slots": len(slots), "mapped": len(points & slots), "missing_ranges": compact_ranges(slots - points)}
        samples = {}
        for name, sample in SAMPLES.items():
            sample_points = set(map(ord, sample))
            missing = sample_points - points
            samples[name] = {"text": sample, "unique_codepoints": len(sample_points), "mapped": len(sample_points & points), "missing": [{"codepoint": f"U+{point:04X}", "character": chr(point)} for point in sorted(missing)]}
        return {"path": str(path.relative_to(REPO)), "sha256": sha256(data), "bytes": len(data), "gzip_level_9_mtime_0_bytes": len(gzip.compress(data, compresslevel=9, mtime=0)), "glyph_count": font['maxp'].numGlyphs, "unicode_cmap_codepoints": len(points), "cmap_semantics_sha256": sha256(json.dumps(cmap_snapshot(font), sort_keys=True).encode()), "cmap_subtables": [{"platform": table.platformID, "encoding": table.platEncID, "format": table.format, "mappings": len(getattr(table, 'cmap', {})), "variation_selectors": len(getattr(table, 'uvsDict', {}))} for table in font['cmap'].tables], "tables": sorted(font.keys()), "axes": [{"tag": axis.axisTag, "min": axis.minValue, "default": axis.defaultValue, "max": axis.maxValue} for axis in font['fvar'].axes] if 'fvar' in font else [], "weight_class": font['OS/2'].usWeightClass, "name_records": {str(identifier): sorted({entry.toUnicode() for entry in font['name'].names if entry.nameID == identifier}) for identifier in [0, 1, 2, 3, 4, 5, 6, 13, 14, 16, 17, 25]}, "blocks": blocks, "samples": samples, "all_supported_ranges": compact_ranges(points)}


def derive_static(source, target):
    with TTFont(source, recalcTimestamp=False) as font:
        original_cmap = cmap_entries(font)
        original_cmap_snapshot = cmap_snapshot(font)
        original_order = font.getGlyphOrder()
        static = instantiateVariableFont(font, {'wght': 400}, inplace=True, updateFontNames=True)
        # Explicit derivative identity; preserve copyright and OFL records.
        names = {1: 'Nvwa Sans SC', 2: 'Regular', 3: 'NvwaSansSC-Regular;Noto2.004;wght400', 4: 'Nvwa Sans SC Regular', 6: 'NvwaSansSC-Regular', 16: 'Nvwa Sans SC', 17: 'Regular'}
        static['name'].names = [entry for entry in static['name'].names if entry.nameID != 25]
        for entry in list(static['name'].names):
            if entry.nameID in names:
                static['name'].setName(names[entry.nameID], entry.nameID, entry.platformID, entry.platEncID, entry.langID)
        for identifier, value in names.items():
            static['name'].setName(value, identifier, 3, 1, 0x409)
        static.recalcTimestamp = False
        static.save(target, reorderTables=True)
    with TTFont(target, recalcTimestamp=False) as result:
        assert cmap_entries(result) == original_cmap, 'Cmap mapping changed'
        assert cmap_snapshot(result) == original_cmap_snapshot, 'Cmap subtable semantics changed'
        assert result.getGlyphOrder() == original_order, 'Glyph order/coverage changed'
        assert not any(table in result for table in ['fvar', 'gvar', 'avar', 'HVAR', 'MVAR', 'VVAR']), 'Variable tables remain'
        assert result['OS/2'].usWeightClass == 400, 'Wrong weight'
        assert result['name'].getDebugName(13), 'OFL record lost'
        assert result['name'].getDebugName(0), 'Copyright record lost'
        assert all('Source' not in result['name'].getDebugName(identifier) for identifier in [1, 2, 3, 4, 6, 16, 17]), 'Reserved primary name used'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true', help='Fetch only missing hash-pinned official font/license/source files')
    parser.add_argument('--rebuild', action='store_true', help='Repeat deterministic static derivation instead of using cached candidate')
    args = parser.parse_args()
    if fontTools.__version__ != '4.60.2':
        raise RuntimeError('Derivation requires already-installed fontTools 4.60.2; do not auto-install')
    source_dir = verify_sources(args.download)
    target_dir = WORK / 'candidates'
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / 'NvwaSansSC-Regular.ttf'
    previous_hash = sha256(target.read_bytes()) if target.exists() else None
    if not target.exists() or args.rebuild:
        derive_static(source_dir / 'NotoSansSC[wght].ttf', target)
        if previous_hash and sha256(target.read_bytes()) != previous_hash:
            raise RuntimeError('Static rebuild differs from previous bytes')
    if sha256(target.read_bytes()) != STATIC_SHA256:
        raise RuntimeError('Static candidate does not match pinned derivative hash')
    variable = measure(source_dir / 'NotoSansSC[wght].ttf')
    static = measure(target)
    with TTFont(source_dir / 'NotoSansSC[wght].ttf') as a, TTFont(target) as b, TTFont(source_dir / 'NotoSansSC-upstream-VF.ttf') as c:
        cmap_identical = cmap_entries(a) == cmap_entries(b)
        upstream_cmap_identical = cmap_entries(a) == cmap_entries(c)
        assert cmap_identical and upstream_cmap_identical
        assert cmap_snapshot(a) == cmap_snapshot(b) == cmap_snapshot(c)
        assert a.getGlyphOrder() == b.getGlyphOrder() == c.getGlyphOrder()
    result = {'python_version': sys.version, 'fonttools_version': fontTools.__version__, 'google_fonts_commit': GF_COMMIT, 'noto_cjk_commit': NOTO_COMMIT, 'sources': {name: {'url': url, 'sha256': expected} for name, (url, expected) in SOURCES.items()}, 'variable': variable, 'static_regular_400': static, 'acceptance': {'static_cmap_identical_to_variable': cmap_identical, 'google_fonts_cmap_identical_to_noto_upstream': upstream_cmap_identical, 'static_has_no_variable_axes': not static['axes'], 'static_weight_is_400': static['weight_class'] == 400, 'basic_latin_printable_complete': static['blocks']['Basic Latin printable']['mapped'] == 95, 'simplified_and_traditional_samples_complete': all(not static['samples'][key]['missing'] for key in ['simplified_ui_and_filenames', 'traditional_filenames']), 'static_font_under_11_MiB': static['bytes'] < 11 * 1024 * 1024, 'static_gzip_under_7_MiB': static['gzip_level_9_mtime_0_bytes'] < 7 * 1024 * 1024, 'native_rendering': 'NOT-RUN', 'web_rendering': 'NOT-RUN'}, 'savings': {'bytes': variable['bytes'] - static['bytes'], 'gzip_bytes': variable['gzip_level_9_mtime_0_bytes'] - static['gzip_level_9_mtime_0_bytes']}}
    (EXPERIMENT / 'measurements.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    (EXPERIMENT / 'OFL.txt').write_bytes((source_dir / 'OFL.txt').read_bytes())
    print(json.dumps({'variable': {key: variable[key] for key in ['bytes', 'gzip_level_9_mtime_0_bytes', 'sha256', 'unicode_cmap_codepoints', 'glyph_count', 'axes']}, 'static': {key: static[key] for key in ['bytes', 'gzip_level_9_mtime_0_bytes', 'sha256', 'unicode_cmap_codepoints', 'glyph_count']}, 'acceptance': result['acceptance'], 'savings': result['savings']}, indent=2))


if __name__ == '__main__':
    main()
