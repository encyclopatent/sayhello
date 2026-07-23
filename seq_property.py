"""
序列理化性质分析引擎 - 计算核酸/蛋白质序列的各种理化性质

功能：
- 自动检测分子类型 (DNA/RNA/Protein)
- 核酸：长度、GC含量、熔解温度、分子量、碱基组成
- 蛋白质：长度、分子量、消光系数、不稳定指数、脂肪指数、GRAVY、等电点、氨基酸组成
- 批量计算支持
"""

import re
import math
from typing import Dict, List, Tuple, Optional, Any

# ─── 氨基酸分子量 ────────────────────────────────────────
AA_MASS: Dict[str, float] = {
    'A': 71.03711, 'R': 156.10111, 'N': 114.04293, 'D': 115.02694,
    'C': 103.00919, 'Q': 128.05858, 'E': 129.04259, 'G': 57.02146,
    'H': 137.05891, 'I': 113.08406, 'L': 113.08406, 'K': 128.09496,
    'M': 131.04049, 'F': 147.06841, 'P': 97.05276, 'S': 87.03203,
    'T': 101.04768, 'W': 186.07931, 'Y': 163.06333, 'V': 99.06841,
    'U': 150.95363, 'O': 237.30100,  # selenocysteine, pyrrolysine
}

# ─── 核酸分子量 ──────────────────────────────────────────
DNA_BASE_MASS: Dict[str, float] = {
    'A': 313.21, 'T': 304.20, 'G': 329.21, 'C': 289.18,
}
RNA_BASE_MASS: Dict[str, float] = {
    'A': 329.21, 'U': 306.17, 'G': 345.21, 'C': 305.18,
}
DNA_MASS_WATER = 18.015  # 减去水分子质量
WATER_MASS = 18.015

# ─── 氨基酸消光系数 (280nm) ──────────────────────────────
EXTINCTION_COEFF: Dict[str, float] = {
    'W': 5690, 'Y': 1280, 'C': 120,  # Cystine (disulfide)
}

# ─── 氨基酸 pKa 值 ─────────────────────────────────────────
AA_PKA: Dict[str, Dict[str, float]] = {
    'A': {'pKa_COOH': 2.34, 'pKa_NH3': 9.69},
    'R': {'pKa_COOH': 2.17, 'pKa_NH3': 9.04, 'pKa_R': 12.48},
    'N': {'pKa_COOH': 2.02, 'pKa_NH3': 8.80},
    'D': {'pKa_COOH': 1.88, 'pKa_NH3': 9.60, 'pKa_R': 3.65},
    'C': {'pKa_COOH': 1.96, 'pKa_NH3': 10.28, 'pKa_R': 8.18},
    'Q': {'pKa_COOH': 2.17, 'pKa_NH3': 9.13},
    'E': {'pKa_COOH': 2.19, 'pKa_NH3': 9.67, 'pKa_R': 4.25},
    'G': {'pKa_COOH': 2.34, 'pKa_NH3': 9.60},
    'H': {'pKa_COOH': 1.82, 'pKa_NH3': 9.17, 'pKa_R': 6.00},
    'I': {'pKa_COOH': 2.36, 'pKa_NH3': 9.68},
    'L': {'pKa_COOH': 2.36, 'pKa_NH3': 9.60},
    'K': {'pKa_COOH': 2.18, 'pKa_NH3': 8.95, 'pKa_R': 10.53},
    'M': {'pKa_COOH': 2.28, 'pKa_NH3': 9.21},
    'F': {'pKa_COOH': 1.83, 'pKa_NH3': 9.13},
    'P': {'pKa_COOH': 1.99, 'pKa_NH3': 10.60},
    'S': {'pKa_COOH': 2.21, 'pKa_NH3': 9.15},
    'T': {'pKa_COOH': 2.09, 'pKa_NH3': 9.10},
    'W': {'pKa_COOH': 2.83, 'pKa_NH3': 9.39},
    'Y': {'pKa_COOH': 2.20, 'pKa_NH3': 9.11, 'pKa_R': 10.07},
    'V': {'pKa_COOH': 2.32, 'pKa_NH3': 9.62},
}

