"""ST26 杂合序列（DNA/RNA）判定与 ¶55 注释的测试

判定按「标注格式 × 是否填了区段列」分四条路径，本文件按这四条组织：
  1. uses_bracket_notation —— 格式判定（全或无）
  2. resolve_hybrid —— 四条路径的纯函数行为
  3. XML：方括号 ASO 自动识别 + ST.26 ¶55 的三条强制改写
  4. XML：方括号 + 手填区段（一致采用 / 矛盾中止）
  5. XML：旧格式 + 手填区段（硬矛盾中止 / 软提示不中止）
  6. XML：旧格式未填区段不被改写（atcg 看不出 RNA/DNA）
  7. Excel「杂合信息=是」的读取
  8. 概要 vs XML 一致性，以及空单元格不再让概要消失
  9. 回归：非杂合输出不变、N[PS] 硫代不丢、L96 后缀仍判为方括号

运行: python test_st26_hybrid.py
"""
import os
import shutil
import sys
import tempfile

import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from xml_generator import generate_xml
from parser import (
    parse_sequence,
    resolve_hybrid,
    uses_bracket_notation,
    is_possible_hybrid,
    get_sequence_summary,
    read_sequences_from_excel,
)

REPO_DIR = os.path.dirname(os.path.abspath(__file__))

# 两条真实 ASO，都是 3-12-3 gapmer：两端 3 个糖修饰残基，中间 12 个脱氧
MOE_ASO = (
    "G[2'-MOE,PS]T[2'-MOE,PS]T[2'-MOE,PS]A[PS]G[PS]A[PS]A[PS]T[PS]T[PS]"
    "G[PS]A[PS]A[PS]G[PS]T[PS]G[PS]A[2'-MOE,PS]G[2'-MOE,PS]A[2'-MOE,PS]"
)
LNA_ASO = (
    "A[LNA,PS]G[LNA,PS]A[LNA,PS]C[PS]T[PS]C[PS]T[PS]T[PS]C[PS]C[PS]"
    "A[PS]T[PS]T[PS]C[PS]T[PS]A[LNA,PS]C[5-Me-LNA-C,PS]C[5-Me-LNA-C,PS]"
)

EXPECTED_ASO = [
    {'start': 1, 'end': 3, 'type': 'RNA'},
    {'start': 4, 'end': 15, 'type': 'DNA'},
    {'start': 16, 'end': 18, 'type': 'RNA'},
]


def check(label, actual, expected):
    if actual == expected:
        print(f"✅ {label}")
        return
    print(f"❌ {label}\n     期望: {expected!r}\n     实际: {actual!r}")
    raise AssertionError(f"{label}: 期望 {expected!r}，实际 {actual!r}")


def expect_value_error(label, fn):
    """断言 fn() 抛 ValueError（该中止的情况必须中止，不能只是提醒后照做）"""
    try:
        result = fn()
    except ValueError:
        print(f"✅ {label}")
        return
    print(f"❌ {label}（未抛异常，返回 {result!r}）")
    raise AssertionError(f"{label}: 未抛 ValueError，返回 {result!r}")


def resolve(seq, moltype="RNA", user_segments=None):
    naked, modifications, *_ = parse_sequence(seq, moltype, 3)
    return resolve_hybrid(seq, moltype, naked, modifications, user_segments, 3)


def segments_of(result):
    return [(s['start'], s['end'], s['type']) for s in result.segments]


def test_bracket_notation_detection():
    print("\n[1] uses_bracket_notation —— 格式判定是全或无")
    for label, seq, expected in (
        ("MOE gapmer", MOE_ASO, True),
        ("LNA gapmer", LNA_ASO, True),
        # 每个残基都带括号，哪怕括号里只有硫代、哪怕括号是空的
        ("全硫代方括号", "G[PS]T[PS]A[PS]", True),
        ("空括号组", "C[]A[]", True),
        # 尾部 L96 配体不是残基，剥掉后仍应判为方括号格式
        ("带 L96 后缀", "G[2'-MOE,PS]T[2'-MOE,PS]A[PS]L96", True),
        # 以下都不算方括号格式
        ("旧格式", "AesCesGesUesGTMAsAsTsAsA", False),
        ("半括号", "A[PS]GCTT", False),
        ("圆括号格式", "(VP)(mG)*(mG)*(mU)", False),
        ("纯裸序列", "AUGCAUGC", False),
        ("空串", "", False),
    ):
        check(label, uses_bracket_notation(seq), expected)


