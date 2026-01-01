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

def convert_new_format_to_old(seq):
    """将新格式的修饰标注转换为旧格式
    新格式：(VP)(mG)*(mG)*(mU)(mU)(fG)(mG)(fA)(mU)(fU)(fU)(fU)(mU)(fC)(mU)(mU)(mG)(mC)(mU)(mA)(mU)(mG)(L96)
    旧格式：VPmG*s*mG*s*mUmUfGmGfAmUfUfUfUmUfCmUmUmGmCmUmAmUmGL96
    * 代表 s 修饰
    括号里m和f在被修饰的碱基左侧
    旧格式要求：碱基 + 修饰符 + 连接修饰
    
    返回：(转换后的序列, ligand_removed)
    """
    # 严格检测是否为新格式：
    # 1. 以(开头
    # 2. 包含至少一个()结构
    # 3. 不包含其他非格式字符
    import re
    
    # 检查是否以(开头
    if not seq.startswith('('):
        return seq, False
    
    # 检查是否包含至少一个()结构且格式正确
    # 匹配所有括号内容及其后的*修饰符
    pattern = r'\(([^)]+)\)(\*)?'
    matches = re.findall(pattern, seq)
    
    # 如果没有匹配到任何()结构，或者匹配的内容与原始序列长度不匹配（包含其他字符）
    if not matches:
        return seq, False
    
    # 验证所有内容是否都被正确匹配
    # 重新构建序列以验证是否完全匹配
    matched_seq = ''
    for content, star_mod in matches:
        matched_seq += f'({content})'
        if star_mod:
            matched_seq += star_mod
    
    # 如果重建的序列与原始序列不完全匹配，说明包含其他非格式字符，返回原始序列
    if matched_seq != seq:
        return seq, False
    
    converted = []
    ligand_removed = False
    
    for i, (content, star_mod) in enumerate(matches):
        # 处理配体L96 - 直接跳过，不添加到转换后的序列中
        if content.upper() == 'L96' or content.upper() == '-L96':
            ligand_removed = True
            continue
        
        # 处理VP修饰符（包括带连字符的版本）
        if content.upper() in ['VP', 'PV', 'Pv', 'Vp', 'pv', 'VP-', 'PV-', 'Pv-', 'Vp-', 'pv-']:
            # 如果是第一个元素，保留为PV修饰符格式
            if i == 0:
                # 移除可能的连字符
                clean_content = content.replace('-', '')
                converted.append(clean_content)
            else:
                # 如果不是第一个元素，忽略VP修饰符
                continue
            continue
        
        # 解析修饰符和碱基：修饰符在前，碱基在后
        # 修饰符只能是m或f
        modifiers = []
        base = ''
        
        # 遍历内容字符，提取修饰符和碱基
        for char in content:
            if char in 'mf':
                modifiers.append(char)
            elif char.lower() in 'agcut':
                base = char
                # 找到碱基后，收集剩余的修饰符（如果有）
                remaining = content[content.index(char)+1:]
                for remaining_char in remaining:
                    if remaining_char in 'mf':
                        modifiers.append(remaining_char)
                break
        
        # 如果没有找到有效的碱基，保留原始内容
        if not base:
            converted.append(f'({content})')
            if star_mod:
                converted.append(star_mod)
            continue
        
        # 旧格式要求：碱基 + 修饰符
        converted.append(base)
        converted.extend(modifiers)
        
        # 处理*修饰符（转换为s修饰，连接修饰在最后）
        if star_mod:
            converted.append('s')
    
    return ''.join(converted), ligand_removed