# ─── 不稳定指数 dipeptide 权重 (部分) ───────────────────
# 完整版太庞大，这里用简化版 + 近似算法
INSTABILITY_WEIGHTS: Dict[str, float] = {
    'DI': 1.0, 'DV': 1.0, 'DP': 1.0, 'DG': 0.8, 'DN': 0.6,
    'DA': 0.5, 'DC': 0.5, 'DE': 0.5, 'DQ': 0.4, 'DS': 0.4,
    'DT': 0.3, 'DW': -0.3, 'DY': -0.3, 'DD': 0.2, 'EE': 0.2,
    'EI': 0.2, 'EQ': 0.2, 'ER': 0.2, 'ES': 0.2, 'ET': 0.2,
    'EW': 0.2, 'EY': 0.2, 'FF': 0.4, 'FI': 0.4, 'FL': 0.4,
    'FM': 0.4, 'FP': 0.4, 'FS': 0.4, 'FW': 0.4, 'FY': 0.4,
    'GI': 0.4, 'GL': 0.4, 'GM': 0.4, 'GP': 0.5, 'GR': 0.4,
    'GS': 0.4, 'GT': 0.4, 'GV': 0.4, 'GW': 0.4, 'GY': 0.4,
    'HI': 0.4, 'HL': 0.4, 'HP': 0.5, 'HS': 0.4, 'HT': 0.4,
    'HV': 0.4, 'HW': 0.4, 'HY': 0.4, 'II': 0.4, 'IL': 0.4,
    'IM': 0.4, 'IP': 0.5, 'IQ': 0.4, 'IR': 0.4, 'IS': 0.4,
    'IT': 0.4, 'IV': 0.4, 'IW': 0.4, 'IY': 0.4,
}

# ─── 氨基酸疏水指数 (Kyte-Doolittle) ─────────────────────
HYDROPHOBICITY: Dict[str, float] = {
    'I': 4.5, 'V': 4.2, 'L': 3.8, 'F': 2.8, 'C': 2.5, 'M': 1.9, 'A': 1.8,
    'G': -0.4, 'T': -0.7, 'S': -0.8, 'W': -0.9, 'Y': -1.3, 'P': -1.6,
    'H': -3.2, 'E': -3.5, 'Q': -3.5, 'D': -3.5, 'N': -3.5, 'K': -3.9, 'R': -4.5,
}


def detect_moltype(seq: str) -> str:
    """自动检测分子类型：DNA, RNA, 或 Protein"""
    seq = seq.upper().strip()
    if not seq:
        return 'Unknown'

    seq_clean = re.sub(r'\s+', '', seq)
    chars = set(seq_clean)

    # Na 只出现在核酸中，U 只出现在 RNA 中
    has_U = 'U' in chars
    has_T = 'T' in chars

    # 只含 ACGT → DNA；只含 ACGU → RNA
    only_dna_letters = chars.issubset({'A', 'C', 'G', 'T', 'N'})
    only_rna_letters = chars.issubset({'A', 'C', 'G', 'U', 'N'})

    if only_dna_letters and not has_U:
        return 'DNA'
    if only_rna_letters and not has_T:
        return 'RNA'

    # 含非核酸字母 → Protein
    nucleic_chars = {'A', 'C', 'G', 'T', 'U', 'N'}
    if any(c not in nucleic_chars for c in chars):
        return 'Protein'

    # 含U且不含纯蛋白字母 → RNA
    if has_U:
        return 'RNA'
    return 'DNA'