def test_resolve_hybrid_paths():
    print("\n[2] resolve_hybrid —— 四条路径")

    # 方括号 + 未填区段 → 按化学推断，分子类型改写为 DNA
    result = resolve(MOE_ASO)
    check("方括号未填区段：推断出三段", segments_of(result), [(1, 3, 'RNA'), (4, 15, 'DNA'), (16, 18, 'RNA')])
    check("方括号未填区段：分子类型改写为 DNA", result.moltype, "DNA")
    check("方括号未填区段：给出核对提醒", any('检测到DNA/RNA杂合序列' in h for h in result.hints), True)

    # 方括号 + 填了吻合的区段 → 采用，不中止；杂合体按 ¶55 仍是 DNA
    result = resolve(MOE_ASO, user_segments=EXPECTED_ASO)
    check("方括号+吻合区段：采用手填", segments_of(result), [(1, 3, 'RNA'), (4, 15, 'DNA'), (16, 18, 'RNA')])
    check("方括号+吻合区段：无额外提醒", result.hints, [])
    check("方括号+吻合区段：分子类型仍是 DNA", result.moltype, "DNA")

    # 相邻同类型的等价拆分不能算「不一致」
    result = resolve("G[2'-MOE]T[PS]A[PS]G[PS]",
                     user_segments=[{'start': 1, 'end': 1, 'type': 'RNA'},
                                    {'start': 2, 'end': 4, 'type': 'DNA'}])
    check("等价拆分不判为不一致", segments_of(result), [(1, 1, 'RNA'), (2, 4, 'DNA')])

    # 方括号 + 填了不吻合的区段 → 中止
    expect_value_error(
        "方括号+矛盾区段：中止",
        lambda: resolve(MOE_ASO, user_segments=[{'start': 1, 'end': 5, 'type': 'RNA'},
                                                {'start': 6, 'end': 18, 'type': 'DNA'}]),
    )

    # 旧格式 + 未填区段 → 不做杂合识别。atcg 在 RNA/DNA 之间写法相同，判不出。
    result = resolve("AmGmCmUmAmG")
    check("旧格式未填区段：不推断区段", result.segments, [])
    check("旧格式未填区段：分子类型不被改写", result.moltype, "RNA")
    check("旧格式未填区段：提示哪些位置没写修饰",
          any('第 6 位没有修饰符号' in h for h in result.hints), True)

    # 旧格式 + 未填区段 + 完全裸的序列 → 一条提示都不该有（这是正常的 RNA 写法）
    check("纯裸序列不提醒", resolve("AUGCAUGC").hints, [])

    # 旧格式 + 填了区段，RNA 段里有裸残基 → 不中止，只提示
    # （糖修饰位置 1,2,3,4,7,8；切在 8/9 之间，DNA 段里没有糖修饰，不构成硬矛盾）
    result = resolve("AmGmCmUmAUGmCmU",
                     user_segments=[{'start': 1, 'end': 8, 'type': 'RNA'},
                                    {'start': 9, 'end': 9, 'type': 'DNA'}])
    check("旧格式 RNA 段含裸残基：不中止",
          segments_of(result), [(1, 8, 'RNA'), (9, 9, 'DNA')])
    check("旧格式 RNA 段含裸残基：给出提示",
          any('第 5..6 位标在RNA段内但没有修饰符号' in h for h in result.hints), True)

    # 旧格式 + 填了区段，DNA 段里有糖修饰 → 硬矛盾，中止
    expect_value_error(
        "旧格式 DNA 段含糖修饰：中止",
        lambda: resolve("AmGmCmUm", user_segments=[{'start': 1, 'end': 2, 'type': 'RNA'},
                                                   {'start': 3, 'end': 4, 'type': 'DNA'}]),
    )
    try:
        resolve("AmGmCmUm", user_segments=[{'start': 1, 'end': 2, 'type': 'RNA'},
                                           {'start': 3, 'end': 4, 'type': 'DNA'}])
    except ValueError as exc:
        check("硬矛盾报错点出位置", '第 3..4 位' in str(exc), True)

    # 含简并 n 时判不出化学，方括号格式下也只能照单全收 + 提醒
    result = resolve("G[2'-MOE]T[2'-MOE]A[PS]N[PS]G[PS]T[PS]",
                     user_segments=[{'start': 1, 'end': 2, 'type': 'RNA'},
                                    {'start': 3, 'end': 6, 'type': 'DNA'}])
    check("含n时采用手填区段", segments_of(result), [(1, 2, 'RNA'), (3, 6, 'DNA')])
    check("含n无法核对时给提醒", any('无法用修饰核对' in h for h in result.hints), True)

    # 多肽没有 DNA/RNA 区段这回事
    result = resolve("GKGKAPKAPK", moltype="AA")
    check("AA 不参与杂合判定", (result.segments, result.hints), ([], []))