def parse_sequence(seq, moltype, line_number=None):
    if not isinstance(seq, str):
        raise ValueError("输入序列必须是字符串类型")
    seq = seq.strip().replace(" ", "")
    
    # 预处理：转换新格式的修饰标注
    seq, new_format_ligand_removed = convert_new_format_to_old(seq)
    naked_sequence = []
    modifications = []
    special_positions = []
    i = 0
    raw_moltype = moltype
    moltype = moltype.upper() if pd.notnull(moltype) else "RNA"
    has_degenerate_bases = False
    
    # 预处理：检测并移除DNA/RNA序列结尾的L96或-L96配体
    ligand_removed = new_format_ligand_removed
    if moltype in ["RNA", "DNA"]:
        seq_len = len(seq)
        if seq_len >= 3:
            if seq[-3:].upper() == "L96":
                seq = seq[:-3]
                ligand_removed = True
            elif seq_len >= 4 and seq[-4:].upper() == "-L96":
                seq = seq[:-4]
                ligand_removed = True
    
    # 定义简并碱基
    DEGENERATE_BASES = {'M', 'R', 'W', 'S', 'Y', 'K', 'V', 'H', 'D', 'B'}
    # 预编译常用正则表达式
    PV_PREFIX_PATTERNS = [
        (r'^[Pp][Vv]-', 3),   # pv-, Pv-, PV-, pV- (开头)
        (r'^[Vv][Pp]-', 3),   # vp-, Vp-, VP-, vP- (开头)
        (r'^[Pp][Vv]', 2),    # pv, Pv, PV, pV (开头)
        (r'^[Vv][Pp]', 2),    # vp, Vp, VP, vP (开头)
    ]

    # 处理pv修饰的各种变体：Pv、PV、VP、Pv-、PV-、VP-
    if moltype in ["RNA", "DNA"]:
        seq_len = len(seq)
        for pattern, length in PV_PREFIX_PATTERNS:
            if seq_len >= length:
                match = re.match(pattern, seq)
                if match:
                    mod_end_pos = len(match.group(0))
                    if mod_end_pos < seq_len:
                        base_after_mod = seq[mod_end_pos].lower()
                        modifications.append((1, 'pv', base_after_mod))
                        seq = seq[mod_end_pos:]
                        break

    # 解析序列主体
    seq_len = len(seq)
    while i < seq_len:
        current_char = seq[i]
        
        if moltype == "AA":
            current_char_upper = current_char.upper()
            if current_char_upper not in VALID_AA:
                error_msg = f"字符 '{current_char}' 并非系统允许的氨基酸表示"
                if line_number:
                    raise ValueError(f"第{line_number}行第{len(naked_sequence)+1}号氨基酸：{error_msg}")
                else:
                    raise ValueError(f"第{len(naked_sequence)+1}号氨基酸：{error_msg}")
            
            naked_sequence.append(current_char_upper)
            if current_char_upper == 'X':
                special_positions.append(len(naked_sequence))
            i += 1
        else:
            # 检查当前字符是否为修饰符（m, f, e, s），如果是，先收集修饰符
            if current_char in 'mfse':
                # 收集所有连续的修饰符
                modifiers = []
                while i < seq_len and seq[i] in 'mfse':
                    modifiers.append(seq[i].lower())
                    i += 1
                
                # 确保修饰符后有碱基
                if i >= seq_len:
                    continue
                    
                # 获取修饰符后的碱基
                base_char = seq[i]
                base_char_lower = base_char.lower()
                
                # 处理碱基
                if base_char in DEGENERATE_BASES:
                    has_degenerate_bases = True
                    naked_sequence.append(base_char)
                    current_base_pos = len(naked_sequence)
                    i += 1
                elif base_char_lower in 'agcut':
                    naked_sequence.append(base_char)
                    current_base_pos = len(naked_sequence)
                    i += 1
                else:
                    # 修饰符后的字符不是有效碱基，忽略
                    i += 1
                    continue
                    
                # 处理修饰符
                for mod in modifiers:
                    if mod in ['m', 'f', 'e']:
                        modifications.append((current_base_pos, mod, base_char_lower))
                    elif mod == 's' and i < seq_len and seq[i].lower() in 'agcut':
                        modifications.append((f"{current_base_pos}^{current_base_pos + 1}", 's', base_char_lower))
            
            # 处理简并碱基（必须大写）
            elif current_char in DEGENERATE_BASES:
                has_degenerate_bases = True
                naked_sequence.append(current_char)
                current_base_pos = len(naked_sequence)
                base_char_lower = current_char.lower()
                i += 1
                
                # 收集修饰符
                if i < seq_len and seq[i] in 'mfse':
                    modifiers = []
                    while i < seq_len and seq[i] in 'mfse':
                        modifiers.append(seq[i].lower())
                        i += 1
                    
                    # 处理修饰符
                    for mod in modifiers:
                        if mod in ['m', 'f', 'e']:
                            modifications.append((current_base_pos, mod, base_char_lower))
                        elif mod == 's' and i < seq_len and seq[i].lower() in 'agcut':
                            modifications.append((f"{current_base_pos}^{current_base_pos + 1}", 's', base_char_lower))
            
            # 处理普通碱基（保持大小写，但记录修饰时使用小写）
            elif current_char.lower() in 'agcut':
                naked_sequence.append(current_char)
                current_base_pos = len(naked_sequence)
                base_char_lower = current_char.lower()
                i += 1
                
                # 收集修饰符
                if i < seq_len and seq[i] in 'mfse':
                    modifiers = []
                    while i < seq_len and seq[i] in 'mfse':
                        modifiers.append(seq[i].lower())
                        i += 1
                    
                    # 处理修饰符
                    for mod in modifiers:
                        if mod in ['m', 'f', 'e']:
                            modifications.append((current_base_pos, mod, base_char_lower))
                        elif mod == 's' and i < seq_len and seq[i].lower() in 'agcut':
                            modifications.append((f"{current_base_pos}^{current_base_pos + 1}", 's', base_char_lower))
            
            # 处理特殊位置N（未知碱基）
            elif current_char.upper() == 'N':
                naked_sequence.append(current_char)
                if moltype in ["DNA", "RNA"]:
                    special_positions.append(len(naked_sequence))
                i += 1
            else:
                # 检查是否为非法的修饰符（小写字母且不在允许的修饰符列表中）
                if seq[i].islower() and seq[i] not in 'mfse':
                    error_msg = f"小写字母为修饰方式，输入了不能处理的修饰方式 '{seq[i]}'"
                else:
                    # 是非法的碱基字符
                    error_msg = f"字符 '{seq[i]}' 并非系统允许的碱基表示"
                
                if line_number:
                    raise ValueError(f"第{line_number}行序列位置 {i+1} 处：{error_msg}")
                else:
                    raise ValueError(f"{error_msg}，位置 {i+1}")

    base_sequence = ''.join(naked_sequence)
    # 替换所有的u为t，无论大小写，以符合ST26标准
    if moltype == "AA":
        final_naked_sequence = base_sequence
    else:
        # 更高效的大小写替换
        final_naked_sequence = base_sequence.translate(str.maketrans('uU', 'tT'))

    return final_naked_sequence, modifications, special_positions, raw_moltype, has_degenerate_bases, ligand_removed

