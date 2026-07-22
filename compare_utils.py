"""
三序列比对与突变分析模块 - 基于EMBOSS needle算法

分析流程：
1. needle比对 ref vs numbering → 建立 ref 残基到编号位置的映射
2. needle比对 ref vs tgt → 提取差异、合并相邻ins/del、计算核心区间同一性
3. 差异位点通过编号映射转换为编号位置
4. 输出：核心区间最长一致性 + 按编号映射的突变列表

同一性口径：
- ref vs tgt needle 全局比对 → 去掉两端 terminal overhang → 核心区间
- identity = 匹配数 / 核心区间总长（含内部gap）
- 结果保留两位小数

突变编号：
- 以 numbering sequence 的编号为准
- 先做 ref vs numbering needle，建立 ref 残基索引 → numbering 编号的映射
- 再做 ref vs tgt needle，提取差异位点
- 每个差异用映射位置作为编号

突变格式：
- ref残基 + 编号位置 + tgt残基，如 S3T
- 缺失：D36-（ref有残基，tgt为gap）
- 多个位点用 / 分隔，不加空格

gap处理：
- 两端 terminal gap 不列入突变
- 相邻的 deletion/insertion 合并为替换（如 D36-/-37S → D36S）
- 内部 deletion 保留为 D36-
- 单独插入保留插入标记
"""

import os
import re
import subprocess
import uuid
import logging
from typing import Dict, List, Optional, Tuple, Any

from Bio import AlignIO

logger = logging.getLogger(__name__)

# EMBOSS环境变量
EMBOSS_ENV = {
    "EMBOSS_ACDROOT": "/opt/anaconda3/envs/rdkit-env/share/EMBOSS/acd/",
    "EMBOSS_DATA": "/opt/anaconda3/envs/rdkit-env/share/EMBOSS/data/",
    "PLPLOT_LIB": "/opt/anaconda3/envs/rdkit-env/share/EMBOSS/",
}

NEEDLE_PATH = "/opt/anaconda3/envs/rdkit-env/bin/_needle"
DEFAULT_GAPOPEN = 10.0
DEFAULT_GAPEXTEND = 0.5


def run_needle_alignment(
    seq_a: str,
    seq_b: str,
    gapopen: float = DEFAULT_GAPOPEN,
    gapextend: float = DEFAULT_GAPEXTEND,
) -> Tuple[str, str, str, float, float]:
    """
    运行EMBOSS needle进行双序列全局比对。

    Returns:
        (aligned_a, aligned_b, raw_result, identity, longest_identity)
    """
    seq_a = re.sub(r'\s+', '', seq_a)
    seq_b = re.sub(r'\s+', '', seq_b)

    job_id = uuid.uuid4().hex[:8]
    fasta_a = f"temp_{job_id}_a.fasta"
    fasta_b = f"temp_{job_id}_b.fasta"
    outfile = f"temp_{job_id}_needle.txt"

    try:
        with open(fasta_a, 'w') as f:
            f.write(f">seq_a\n{seq_a}\n")
        with open(fasta_b, 'w') as f:
            f.write(f">seq_b\n{seq_b}\n")

        cmd = (
            f"{NEEDLE_PATH} -nobrief -asequence={fasta_a} -bsequence={fasta_b} "
            f"-gapopen={gapopen} -gapextend={gapextend} -outfile={outfile}"
        )
        logger.debug(f"Running needle: {cmd}")
        subprocess.run(
            cmd, shell=True, check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            encoding='utf-8', env={**os.environ, **EMBOSS_ENV}
        )

        with open(outfile, 'r') as f:
            raw_result = f.read()

        # 提取同一性
        identity = 0.0
        longest_identity = 0.0
        for line in raw_result.split('\n'):
            if "# Identity:" in line:
                parts = line.split()
                if len(parts) > 2:
                    vals = parts[2].split('/')
                    if len(vals) == 2:
                        identity = float(vals[0]) / float(vals[1]) if float(vals[1]) > 0 else 0.0
            elif "# Longest_Identity" in line:
                parts = line.split('=')
                if len(parts) > 1:
                    val = parts[1].strip().strip('%').strip()
                    try:
                        longest_identity = float(val) / 100.0
                    except ValueError:
                        pass

        # 读取比对结果
        alignment = AlignIO.read(outfile, "emboss")
        aligned_a = str(alignment[0].seq)
        aligned_b = str(alignment[1].seq)

        return aligned_a, aligned_b, raw_result, identity, longest_identity

    finally:
        for f in [fasta_a, fasta_b, outfile]:
            if os.path.exists(f):
                os.remove(f)