def _sequence_entry(seq, hybrid_segments=None, moltype='RNA', qual_moltype='other RNA', line_number=1):
    return {
        'sequence': seq,
        'moltype': moltype,
        'organism': 'synthetic construct',
        'qual_moltype': qual_moltype,
        'freetexts': [],
        'ring_infos': [],
        'hybrid_segments': hybrid_segments or [],
        'check_ref': None,
        'line_number': line_number,
    }


BASIC_DATA = {
    'ApplicantFileReference': 'HYBRID_TEST',
    'ApplicantName': '测试用户',
    'ApplicantNameLatin': 'Test User',
    'InventorName': '测试发明人',
    'InventorNameLatin': 'Test Inventor',
    'InventionTitle': '测试发明',
}


def _seq_element(root, seq_index):
    return list(root.iter('INSDSeq'))[seq_index]


def _misc_features(seq_el):
    """非 source 的 feature：(location, note)"""
    return [
        (f.findtext('INSDFeature_location'),
         {q.findtext('INSDQualifier_name'): q.findtext('INSDQualifier_value')
          for q in f.iter('INSDQualifier')}.get('note'))
        for f in seq_el.iter('INSDFeature')
        if f.findtext('INSDFeature_key') == 'misc_feature'
    ]


def _source_quals(seq_el):
    return {
        q.findtext('INSDQualifier_name'): q.findtext('INSDQualifier_value')
        for f in seq_el.iter('INSDFeature') if f.findtext('INSDFeature_key') == 'source'
        for q in f.iter('INSDQualifier')
    }


def test_st26_paragraph_55():
    print("\n[3] 生成 XML —— 方括号 ASO 自动识别 + ST.26 ¶55 的三条强制要求")
    root, reminders = generate_xml([_sequence_entry(MOE_ASO)], BASIC_DATA, '/tmp')
    seq_el = _seq_element(root, 0)

    # ¶55 第一、二条：分子类型必须 DNA；mol_type 必须 other DNA、organism 必须 synthetic construct
    check("INSDSeq_moltype 强制为 DNA", seq_el.findtext('INSDSeq_moltype'), 'DNA')
    check("source mol_type 为 other DNA", _source_quals(seq_el).get('mol_type'), 'other DNA')
    check("source organism 为 synthetic construct", _source_quals(seq_el).get('organism'), 'synthetic construct')

    # ¶55 第三条：每段一个 misc_feature + note
    check("三段 misc_feature", _misc_features(seq_el), [('1..3', 'RNA'), ('4..15', 'DNA'), ('16..18', 'RNA')])

    # 序列字母不含修饰符号，且维持小写
    check("序列字母", seq_el.findtext('INSDSeq_sequence'), 'gttagaattgaagtgaga')
    check("序列长度", seq_el.findtext('INSDSeq_length'), '18')

    check("产生了核对提醒",
          any('检测到DNA/RNA杂合序列' in r and 'RNA 1..3' in r for r in reminders), True)