def read_basic_data_from_excel(file_path):
    df = pd.read_excel(file_path, sheet_name='basicdata', engine='openpyxl')
    basic_data = {}
    
    # 动态定位Field和Value列
    field_col = next((col for col in df.columns if any(keyword in str(col).lower() for keyword in ['field', '字段', '项'])), None)
    value_col = next((col for col in df.columns if any(keyword in str(col).lower() for keyword in ['value', '值', '内容'])), None)
    
    # 如果没有找到，使用默认索引
    if field_col is None:
        field_col = df.columns[0]
    if value_col is None and len(df.columns) > 1:
        value_col = df.columns[1]
    
    for index, row in df.iterrows():
        field = row[field_col]
        value = row[value_col]
        
        # 确保字段名不为空
        if pd.notna(field) and pd.notna(value):
            field_str = str(field).strip()
            value_str = str(value).strip()
            basic_data[field_str] = value_str
    
    print("\n=== 读取的基础数据 ===")
    for key, val in basic_data.items():
        print(f"{key}: {val}")
    print("====================\n")
    return basic_data

def read_sequences_from_excel(file_path):
    df = pd.read_excel(file_path, sheet_name='seqdata', engine='openpyxl')
    
    # 动态定位关键列 - 使用集合交集提高查找效率
    col_names = [str(col).lower() for col in df.columns]
    
    # 预编译常用正则表达式
    segment_pattern = re.compile(r'第[一二三四五六七八九十]+区段')
    chinese_num_pattern = re.compile(r'第([一二三四五六七八九十]+)区段')
    ring_pattern = re.compile(r'region\s*[:：]?\s*(\d+)\.\.(\d+).*note\s*[:：]?\s*(.+)', re.I)
    hybrid_segment_pattern1 = re.compile(r'\s*(\d+)\s*\.\.\s*(\d+)\s*(RNA|DNA)\s*', re.IGNORECASE)
    hybrid_segment_pattern2 = re.compile(r'\s*(\d+)\s*-\s*(\d+)\s*(RNA|DNA)\s*', re.IGNORECASE)
    
    # 序列列
    seq_col = None
    for i, col in enumerate(col_names):
        if any(keyword in col for keyword in ['序列', 'sequence', 'seq']):
            seq_col = df.columns[i]
            break
    if seq_col is None:
        seq_col = df.columns[0]
    
    # 分子类型列
    moltype_col = None
    for i, col in enumerate(col_names):
        if any(keyword in col for keyword in ['分子类型', 'moltype', '类型']):
            moltype_col = df.columns[i]
            break
    if moltype_col is None and len(df.columns) > 1:
        moltype_col = df.columns[1]
    
    # 来源列
    organism_col = None
    for i, col in enumerate(col_names):
        if any(keyword in col for keyword in ['来源', 'organism', 'source']):
            organism_col = df.columns[i]
            break
    if organism_col is None and len(df.columns) > 2:
        organism_col = df.columns[2]
    
    # 修饰类型列
    qual_moltype_col = None
    for i, col in enumerate(col_names):
        if any(keyword in col for keyword in ['修饰类型', 'qualifier', 'qual_moltype']):
            qual_moltype_col = df.columns[i]
            break
    if qual_moltype_col is None and len(df.columns) > 3:
        qual_moltype_col = df.columns[3]
    
    # 其他列
    ring_col = None
    for i, col in enumerate(df.columns):
        if '环信息' in str(col):
            ring_col = col
            break
    
    hybrid_col = None
    for i, col in enumerate(df.columns):
        if '杂合信息' in str(col):
            hybrid_col = col
            break
    
    check_col = None
    for i, col in enumerate(df.columns):
        if '翻译校验' in str(col):
            check_col = col
            break
    
    # 处理区段列
    segment_cols = []
    if hybrid_col:
        for col in df.columns:
            if re.search(r'第[一二三四五六七八九十]+区段', str(col)):
                segment_cols.append(col)
        
        def get_segment_num(col_name):
            match = chinese_num_pattern.search(str(col_name))
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
        # 根据列名获取数据
        seq = row[seq_col]
        raw_moltype = row[moltype_col] if moltype_col else None
        organism = row[organism_col] if organism_col else 'synthetic construct'
        qual_moltype = row[qual_moltype_col] if qual_moltype_col else None
        check_ref = str(row[check_col]).strip() if check_col and pd.notna(row[check_col]) else None
        
        # 确保seq是字符串
        if not isinstance(seq, str):
            seq = str(seq) if pd.notna(seq) else ""
        
        # 解析环信息
        ring_infos = []
        if raw_moltype and str(raw_moltype).upper() == "AA" and ring_col is not None and pd.notna(row[ring_col]):
            ring_text = str(row[ring_col])
            for item in re.split(r'[；;]', ring_text):
                match = ring_pattern.search(item.strip())
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
                        match = hybrid_segment_pattern1.match(seg_str) or hybrid_segment_pattern2.match(seg_str)
                        
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
        freetext_values = [str(row[col]) for col in freetext_cols if pd.notna(row[col])]
        
        if current_moltype in ["DNA", "RNA"]:
            n_count = seq.lower().count('n')
            if n_count > len(freetext_values):
                raise ValueError(f"第{row_idx+1}行{current_moltype}序列包含{n_count}个N，但只有{len(freetext_values)}个freetext定义")
            freetext_to_use = freetext_values[:n_count]
        else:
            x_count = seq.upper().count('X')
            if x_count > len(freetext_values):
                raise ValueError(f"第{row_idx+1}行AA序列包含{x_count}个X，但只有{len(freetext_values)}个freetext定义")
            freetext_to_use = freetext_values[:x_count]
        
        # 解析序列，避免后续重复解析
        parsed_seq_data = None
        if seq:
            try:
                final_naked_sequence, modifications, special_positions, _, has_degenerate_bases, ligand_removed = parse_sequence(seq, raw_moltype, line_number=row_idx+1)
                parsed_seq_data = {
                    'final_naked_sequence': final_naked_sequence,
                    'modifications': modifications,
                    'special_positions': special_positions,
                    'has_degenerate_bases': has_degenerate_bases,
                    'ligand_removed': ligand_removed
                }
            except Exception as e:
                # 保持向后兼容，解析失败时返回None
                parsed_seq_data = None
        
        sequences.append((
            seq,
            raw_moltype,
            organism,
            qual_moltype,
            freetext_to_use,
            ring_infos,
            hybrid_segments,
            check_ref,
            parsed_seq_data,  # 添加解析后的序列数据
            row_idx + 1  # 添加行号信息（从1开始计数）
        ))
    
    return sequences