def _compute_core_identity(aligned_a: str, aligned_b: str) -> Tuple[float, int, int, int, int]:
    """
    计算核心区间同一性。

    去掉两端 terminal overhang/gap（只有一方有残基的区域），
    在剩余核心区间内计算 identity = matches / core_length。

    Returns:
        (identity, matches, core_length, core_start, core_end)
    """
    n = len(aligned_a)
    # 找到核心区间的起始和结束
    start = 0
    while start < n and (aligned_a[start] == '-' or aligned_b[start] == '-'):
        start += 1
    end = n - 1
    while end >= start and (aligned_a[end] == '-' or aligned_b[end] == '-'):
        end -= 1

    if end < start:
        return 0.0, 0, 0, 0, 0

    core_length = end - start + 1
    matches = sum(1 for i in range(start, end + 1) if aligned_a[i] == aligned_b[i])
    identity = matches / core_length if core_length > 0 else 0.0
    return identity, matches, core_length, start, end


def _build_ref_to_numbering_map(ref_aligned: str, num_aligned: str) -> Dict[int, int]:
    """
    建立 ref 残基索引 → numbering 编号位置的映射。

    Args:
        ref_aligned: ref vs numbering needle 比对结果中的 ref 行
        num_aligned: ref vs numbering needle 比对结果中的 numbering 行

    Returns:
        {ref_residue_index_1base: numbering_position_1base}
        例如 ref 的第5个残基对应编号位置17 → {5: 17}
        只有 ref 和 numbering 都有残基的对齐位置才记录映射
    """
    mapping: Dict[int, int] = {}
    ref_idx = 0
    num_pos = 0
    for r_char, n_char in zip(ref_aligned, num_aligned):
        if r_char != '-':
            ref_idx += 1
        if n_char != '-':
            num_pos += 1
        if r_char != '-' and n_char != '-':
            mapping[ref_idx] = num_pos
    return mapping


