# parser.py
import pandas as pd
import re

# 常量定义
BASE_NAMES = {
    'A': {'en': 'adenosine', 'zh': '腺苷'},
    'U': {'en': 'uridine',   'zh': '尿苷'},
    'C': {'en': 'cytidine',  'zh': '胞苷'},
    'G': {'en': 'guanosine', 'zh': '鸟苷'},
    'T': {'en': 'thymidine', 'zh': '胸苷'}
}

VALID_AA = {'A','R','N','D','C','Q','E','G','H','I','L','K','M','F','P','O','S','U','T','W','Y','V','B','Z','J','X'}
PREDEFINED_MODS = {'ac4c','chm5u','cm','cmnm5s2u','cmnm5u','dhu','fm','galq','gm','i','i6a','m1a','m1f','m1g','m1i',
                  'm22g','m2a','m2g','m3c','m4c','m5c','m6a','m7g','mam5u','mam5s2u','manq','mcm5s2u','mcm5u','mo5u',
                  'ms2i6a','ms2t6a','mt6a','mv','o5u','osyw','p','q','s2c','s2t','s2u','s4u','m5u','t6a','tm','um','yw','x'}

# 遗传密码表
DNA_TO_AA = {
    'TTT': 'F', 'TTC': 'F', 'TTA': 'L', 'TTG': 'L',
    'CTT': 'L', 'CTC': 'L', 'CTA': 'L', 'CTG': 'L',
    'ATT': 'I', 'ATC': 'I', 'ATA': 'I', 'ATG': 'M',
    'GTT': 'V', 'GTC': 'V', 'GTA': 'V', 'GTG': 'V',
    'TCT': 'S', 'TCC': 'S', 'TCA': 'S', 'TCG': 'S',
    'CCT': 'P', 'CCC': 'P', 'CCA': 'P', 'CCG': 'P',
    'ACT': 'T', 'ACC': 'T', 'ACA': 'T', 'ACG': 'T',
    'GCT': 'A', 'GCC': 'A', 'GCA': 'A', 'GCG': 'A',
    'TAT': 'Y', 'TAC': 'Y', 'TAA': '*', 'TAG': '*',
    'CAT': 'H', 'CAC': 'H', 'CAA': 'Q', 'CAG': 'Q',
    'AAT': 'N', 'AAC': 'N', 'AAA': 'K', 'AAG': 'K',
    'GAT': 'D', 'GAC': 'D', 'GAA': 'E', 'GAG': 'E',
    'TGT': 'C', 'TGC': 'C', 'TGA': '*', 'TGG': 'W',
    'CGT': 'R', 'CGC': 'R', 'CGA': 'R', 'CGG': 'R',
    'AGT': 'S', 'AGC': 'S', 'AGA': 'R', 'AGG': 'R',
    'GGT': 'G', 'GGC': 'G', 'GGA': 'G', 'GGG': 'G'
}

