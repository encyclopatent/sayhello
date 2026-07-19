"""
三序列比对与突变分析模块 - 基于EMBOSS needle算法

分析流程：
1. needle比对 参比序列 vs 编号序列
2. needle比对 目标序列 vs 编号序列
3. 以编号序列为坐标系统，比对参比与目标的差异
4. 计算序列同一性并报告突变位点
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
) -> Tuple[str, str, str, float]:
    """
    运行EMBOSS needle进行双序列全局比对。

    Args:
        seq_a: 第一条序列
        seq_b: 第二条序列
        gapopen: Gap open罚分
        gapextend: Gap extend罚分

    Returns:
        (aligned_a, aligned_b, raw_result, identity)
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
        for line in raw_result.split('\n'):
            if "# Identity:" in line:
                parts = line.split()
                if len(parts) > 2:
                    vals = parts[2].split('/')
                    if len(vals) == 2:
                        identity = float(vals[0]) / float(vals[1]) if float(vals[1]) > 0 else 0.0
                        break

        # 读取比对结果
        alignment = AlignIO.read(outfile, "emboss")
        aligned_a = str(alignment[0].seq)
        aligned_b = str(alignment[1].seq)

        return aligned_a, aligned_b, raw_result, identity

    finally:
        for f in [fasta_a, fasta_b, outfile]:
            if os.path.exists(f):
                os.remove(f)


def compare_sequences(
    ref_seq: str,
    num_seq: str,
    tgt_seq: str,
    gapopen: float = DEFAULT_GAPOPEN,
    gapextend: float = DEFAULT_GAPEXTEND,
) -> Dict[str, Any]:
    """
    三序列比对分析：以编号序列为坐标，比较参比序列与目标序列的差异。

    Args:
        ref_seq: 参比序列
        num_seq: 编号序列（提供坐标系统）
        tgt_seq: 目标序列
        gapopen: Gap open罚分
        gapextend: Gap extend罚分

    Returns:
        dict:
            - identity: 参比vs目标同一性
            - matches: 匹配数
            - mismatches: 错配数
            - total_positions: 总比对位置
            - mutations: 突变列表 [{numbering_position, reference_residue, target_residue}]
            - alignments: 比对序列详情
            - raw_results: needle原始输出
    """
    logger.info("Starting three-sequence comparison analysis")

    # Step 1: Align Reference vs Numbering
    ref_aligned, num_aligned_ref, raw_ref_num, identity_ref_num = run_needle_alignment(
        ref_seq, num_seq, gapopen, gapextend
    )
    logger.info(f"Ref vs Num identity: {identity_ref_num:.2%}")

    # Step 2: Align Target vs Numbering
    tgt_aligned, num_aligned_tgt, raw_tgt_num, identity_tgt_num = run_needle_alignment(
        tgt_seq, num_seq, gapopen, gapextend
    )
    logger.info(f"Tgt vs Num identity: {identity_tgt_num:.2%}")

    # Step 3: Build numbering-position-to-residue maps
    num_pos_to_ref: Dict[int, str] = {}
    num_pos_to_tgt: Dict[int, str] = {}

    num_idx = 0
    for i, char in enumerate(num_aligned_ref):
        if char != '-':
            num_pos_to_ref[num_idx] = ref_aligned[i]
            num_idx += 1

    num_idx = 0
    for i, char in enumerate(num_aligned_tgt):
        if char != '-':
            num_pos_to_tgt[num_idx] = tgt_aligned[i]
            num_idx += 1

    # Step 4: Compare by numbering coordinate
    mutations: List[Dict[str, Any]] = []
    matches = 0
    mismatches = 0
    all_positions = sorted(set(num_pos_to_ref.keys()) | set(num_pos_to_tgt.keys()))

    for num_pos in all_positions:
        ref_char = num_pos_to_ref.get(num_pos, '-')
        tgt_char = num_pos_to_tgt.get(num_pos, '-')

        if ref_char == '-' or tgt_char == '-':
            continue  # 任一缺失则不统计

        if ref_char == tgt_char:
            matches += 1
        else:
            mismatches += 1
            mutations.append({
                'numbering_position': num_pos + 1,
                'reference_residue': ref_char,
                'target_residue': tgt_char,
            })

    total = matches + mismatches
    identity = matches / total if total > 0 else 0.0
    logger.info(f"Comparison complete: identity={identity:.2%}, mutations={len(mutations)}")

    # 构建可视化字符串
    alignment_chunks = _build_visual_alignment(mutations, num_seq, num_pos_to_ref, num_pos_to_tgt)

    return {
        'identity': identity,
        'matches': matches,
        'mismatches': mismatches,
        'total_positions': total,
        'mutations': mutations,
        'alignments': {
            'ref_vs_num': {
                'sequence_a': ref_aligned,
                'sequence_b': num_aligned_ref,
                'identity': identity_ref_num,
            },
            'tgt_vs_num': {
                'sequence_a': tgt_aligned,
                'sequence_b': num_aligned_tgt,
                'identity': identity_tgt_num,
            },
        },
        'raw_results': {
            'ref_vs_num': raw_ref_num,
            'tgt_vs_num': raw_tgt_num,
        },
        'alignment_chunks': alignment_chunks,
    }


def _build_visual_alignment(
    mutations: List[Dict[str, Any]],
    num_seq: str,
    num_pos_to_ref: Dict[int, str],
    num_pos_to_tgt: Dict[int, str],
    chunk_size: int = 30,
) -> List[Dict[str, Any]]:
    """
    构建可视化的序列比对，每30个残基为一块分块显示。

    返回块列表，每块包含:
    - range_start / range_end: 该块的编号范围
    - coord, numbering, reference, target, marker: 对应行字符串
    """
    seq_len = len(num_seq)

    num_chars: List[str] = []
    ref_chars: List[str] = []
    tgt_chars: List[str] = []
    marker_chars: List[str] = []

    for pos in range(seq_len):
        ref_char = num_pos_to_ref.get(pos, '-')
        tgt_char = num_pos_to_tgt.get(pos, '-')
        num_char = num_seq[pos]

        num_chars.append(num_char)
        ref_chars.append(ref_char)
        tgt_chars.append(tgt_char)

        is_mutation = (ref_char != '-' and tgt_char != '-' and ref_char != tgt_char)
        marker_chars.append('*' if is_mutation else ' ')

    # 坐标轴：数字最后一位与所在位点对齐
    coord_chars = [' '] * seq_len
    for i in range(1, seq_len + 1):
        if i == 1 or i % 10 == 0:
            s = str(i)
            last_idx = i - 1
            start = last_idx - len(s) + 1
            for j, c in enumerate(s):
                if 0 <= start + j < seq_len:
                    coord_chars[start + j] = c

    # 分块
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

    Excel需要包含列:
    - 参比序列 / reference / ref
    - 编号序列 / numbering / num
    - 目标序列 / target / tgt
    - 序列名称 / name (可选)

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
        logger.info(f"Batch {idx + 1}/{len(df)}: {seq_name} - identity: {result['identity']:.2%}")

    return results