def _find_core_mutations(
    ref_aligned: str,
    tgt_aligned: str,
    core_start: int,
    core_end: int,
    ref_to_num: Dict[int, int],
) -> List[Dict[str, Any]]:
    """
    在核心区间内提取差异位点，合并相邻ins/del，映射到编号位置。

    Args:
        ref_aligned: ref vs tgt needle ref行
        tgt_aligned: ref vs tgt needle tgt行
        core_start: 核心区间起始位置（0-based, aligned坐标）
        core_end: 核心区间结束位置（0-based, aligned坐标）
        ref_to_num: {ref_idx: numbering_position}

    Returns:
        突变列表 [{reference_residue, numbering_position, target_residue, mutation_string}]
    """
    if core_start < 0 or core_end < 0:
        return []

    # --- 第一步：收集核心区间内的原始差异 ---
    # raw_diffs: [(aligned_pos, ref_char, tgt_char)]
    raw_diffs: List[Tuple[int, str, str]] = []
    for i in range(core_start, core_end + 1):
        r_char = ref_aligned[i]
        t_char = tgt_aligned[i]
        if r_char != t_char:
            raw_diffs.append((i, r_char, t_char))

    if not raw_diffs:
        return []

    # --- 辅助：获取 aligned 位置对应的 ref 索引（1-based）---
    def _ref_idx_at(aln_pos: int) -> Optional[int]:
        if ref_aligned[aln_pos] == '-':
            return None
        cnt = sum(1 for j in range(0, aln_pos + 1) if ref_aligned[j] != '-')
        return cnt

    # --- 辅助：获取编号位置 ---
    def _num_pos_at(aln_pos: int) -> Optional[int]:
        ref_idx = _ref_idx_at(aln_pos)
        if ref_idx is not None:
            return ref_to_num.get(ref_idx)
        # ref 为 gap（插入），找左侧最近 ref 残基的编号位置
        for j in range(aln_pos - 1, -1, -1):
            if ref_aligned[j] != '-':
                idx = _ref_idx_at(j)
                if idx and idx in ref_to_num:
                    return ref_to_num[idx]
        return None

    # --- 第二步：合并相邻 ins/del 对 ---
    merged: List[Tuple[str, int, str]] = []  # (ref_char, num_pos, tgt_char)

    i = 0
    while i < len(raw_diffs):
        aln_pos, r_char, t_char = raw_diffs[i]

        # 检查是否与下一个差异构成相邻 ins/del 对
        is_del = (r_char != '-' and t_char == '-')
        is_ins = (r_char == '-' and t_char != '-')
        is_sub = (r_char != '-' and t_char != '-')

        if (is_del or is_ins) and i + 1 < len(raw_diffs):
            next_pos, next_r, next_t = raw_diffs[i + 1]
            if next_pos == aln_pos + 1:  # 在比对中相邻
                next_is_del = (next_r != '-' and next_t == '-')
                next_is_ins = (next_r == '-' and next_t != '-')

                # Case 1: deletion followed by insertion → 合并为替换
                if is_del and next_is_ins:
                    ref_idx = _ref_idx_at(aln_pos)
                    num_pos = ref_to_num.get(ref_idx) if ref_idx else None
                    if num_pos is not None:
                        merged.append((r_char, num_pos, next_t))
                        i += 2
                        continue

                # Case 2: insertion followed by deletion → 合并为替换
                if is_ins and next_is_del:
                    ref_idx = _ref_idx_at(next_pos)
                    num_pos = ref_to_num.get(ref_idx) if ref_idx else None
                    if num_pos is not None:
                        merged.append((next_r, num_pos, t_char))
                        i += 2
                        continue

        # 无法合并：正常处理
        num_pos = _num_pos_at(aln_pos)
        if num_pos is None:
            i += 1
            continue

        if is_sub:
            merged.append((r_char, num_pos, t_char))
        elif is_del:
            # 内部 deletion: D36-
            merged.append((r_char, num_pos, '-'))
        elif is_ins:
            # 单独插入：保留插入标记
            merged.append(('-', num_pos, t_char))

        i += 1

    # --- 第三步：格式化为突变列表 ---
    mutations: List[Dict[str, Any]] = []
    seen_positions: set = set()

    for r_char, num_pos, t_char in merged:
        # 去重：同一个编号位置可能有多个差异
        key = (num_pos, r_char, t_char)
        if key in seen_positions:
            continue
        seen_positions.add(key)

        mutation_str = f"{r_char}{num_pos}{t_char}"
        mutations.append({
            'reference_residue': r_char,
            'numbering_position': num_pos,
            'target_residue': t_char,
            'mutation_string': mutation_str,
        })

    # 按编号位置排序
    mutations.sort(key=lambda m: m['numbering_position'])
    return mutations