def parse_sequence(seq, moltype):
    if not isinstance(seq, str):
        raise ValueError("输入序列必须是字符串类型")
    seq = seq.strip().replace(" ", "")
    naked_sequence = []
    modifications = []
    special_positions = []
    position_map = {}
    i = 0
    raw_moltype = moltype
    moltype = moltype.upper() if pd.notnull(moltype) else "RNA"
    
    # 定义简并碱基
    DEGENERATE_BASES = {'M', 'R', 'W', 'S', 'Y', 'K', 'V', 'H', 'D', 'B'}

    # 处理pv修饰
    if moltype in ["RNA", "DNA"] and (seq.startswith('pv') or seq.startswith('pv-')):
        first_base_pos = 0
        valid_chars = 'GAUC' + ''.join(DEGENERATE_BASES)
        while first_base_pos < len(seq) and seq[first_base_pos].upper() not in valid_chars:
            first_base_pos += 1
        
        if first_base_pos < len(seq) and seq[first_base_pos].upper() in valid_chars:
            modifications.append((1, 'pv', 'other'))
            seq = seq[first_base_pos+2:] if seq[first_base_pos+1] == '-' else seq[first_base_pos+3:]
            i = 0

    # 解析序列主体
    while i < len(seq):
        current_char = seq[i]
        
        if moltype == "AA":
            current_char_upper = current_char.upper()
            if current_char_upper not in VALID_AA:
                raise ValueError(f"第{len(naked_sequence)+1}号氨基酸字符'{current_char}'非法")
            
            naked_sequence.append(current_char_upper)
            current_base_pos = len(naked_sequence)
            position_map[i] = current_base_pos
            
            if current_char_upper == 'X':
                special_positions.append(current_base_pos)
            i += 1
        else:
            # 处理简并碱基（必须大写）
            if current_char.upper() in DEGENERATE_BASES:
                # 保存大写简并碱基
                naked_sequence.append(current_char.upper())
                current_base_pos = len(naked_sequence)
                position_map[i] = current_base_pos
                i += 1
                
                # 收集修饰符
                modifiers = []
                while i < len(seq) and seq[i].lower() in 'mfse':
                    modifiers.append(seq[i].lower())
                    i += 1
                    
                # 处理修饰符
                for mod in modifiers:
                    if mod in ['m', 'f', 'e']:
                        modifications.append((current_base_pos, mod, current_char.upper()))
                    elif mod == 's':
                        if i < len(seq) and seq[i].lower() in 'agcut':
                            next_base_pos = len(naked_sequence) + 1
                            modifications.append((f"{current_base_pos}^{next_base_pos}", 's', current_char.upper()))
            
            # 处理普通碱基（允许大小写）
            elif current_char.lower() in 'agcut':
                naked_sequence.append(current_char.lower())
                current_base_pos = len(naked_sequence)
                position_map[i] = current_base_pos
                i += 1
                
                # 收集修饰符
                modifiers = []
                while i < len(seq) and seq[i].lower() in 'mfse':
                    modifiers.append(seq[i].lower())
                    i += 1
                    
                # 处理修饰符
                for mod in modifiers:
                    if mod in ['m', 'f', 'e']:
                        modifications.append((current_base_pos, mod, current_char.lower()))
                    elif mod == 's':
                        if i < len(seq) and seq[i].lower() in 'agcut':
                            next_base_pos = len(naked_sequence) + 1
                            modifications.append((f"{current_base_pos}^{next_base_pos}", 's', current_char.lower()))
            
            # 处理特殊位置N（未知碱基）
            elif current_char.upper() == 'N':
                naked_sequence.append('n')
                current_base_pos = len(naked_sequence)
                if moltype in ["DNA", "RNA"]:
                    special_positions.append(current_base_pos)
                position_map[i] = current_base_pos
                i += 1
            else:
                raise ValueError(f"非法字符 '{seq[i]}' 在位置 {i+1}")

    base_sequence = ''.join(naked_sequence)
    final_naked_sequence = base_sequence if moltype == "AA" else base_sequence.replace('u', 't')
    
    return final_naked_sequence, modifications, special_positions, raw_moltype

def read_basic_data_from_excel(file_path):
    df = pd.read_excel(file_path, sheet_name='basicdata', engine='openpyxl')
    # 添加dropna操作，解决幽灵数据问题
    df.dropna(how='all', inplace=True)
    basic_data = {}
    for index, row in df.iterrows():
        field = row['Field']
        value = row['Value']
        if field == 'earliestpriorityIPOfficeCode':
            basic_data['earliestpriorityIPOfficeCode'] = value
        elif field == 'ApplicationNumberText':
            basic_data['ApplicationNumberText'] = value
        elif field == 'earliestpriorityFilingDate':
            basic_data['earliestpriorityFilingDate'] = value
        elif field == 'InventorName':
            basic_data['InventorName'] = value
        elif field == 'InventorNameLatin':
            basic_data['InventorNameLatin'] = value
        else:
            basic_data[field] = value
    print("\n=== 读取的基础数据 ===")
    for key, val in basic_data.items():
        print(f"{key}: {val}")
    print("====================\n")
    return basic_data

