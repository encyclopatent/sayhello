from Bio.Align import PairwiseAligner, substitution_matrices
import subprocess
from Bio import AlignIO
import os

def create_aligner(mode): 
    # 1. 创建对齐器实例 
    aligner = PairwiseAligner() 
    
    # 2. 加载 BLOSUM62 矩阵 (这是 BLASTP 的标准矩阵) 
    try: 
        matrix = substitution_matrices.load("BLOSUM62") 
        aligner.substitution_matrix = matrix 
    except Exception as e: 
        # 如果加载失败（极少数情况），打印警告或使用默认 
        print(f"Warning: Could not load BLOSUM62 matrix: {e}") 

    # 3. 设置模式 
    if mode == 'global': 
        aligner.mode = 'global' 
    else: 
        aligner.mode = 'local' # 假设你有局部比对的需求 
        
    return aligner

def calculate_identity(t_aligned, q_aligned):
    """计算序列同一性百分比（基于比对后长度）"""
    matches = sum(1 for t, q in zip(t_aligned, q_aligned) if t == q)
    total = len(t_aligned)
    return matches / total if total > 0 else 0.0

def process_alignment(target, query, sites, key_positions=None, algorithm='global'):
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
    
    # 执行全局比对
    global_aligner = create_aligner('global')
    global_alignments = global_aligner.align(target, query)
    if not global_alignments:
        global_identity = 0.0
        global_map = {}
    else:
        best_global = global_alignments[0]
        # --- 修改开始 ---
        try:
            # 尝试使用新版写法 (Python 3.8+ / Biopython 1.80+)
            seq_a = best_global[0]
            seq_b = best_global[1]
        except NotImplementedError:
            # 针对你的服务器环境 (Python 3.6 / Biopython 1.79)
            # 将对齐结果格式化为字符串，通常格式为三行：
            # 第一行：序列A (带gap)
            # 第二行：匹配符号 (|)
            # 第三行：序列B (带gap)
            lines = str(best_global).split('\n')
            seq_a = lines[0]
            seq_b = lines[2]
        
        global_identity = calculate_identity(seq_a, seq_b)
        # --- 修改结束 ---
        
        # 生成全局映射
        global_map = {}
        t_pos, q_pos = -1, -1
        for t, q in zip(seq_a, seq_b):
            t_pos += t != '-'
            q_pos += q != '-'
            if t != '-' and q != '-':
                global_map[t_pos] = q_pos
        # 保存比对后的序列
        aligned_sequences['global']['target'] = str(seq_a)
        aligned_sequences['global']['query'] = str(seq_b)

    # 执行局部比对
    local_aligner = create_aligner('local')
    local_alignments = local_aligner.align(target, query)
    if not local_alignments:
        local_identity = 0.0
        local_map = {}
    else:
        best_local = local_alignments[0]
        # --- 修改开始 ---
        try:
            # 尝试使用新版写法 (Python 3.8+ / Biopython 1.80+)
            seq_a = best_local[0]
            seq_b = best_local[1]
        except NotImplementedError:
            # 针对你的服务器环境 (Python 3.6 / Biopython 1.79)
            # 将对齐结果格式化为字符串，通常格式为三行：
            # 第一行：序列A (带gap)
            # 第二行：匹配符号 (|)
            # 第三行：序列B (带gap)
            lines = str(best_local).split('\n')
            seq_a = lines[0]
            seq_b = lines[2]
        
        local_identity = calculate_identity(seq_a, seq_b)
        # --- 修改结束 ---
        
        # 生成局部映射
        local_map = {}
        t_pos, q_pos = -1, -1
        for t, q in zip(seq_a, seq_b):
            t_pos += t != '-'
            q_pos += q != '-'
            if t != '-' and q != '-':
                local_map[t_pos] = q_pos
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
            config_file.write("GAP_OPEN = 10.0\n")
            config_file.write("GAP_EXTEND = 0.2\n")
        
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
            f"-gapopen=10.0 -gapextend=0.5 -outfile=needle.txt"
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
            f"-gapopen=10.0 -gapextend=0.5 -outfile=water.txt"
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