def test_bracket_manual_segments():
    print("\n[4] 方括号 + 手填区段：一致时采用，不一致时中止")
    root, _ = generate_xml(
        [_sequence_entry(MOE_ASO, hybrid_segments=[
            {'start': 1, 'end': 3, 'type': 'rna'},     # 故意小写，验证会被规范化
            {'start': 4, 'end': 15, 'type': 'DNA'},
            {'start': 16, 'end': 18, 'type': 'RNA'},
        ])], BASIC_DATA, '/tmp')
    check("手填区段被采用且 note 转大写", _misc_features(_seq_element(root, 0)),
          [('1..3', 'RNA'), ('4..15', 'DNA'), ('16..18', 'RNA')])

    # 用户填的区段与推断不符 → 必须中止，而不是提醒后照做
    mismatched = [{'start': 1, 'end': 5, 'type': 'RNA'}, {'start': 6, 'end': 18, 'type': 'DNA'}]
    expect_value_error(
        "区段与修饰不一致时中止",
        lambda: generate_xml([_sequence_entry(MOE_ASO, hybrid_segments=mismatched)], BASIC_DATA, '/tmp'),
    )
    # 报错文案要同时给出两边，用户才知道该改区段列还是改序列
    try:
        generate_xml([_sequence_entry(MOE_ASO, hybrid_segments=mismatched)], BASIC_DATA, '/tmp')
    except ValueError as exc:
        message = str(exc)
        check("报错含填写的区段", 'RNA 1..5' in message and 'DNA 6..18' in message, True)
        check("报错含推断的区段", 'DNA 4..15' in message, True)

    # 用户的 organism 不是 synthetic construct 时会被改写并提醒
    entry = _sequence_entry(MOE_ASO)
    entry['organism'] = 'Homo sapiens'
    root, reminders = generate_xml([entry], BASIC_DATA, '/tmp')
    check("organism 被改写", _source_quals(_seq_element(root, 0)).get('organism'), 'synthetic construct')
    check("organism 改写有提醒", any('synthetic construct' in r and '第55段' in r for r in reminders), True)


def test_old_format_manual_segments():
    print("\n[5] 旧格式 + 手填区段：只查硬矛盾，不做事后比对")

    # RNA 段里有裸残基 → 判不出是漏写还是真脱氧，按未修饰的 RNA 残基处理，不中止。
    # 序列 AmGmCmUmAUGmCmU 的糖修饰位置是 1,2,3,4,7,8，第 5、6 位没写修饰；
    # 切在 8/9 之间，则 DNA 段（第 9 位）里没有糖修饰，不构成硬矛盾。
    root, reminders = generate_xml(
        [_sequence_entry("AmGmCmUmAUGmCmU",
                         hybrid_segments=[{'start': 1, 'end': 8, 'type': 'RNA'},
                                          {'start': 9, 'end': 9, 'type': 'DNA'}])],
        BASIC_DATA, '/tmp')
    check("RNA 段含裸残基不中止",
          _misc_features(_seq_element(root, 0)), [('1..8', 'RNA'), ('9', 'DNA')])
    check("RNA 段含裸残基给提示",
          any('第 5..6 位标在RNA段内但没有修饰符号' in r for r in reminders), True)

    # DNA 段里有糖修饰残基 → 化学上不可能，中止整批转换
    expect_value_error(
        "DNA 段含糖修饰时中止",
        lambda: generate_xml(
            [_sequence_entry("AmGmCmUm",
                             hybrid_segments=[{'start': 1, 'end': 2, 'type': 'RNA'},
                                              {'start': 3, 'end': 4, 'type': 'DNA'}])],
            BASIC_DATA, '/tmp'),
    )