def read_sequences_from_excel(file_path):
    df = pd.read_excel(file_path, sheet_name='seqdata', engine='openpyxl')
    # 添加dropna操作，解决幽灵数据问题
    df.dropna(how='all', inplace=True)
    
    # 动态定位列
    ring_col = next((col for col in df.columns if '环信息' in str(col)), None)
    hybrid_col = next((col for col in df.columns if '杂合信息' in str(col)), None)
    check_col = next((col for col in df.columns if '翻译校验' in str(col)), None)  # 新增校验列
    
    # 处理区段列
    segment_cols = []
    if hybrid_col:
        segment_cols = [col for col in df.columns if re.search(r'第[一二三四五六七八九十]+区段', str(col))]
        def get_segment_num(col_name):
            match = re.search(r'第([一二三四五六七八九十]+)区段', str(col_name))
            if match:
                chinese_num = match.group(1)
                num_map = {'一':1,'二':2,'三':3,'四':4,'五':5,
                          '六':6,'七':7,'八':8,'九':9,'十':10}
                return num_map.get(chinese_num, 0)
            return 0
        
        segment_cols = sorted(segment_cols, key=get_segment_num)
    
    freetext_cols = sorted([col for col in df.columns if col.startswith('freetext')], 
                          key=lambda x: (len(x), x))
    
    sequences = []
    for row_idx, row in df.iterrows():
        seq = row.iloc[0]
        raw_moltype = row.iloc[1]
        organism = row.iloc[2]
        qual_moltype = row.iloc[3]
        check_ref = str(row[check_col]).strip() if check_col and pd.notna(row[check_col]) else None
        
        # 解析环信息
        ring_infos = []
        if raw_moltype and str(raw_moltype).upper() == "AA" and ring_col is not None and pd.notna(row[ring_col]):
            for item in re.split(r'[；;]', str(row[ring_col])):
                match = re.search(r'region\s*[:：]?\s*(\d+)\.\.(\d+).*note\s*[:：]?\s*(.+)', item.strip(), re.I)
                if match:
                    ring_infos.append({
                        'start': int(match.group(1)),
                        'end': int(match.group(2)),
                        'note': match.group(3).strip()
                    })

        # 解析杂合信息
        hybrid_segments = []
        if raw_moltype and str(raw_moltype).upper() == "DNA" and hybrid_col and pd.notna(row[hybrid_col]):
            hybrid_value = str(row[hybrid_col]).strip()
            if hybrid_value.lower() == '是':
                if not segment_cols:
                    raise ValueError(f"第{row_idx+1}行标记为杂合DNA但未找到区段定义列")
                
                for seg_col in segment_cols:
                    if pd.notna(row[seg_col]):
                        seg_str = str(row[seg_col]).strip()
                        match = re.match(r'\s*(\d+)\s*\.\.\s*(\d+)\s*(RNA|DNA)\s*', seg_str, re.IGNORECASE) or \
                               re.match(r'\s*(\d+)\s*-\s*(\d+)\s*(RNA|DNA)\s*', seg_str, re.IGNORECASE)
                        
                        if match:
                            start = int(match.group(1))
                            end = int(match.group(2))
                            seg_type = match.group(3)
                            
                            if start <= 0:
                                raise ValueError(f"第{row_idx+1}行区段起始位置必须大于0")
                            if start > end:
                                raise ValueError(f"第{row_idx+1}行区段起始位置{start}不能大于结束位置{end}")
                            
                            hybrid_segments.append({
                                'start': start,
                                'end': end,
                                'type': seg_type
                            })
                        else:
                            raise ValueError(f"第{row_idx+1}行区段格式错误，应为'起始..结束 类型'或'起始-结束 类型'")
        
        # 处理freetext
        current_moltype = str(raw_moltype).upper() if pd.notnull(raw_moltype) else "RNA"
        if current_moltype in ["DNA", "RNA"]:
            n_count = seq.lower().count('n')
            freetext_values = [str(row[col]) for col in freetext_cols if pd.notna(row[col])]
            if n_count > len(freetext_values):
                raise ValueError(f"第{row_idx+1}行{current_moltype}序列包含{n_count}个N，但只有{len(freetext_values)}个freetext定义")
        else:
            x_count = seq.upper().count('X')
            freetext_values = [str(row[col]) for col in freetext_cols if pd.notna(row[col])]
            if x_count > len(freetext_values):
                raise ValueError(f"第{row_idx+1}行AA序列包含{x_count}个X，但只有{len(freetext_values)}个freetext定义")
        
        sequences.append((
            seq,
            raw_moltype,
            organism,
            qual_moltype,
            freetext_values[:n_count] if current_moltype in ["DNA", "RNA"] else freetext_values[:x_count],
            ring_infos,
            hybrid_segments,
            check_ref
        ))
    
    return sequences

def print_sequence_info(sequences):
    from tabulate import tabulate
    
    print("\n=== 序列数据统计 ===")
    print(f"序列总条数: {len(sequences)}")
    
    type_counts = {'DNA': 0, 'RNA': 0, 'AA': 0}
    for seq in sequences:
        moltype = str(seq[1]).upper() if pd.notnull(seq[1]) else "RNA"
        if moltype == "DNA":
            type_counts['DNA'] += 1
        elif moltype == "RNA":
            type_counts['RNA'] += 1
        else:
            type_counts['AA'] += 1
    
    print(f"DNA序列条数: {type_counts['DNA']}")
    print(f"RNA序列条数: {type_counts['RNA']}")
    print(f"AA序列条数: {type_counts['AA']}")
    
    table_data = []
    for i, seq_data in enumerate(sequences, 1):
        sequence, raw_moltype, organism, _, _, _, _, _ = seq_data
        moltype = str(raw_moltype).upper() if pd.notnull(raw_moltype) else "RNA"
        organism = organism if pd.notnull(organism) else "synthetic construct"
        
        table_data.append([
            i,
            moltype,
            organism,
        ])
    
    print("\n=== 序列详细信息 ===")
    print(tabulate(
        table_data,
        headers=["序号", "类型", "来源"],
        tablefmt="grid",
        stralign="center",
        numalign="center"
    ))
    print("====================\n")
