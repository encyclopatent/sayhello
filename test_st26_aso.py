"""ST26 ASO 括号标注（MOE / LNA）的测试

覆盖四部分：
  1. 厂商括号格式 → 旧格式的转换（含大小写、全角撇号、名称变体、报错路径）
  2. parse_sequence 对两条 ASO 真实序列的解析结果
  3. 生成 XML 时的注释形式（modified_base + mod_base=OTHER + note）
  4. 连续硫代磷酸酯键的区段合并，以及既有两种格式的回归

运行: python test_st26_aso.py
也可被 pytest 直接收集（断言失败会抛 AssertionError）。
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from xml_generator import generate_xml, merge_phosphorothioate_regions
from parser import convert_bracket_format_to_old, parse_sequence

# 用户给的两条真实 ASO 序列
MOE_ASO = (
    "G[2'-MOE,PS]T[2'-MOE,PS]T[2'-MOE,PS]A[PS]G[PS]A[PS]A[PS]T[PS]T[PS]"
    "G[PS]A[PS]A[PS]G[PS]T[PS]G[PS]A[2'-MOE,PS]G[2'-MOE,PS]A[2'-MOE,PS]"
)
LNA_ASO = (
    "A[LNA,PS]G[LNA,PS]A[LNA,PS]C[PS]T[PS]C[PS]T[PS]T[PS]C[PS]C[PS]"
    "A[PS]T[PS]T[PS]C[PS]T[PS]A[LNA,PS]C[5-Me-LNA-C,PS]C[5-Me-LNA-C,PS]"
)


def check(label, actual, expected):
    if actual == expected:
        print(f"✅ {label}")
        return
    print(f"❌ {label}\n     期望: {expected!r}\n     实际: {actual!r}")
    raise AssertionError(f"{label}: 期望 {expected!r}，实际 {actual!r}")


def expect_value_error(label, fn):
    """断言 fn() 抛 ValueError（认不出的修饰名必须报错而不是静默丢弃）"""
    try:
        result = fn()
    except ValueError:
        print(f"✅ {label}")
        return
    print(f"❌ {label}（未抛异常，返回 {result!r}）")
    raise AssertionError(f"{label}: 未抛 ValueError，返回 {result!r}")


def test_bracket_conversion():
    print("\n[1] convert_bracket_format_to_old —— 括号格式转换")
    check("MOE 修饰符在碱基后", convert_bracket_format_to_old("G[2'-MOE,PS]T[2'-MOE,PS]"), "GesTes")
    check("LNA", convert_bracket_format_to_old("A[LNA,PS]"), "Als")
    check("5-Me-LNA-C", convert_bracket_format_to_old("C[5-Me-LNA-C,PS]"), "Cks")
    check("只有 PS", convert_bracket_format_to_old("A[PS]G[PS]"), "AsGs")
    check("单个修饰（无逗号）", convert_bracket_format_to_old("G[2'-MOE]"), "Ge")

    # 大小写、全角撇号、空格 —— 用户常从 Word/PDF 粘贴
    check("全角撇号", convert_bracket_format_to_old("G[2’MOE,PS]"), "Ges")
    check("名称内空格", convert_bracket_format_to_old("G[2'-MOE, ps]"), "Ges")
    check("小写名称", convert_bracket_format_to_old("G[moe,lna]"), "Gel")
    check("小写碱基", convert_bracket_format_to_old("g[PS]t[PS]"), "gsts")

    # 括号内名称顺序无关：两种写法解析出的修饰必须一致。
    # 比的是解析结果而非转换后的字符串 —— 修饰符在串里的先后会跟着括号内顺序走，
    # 但两者记下的是同一组修饰。
    mods_ps_first = parse_sequence("C[PS,5-Me-LNA-C]G", "RNA")[1]
    mods_ps_last = parse_sequence("C[5-Me-LNA-C,PS]G", "RNA")[1]
    check("顺序无关：解析出的修饰一致", set(mods_ps_first), set(mods_ps_last))
    check("顺序无关：两种修饰都记下了", sorted(m[1] for m in mods_ps_first), ['k', 's'])

    # 无括号的序列原样返回
    check("旧格式序列不受影响", convert_bracket_format_to_old("GesTes"), "GesTes")
    check("新格式序列不受影响", convert_bracket_format_to_old("(mG)*(mU)"), "(mG)*(mU)")

    # 认不出的修饰名必须报错
    expect_value_error(
        "未知修饰名报错",
        lambda: convert_bracket_format_to_old("X[FOO,PS]"),
    )
    expect_value_error(
        "缺右括号报错",
        lambda: convert_bracket_format_to_old("G[2'-MOE,PS"),
    )


def test_aso_parsing():
    print("\n[2] parse_sequence —— 两条真实 ASO 序列")
    for label, seq, expect_base_mods, expect_count in (
        ("MOE-ASO", MOE_ASO, {'e': 6}, 6),
        ("LNA-ASO", LNA_ASO, {'l': 4, 'k': 2}, 6),
    ):
        naked, mods, _, _, _, _ = parse_sequence(seq, "RNA")
        check(f"{label} 裸序列长度", len(naked), 18)
        counts = {}
        for _, mod_type, _base in mods:
            counts[mod_type] = counts.get(mod_type, 0) + 1
        check(f"{label} 修饰统计", counts, {**expect_base_mods, 's': 17})
        check(f"{label} 糖修饰总数", sum(v for k, v in counts.items() if k != 's'), expect_count)
        check(f"{label} 序列字母无修饰符号", naked.isalpha() and naked.isupper(), True)

    # 末尾的 [PS] 后面没有碱基，按既有规则静默忽略 → 18nt 只有 17 根键
    naked, mods, _, _, _, _ = parse_sequence("A[PS]", "RNA")
    check("单个 A[PS] 无硫代键", [m for m in mods if m[1] == 's'], [])
    check("单个 A[PS] 裸序列", naked, "A")


def test_merge_helper():
    print("\n[3] merge_phosphorothioate_regions —— 区段合并")
    check("单键保持 x^y", merge_phosphorothioate_regions([('1^2', 's', 'a')]), [('1^2', 's', 'a')])
    check("两键相接成区段",
          merge_phosphorothioate_regions([('1^2', 's', 'a'), ('2^3', 's', 'a')]),
          [('1..3', 's', 'a')])
    check("不相接的单键各自保留",
          merge_phosphorothioate_regions([('1^2', 's', 'a'), ('5^6', 's', 'a')]),
          [('1^2', 's', 'a'), ('5^6', 's', 'a')])
    # 关键：硫代键在 modifications 里是被糖修饰隔开的，不能只合并相邻条目
    check("被糖修饰隔开仍要合并",
          merge_phosphorothioate_regions([('1^2', 's', 'a'), (2, 'e', 'c'), ('2^3', 's', 'c')]),
          [('1..3', 's', 'a'), (2, 'e', 'c')])
    check("无硫代时原样", merge_phosphorothioate_regions([(1, 'm', 'a')]), [(1, 'm', 'a')])
    check("空列表", merge_phosphorothioate_regions([]), [])
    # 合并后按位置重排，feature 表保持有序
    check("合并后按位置排序",
          [loc for loc, _, _ in merge_phosphorothioate_regions(
              [(1, 'e', 'g'), ('1^2', 's', 'g'), (2, 'e', 't'), ('2^3', 's', 't'), (3, 'e', 't')])],
          [1, '1..3', 2, 3])


def _sequence_entry(seq, moltype='RNA'):
    return {
        'sequence': seq,
        'moltype': moltype,
        'organism': 'synthetic construct',
        'qual_moltype': 'other RNA' if moltype == 'RNA' else 'other DNA',
        'freetexts': [],
        'ring_infos': [],
        'hybrid_segments': [],
        'check_ref': None,
        'line_number': 1,
    }


BASIC_DATA = {
    'ApplicantFileReference': 'ASO_TEST',
    'ApplicantName': '测试用户',
    'ApplicantNameLatin': 'Test User',
    'InventorName': '测试发明人',
    'InventorNameLatin': 'Test Inventor',
    'InventionTitle': '测试发明',
}


def _features(root, seq_index):
    """取出第 seq_index 条序列（从 0 起）的所有 feature"""
    seq_el = list(root.iter('INSDSeq'))[seq_index]
    return [
        (f.findtext('INSDFeature_key'),
         f.findtext('INSDFeature_location'),
         {q.findtext('INSDQualifier_name'): q.findtext('INSDQualifier_value')
          for q in f.iter('INSDQualifier')})
        for f in seq_el.iter('INSDFeature')
        if f.findtext('INSDFeature_key') != 'source'
    ]


def test_xml_annotation():
    print("\n[4] 生成 XML —— 注释形式")
    root, _ = generate_xml(
        [_sequence_entry(MOE_ASO), _sequence_entry(LNA_ASO)],
        BASIC_DATA, '/tmp',
    )

    moe_feats = _features(root, 0)
    lna_feats = _features(root, 1)

    # 所有修饰都用 modified_base。除杂合区段外不该有别的 feature ——
    # ASO 是 3-12-3 gapmer，¶55 要求每个 DNA/RNA 区段各给一条 misc_feature + note，
    # 所以这里恰好三条；若不是这三条，说明修饰被错误地写成了 misc_feature。
    for label, feats in (("MOE-ASO", moe_feats), ("LNA-ASO", lna_feats)):
        others = [(k, q.get('note')) for k, _, q in feats if k != 'modified_base']
        check(f"{label} 非 modified_base 的 feature 只有杂合区段",
              others, [('misc_feature', 'RNA'), ('misc_feature', 'DNA'), ('misc_feature', 'RNA')])

    # MOE / LNA / 5-Me-LNA-C 都是 OTHER + note（不在 Annex I 表 2 内）
    notes = {loc: quals.get('note') for _, loc, quals in moe_feats}
    check("MOE 的 note", notes.get('1'), '2prime-methoxyethyl')
    lna_notes = {loc: quals.get('note') for _, loc, quals in lna_feats}
    check("LNA 的 note 含碱基全名", lna_notes.get('1'), 'locked nucleic acid adenosine')
    check("5-Me-LNA-C 的 note 含碱基全名",
          lna_notes.get('17'), '5-methyl-locked nucleic acid cytidine')

    # 全硫代：18nt 应只有一条 1..18 的区段，而不是 17 条
    ps = [(loc, q) for _, loc, q in moe_feats if q.get('note') == 'phosphorothioate linkage']
    check("MOE-ASO 硫代 feature 条数", len(ps), 1)
    check("MOE-ASO 硫代区段位置", ps[0][0], '1..18')
    check("硫代也用 modified_base + OTHER", ps[0][1].get('mod_base'), 'OTHER')

    lna_ps = [(loc, q) for _, loc, q in lna_feats if q.get('note') == 'phosphorothioate linkage']
    check("LNA-ASO 硫代区段位置", [loc for loc, _ in lna_ps], ['1..18'])


def test_existing_formats_unchanged():
    print("\n[5] 回归 —— 既有两种格式")
    root, _ = generate_xml(
        [_sequence_entry("GesTesAsGsGsAsAsTsT"), _sequence_entry("(mG)*(mU)(fC)")],
        BASIC_DATA, '/tmp',
    )

    old_feats = _features(root, 0)
    notes = {loc: quals.get('note') for _, loc, quals in old_feats}
    check("旧格式 e 的 note 未变", notes.get('1'), '2prime-methoxyethyl')
    # XML 里的序列一律小写（generate_xml 既有行为），parse_sequence 才返回大写
    check("旧格式裸序列", list(root.iter('INSDSeq'))[0].findtext('INSDSeq_sequence'), 'gtaggaatt')
    check("旧格式硫代合并为一条",
          [loc for _, loc, q in old_feats if q.get('note') == 'phosphorothioate linkage'],
          ['1..9'])

    # 新格式：(mG)/(mU) 仍是表 2 里的 gm/um；单根硫代键保持 x^y
    new_feats = _features(root, 1)
    mod_bases = {loc: q.get('mod_base') for _, loc, q in new_feats if 'mod_base' in q}
    check("新格式 gm 缩写保留", mod_bases.get('1'), 'gm')
    check("新格式 um 缩写保留", mod_bases.get('2'), 'um')
    check("新格式单根硫代键保持 x^y",
          [loc for _, loc, q in new_feats if q.get('note') == 'phosphorothioate linkage'],
          ['1^2'])


if __name__ == "__main__":
    tests = [
        test_bracket_conversion,
        test_aso_parsing,
        test_merge_helper,
        test_xml_annotation,
        test_existing_formats_unchanged,
    ]

    failed = []
    for test in tests:
        try:
            test()
        except AssertionError as exc:
            failed.append((test.__name__, str(exc)))

    print("\n" + "=" * 50)
    if failed:
        print(f"❌ {len(failed)} 个测试函数失败：")
        for name, message in failed:
            print(f"   - {name}: {message}")
        sys.exit(1)
    print("✅ 全部通过")