def compare_sequences(
    ref_seq: str,
    num_seq: str,
    tgt_seq: str,
    gapopen: float = DEFAULT_GAPOPEN,
    gapextend: float = DEFAULT_GAPEXTEND,
) -> Dict[str, Any]:
    """
    三序列比对分析：以编号序列为坐标，比较参比序列与目标序列的差异。

    流程：
    1. ref vs numbering needle → 建立编号映射
    2. ref vs tgt needle → core identity + 差异位点
    3. 差异位点 → 编号映射 → 突变列表

    Args:
        ref_seq: 参比序列（权利要求用于限定同一性的参考序列）
        num_seq: 编号序列（权利要求指定用于编号的位置序列，默认等于 ref_seq）
        tgt_seq: 目标序列（待评估的目标蛋白序列）
        gapopen: Gap open罚分
        gapextend: Gap extend罚分

    Returns:
        dict:
            - core_identity: 核心区间同一性（去掉terminal overhang后的identity）
            - longest_identity: needle Longest_Identity
            - matches: 核心区间匹配数
            - core_length: 核心区间长度（含内部gap）
            - total_mutations: 突变总数
            - mutations: 突变列表 [{reference_residue, numbering_position, target_residue, mutation_string}]
            - mutation_string: 斜杠连接的突变字符串，如 "S3T/N43R/G118M"
            - alignments: 比对详情
            - alignment_chunks: 分块可视化
    """
    logger.info("Starting three-sequence comparison analysis")

    # Step 1: Align Reference vs Numbering → 建立编号映射
    ref_vs_num_a, num_aligned, raw_ref_num, identity_ref_num, longest_id_ref = run_needle_alignment(
        ref_seq, num_seq, gapopen, gapextend
    )
    ref_to_num = _build_ref_to_numbering_map(ref_vs_num_a, num_aligned)
    logger.info(f"Ref vs Num: identity={identity_ref_num:.2%}, mapped {len(ref_to_num)} residues")

    # Step 2: Align Reference vs Target
    ref_vs_tgt_a, ref_vs_tgt_b, raw_ref_tgt, identity_full, longest_id_ref_tgt = run_needle_alignment(
        ref_seq, tgt_seq, gapopen, gapextend
    )
    logger.info(f"Ref vs Tgt: full_identity={identity_full:.2%}, longest={longest_id_ref_tgt:.2%}")

    # Step 3: 计算核心区间同一性
    core_identity, core_matches, core_length, core_start, core_end = _compute_core_identity(
        ref_vs_tgt_a, ref_vs_tgt_b
    )
    logger.info(f"Core region: identity={core_identity:.2%}, length={core_length}, matches={core_matches}")

    # Step 4: 核心区间内提取突变
    mutations = _find_core_mutations(
        ref_vs_tgt_a, ref_vs_tgt_b, core_start, core_end, ref_to_num
    )
    logger.info(f"Mutations in core region: {len(mutations)}")

    # Step 5: 突变字符串
    mutation_string = '/'.join(m['mutation_string'] for m in mutations)

    # Step 6: 构建可视化
    # 重新获取 num_pos_to_ref / num_pos_to_tgt 用于可视化
    num_pos_to_ref: Dict[int, str] = {}
    num_pos_to_tgt: Dict[int, str] = {}
    ref_idx = 0
    for i, char in enumerate(num_aligned):
        if char != '-':
            if ref_vs_num_a[i] != '-':
                ref_idx += 1
                num_pos_to_ref[ref_idx - 1] = ref_vs_num_a[i]
    ref_idx = 0
    # tgt vs numbering 对齐用于 tgt 序列可视化
    _, num_aligned_tgt, _, _, _ = run_needle_alignment(tgt_seq, num_seq, gapopen, gapextend)
    # 用 ref_vs_tgt 构建 tgt 行
    tgt_aligned_for_viz = ref_vs_tgt_b

    # 简单可视化：直接基于 ref vs tgt 比对构建
    seq_len = len(num_seq)
    num_chars = list(num_seq)
    ref_chars_list: List[str] = []
    tgt_chars_list: List[str] = []
    marker_list: List[str] = []

    mutation_positions = {m['numbering_position'] for m in mutations}

    # 映射编号位置到对齐位置
    num_to_aln: Dict[int, int] = {}
    num_cnt = 0
    for i, n_char in enumerate(num_aligned):
        if n_char != '-':
            num_cnt += 1
            num_to_aln[num_cnt] = i

    for pos in range(len(num_seq)):
        aln_pos = num_to_aln.get(pos + 1)
        if aln_pos is not None and aln_pos < len(ref_vs_tgt_a) and aln_pos < len(ref_vs_tgt_b):
            ref_chars_list.append(ref_vs_tgt_a[aln_pos])
            tgt_chars_list.append(ref_vs_tgt_b[aln_pos])
            is_mut = (pos + 1) in mutation_positions
            marker_list.append('*' if is_mut else ' ')
        else:
            ref_chars_list.append('-')
            tgt_chars_list.append('-')
            marker_list.append(' ')

    alignment_chunks = _build_visual_alignment(
        num_chars, ref_chars_list, tgt_chars_list, marker_list, len(num_seq)
    )

    return {
        'core_identity': round(core_identity * 100, 2),
        'longest_identity': round(longest_id_ref_tgt * 100, 2),
        'core_matches': core_matches,
        'core_length': core_length,
        'total_mutations': len(mutations),
        'mutations': mutations,
        'mutation_string': mutation_string,
        'alignments': {
            'ref_vs_num': {
                'aligned_a': ref_vs_num_a,
                'aligned_b': num_aligned,
                'identity': identity_ref_num,
                'longest_identity': longest_id_ref,
            },
            'ref_vs_tgt': {
                'aligned_a': ref_vs_tgt_a,
                'aligned_b': ref_vs_tgt_b,
                'identity': identity_full,
                'core_identity': round(core_identity, 4),
            },
        },
        'raw_results': {
            'ref_vs_num': raw_ref_num,
            'ref_vs_tgt': raw_ref_tgt,
        },
        'alignment_chunks': alignment_chunks,
    }


