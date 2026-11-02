from Bio.Align import PairwiseAligner, substitution_matrices
import subprocess
from Bio import AlignIO
import os

def create_aligner(mode, matrix_name="BLOSUM62", gapopen=10.0, gapextend=0.5):
    # 1. 创建对齐器实例
    aligner = PairwiseAligner()

    # 2. 加载替代矩阵
    try:
        matrix = substitution_matrices.load(matrix_name)
        aligner.substitution_matrix = matrix
    except Exception as e:
        print(f"Warning: Could not load {matrix_name} matrix: {e}")

    # 3. 设置模式
    aligner.mode = mode

    # 4. 设置空位罚分
    #    必须设置：PairwiseAligner 默认 open/extend gap score 都是 0，
    #    相当于允许在任意位置插入任意多个空位且不扣分，最优比对路径数会指数级膨胀，
    #    Biopython 在统计最优解数量时抛
    #    OverflowError: number of optimal alignments is larger than 9223372036854775807
    #    另外空位不扣分时比对结果也和 EMBOSS needle/water 不一致。
    try:
        aligner.open_gap_score = -abs(float(gapopen))
        aligner.extend_gap_score = -abs(float(gapextend))
    except (TypeError, ValueError):
        pass

    return aligner


def _aligned_pair(aln):
    """取比对后的两条带空位序列 (target, query) 及其在原始序列中的起始位置。

    返回 (seq_a, seq_b, t_start, q_start)：
      - seq_a / seq_b 是比对区内的序列（含 '-' 空位）
      - t_start / q_start 是比对区第一列对应在原始 target / query 中的 0-based 下标
        （全局比对为 0；局部比对可能是非 0 的两翼偏移）

    兼容 Biopython 1.79（py3.6，线上环境）与 1.80+：
      - 1.80+ 直接支持 aln[0] / aln[1]，起点从 aln.coordinates 取
      - 1.79 的 aln[0] 抛 NotImplementedError，起点从 aln.path[0] 取
    """
    # --- Biopython 1.80+ ---
    try:
        seq_a = aln[0]
        seq_b = aln[1]
        coords = getattr(aln, 'coordinates', None)
        t_start = q_start = 0
        if coords is not None and len(coords) == 2 and len(coords[0]) and len(coords[1]):
            t_start = int(coords[0][0])
            q_start = int(coords[1][0])
        return seq_a, seq_b, t_start, q_start
    except (NotImplementedError, TypeError, IndexError, KeyError):
        pass

    # --- Biopython 1.79：按 path 重建比对区 ---
    path = getattr(aln, 'path', None)
    target = getattr(aln, 'target', None)
    query = getattr(aln, 'query', None)
    if path and target is not None and query is not None:
        t_parts, q_parts = [], []
        p1, p2 = path[0]
        t_start, q_start = p1, p2
        for e1, e2 in path[1:]:
            if e1 > p1 and e2 > p2:
                t_parts.append(target[p1:e1])
                q_parts.append(query[p2:e2])
            elif e1 > p1:
                t_parts.append(target[p1:e1])
                q_parts.append('-' * (e1 - p1))
            elif e2 > p2:
                t_parts.append('-' * (e2 - p2))
                q_parts.append(query[p2:e2])
            p1, p2 = e1, e2
        return ''.join(t_parts), ''.join(q_parts), t_start, q_start

    lines = str(aln).split('\n')
    seq_a = lines[0]
    seq_b = lines[2] if len(lines) > 2 else ''
    return seq_a, seq_b, 0, 0


def _build_map(seq_a, seq_b, t_start=0, q_start=0):
    """由比对后的两条序列生成 target位置 -> query位置 的映射。"""
    mapping = {}
    t_pos = t_start - 1
    q_pos = q_start - 1
    for t, q in zip(seq_a, seq_b):
        t_pos += t != '-'
        q_pos += q != '-'
        if t != '-' and q != '-':
            mapping[t_pos] = q_pos
    return mapping

def calculate_identity(t_aligned, q_aligned):
    """计算序列同一性百分比（基于比对后长度）"""
    matches = sum(1 for t, q in zip(t_aligned, q_aligned) if t == q)
    total = len(t_aligned)
    return matches / total if total > 0 else 0.0