def get_sequence_summary(sequences):
    """返回序列数据统计信息"""
    type_counts = {'DNA': 0, 'RNA': 0, 'AA': 0}
    for seq in sequences:
        moltype = str(seq[1]).upper() if pd.notnull(seq[1]) else "RNA"
        if moltype == "DNA":
            type_counts['DNA'] += 1
        elif moltype == "RNA":
            type_counts['RNA'] += 1
        else:
            type_counts['AA'] += 1
    
    sequence_details = []
    has_degenerate_bases = False  # 标记是否有任何序列包含简并碱基
    has_ligand_ignored = False  # 标记是否有任何序列包含被忽略的配体
    
    for i, seq_data in enumerate(sequences, 1):
        sequence, raw_moltype, organism, qual_moltype, freetext_values, ring_infos, hybrid_segments, check_ref, parsed_seq_data, line_number = seq_data
        moltype = str(raw_moltype).upper() if pd.notnull(raw_moltype) else "RNA"
        organism = organism if pd.notnull(organism) else "synthetic construct"
        
        # 使用缓存的解析结果或重新解析
        naked_length = 0
        modification_count = 0
        modifications = []
        special_positions = []
        naked_sequence = ""
        ligand_removed = False
        current_has_degenerate = False
        
        if parsed_seq_data:
            # 使用缓存的解析结果
            naked_sequence = parsed_seq_data['final_naked_sequence']
            modifications = parsed_seq_data['modifications']
            special_positions = parsed_seq_data['special_positions']
            current_has_degenerate = parsed_seq_data['has_degenerate_bases']
            ligand_removed = parsed_seq_data['ligand_removed']
        elif isinstance(sequence, str):
            # 如果没有缓存结果，回退到重新解析
            naked_sequence, modifications, special_positions, _, current_has_degenerate, ligand_removed = parse_sequence(sequence, raw_moltype, line_number=line_number)
        
        naked_length = len(naked_sequence)
        modification_count = len(modifications)
        has_degenerate_bases = has_degenerate_bases or current_has_degenerate
        
        # 生成修饰和特殊说明
        modification_special_notes = []
        
        # 处理修饰符
        if modifications:
            mod_types = {}
            ligand_ignored = False
            
            for pos, mod, base in modifications:
                if mod == "ligand_ignored":
                    ligand_ignored = True
                    continue
                if mod not in mod_types:
                    mod_types[mod] = 0
                mod_types[mod] += 1
            
            mod_notes = []
            for mod, count in mod_types.items():
                mod_notes.append(f"{mod}×{count}")
            
            if mod_notes:
                modification_special_notes.append("修饰: " + ", ".join(mod_notes))
            
            # 添加L96配体忽略提醒
            if ligand_removed:
                modification_special_notes.append("L96")
                # 更新全局标志
                has_ligand_ignored = True

        
        # 处理特殊碱基（N、X等）和对应的注释
        if moltype in ["DNA", "RNA"] and naked_sequence:
            n_count = naked_sequence.count('N')
            if n_count > 0:
                n_note = f"特殊碱基: N×{n_count}"
                # 如果有注释，添加注释信息
                if freetext_values and len(freetext_values) >= n_count:
                    # 收集所有N的注释
                    n_comments = [f"N{idx+1}: {comment}" for idx, comment in enumerate(freetext_values[:n_count])]
                    n_note += f" (注释: {'; '.join(n_comments)})"
                modification_special_notes.append(n_note)
        elif moltype == "AA" and naked_sequence:
            x_count = naked_sequence.count('X')
            if x_count > 0:
                x_note = f"特殊氨基酸: X×{x_count}"
                # 如果有注释，添加注释信息
                if freetext_values and len(freetext_values) >= x_count:
                    # 收集所有X的注释
                    x_comments = [f"X{idx+1}: {comment}" for idx, comment in enumerate(freetext_values[:x_count])]
                    x_note += f" (注释: {'; '.join(x_comments)})"
                modification_special_notes.append(x_note)
        
        # 处理简并碱基
        if current_has_degenerate:
            # 找出所有简并碱基及其位置
            DEGENERATE_BASES = {'M', 'R', 'W', 'S', 'Y', 'K', 'V', 'H', 'D', 'B'}
            degenerate_bases = []
            for pos, base in enumerate(naked_sequence, 1):
                if base in DEGENERATE_BASES:
                    degenerate_bases.append((pos, base))
            
            if degenerate_bases:
                base_counts = {}
                for pos, base in degenerate_bases:
                    if base not in base_counts:
                        base_counts[base] = 0
                    base_counts[base] += 1
                
                degenerate_notes = []
                for base, count in base_counts.items():
                    degenerate_notes.append(f"{base}×{count}")
                modification_special_notes.append("简并碱基: " + ", ".join(degenerate_notes))
        
        # 处理氨基酸序列的环信息
        if moltype == "AA" and ring_infos:
            ring_notes = []
            for ring in ring_infos:
                ring_notes.append(f"环({ring['start']}-{ring['end']}, {ring['note']})")
            modification_special_notes.append("环结构: " + ", ".join(ring_notes))
        
        # 处理杂合DNA
        if moltype == "DNA" and hybrid_segments:
            hybrid_notes = []
            for seg in hybrid_segments:
                hybrid_notes.append(f"{seg['type']}({seg['start']}-{seg['end']})")
            modification_special_notes.append("杂合: " + ", ".join(hybrid_notes))
        
        # 合并所有说明
        full_notes = "; ".join(modification_special_notes) if modification_special_notes else "无"
        
        sequence_details.append({
            'id': i,
            'type': moltype,
            'organism': organism,
            'length': len(sequence) if isinstance(sequence, str) else 0,
            'naked_length': naked_length,
            'modification_count': modification_count,
            'has_degenerate_bases': current_has_degenerate,  # 添加到详细信息
            'modification_special_notes': full_notes  # 添加修饰和特殊说明
        })
    
    return {
        'total_count': len(sequences),
        'type_counts': type_counts,
        'details': sequence_details,
        'has_degenerate_bases': has_degenerate_bases,  # 添加到摘要信息
        'has_ligand_ignored': has_ligand_ignored  # 添加配体被忽略的标记
    }


def print_sequence_info(sequences):
    """打印序列数据统计信息"""
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
        sequence, raw_moltype, organism, _, _, _, _, _, _, _ = seq_data
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