def _build_visual_alignment(
    num_chars: List[str],
    ref_chars: List[str],
    tgt_chars: List[str],
    marker_chars: List[str],
    seq_len: int,
    chunk_size: int = 30,
) -> List[Dict[str, Any]]:
    """
    构建分块可视化比对。

    返回块列表，每块包含:
    - range_start / range_end: 编号范围
    - coord, numbering, reference, target, marker
    """
    # 坐标轴
    coord_chars = [' '] * seq_len
    for i in range(1, seq_len + 1):
        if i == 1 or i % 10 == 0:
            s = str(i)
            last_idx = i - 1
            start = last_idx - len(s) + 1
            for j, c in enumerate(s):
                if 0 <= start + j < seq_len:
                    coord_chars[start + j] = c

    chunks = []
    for start_pos in range(0, seq_len, chunk_size):
        end_pos = min(start_pos + chunk_size, seq_len)
        chunk = {
            'range_start': start_pos + 1,
            'range_end': end_pos,
            'coord': ''.join(coord_chars[start_pos:end_pos]),
            'numbering': ''.join(num_chars[start_pos:end_pos]),
            'reference': ''.join(ref_chars[start_pos:end_pos]),
            'target': ''.join(tgt_chars[start_pos:end_pos]),
            'marker': ''.join(marker_chars[start_pos:end_pos]),
        }
        chunks.append(chunk)

    return chunks


def batch_compare_from_excel(
    file_path: str,
    gapopen: float = DEFAULT_GAPOPEN,
    gapextend: float = DEFAULT_GAPEXTEND,
) -> List[Dict[str, Any]]:
    """
    从Excel文件批量处理三序列比对。

    Returns:
        每个元素的dict包含 compare_sequences() 的输出 + name, index
    """
    import pandas as pd

    df = pd.read_excel(file_path, engine='openpyxl')
    df.dropna(how='all', inplace=True)

    col_names = [str(col).lower() for col in df.columns]

    ref_col = None
    num_col = None
    tgt_col = None
    name_col = None

    for i, col in enumerate(col_names):
        if any(kw in col for kw in ['参比', 'reference', 'ref']):
            ref_col = df.columns[i]
        elif any(kw in col for kw in ['编号', 'numbering', 'num']):
            num_col = df.columns[i]
        elif any(kw in col for kw in ['目标', 'target', 'tgt']):
            tgt_col = df.columns[i]
        elif any(kw in col for kw in ['名称', 'name', '序列名']):
            name_col = df.columns[i]

    if not ref_col:
        ref_col = df.columns[0]
    if not num_col and len(df.columns) > 1:
        num_col = df.columns[1]
    if not tgt_col and len(df.columns) > 2:
        tgt_col = df.columns[2]

    results = []
    for idx, row in df.iterrows():
        ref_seq = str(row[ref_col]) if pd.notna(row[ref_col]) else ''
        num_seq = str(row[num_col]) if pd.notna(row[num_col]) else ''
        tgt_seq = str(row[tgt_col]) if pd.notna(row[tgt_col]) else ''
        seq_name = str(row[name_col]) if name_col and pd.notna(row[name_col]) else f'序列{idx + 1}'

        if not ref_seq or not num_seq or not tgt_seq:
            logger.warning(f"Row {idx + 1}: 缺少序列数据，已跳过")
            continue

        result = compare_sequences(ref_seq, num_seq, tgt_seq, gapopen, gapextend)
        result['name'] = seq_name
        result['index'] = idx + 1
        results.append(result)
        logger.info(f"Batch {idx + 1}/{len(df)}: {seq_name} - core_identity={result['core_identity']}%")

    return results