def analyze_protein(seq: str) -> Dict[str, Any]:
    """分析蛋白质序列的理化性质"""
    seq = re.sub(r'\s+', '', seq).upper()
    length = len(seq)

    if length == 0:
        return {}

    # 1. 氨基酸组成
    composition: Dict[str, int] = {}
    for aa in seq:
        composition[aa] = composition.get(aa, 0) + 1

    composition_pct = {k: round(v / length * 100, 2) for k, v in sorted(composition.items())}
    composition_pct_sorted = sorted(composition_pct.items(), key=lambda x: -x[1])

    # 2. 分子量 (减去水的质量)
    mass = WATER_MASS  # N-terminus extra H + C-terminus OH
    for aa in seq:
        mass += AA_MASS.get(aa, 110.0)  # fallback for unusual AAs

    # 3. 消光系数 (280nm, 假设二硫键)
    n_trp = composition.get('W', 0)
    n_tyr = composition.get('Y', 0)
    n_cys = composition.get('C', 0)
    extinction_reduced = n_trp * 5690 + n_tyr * 1280
    extinction_oxidized = n_trp * 5690 + n_tyr * 1280 + n_cys * 120

    # 4. 摩尔消光系数 → mg/mL (1 mg/mL = 1 g/L)
    epsilon_1mg_per_ml_reduced = extinction_reduced / mass if mass > 0 else 0
    epsilon_1mg_per_ml_oxidized = extinction_oxidized / mass if mass > 0 else 0

    # 5. GRAVY (Grand Average of Hydropathy)
    gravy = sum(HYDROPHOBICITY.get(aa, 0) for aa in seq) / length if length > 0 else 0

    # 6. 脂肪指数 (Aliphatic index)
    ala = composition.get('A', 0)
    val = composition.get('V', 0)
    ile = composition.get('I', 0)
    leu = composition.get('L', 0)
    aliphatic_index = (ala * 1.0 + val * 2.9 + (ile + leu) * 3.9) / length * 100 if length > 0 else 0

    # 7. 不稳定指数 (简化算法)
    instability = 0
    for i in range(length - 1):
        dipep = seq[i:i+2]
        weight = INSTABILITY_WEIGHTS.get(dipep, 0)
        instability += weight
    instability_index = (10.0 / length) * instability if length > 0 else 0

    # 8. 等电点 (pI) - 使用Henderson-Hasselbalch近似
    pI = _calculate_pI(seq, composition)

    # 9. 净电荷 vs pH (在几个关键pH下)
    charge_profile = []
    for ph_int in range(1, 14):
        ph = float(ph_int)
        charge = _calculate_charge_at_ph(seq, composition, ph)
        if abs(charge - 0) < 0.05:
            pI = round(ph, 1)
        charge_profile.append({'ph': ph, 'charge': round(charge, 3)})

    # 10. 分类计数
    pos_charged = composition.get('K', 0) + composition.get('R', 0) + composition.get('H', 0)
    neg_charged = composition.get('D', 0) + composition.get('E', 0)
    polar = sum(composition.get(aa, 0) for aa in 'NQSTYC')
    hydrophobic_res = sum(composition.get(aa, 0) for aa in 'AILMFWVP')

    return {
        'length': length,
        'molecular_weight': round(mass, 2),
        'extinction_280_reduced': extinction_reduced,
        'extinction_280_oxidized': extinction_oxidized,
        'extinction_1mg_reduced': round(epsilon_1mg_per_ml_reduced, 3),
        'extinction_1mg_oxidized': round(epsilon_1mg_per_ml_oxidized, 3),
        'pI': round(pI, 2),
        'gravy': round(gravy, 3),
        'aliphatic_index': round(aliphatic_index, 2),
        'instability_index': round(instability_index, 2),
        'instability_class': '不稳定' if instability_index > 40 else '稳定',
        'charge_ph7': round(_calculate_charge_at_ph(seq, composition, 7.0), 3),
        'composition': {k: v for k, v in composition_pct_sorted},
        'composition_raw': {k: v for k, v in sorted(composition.items())},
        'charge_profile': charge_profile,
        'pos_charged': pos_charged,
        'neg_charged': neg_charged,
        'polar': polar,
        'hydrophobic': hydrophobic_res,
    }


def _calculate_pI(seq: str, composition: Dict[str, int]) -> float:
    """使用二分法计算等电点"""
    low, high = 0.0, 14.0
    for _ in range(100):
        mid = (low + high) / 2
        charge = _calculate_charge_at_ph(seq, composition, mid)
        if abs(charge) < 0.001:
            return mid
        if charge > 0:
            low = mid
        else:
            high = mid
    return (low + high) / 2


def _calculate_charge_at_ph(seq: str, composition: Dict[str, int], ph: float) -> float:
    """计算指定 pH 下的净电荷"""
    # N-terminus pKa ~ 8.0, C-terminus pKa ~ 3.1
    n_term_pka = 8.0
    c_term_pka = 3.1

    charge = 0.0

    # N-terminus
    charge += 10 ** (n_term_pka - ph) / (1 + 10 ** (n_term_pka - ph))

    # C-terminus
    charge -= 10 ** (ph - c_term_pka) / (1 + 10 ** (ph - c_term_pka))

    # Side chains
    # K: pKa ~ 10.5, R: pKa ~ 12.5, H: pKa ~ 6.0
    # D: pKa ~ 3.9, E: pKa ~ 4.1, C: pKa ~ 8.3, Y: pKa ~ 10.1
    side_chain_pka = {
        'K': 10.5, 'R': 12.5, 'H': 6.0,
        'D': 3.9, 'E': 4.1, 'C': 8.3, 'Y': 10.1,
    }

    for aa, count in composition.items():
        pka = side_chain_pka.get(aa)
        if pka is None:
            continue
        if aa in ('K', 'R', 'H'):
            # Positive charged
            charge += count * (10 ** (pka - ph) / (1 + 10 ** (pka - ph)))
        elif aa in ('D', 'E', 'C', 'Y'):
            # Negative charged
            charge -= count * (10 ** (ph - pka) / (1 + 10 ** (ph - pka)))

    return charge


