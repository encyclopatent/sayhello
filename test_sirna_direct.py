"""直接输入模式（/sirna/direct）的测试

覆盖三部分：
  1. 文本解析与净化（sanitize_sequence / parse_sequences_from_text / parse_target_from_text）
  2. 匹配编排（analyze_direct / generate_direct_results_table）
  3. 路由层的输入上限与参数解析（estimate_scan_cost / parse_mismatch_count）

运行: python test_sirna_direct.py
也可被 pytest 直接收集（断言失败会抛 AssertionError）。
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from Bio.Seq import Seq

from sirna_analysis import (
    analyze_direct,
    check_sirna_match,
    extract_match_length,
    generate_direct_results_table,
    parse_sequences_from_text,
    parse_target_from_text,
    sanitize_sequence,
)
from routes.sirna import estimate_scan_cost, parse_mismatch_count

# 一个自造的靶序列，用于构造确定性的匹配用例。
# 片段取自随机序列，避免重复序列导致滑窗命中多个等价位置。
TARGET = "ACGGTCATTGCAGCTTAGGCATCGTAA"
FORWARD = TARGET[3:22]  # 19bp，正向完全匹配，位置 3-22


def check(label, actual, expected):
    if actual == expected:
        print(f"✅ {label}")
        return
    print(f"❌ {label}\n     期望: {expected!r}\n     实际: {actual!r}")
    raise AssertionError(f"{label}: 期望 {expected!r}，实际 {actual!r}")


def check_true(label, condition, detail=""):
    if condition:
        print(f"✅ {label}")
        return
    print(f"❌ {label}" + (f"\n     {detail}" if detail else ""))
    raise AssertionError(f"{label}" + (f": {detail}" if detail else ""))


def expect_value_error(label, fn):
    """断言 fn() 抛出 ValueError（输入格式歧义时必须报错而不是静默处理）"""
    try:
        result = fn()
    except ValueError:
        print(f"✅ {label}")
        return
    print(f"❌ {label}（未抛异常，返回 {result!r}）")
    raise AssertionError(f"{label}: 未抛 ValueError，返回 {result!r}")


def test_sanitize_sequence():
    print("\n[1] sanitize_sequence —— 序列净化")
    check("小写转大写", sanitize_sequence("acgt"), "ACGT")
    check("RNA 的 U 归一为 T", sanitize_sequence("acgU"), "ACGT")
    check("非核酸字符被剔除", sanitize_sequence("ATGCNR"), "ATGC")
    check("空白与换行被剔除", sanitize_sequence("atg\ncgt taa"), "ATGCGTTAA")
    check("None 输入", sanitize_sequence(None), "")
    check("数字与标点被剔除", sanitize_sequence("ATG-123.CGT"), "ATGCGT")


def test_extract_match_length():
    print("\n[2] extract_match_length —— 匹配长度解析")
    check("标准位置串", extract_match_length("5-24 (19bp)"), 19)
    check("带突出端标记", extract_match_length("2-20 (19bp) [存在突出端]"), 19)
    check("N/A", extract_match_length("N/A"), 0)
    check("空串", extract_match_length(""), 0)
    check("None", extract_match_length(None), 0)
    check("无长度信息", extract_match_length("abc"), 0)


def test_parse_sequences_plain():
    print("\n[3] parse_sequences_from_text —— 多行纯文本")
    text = "GUGUUCUAC\n\nGCUUACCUA\n   \nACGUACGU\n"
    seqs, names = parse_sequences_from_text(text)
    check("序列净化结果", seqs, ["GTGTTCTAC", "GCTTACCTA", "ACGTACGT"])
    check("按 Query_N 编号（跳过空行）", names, ["Query_1", "Query_2", "Query_3"])

    seqs, names = parse_sequences_from_text("")
    check("空输入返回空列表", (seqs, names), ([], []))


def test_parse_sequences_fasta():
    print("\n[4] parse_sequences_from_text —— FASTA 格式")
    fasta = ">seq_alpha\nGUGUUCUAC\n>seq_beta\nGCUUACCUA\n"
    seqs, names = parse_sequences_from_text(fasta)
    check("FASTA 序列净化结果", seqs, ["GTGTTCTAC", "GCTTACCTA"])
    check("FASTA 用记录名命名", names, ["seq_alpha", "seq_beta"])

    # 多行折行的 FASTA 记录应被合并成一条
    wrapped = ">folded\nGUGUUC\nUACGCU\n"
    seqs, names = parse_sequences_from_text(wrapped)
    check("折行的 FASTA 记录合并为一条", (seqs, names), (["GTGTTCTACGCT"], ["folded"]))


def test_parse_target():
    print("\n[5] parse_target_from_text —— 靶序列")
    check("单行", parse_target_from_text("ATCGTACGTACGTACGTA"), "ATCGTACGTACGTACGTA")
    check("折行拼接", parse_target_from_text("ATCGTACGT\nACGTACGTA\n"), "ATCGTACGTACGTACGTA")
    check("带前后空白", parse_target_from_text("  ATCGTACGTACGTACGTA  "), "ATCGTACGTACGTACGTA")
    check("RNA 归一为 T", parse_target_from_text("AUCGUACGUACGUACGUA"), "ATCGTACGTACGTACGTA")
    check("空输入返回 None", parse_target_from_text("   \n  "), None)

    # 回归：FASTA 表头若参与净化会污染靶序列。
    # 这里刻意让表头由核酸字母组成，表头剥离失败时结果会是 "ATGCATCG" 而不是 "ATCG"。
    polluted = parse_target_from_text(">ATGC\nATCG")
    check("FASTA 表头不污染靶序列", polluted, "ATCG")

    multi = parse_target_from_text(">first\nATCGATCGATCGATCGATC\n>second\nGGGGGGGGGGGGGGGGGGGG")
    check("多条 FASTA 记录只取第一条", multi, "ATCGATCGATCGATCGATC")


def test_stray_fasta_header():
    print("\n[5b] 格式歧义 —— 表头不在首行时必须报错")

    # Biopython 会静默丢弃首个表头之前的内容。若放宽 FASTA 判定，
    # 下面这两条输入会无声丢掉前半段序列，所以必须显式报错。
    expect_value_error(
        "靶序列混入非首行表头",
        lambda: parse_target_from_text("ACGTACGTACGTACGTACGT\n>x\nACGTACGTACGTACGTACGT"),
    )
    expect_value_error(
        "序列混入非首行表头",
        lambda: parse_sequences_from_text("GTCATTGCAGCTTAGGCAT\n>seq2\nACGTACGTACGTACGTACGT"),
    )

    # 首行就是表头 → 正常走 FASTA 分支，不报错
    seqs, names = parse_sequences_from_text(">s1\nGTCATTGCAGCTTAGGCAT")
    check("首行表头仍按 FASTA 解析", names, ["s1"])


def test_analyze_direct():
    print("\n[6] analyze_direct —— 匹配编排")

    check("测试前提：正向查询序列", FORWARD, "GTCATTGCAGCTTAGGCAT")

    # 6.1 正向命中
    results = analyze_direct([FORWARD], TARGET, 1)
    check("正向命中条数", len(results), 1)
    check("正向命中链类型", results[0]["strand_type"], "正义链")
    check("正向命中位置", results[0]["match_position"], "3-22 (19bp)")
    check("正向命中长度", results[0]["match_length"], 19)
    check("正向命中序列内编号", results[0]["query_id"], "Query_1")
    check("正向命中带比对详情", "query_alignment" in results[0], True)

    # 6.2 反向互补命中
    antisense_query = str(Seq(FORWARD).reverse_complement())
    results = analyze_direct([antisense_query], TARGET, 1)
    check("反义命中链类型", results[0]["strand_type"], "反义链")
    check("反义命中位置", results[0]["match_position"], "3-22 (19bp)")

    # 6.3 两端各带 2 个突出端碱基，需截短后才能匹配
    overhang_query = "AA" + FORWARD + "CC"
    results = analyze_direct([overhang_query], TARGET, 1)
    check("突出端：链类型", results[0]["strand_type"], "正义链")
    check("突出端：位置带标记", results[0]["match_position"], "3-22 (19bp) [存在突出端]")
    check("突出端：长度仍为 19", results[0]["match_length"], 19)

    # 6.4 不命中
    results = analyze_direct(["TTTTTTTTTTTTTTTTTTT"], TARGET, 1)
    check("不命中链类型", results[0]["strand_type"], "非siRNA")
    check("不命中位置", results[0]["match_position"], "N/A")
    check("不命中长度", results[0]["match_length"], 0)
    check("不命中无比对详情", "query_alignment" in results[0], False)

    # 6.5 多条序列的顺序与编号
    results = analyze_direct([FORWARD, "TTTTTTTTTTTTTTTTTTT", antisense_query], TARGET, 1)
    check("多条：条数", len(results), 3)
    check("多条：编号顺序", [r["query_id"] for r in results],
          ["Query_1", "Query_2", "Query_3"])
    check("多条：链类型顺序", [r["strand_type"] for r in results],
          ["正义链", "非siRNA", "反义链"])

    # 6.6 编排层与既有匹配引擎保持一致（新增代码的正确性锚点）
    pairs = [
        (FORWARD, TARGET),
        (antisense_query, TARGET),
        (overhang_query, TARGET),
        ("TTTTTTTTTTTTTTTTTTT", TARGET),
        ("ATCGATCGATCGATCGATC", "ATCGATCGATCGATCGATCGATCG"),
    ]
    for query, tgt in pairs:
        for mismatch in (1, 2):
            expected = check_sirna_match(query, tgt, mismatch)
            actual = analyze_direct([query], tgt, mismatch)[0]
            check_true(
                f"与 check_sirna_match 一致 (mismatch={mismatch}, query={query[:12]}...)",
                (actual["strand_type"], actual["match_position"]) == expected,
                f"check_sirna_match={expected} analyze_direct="
                f"({actual['strand_type']}, {actual['match_position']})",
            )


def test_overhang_alignment_consistency():
    print("\n[6c] 突出端输入：比对详情必须与所在行一致")

    # check_sirna_match 对 >=22nt 的序列会两端各截 2 个碱基再匹配。
    # 若比对详情用未截短的原始序列生成，展开框里的位置/长度会和行内容互相矛盾。
    overhang_query = "AA" + FORWARD + "CC"
    result = analyze_direct([overhang_query], TARGET, 1)[0]

    check("行内位置", result["match_position"], "3-22 (19bp) [存在突出端]")
    alignment = result["query_alignment"]
    check("详情位置与行一致",
          (alignment["target_start"], alignment["target_end"]), (3, 22))
    check("详情长度与行一致", alignment["alignment_length"], 19)
    check("详情用的是截短后的序列", alignment["query_aligned"], FORWARD)


def test_sequence_names():
    print("\n[6d] analyze_direct —— FASTA 记录名")

    results = analyze_direct([FORWARD, FORWARD], TARGET, 1, ["s1", "s2"])
    check("使用传入的 FASTA 记录名", [r["query_id"] for r in results], ["s1", "s2"])

    results = analyze_direct([FORWARD], TARGET, 1, None)
    check("names 为 None 时退回 Query_N", results[0]["query_id"], "Query_1")

    results = analyze_direct([FORWARD, FORWARD], TARGET, 1, ["only_one"])
    check("names 长度不符时退回 Query_N",
          [r["query_id"] for r in results], ["Query_1", "Query_2"])


def test_html_escaping():
    print("\n[6e] HTML 转义 —— FASTA 记录名来自用户输入")

    # 载荷刻意不含空格：Biopython 在空白处截断记录 ID，
    # 带空格的载荷会被截成 "<img"，那样断言就失去意义了
    payload = "<img/src=x/onerror=alert(1)>"
    seqs, names = parse_sequences_from_text(f">{payload}\n{FORWARD}\n")
    check("记录名被完整保留", names, [payload])

    html = generate_direct_results_table(analyze_direct(seqs, TARGET, 1, names))
    check_true("危险标签未以原始形式出现", payload not in html, html[:300])
    check_true("已转义为实体", "&lt;img/src=x/onerror=alert(1)&gt;" in html, html[:300])


def test_direct_results_table():
    print("\n[7] generate_direct_results_table —— 表格渲染")

    # 关键回归：未命中文献的结果也必须展示。
    # generate_results_table 会按文献匹配过滤，直接输入模式若复用它表格会永远为空。
    results = analyze_direct([FORWARD, "TTTTTTTTTTTTTTTTTTT"], TARGET, 1)
    html = generate_direct_results_table(results)
    check_true("命中行出现", "正义链" in html, html[:200])
    check_true("未命中行也出现（不被过滤）", "非siRNA" in html, html[:200])
    check_true("命中行有查看比对按钮",
               'onclick="toggleAlignmentDetails(\'direct_result_0\')"' in html)
    check_true("未命中行没有比对按钮", "btn_direct_result_1" not in html)
    check_true("比对详情行 id 使用 direct_result 前缀", 'id="direct_result_0_details"' in html)
    check_true("不复用文件模式的 result_ 前缀", 'id="result_0_row"' not in html)

    empty_html = generate_direct_results_table([])
    check_true("空结果给出提示", "未找到匹配结果" in empty_html, empty_html[:200])


def test_route_helpers():
    print("\n[8] 路由层 —— 参数解析与计算量估算")

    check("错配数：正常值", parse_mismatch_count("2"), 2)
    check("错配数：非法输入回退默认", parse_mismatch_count("abc"), 1)
    check("错配数：None 回退默认", parse_mismatch_count(None), 1)
    check("错配数：超上限被钳制", parse_mismatch_count("99"), 4)
    check("错配数：负数被钳制", parse_mismatch_count("-3"), 0)

    # 计算量 = 靶长度 × 所有序列长度之和
    check("计算量估算", estimate_scan_cost("A" * 100, ["A" * 19, "A" * 21]), 100 * 40)
    check("空序列列表计算量为 0", estimate_scan_cost("A" * 100, []), 0)


if __name__ == "__main__":
    tests = [
        test_sanitize_sequence,
        test_extract_match_length,
        test_parse_sequences_plain,
        test_parse_sequences_fasta,
        test_parse_target,
        test_stray_fasta_header,
        test_analyze_direct,
        test_overhang_alignment_consistency,
        test_sequence_names,
        test_html_escaping,
        test_direct_results_table,
        test_route_helpers,
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