def process_alignment(target, query, sites, key_positions=None, algorithm='global',
                      matrix_name='BLOSUM62', gapopen=10.0, gapextend=0.5):
    """处理序列比对，使用BioPython内置功能和外部工具"""
    if key_positions is None:
        key_positions = set()
    
    # 存储比对后的序列，用于可视化
    aligned_sequences = {
        'global': {'target': '', 'query': ''},
        'local': {'target': '', 'query': ''},
        'clustalw': {'target': '', 'query': ''},
        'needle': {'target': '', 'query': ''},
        'muscle': {'target': '', 'query': ''},
        'water': {'target': '', 'query': ''}
    }
    
    # 输入校验：保持与之前一致的错误提示
    if not target or not query:
        raise ValueError("sequence has zero length")

    # 执行全局比对
    global_aligner = create_aligner('global', matrix_name, gapopen, gapextend)
    global_identity = 0.0
    global_map = {}
    try:
        best_global = global_aligner.align(target, query)[0]
    except (IndexError, StopIteration):
        best_global = None
    except OverflowError as e:
        # 最优比对方案数溢出（理论上设置空位罚分后不会再发生），降级为无结果
        print(f"Biopython全局比对方案数溢出: {e}")
        best_global = None
    if best_global is not None:
        seq_a, seq_b, t_start, q_start = _aligned_pair(best_global)
        global_identity = calculate_identity(seq_a, seq_b)
        global_map = _build_map(seq_a, seq_b, t_start, q_start)
        # 保存比对后的序列
        aligned_sequences['global']['target'] = str(seq_a)
        aligned_sequences['global']['query'] = str(seq_b)

    # 执行局部比对
    local_aligner = create_aligner('local', matrix_name, gapopen, gapextend)
    local_identity = 0.0
    local_map = {}
    try:
        best_local = local_aligner.align(target, query)[0]
    except (IndexError, StopIteration):
        best_local = None
    except OverflowError as e:
        print(f"Biopython局部比对方案数溢出: {e}")
        best_local = None
    if best_local is not None:
        seq_a, seq_b, t_start, q_start = _aligned_pair(best_local)
        local_identity = calculate_identity(seq_a, seq_b)
        local_map = _build_map(seq_a, seq_b, t_start, q_start)
        # 保存比对后的序列
        aligned_sequences['local']['target'] = str(seq_a)
        aligned_sequences['local']['query'] = str(seq_b)

    # 初始化各工具相关变量
    clustalw_identity = 0.0
    clustalw_map = {}
    
    needle_identity = 0.0
    needle_longest_identity = 0.0
    needle_map = {}
    
    muscle_identity = 0.0
    muscle_map = {}
    
    water_identity = 0.0
    water_map = {}
    
    # 创建临时文件
    with open("temp_target.fasta", "w") as temp_target_file:
        temp_target_file.write(f">target\n{target}\n")
    with open("temp_query.fasta", "w") as temp_query_file:
        temp_query_file.write(f">query\n{query}\n")
    
    # 合并序列文件用于多序列比对工具
    combined_file = "temp_combined.fasta"
    with open(combined_file, "w") as combined_file_handle:
        combined_file_handle.write(f">target\n{target}\n")
        combined_file_handle.write(f">query\n{query}\n")
    
    # 环境变量设置
    env = os.environ.copy()
    env["EMBOSS_ACDROOT"] = "/opt/anaconda3/envs/rdkit-env/share/EMBOSS/acd/"
    env["EMBOSS_DATA"] = "/opt/anaconda3/envs/rdkit-env/share/EMBOSS/data/"
    env["PLPLOT_LIB"] = "/opt/anaconda3/envs/rdkit-env/share/EMBOSS/"
    
    # 1. 使用ClustalW进行比对
    try:
        # 创建ClustalW配置文件
        with open("clustalw.cfg", "w") as config_file:
            config_file.write("TYPE = PROTEIN\n")
            config_file.write("MATRIX = BLOSUM\n")
            config_file.write(f"GAP_OPEN = {gapopen}\n")
            config_file.write(f"GAP_EXTEND = {gapextend}\n")
        
        # 使用ClustalW进行比对
        clustalw_path = "/opt/anaconda3/envs/rdkit-env/bin/clustalw2"
        clustalw_cmd = (
            f"{clustalw_path} -infile={combined_file} -outfile=temp_combined.aln "
            f"-OUTPUT=FASTA -quiet -PROFILE=clustalw.cfg"
        )
        subprocess.run(
            clustalw_cmd,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding='utf-8'
        )
        
        # 读取ClustalW比对结果
        align = AlignIO.read("temp_combined.aln", "fasta")
        t_seq_clustalw = str(align[0].seq)
        q_seq_clustalw = str(align[1].seq)
        
        # 生成ClustalW映射
        t_pos, q_pos = -1, -1
        for t, q in zip(t_seq_clustalw, q_seq_clustalw):
            t_pos += t != '-'
            q_pos += q != '-'
            if t != '-' and q != '-':
                clustalw_map[t_pos] = q_pos
        
        # 计算ClustalW同一性
        clustalw_identity = calculate_identity(t_seq_clustalw, q_seq_clustalw)
        
        # 保存比对后的序列
        aligned_sequences['clustalw']['target'] = t_seq_clustalw
        aligned_sequences['clustalw']['query'] = q_seq_clustalw
    except Exception as e:
        print(f"ClustalW工具调用失败: {e}")
    
    # 2. 使用needle工具进行比对
    needle_raw_result = ""
    try:
        # 直接调用_needle可执行文件
        needle_path = "/opt/anaconda3/envs/rdkit-env/bin/_needle"
        needle_cmd = (
            f"{needle_path} -nobrief -asequence=temp_target.fasta -bsequence=temp_query.fasta "
            f"-gapopen={gapopen} -gapextend={gapextend} -outfile=needle.txt"
        )
        subprocess.run(
            needle_cmd,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding='utf-8',
            env=env
        )
        
        # 读取needle比对结果
        with open("needle.txt", "r") as needle_file:
            lines = needle_file.readlines()
            needle_raw_result = ''.join(lines)  # 保存原始结果
        
        # 提取needle比对结果中的同一性和最长一致性
        identity_found = False
        longest_identity_found = False
        for line in lines:
            if "# Identity:" in line:
                identity_parts = line.split()
                if len(identity_parts) > 2:
                    identity_values = identity_parts[2].split('/')
                    if len(identity_values) == 2:
                        needle_identity = float(identity_values[0]) / float(identity_values[1])
                        identity_found = True
            elif "# Longest_Identity = " in line:
                longest_identity_parts = line.split('=')
                if len(longest_identity_parts) > 1:
                    longest_identity_value = longest_identity_parts[1].strip().strip('%')
                    needle_longest_identity = float(longest_identity_value) / 100
                    longest_identity_found = True
        
        # 使用AlignIO读取比对结果，生成映射
        alignment = AlignIO.read("needle.txt", "emboss")
        t_seq_needle = str(alignment[0].seq)
        q_seq_needle = str(alignment[1].seq)
        
        # 生成needle映射
        if t_seq_needle and q_seq_needle:
            t_pos, q_pos = -1, -1
            for t, q in zip(t_seq_needle, q_seq_needle):
                t_pos += t != '-'
                q_pos += q != '-'
                if t != '-' and q != '-':
                    needle_map[t_pos] = q_pos
        
        # 保存比对后的序列
        aligned_sequences['needle']['target'] = t_seq_needle
        aligned_sequences['needle']['query'] = q_seq_needle
    except Exception as e:
        print(f"needle工具调用失败: {e}")
    
    # 3. 尝试使用MUSCLE工具进行比对
    try:
        # 检查muscle工具是否存在
        muscle_path = "/opt/anaconda3/envs/rdkit-env/bin/muscle"
        if os.path.exists(muscle_path):
            muscle_cmd = (
                f"{muscle_path} -align {combined_file} -output muscle_output.fasta"
            )
            subprocess.run(
                muscle_cmd,
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding='utf-8'
            )
            
            # 读取MUSCLE比对结果
            align = AlignIO.read("muscle_output.fasta", "fasta")
            t_seq_muscle = str(align[0].seq)
            q_seq_muscle = str(align[1].seq)
            
            # 计算MUSCLE同一性
            muscle_identity = calculate_identity(t_seq_muscle, q_seq_muscle)
            
            # 生成MUSCLE映射
            t_pos, q_pos = -1, -1
            for t, q in zip(t_seq_muscle, q_seq_muscle):
                t_pos += t != '-'
                q_pos += q != '-'
                if t != '-' and q != '-':
                    muscle_map[t_pos] = q_pos
    except Exception as e:
        print(f"MUSCLE工具调用失败: {e}")
    
    # 4. 使用water工具进行比对
    try:
        # 直接调用_water可执行文件
        water_path = "/opt/anaconda3/envs/rdkit-env/bin/_water"
        water_cmd = (
            f"{water_path} -nobrief -asequence=temp_target.fasta -bsequence=temp_query.fasta "
            f"-gapopen={gapopen} -gapextend={gapextend} -outfile=water.txt"
        )
        subprocess.run(
            water_cmd,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding='utf-8',
            env=env
        )
        
        # 读取water比对结果
        with open("water.txt", "r") as water_file:
            lines = water_file.readlines()
        
        # 提取water比对结果中的同一性
        for line in lines:
            if "# Identity:" in line:
                identity_parts = line.split()
                if len(identity_parts) > 2:
                    identity_values = identity_parts[2].split('/')
                    if len(identity_values) == 2:
                        water_identity = float(identity_values[0]) / float(identity_values[1])
                        break
        
        # 使用AlignIO读取比对结果
        alignment = AlignIO.read("water.txt", "emboss")
        t_seq_water = str(alignment[0].seq)
        q_seq_water = str(alignment[1].seq)
        
        # 生成water映射
        if t_seq_water and q_seq_water:
            t_pos, q_pos = -1, -1
            for t, q in zip(t_seq_water, q_seq_water):
                t_pos += t != '-'
                q_pos += q != '-'
                if t != '-' and q != '-':
                    water_map[t_pos] = q_pos
        
        # 保存比对后的序列
        aligned_sequences['water']['target'] = t_seq_water
        aligned_sequences['water']['query'] = q_seq_water
    except Exception as e:
        print(f"water工具调用失败: {e}")
    
    # 清理临时文件
    temp_files = [
        "temp_target.fasta", "temp_query.fasta", "temp_combined.fasta", 
        "clustalw.cfg", "temp_combined.aln", "needle.txt", 
        "muscle_output.fasta", "water.txt"
    ]
    for temp_file in temp_files:
        if os.path.exists(temp_file):
            os.remove(temp_file)

    results = []
    for site in sites:
        target_pos = site - 1
        if target_pos < 0 or target_pos >= len(target):
            results.append({
                '参考位点': site,
                '全局匹配': "-",
                '局部匹配': "-",
                'ClustalW匹配': "-",
                'needle匹配': "-",
                'MUSCLE匹配': "-",
                'water匹配': "-",
                '关键位点': "-"
            })
            continue
        
        # 获取匹配位置
        global_match = global_map.get(target_pos)
        local_match = local_map.get(target_pos)
        clustalw_match = clustalw_map.get(target_pos)
        needle_match = needle_map.get(target_pos)
        muscle_match = muscle_map.get(target_pos)
        water_match = water_map.get(target_pos)
        
        # 检测关键位点
        alerts = []
        if global_match is not None and (global_match + 1) in key_positions:
            alerts.append(f"全局:{global_match + 1}")
        if local_match is not None and (local_match + 1) in key_positions:
            alerts.append(f"局部:{local_match + 1}")
        if clustalw_match is not None and (clustalw_match + 1) in key_positions:
            alerts.append(f"ClustalW:{clustalw_match + 1}")
        if needle_match is not None and (needle_match + 1) in key_positions:
            alerts.append(f"needle:{needle_match + 1}")
        if muscle_match is not None and (muscle_match + 1) in key_positions:
            alerts.append(f"MUSCLE:{muscle_match + 1}")
        if water_match is not None and (water_match + 1) in key_positions:
            alerts.append(f"water:{water_match + 1}")
        
        results.append({
            '参考位点': site,
            '全局匹配': global_match + 1 if global_match is not None else "-",
            '局部匹配': local_match + 1 if local_match is not None else "-",
            'ClustalW匹配': clustalw_match + 1 if clustalw_match is not None else "-",
            'needle匹配': needle_match + 1 if needle_match is not None else "-",
            'MUSCLE匹配': muscle_match + 1 if muscle_match is not None else "-",
            'water匹配': water_match + 1 if water_match is not None else "-",
            '关键位点': ", ".join(alerts) if alerts else "-"
        })
    
    # 添加最后一行，包含所有比对方法的同一性信息
    results.append({
        '参考位点': "同一性",
        '全局匹配': f"{global_identity:.2%}",
        '局部匹配': f"{local_identity:.2%}",
        'ClustalW匹配': f"{clustalw_identity:.2%}",
        'needle匹配': f"{needle_identity:.2%}",
        'MUSCLE匹配': f"{muscle_identity:.2%}",
        'water匹配': f"{water_identity:.2%}",
        '关键位点': "-"
    })
    
    # 添加needle最长一致性信息
    results.append({
        '参考位点': "needle最长一致性",
        '全局匹配': "-",
        '局部匹配': "-",
        'ClustalW匹配': "-",
        'needle匹配': f"{needle_longest_identity:.2%}",
        'MUSCLE匹配': "-",
        'water匹配': "-",
        '关键位点': "-"
    })
    
    # 构建完整结果，包含比对后的序列和原始needle结果
    return {
        'results': results,
        'aligned_sequences': aligned_sequences,
        'needle_raw_result': needle_raw_result,
        'global_identity': global_identity,
        'local_identity': local_identity,
        'clustalw_identity': clustalw_identity,
        'needle_identity': needle_identity,
        'needle_longest_identity': needle_longest_identity,
        'muscle_identity': muscle_identity,
        'water_identity': water_identity
    }