def analyze_nucleic(seq: str, moltype: str) -> Dict[str, Any]:
    """分析核酸序列的理化性质"""
    seq = re.sub(r'\s+', '', seq).upper()
    length = len(seq)

    if length == 0:
        return {}

    # 1. 碱基组成
    base_counts: Dict[str, int] = {}
    for base in seq:
        base_counts[base] = base_counts.get(base, 0) + 1

    base_pct = {}
    gc_count = 0
    for base, count in base_counts.items():
        base_pct[base] = round(count / length * 100, 2)
        if base in ('G', 'C', 'S'):
            gc_count += count

    gc_pct = round(gc_count / length * 100, 2) if length > 0 else 0

    # 2. 分子量
    mass_table = DNA_BASE_MASS if moltype == 'DNA' else RNA_BASE_MASS
    mass = 0
    for base in seq:
        if base in mass_table:
            mass += mass_table[base]
        elif base == 'N' and moltype == 'DNA':
            mass += sum(DNA_BASE_MASS.values()) / 4
        elif base == 'N' and moltype == 'RNA':
            mass += sum(RNA_BASE_MASS.values()) / 4
    if mass > 0:
        mass -= (length - 1) * DNA_MASS_WATER  # 减去磷酸二酯键脱水

    # 3. 熔解温度 (多种公式)
    # 基本公式: Tm = 81.5 + 16.6*log10(Na+) + 0.41*(%GC) - 675/length
    na_conc = 0.05  # 50 mM Na+
    tm_basic = 81.5 + 16.6 * math.log10(na_conc) + 0.41 * gc_pct - (675.0 / length) if length > 0 else 0
    # Wallace 公式 (短序列)
    if length <= 14:
        at_count = sum(base_counts.get(b, 0) for b in ('A', 'T', 'U'))
        tm_wallace = 2 * at_count + 4 * gc_count
    else:
        tm_wallace = tm_basic

    return {
        'length': length,
        'moltype': moltype,
        'base_counts': base_counts,
        'base_pct': base_pct,
        'gc_pct': gc_pct,
        'at_pct': round(100 - gc_pct, 2),
        'molecular_weight': round(mass, 2),
        'tm_basic': round(tm_basic, 1),
        'tm_wallace': round(tm_wallace, 1),
        'is_dna': moltype == 'DNA',
    }


def analyze_sequence(seq_str: str, name: str = '') -> Dict[str, Any]:
    """综合分析一条序列"""
    seq = re.sub(r'\s+', '', seq_str)
    if not seq:
        return {}

    moltype = detect_moltype(seq)
    seq_upper = seq.upper()

    result: Dict[str, Any] = {
        'name': name or '未命名序列',
        'sequence': seq_str[:200],  # 仅保留前200字符用于展示
        'raw_length': len(seq_str),
        'clean_length': len(seq),
        'moltype': moltype,
    }

    if moltype in ('DNA', 'RNA'):
        result['nucleic'] = analyze_nucleic(seq_upper, moltype)
        # 也用核酸算分子量
        result['molecular_weight'] = result['nucleic']['molecular_weight']
    else:
        result['protein'] = analyze_protein(seq_upper)
        result['molecular_weight'] = result['protein']['molecular_weight']

    return result


def batch_analyze_excel(file_path: str) -> List[Dict[str, Any]]:
    """从Excel批量分析序列"""
    import pandas as pd

    df = pd.read_excel(file_path, engine='openpyxl')
    df.dropna(how='all', inplace=True)

    col_names = [str(col).lower() for col in df.columns]

    seq_col = None
    name_col = None
    for i, col in enumerate(col_names):
        if any(kw in col for kw in ['序列', 'sequence', 'seq']):
            seq_col = df.columns[i]
        if any(kw in col for kw in ['名称', 'name', '序列名', '标题']):
            name_col = df.columns[i]

    if not seq_col:
        seq_col = df.columns[0]

    results = []
    for idx, row in df.iterrows():
        seq = str(row[seq_col]) if pd.notna(row[seq_col]) else ''
        if not seq:
            continue
        name = str(row[name_col]) if name_col and pd.notna(row[name_col]) else f'序列{idx + 1}'
        result = analyze_sequence(seq, name)
        result['index'] = idx + 1
        results.append(result)

    return results