def test_old_format_without_segments_unchanged():
    print("\n[6] 旧格式未填区段：不做杂合识别，输出不被改写")

    # 这两种写法在旧格式里都无法归因到 DNA，判不出就不猜 —— 这是本次改动的主旨
    for label, seq in (("局部修饰", "GesTesAsGsGsAsAsTsT"), ("单个裸残基", "AmGmCmUmAmG")):
        root, reminders = generate_xml([_sequence_entry(seq)], BASIC_DATA, '/tmp')
        seq_el = _seq_element(root, 0)
        check(f"{label}：分子类型保持 RNA", seq_el.findtext('INSDSeq_moltype'), 'RNA')
        check(f"{label}：不产生 misc_feature", _misc_features(seq_el), [])
        check(f"{label}：给出漏写修饰的提示",
              any('已按未修饰的RNA残基处理' in r for r in reminders), True)

    # 半括号写法会掉进旧格式分支，行为落差大，必须提示
    _, reminders = generate_xml([_sequence_entry("A[PS]GCTT")], BASIC_DATA, '/tmp')
    check("半括号给出格式提示",
          any('并非每个残基都标注了修饰' in r for r in reminders), True)


def test_summary_matches_xml():
    print("\n[7] 概要 vs XML 一致性 —— resolve_hybrid 存在的唯一理由")
    entries = [
        _sequence_entry(MOE_ASO, line_number=2),
        _sequence_entry("AmGmCmU", line_number=3),
        _sequence_entry("AUGCAUGC", line_number=4),
    ]
    root, _ = generate_xml(entries, BASIC_DATA, '/tmp')
    summary = get_sequence_summary(entries)

    for index in range(len(entries)):
        xml_moltype = _seq_element(root, index).findtext('INSDSeq_moltype')
        check(f"第{index+1}条 概要类型 == XML 分子类型",
              summary['details'][index]['type'], xml_moltype)

    # ASO 被自动改写后，概要里要看得见，不能还显示用户填的 RNA
    check("ASO 在概要里显示为 DNA", summary['details'][0]['type'], 'DNA')
    check("ASO 的说明列含提醒",
          '检测到DNA/RNA杂合序列' in summary['details'][0]['modification_special_notes'], True)
    check("ASO 的说明列含区段",
          '杂交: RNA(1..3); DNA(4..15); RNA(16..18)' in summary['details'][0]['modification_special_notes'], True)
    check("type_counts 反映改写后的结果", summary['type_counts'], {'DNA': 1, 'RNA': 2, 'AA': 0})

    # 空单元格（NaN）不能让整个概要消失 —— 概要里要显示提醒，它必须存在
    summary = get_sequence_summary([
        {'sequence': float('nan'), 'moltype': float('nan'), 'line_number': 5},
        _sequence_entry("AUGCAUGC", line_number=6),
    ])
    check("空序列单元格不崩", summary['details'][0]['length'], 0)
    check("空分子类型单元格按 RNA 处理", summary['details'][0]['type'], 'RNA')
    check("概要仍然生成", len(summary['details']), 2)


def test_excel_hybrid_flag_honored():
    print("\n[8] Excel「杂合信息=是」—— 分子类型填 RNA 也不丢区段")
    tmp_dir = tempfile.mkdtemp()
    xlsx = os.path.join(tmp_dir, 'hybrid.xlsx')
    shutil.copy(os.path.join(REPO_DIR, 'static', 'templates', 'template.xlsx'), xlsx)

    template = pd.read_excel(xlsx, sheet_name='seqdata', header=0)
    columns = list(template.columns)

    def excel_row(seq, moltype, hybrid=None, first_seg=None, second_seg=None):
        row = dict.fromkeys(columns)
        row.update({
            '序列': seq, '分子类型': moltype, '生物体名称': 'synthetic construct',
            '限定符分子类型': 'other RNA', '杂合信息': hybrid,
            '第一区段': first_seg, '第二区段': second_seg,
        })
        return [row[column] for column in columns]

    rows = template.iloc[0:0]
    # 分子类型写 RNA —— 这正是原先区段列被静默丢弃的写法
    rows.loc[0] = excel_row('AesCesGesUesGTMAsAesUesAesAe', 'RNA', '是', '1..4RNA', '5..12DNA')
    rows.loc[1] = excel_row('AesCesGesUes', 'RNA')          # 没标杂合信息 → 不该有区段
    rows.loc[2] = excel_row('GKGKAPKAPK', 'AA')             # 多肽 → 区段概念不适用
    with pd.ExcelWriter(xlsx, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
        rows.to_excel(writer, sheet_name='seqdata', index=False)

    sequences = read_sequences_from_excel(xlsx)
    check("分子类型=RNA 时区段列不再被丢弃", sequences[0]['hybrid_segments'],
          [{'start': 1, 'end': 4, 'type': 'RNA'}, {'start': 5, 'end': 12, 'type': 'DNA'}])
    check("没标杂合信息时无区段", sequences[1]['hybrid_segments'], [])
    check("非核苷酸序列不读区段列", sequences[2]['hybrid_segments'], [])


def test_regressions():
    print("\n[9] 回归 —— 非杂合输出不变、修饰解析不丢")

    root, reminders = generate_xml(
        [_sequence_entry("AUGCAUGC"),
         _sequence_entry("ATGCATGC", moltype='DNA', qual_moltype='other DNA')],
        BASIC_DATA, '/tmp')

    check("纯 RNA 分子类型不变", _seq_element(root, 0).findtext('INSDSeq_moltype'), 'RNA')
    check("纯 RNA 无 misc_feature", _misc_features(_seq_element(root, 0)), [])
    check("纯 RNA 的 u 仍写成 t", _seq_element(root, 0).findtext('INSDSeq_sequence'), 'atgcatgc')
    check("纯 DNA 分子类型不变", _seq_element(root, 1).findtext('INSDSeq_moltype'), 'DNA')
    check("纯 DNA mol_type 不变", _source_quals(_seq_element(root, 1)).get('mol_type'), 'other DNA')
    check("非杂合不产生杂合提醒", any('杂合' in r for r in reminders), False)

    # N[PS]：n 后面的修饰符必须被消费。不修的话整串硫代键会静默消失。
    _, modifications, *_ = parse_sequence("N[PS]G[PS]A[PS]", "RNA", 1)
    check("N[PS] 的硫代键不丢",
          [m[:2] for m in modifications], [('1^2', 's'), ('2^3', 's')])

    # 尾部 L96 剥掉后仍应识别为方括号格式，否则真 ASO 会掉进旧格式分支
    root, reminders = generate_xml(
        [_sequence_entry("G[2'-MOE,PS]T[2'-MOE,PS]A[PS]L96")], BASIC_DATA, '/tmp')
    check("带 L96 的 ASO 仍被识别为杂合", _seq_element(root, 0).findtext('INSDSeq_moltype'), 'DNA')
    check("L96 仍有移除提醒", any('L96' in r for r in reminders), True)


def test_single_type_segments_rejected():
    print("\n[11] 填了区段却只有单一类型 —— 不是杂合体，中止")

    # ¶55 的三条强制改写只对 DNA/RNA 混合分子成立。照着纯 RNA 的区段集套用，
    # 会把 AmGmCmUm 这种全修饰的纯 RNA 写成分子上是 DNA。
    for label, seq, moltype, segments in (
        ("旧格式 全 RNA 段", "AmGmCmUm", "RNA", [{'start': 1, 'end': 4, 'type': 'RNA'}]),
        ("旧格式 全 DNA 段", "GATTACA", "DNA", [{'start': 1, 'end': 7, 'type': 'DNA'}]),
        ("方括号 全 RNA 段", "G[2'-MOE]T[2'-MOE]A[2'-MOE]", "RNA",
         [{'start': 1, 'end': 3, 'type': 'RNA'}]),
        # 含 n 时判不出化学，但「只填了 RNA 段」本身就是用户自己写矛盾了，照样中止
        ("含 n 全 RNA 段", "AmnCmUm", "RNA", [{'start': 1, 'end': 4, 'type': 'RNA'}]),
    ):
        expect_value_error(label + "：中止", lambda s=seq, m=moltype, g=segments: resolve(s, m, g))
        expect_value_error(
            label + "：XML 也不产出",
            lambda s=seq, m=moltype, g=segments: generate_xml(
                [_sequence_entry(s, moltype=m, hybrid_segments=g)], BASIC_DATA, '/tmp'),
        )

    # 报错文案要指出「应当清空杂合信息列」，否则用户不知道该改哪一格
    try:
        resolve("AmGmCmUm", user_segments=[{'start': 1, 'end': 4, 'type': 'RNA'}])
    except ValueError as exc:
        check("提示如何修正", '清空「杂合信息」列' in str(exc), True)

    # 真正的杂合体不受影响
    result = resolve("AmGmCmUmAUGmCmU",
                     user_segments=[{'start': 1, 'end': 8, 'type': 'RNA'},
                                    {'start': 9, 'end': 9, 'type': 'DNA'}])
    check("真杂合体仍照常制作", result.moltype, "DNA")


def test_default_qual_moltype_reminder_matches_xml():
    print("\n[12] 限定符分子类型默认值的提醒 —— 必须等于实际写进 XML 的值")

    # 杂合体：¶55 会把 mol_type 改写成 'other DNA'，提醒不能再报 'other RNA'
    _, reminders = generate_xml(
        [_sequence_entry(MOE_ASO, qual_moltype=None, line_number=5)], BASIC_DATA, '/tmp')
    reminder = next((r for r in reminders if '未指定限定符分子类型' in r), None)
    check("杂合体提醒的是实际写入值 other DNA",
          reminder, "第5行：未指定限定符分子类型，使用了默认值'other DNA'")

    # 非杂合体：保持原样（这里 mol_type 就是 default 算出来的值）
    root, reminders = generate_xml(
        [_sequence_entry("AUGCAUGC", qual_moltype=None, line_number=6)], BASIC_DATA, '/tmp')
    reminder = next((r for r in reminders if '未指定限定符分子类型' in r), None)
    source_quals = _seq_element(root, 0).find('INSDSeq_feature-table')[0]
    written = next(q.findtext('INSDQualifier_value')
                   for q in source_quals.iter('INSDQualifier')
                   if q.findtext('INSDQualifier_name') == 'mol_type')
    check("非杂合体提醒的是实际写入值 other RNA",
          reminder, "第6行：未指定限定符分子类型，使用了默认值'other RNA'")
    check("提醒与 XML 一致", written, 'other RNA')

    # 没填默认值时不该有这条提醒
    _, reminders = generate_xml(
        [_sequence_entry("AUGCAUGC", qual_moltype='other RNA', line_number=7)], BASIC_DATA, '/tmp')
    check("填了值就不提醒",
          any('未指定限定符分子类型' in r for r in reminders), False)


def test_possible_hybrid():
    print("\n[10] is_possible_hybrid —— 含 n 时的兜底判定")
    for label, seq, expected in (
        # 含 n，且去掉 n 之后确实是混合的 → 很可能真是杂合体，必须提醒
        ("含n的gapmer", "G[2'-MOE]T[2'-MOE]A[PS]G[PS]A[PS]N[PS]T[PS]", True),
        # 含 n 但全是裸残基 → 判不出，不提醒
        ("含n的纯序列", "AUGCNUGC", False),
        # 不含 n → 这个函数不管，交给 resolve_hybrid 的方括号分支
        ("不含n", MOE_ASO, False),
    ):
        naked, modifications, *_ = parse_sequence(seq, "RNA")
        check(label, is_possible_hybrid(naked, modifications), expected)


if __name__ == "__main__":
    tests = [
        test_bracket_notation_detection,
        test_resolve_hybrid_paths,
        test_st26_paragraph_55,
        test_bracket_manual_segments,
        test_old_format_manual_segments,
        test_old_format_without_segments_unchanged,
        test_summary_matches_xml,
        test_excel_hybrid_flag_honored,
        test_regressions,
        test_possible_hybrid,
        test_single_type_segments_rejected,
        test_default_qual_moltype_reminder_matches_xml,
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
