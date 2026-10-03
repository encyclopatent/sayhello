# xml_generator.py
import xml.etree.ElementTree as ET
import pandas as pd
import os
import re
from functools import lru_cache
from parser import parse_sequence, resolve_hybrid
from datetime import datetime
from parser import BASE_NAMES, PREDEFINED_MODS
from modifier_config import get_modifier_name_en

# 从模板文件提取的标准字符表映射（硬编码以避免用户修改模板文件导致失效）
ABBREV_TO_FULLNAME = {
    'ac4c': '4-acetylcytidine',
    'chm5u': '5-(carboxyhydroxylmethyl)uridine',
    'cm': '2''-O-methylcytidine',
    'cmnm5s2u': '5-carboxymethylaminomethyl-2-thiouridine',
    'cmnm5u': '5-carboxymethylaminomethyluridine',
    'dhu': 'dihydrouridine',
    'fm': '2''-O-methylpseudouridine',
    'gal q': 'beta-D-galactosylqueuosine',
    'gm': '2''-O-methylguanosine',
    'i': 'inosine',
    'i6a': 'N6-isopentenyladenosine',
    'm1a': '1-methyladenosine',
    'm1f': '1-methylpseudouridine',
    'm1g': '1-methylguanosine',
    'm1i': '1-methylinosine',
    'm22g': '2,2-dimethylguanosine',
    'm2a': '2-methyladenosine',
    'm2g': '2-methylguanosine',
    'm3c': '3-methylcytidine',
    'm4c': 'N4-methylcytosine',
    'm5c': '5-methylcytidine',
    'm6a': 'N6-methyladenosine',
    'm7g': '7-methylguanosine',
    'mam5u': '5-methylaminomethyluridine',
    'mam5s2u': '5-methylaminomethyl-2-thiouridine',
    'man q': 'beta-D-mannosylqueuosine',
    'mcm5s2u': '5-methoxycarbonylmethyl-2-thiouridine',
    'mcm5u': '5-methoxycarbonylmethyluridine',
    'mo5u': '5-methoxyuridine',
    'ms2i6a': '2-methylthio-N6-isopentenyladenosine',
    'ms2t6a': 'N-((9-beta-D-ribofuranosyl-2-methylthiopurine-6-yl)carbamoyl)threonine',
    'mt6a': 'N-((9-beta-D-ribofuranosylpurine-6-yl)N-methyl-carbamoyl)threonine',
    'mv': 'uridine-5-oxoacetic acid-methylester',
    'o5u': 'uridine-5-oxyacetic acid (v)',
    'osyw': 'wybutoxosine',
    'p': 'pseudouridine',
    'q': 'queuosine',
    's2c': '2-thiocytidine',
    's2t': '5-methyl-2-thiouridine',
    's2u': '2-thiouridine',
    's4u': '4-thiouridine',
    'm5u': '5-methyluridine',
    't6a': 'N-((9-beta-D-ribofuranosylpurine-6-yl)carbamoyl)threonine',
    'tm': '2''-O-methyl-5-methyluridine',
    'um': '2''-O-methyluridine',
    'yw': 'wybutosine',
    'x': '3-(3-amino-3-carboxypropyl)uridine, (acp3)u',
}

# 碱基类型识别函数
def get_base_type(fullname):
    """根据修饰碱基的全名识别对应的碱基类型"""
    fullname_lower = fullname.lower()
    if 'adenosine' in fullname_lower or 'adenine' in fullname_lower:
        return 'a'
    elif 'uridine' in fullname_lower or 'uracil' in fullname_lower:
        return 'u'
    elif 'cytidine' in fullname_lower or 'cytosine' in fullname_lower:
        return 'c'
    elif 'guanosine' in fullname_lower or 'guanine' in fullname_lower:
        return 'g'
    else:
        return None


@lru_cache(maxsize=1000)
def is_predefined_modifier(mod_text: str) -> bool:
    """
    检查修饰符是否在预定义列表中（带缓存）

    Args:
        mod_text: 修饰符文本

    Returns:
        是否为预定义修饰符
    """
    return mod_text.lower() in PREDEFINED_MODS


@lru_cache(maxsize=500)
def get_modifier_fullname(abbrev: str) -> str:
    """
    获取修饰符的完整名称（带缓存）

    Args:
        abbrev: 修饰符缩写

    Returns:
        修饰符完整名称，如果不存在则返回原缩写
    """
    return ABBREV_TO_FULLNAME.get(abbrev.lower(), abbrev)


def merge_phosphorothioate_regions(modifications):
    """
    把首尾相接的硫代磷酸酯键合并成区段。

    WIPO ST.26 网络研讨会 Q11/A11 明确：连续硫代键可用 x..y 单条描述，
    不必逐键展开。全硫代的 ASO（如 18nt gapmer）逐键会产生 17 条 feature，
    合并后只剩一条 1..18。

    位置串形如 "1^2"，首尾相接的键（1^2、2^3、3^4）合并后形如 "1..4"；
    落单的键仍保持 "x^y" 写法。其他修饰原样保留，最后按位置重排一次。

    Args:
        modifications: [(位置, 修饰类型, 碱基), ...]

    Returns:
        合并后的新列表（不修改入参）
    """
    # 注意 modifications 是按位置排列的，同一个碱基上的糖修饰会插在硫代键中间
    # （"1 号位的 MOE" 夹在 "1^2" 和 "2^3" 之间），所以不能只合并列表里相邻的
    # 条目 —— 必须按位置把整条链找出来。
    chains = []  # [(区段起点, 区段终点, 碱基, [在 modifications 中的下标...]), ...]

    for index, (location, mod_type, base) in enumerate(modifications):
        if mod_type != 's' or not isinstance(location, str) or '^' not in location:
            continue
        try:
            start, end = (int(part) for part in location.split('^', 1))
        except ValueError:
            continue  # 位置不是预期的 x^y 形式，原样保留，不猜测

        if chains and chains[-1][1] == start:
            chain = chains[-1]
            chains[-1] = (chain[0], end, chain[2], chain[3] + [index])
        else:
            chains.append((start, end, base, [index]))

    # 每条链只在它第一次出现的位置输出一条区段，链内其余位置跳过
    region_at = {}
    skipped = set()
    for start, end, base, indexes in chains:
        # 单个键用 x^y（表示 x 与 y 之间那一根键），多个键相接才用 x..y 区段。
        # 判断依据是键的数量而非端点：一根键的起点终点本来就不相等。
        location = f"{start}^{end}" if len(indexes) == 1 else f"{start}..{end}"
        region_at[indexes[0]] = (location, 's', base)
        skipped.update(indexes[1:])

    merged = [
        region_at.get(index, entry)
        for index, entry in enumerate(modifications)
        if index not in skipped
    ]

    # 合并后区段的起点可能落在若干糖修饰之后，按位置重排一次让 feature 表保持有序
    # （排序是稳定的，原有条目的相对顺序不变）
    return sorted(merged, key=lambda entry: _location_sort_key(entry[0]))


def _location_sort_key(location):
    """位置的排序键：正常位置按起点数字排，解析不出来的排到最后（不猜它的位置）"""
    match = re.match(r'\s*(\d+)', str(location))
    return (0, int(match.group(1))) if match else (1, 0)


def generate_xml(sequences, basic_data, output_folder, expert_settings=None):
    # 创建提醒列表
    reminders = []
    
    root = ET.Element("ST26SequenceListing", {
        "originalFreeTextLanguageCode": "en",
        "nonEnglishFreeTextLanguageCode": "",
        "dtdVersion": "V1_3",
        "fileName": f"{basic_data['ApplicantFileReference']}.xml",
        "softwareName": "WIPO Sequence",
        "softwareVersion": "2.3.0",
        "productionDate": datetime.now().strftime("%Y-%m-%d")
    })

    ET.SubElement(root, "ApplicantFileReference").text = basic_data['ApplicantFileReference']
    
    # 处理最早优先权信息 - 只有当至少有一个字段有值时才生成对应的元素
    earliest_priority_fields = {
        'IPOfficeCode': basic_data.get('earliestpriorityIPOfficeCode'),
        'ApplicationNumberText': basic_data.get('ApplicationNumberText'),
        'FilingDate': basic_data.get('earliestpriorityFilingDate')
    }
    
    # 过滤掉空值字段
    non_empty_fields = {k: v for k, v in earliest_priority_fields.items() if v}
    
    if non_empty_fields:
        earliest_priority = ET.SubElement(root, "EarliestPriorityApplicationIdentification")
        for field_name, field_value in non_empty_fields.items():
            ET.SubElement(earliest_priority, field_name).text = field_value
    
    # 处理申请人名称 - 只有当ApplicantName有值时才生成对应元素，始终处理，不受优先权信息影响
    applicant_name = basic_data.get('ApplicantName')
    if applicant_name:
        if re.match(r'^[A-Za-z0-9\s,\.\-\(\)\[\]\{\}\/\\\'"&:;!?@#$%^&*+=<>]*$', applicant_name):
            ET.SubElement(root, "ApplicantName", {"languageCode": "en"}).text = applicant_name
            ET.SubElement(root, "ApplicantNameLatin").text = ""
        else:
            ET.SubElement(root, "ApplicantName", {"languageCode": "zh"}).text = applicant_name
            ET.SubElement(root, "ApplicantNameLatin").text = basic_data.get('ApplicantNameLatin', '')
    
    # 处理发明人名称 - 始终处理，不受优先权信息影响
    inventor_name = basic_data.get('InventorName')
    if inventor_name:
        if re.match(r'^[A-Za-z0-9\s,\.\-\(\)\[\]\{\}\/\\\'"&:;!?@#$%^&*+=<>]*$', inventor_name):
            ET.SubElement(root, "InventorName", {"languageCode": "en"}).text = inventor_name
            ET.SubElement(root, "InventorNameLatin").text = ""
        else:
            ET.SubElement(root, "InventorName", {"languageCode": "zh"}).text = inventor_name
            ET.SubElement(root, "InventorNameLatin").text = basic_data.get('InventorNameLatin', '')
    
    # 处理发明名称 - 始终处理，不受优先权信息影响
    invention_title = basic_data.get('InventionTitle')
    if invention_title:
        if re.match(r'^[A-Za-z0-9\s,\.\-\(\)\[\]\{\}\/\\\'"&:;!?@#$%^&*+=<>]*$', invention_title):
            ET.SubElement(root, "InventionTitle", {"languageCode": "en"}).text = invention_title
        else:
            ET.SubElement(root, "InventionTitle", {"languageCode": "zh"}).text = invention_title
    ET.SubElement(root, "SequenceTotalQuantity").text = str(len(sequences))
    sequence_id_counter = 1
    qualifier_counter = 2

    for seq_data in sequences:
        # 从字典中提取数据（兼容字典和元组格式）
        if isinstance(seq_data, dict):
            sequence = seq_data['sequence']
            raw_moltype = seq_data['moltype']
            organism = seq_data['organism']
            qual_moltype = seq_data['qual_moltype']
            freetexts = seq_data['freetexts']
            ring_infos = seq_data['ring_infos']
            hybrid_segments = seq_data['hybrid_segments']
            check_ref = seq_data['check_ref']
            parsed_seq_data = seq_data.get('parsed_seq_data')
            line_number = seq_data['line_number']
        else:
            # 兼容旧的元组格式
            sequence, raw_moltype, organism, qual_moltype, freetexts, ring_infos, hybrid_segments, check_ref, parsed_seq_data, line_number = seq_data

        hybrid_segments = hybrid_segments or []

        # 检查是否使用了默认分子类型
        if pd.isnull(raw_moltype):
            moltype = "RNA"
            reminders.append(f"第{line_number}行：未指定分子类型，按照RNA进行了处理，请核对")
        else:
            moltype = raw_moltype.upper()
        
        # 检查是否使用了默认生物体名称
        if pd.isnull(organism):
            organism = "synthetic construct"
            reminders.append(f"第{line_number}行：未指定生物体名称，使用了默认值'synthetic construct'")
        
        # 检查是否使用了默认限定符分子类型。这里只算默认值，提醒推迟到下面
        # mol_type 真正写入的地方 —— 杂合序列会被 ¶55 改写成 'other DNA'，
        # 在这里就报「默认值 'other RNA'」会与实际写进 XML 的值对不上。
        qual_moltype_defaulted = pd.isnull(qual_moltype)
        if qual_moltype_defaulted:
            qual_moltype = "other RNA" if moltype in ["DNA", "RNA"] else "protein"
        
        # 使用缓存的解析结果或重新解析
        if parsed_seq_data:
            # 使用缓存的解析结果
            naked_sequence = parsed_seq_data['final_naked_sequence']
            modifications = parsed_seq_data['modifications']
            special_positions = parsed_seq_data['special_positions']
            original_moltype = raw_moltype
            has_degenerate_bases = parsed_seq_data['has_degenerate_bases']
            ligand_removed = parsed_seq_data['ligand_removed']
        else:
            # 如果没有缓存结果，回退到重新解析
            naked_sequence, modifications, special_positions, original_moltype, has_degenerate_bases, ligand_removed = parse_sequence(sequence, raw_moltype, line_number)
        
        # 检查是否移除了L96配体
        if ligand_removed:
            reminders.append(f"第{line_number}行：检测到并移除了L96配体，未将其加工为注释")
        
        # 检查是否包含简并碱基
        if has_degenerate_bases:
            reminders.append(f"第{line_number}行：序列包含简并碱基（M/R/W/S/Y/K/V/H/D/B），请核查是否为预期使用")

        # 杂合序列（DNA/RNA）的区段判定统一走 parser.resolve_hybrid —— 概要页调用同一
        # 函数，否则「概要里显示的类型」和「实际生成的 XML」会对不上。判定规则（按标注
        # 格式分四条路径）都写在那边的 docstring 里，这里只负责接结果。
        # 它只在「用户明确标注了区段、但化学上不可能」时才抛错中止整批转换。
        resolution = resolve_hybrid(
            sequence, moltype, naked_sequence, modifications, hybrid_segments, line_number
        )
        hybrid_segments = resolution.segments
        reminders.extend(f"第{line_number}行：{hint}" for hint in resolution.hints)

        if moltype in ["DNA", "RNA"] and len(special_positions) > 0:
            seq_list = list(naked_sequence)
            for idx, pos in enumerate(special_positions):
                if idx >= len(freetexts):
                    continue
                freetext = freetexts[idx].lower()
                
                # 如果freetext包含"or"，不替换N
                if 'or' in freetext:
                    continue
                    
                replacement = None
                
                # 优先检查是否为PREDEFINED_MODS中的字符
                if freetext in PREDEFINED_MODS and freetext in ABBREV_TO_FULLNAME:
                    fullname = ABBREV_TO_FULLNAME[freetext]
                    base_type = get_base_type(fullname)
                    if base_type:
                        replacement = base_type
                        # 无论DNA还是RNA，u都替换为t以符合ST26标准
                        if replacement == 'u':
                            replacement = 't'
                
                # 如果不是PREDEFINED_MODS或无法识别，再检查freetext本身
                if not replacement:
                    if 'adenosine' in freetext:
                        replacement = 'a'
                    elif 'uridine' in freetext:
                        replacement = 't'  # 无论DNA还是RNA，都使用't'以符合ST26标准
                    elif 'cytidine' in freetext or 'cytosine' in freetext:
                        replacement = 'c'
                    elif 'guanosine' in freetext:
                        replacement = 'g'
                
                if replacement and seq_list[pos-1].lower() == 'n':
                    seq_list[pos-1] = replacement
                
            naked_sequence = ''.join(seq_list)
        
        # ST.26 ¶55：杂合体的分子类型必须是 DNA，与用户在表里填的 DNA/RNA 无关。
        # 注意 INSDSeq_moltype（元素，取值 DNA/RNA/AA）与 mol_type（source 上的限定符）
        # 是两个不同字段，¶54 和 ¶84 两次警告过不要混淆。
        is_hybrid = bool(hybrid_segments)
        if is_hybrid:
            output_moltype = "DNA"
        elif pd.notnull(original_moltype):
            output_moltype = str(original_moltype).upper()
        else:
            output_moltype = "RNA"

        sequence_data = ET.SubElement(root, "SequenceData", {"sequenceIDNumber": str(sequence_id_counter)})
        insd_seq = ET.SubElement(sequence_data, "INSDSeq")
        ET.SubElement(insd_seq, "INSDSeq_length").text = str(len(naked_sequence))
        ET.SubElement(insd_seq, "INSDSeq_moltype").text = output_moltype
        ET.SubElement(insd_seq, "INSDSeq_division").text = "PAT"

        insd_feature_table = ET.SubElement(insd_seq, "INSDSeq_feature-table")
        
        # 必须的source特征
        insd_feature_source = ET.SubElement(insd_feature_table, "INSDFeature")
        ET.SubElement(insd_feature_source, "INSDFeature_key").text = "source"
        ET.SubElement(insd_feature_source, "INSDFeature_location").text = f"1..{len(naked_sequence)}"
        insd_feature_quals_source = ET.SubElement(insd_feature_source, "INSDFeature_quals")
        
        # ST.26 ¶55：杂合体的 mol_type 必须是 other DNA、organism 必须是 synthetic construct
        if is_hybrid:
            add_qualifier(insd_feature_quals_source, "mol_type", "other DNA")
        else:
            add_qualifier(insd_feature_quals_source, "mol_type", qual_moltype)

        if qual_moltype_defaulted:
            effective_moltype = "other DNA" if is_hybrid else qual_moltype
            reminders.append(
                f"第{line_number}行：未指定限定符分子类型，使用了默认值'{effective_moltype}'"
            )

        if is_hybrid and str(organism) != "synthetic construct":
            reminders.append(
                f"第{line_number}行：杂合序列的organism按ST.26第55段改为'synthetic construct'"
                f"（原填写'{organism}'）"
            )
            organism = "synthetic construct"

        organism_id = f"q{qualifier_counter}"
        add_qualifier_with_id(insd_feature_quals_source, "organism", organism, organism_id)
        qualifier_counter += 1

        # 处理杂合序列的区段特征
        if is_hybrid:
            segments = sorted(hybrid_segments, key=lambda x: x['start'])
            prev_end = 0
            for seg in segments:
                if seg['start'] != prev_end + 1:
                    raise ValueError(f"区段不连续：前段结束于{prev_end}，当前开始于{seg['start']}")
                if seg['end'] > len(naked_sequence):
                    raise ValueError(f"区段结束位置{seg['end']}超出序列长度{len(naked_sequence)}")
                prev_end = seg['end']
            
            for seg in segments:
                feature = ET.SubElement(insd_feature_table, "INSDFeature")
                ET.SubElement(feature, "INSDFeature_key").text = "misc_feature"
                # 单碱基段用 N，范围段用 N..M（符合 INSDC/ST26 规范）
                location = str(seg['start']) if seg['start'] == seg['end'] else f"{seg['start']}..{seg['end']}"
                ET.SubElement(feature, "INSDFeature_location").text = location
                
                quals = ET.SubElement(feature, "INSDFeature_quals")
                qual = ET.SubElement(quals, "INSDQualifier")
                qual.set("id", f"q{qualifier_counter}")
                ET.SubElement(qual, "INSDQualifier_name").text = "note"
                # 区段列的正则带 re.IGNORECASE，用户写 'rna' 也会被接受，
                # 但 ¶55 的例子用的是大写，统一后再写进 XML。
                ET.SubElement(qual, "INSDQualifier_value").text = str(seg['type']).upper()
                qualifier_counter += 1

        # 处理修饰碱基。连续硫代键先合并成区段，否则全硫代的 ASO 会产生上百条 feature。
        for mod_info in merge_phosphorothioate_regions(modifications):
            location, mod_type, base = mod_info
            feature = ET.SubElement(insd_feature_table, "INSDFeature")

            # 所有修饰都走 modified_base。硫代键（s）早先写成 misc_feature，但
            # ST.26 网络研讨会 Q11/A11 明确它必须用 modified_base + mod_base=OTHER
            # + note 描述，故一并统一。
            if mod_type not in ('m', 'f', 'e', 'pv', 'l', 'k', 's'):
                raise ValueError(f"未知的修饰类型 '{mod_type}'，无法生成 XML")
            ET.SubElement(feature, "INSDFeature_key").text = "modified_base"
            
            ET.SubElement(feature, "INSDFeature_location").text = str(location)
            
            quals = ET.SubElement(feature, "INSDFeature_quals")
            
            if mod_type == 'pv':
                add_qualifier(quals, "mod_base", "OTHER")
                note_id = f"q{qualifier_counter}"
                qual = ET.SubElement(quals, "INSDQualifier")
                qual.set("id", note_id)
                ET.SubElement(qual, "INSDQualifier_name").text = "note"
                ET.SubElement(qual, "INSDQualifier_value").text = get_modifier_name_en('pv', None, expert_settings)
                qualifier_counter += 1
            elif mod_type == 'm':
                base_name = BASE_NAMES.get(base.upper(), {}).get('en', 'base')
                if base == 'a':
                    add_qualifier(quals, "mod_base", "OTHER")
                    note_id = f"q{qualifier_counter}"
                    qual = ET.SubElement(quals, "INSDQualifier")
                    qual.set("id", note_id)
                    ET.SubElement(qual, "INSDQualifier_name").text = "note"
                    ET.SubElement(qual, "INSDQualifier_value").text = get_modifier_name_en('m', base, expert_settings)
                    qualifier_counter += 1
                else:
                    add_qualifier(quals, "mod_base", f"{base}m")
                    # 只有当mod_base为OTHER时才添加note注释，这里不添加note
            elif mod_type == 'f':
                base_name = BASE_NAMES.get(base.upper(), {}).get('en', 'base')
                add_qualifier(quals, "mod_base", "OTHER")
                note_id = f"q{qualifier_counter}"
                qual = ET.SubElement(quals, "INSDQualifier")
                qual.set("id", note_id)
                ET.SubElement(qual, "INSDQualifier_name").text = "note"
                ET.SubElement(qual, "INSDQualifier_value").text = get_modifier_name_en('f', base, expert_settings)
                qualifier_counter += 1
            # MOE / LNA / 5-Me-LNA-C 都不在 Annex I 表 2 的受控词表内，只能
            # mod_base=OTHER + note 写完整未缩写名称（note 里带碱基名）。
            elif mod_type in ('e', 'l', 'k'):
                base_name = BASE_NAMES.get(base.upper(), {}).get('en', 'base')
                add_qualifier(quals, "mod_base", "OTHER")
                note_id = f"q{qualifier_counter}"
                qual = ET.SubElement(quals, "INSDQualifier")
                qual.set("id", note_id)
                ET.SubElement(qual, "INSDQualifier_name").text = "note"
                ET.SubElement(qual, "INSDQualifier_value").text = get_modifier_name_en(mod_type, base, expert_settings)
                qualifier_counter += 1
            elif mod_type == 's':
                add_qualifier(quals, "mod_base", "OTHER")
                note_id = f"q{qualifier_counter}"
                qual = ET.SubElement(quals, "INSDQualifier")
                qual.set("id", note_id)
                ET.SubElement(qual, "INSDQualifier_name").text = "note"
                ET.SubElement(qual, "INSDQualifier_value").text = get_modifier_name_en('s', None, expert_settings)
                qualifier_counter += 1

        # 处理特殊位置
        if moltype == "AA":
            for x_pos, freetext in zip(special_positions, freetexts):
                # 分离中英文
                english_part, chinese_part = split_chinese_english(freetext)
                
                # 如果freetext包含中文但没有英文，使用默认英文
                if chinese_part and not english_part:
                    english_part = "custom modification"
                
                feature = ET.SubElement(insd_feature_table, "INSDFeature")
                ET.SubElement(feature, "INSDFeature_key").text = "SITE"
                ET.SubElement(feature, "INSDFeature_location").text = str(x_pos)
                
                quals = ET.SubElement(feature, "INSDFeature_quals")
                add_qualifier_with_id(
                    quals, 
                    "note", 
                    english_part, 
                    f"q{qualifier_counter}",
                    chinese_part if chinese_part else None
                )
                qualifier_counter += 1
        else:
            for n_pos, freetext in zip(special_positions, freetexts):
                # 分离中英文
                english_part, chinese_part = split_chinese_english(freetext)
                
                # 如果freetext包含中文但没有英文，使用默认英文
                if chinese_part and not english_part:
                    english_part = "custom modification"
                
                # 构建完整的freetext用于检测"or"
                # 注意："or"检测仍然使用原始freetext
                full_freetext = freetext.lower()
                
                # 如果freetext包含"or"，添加misc_difference特征
                if 'or' in full_freetext:
                    # 添加misc_difference特征
                    misc_feature = ET.SubElement(insd_feature_table, "INSDFeature")
                    ET.SubElement(misc_feature, "INSDFeature_key").text = "misc_difference"
                    ET.SubElement(misc_feature, "INSDFeature_location").text = str(n_pos)
                    
                    misc_quals = ET.SubElement(misc_feature, "INSDFeature_quals")
                    add_qualifier_with_id(
                        misc_quals, 
                        "note", 
                        english_part, 
                        f"q{qualifier_counter}",
                        chinese_part if chinese_part else None
                    )
                    qualifier_counter += 1
                
                # 无论是否包含"or"，都添加modified_base特征
                base_feature = ET.SubElement(insd_feature_table, "INSDFeature")
                ET.SubElement(base_feature, "INSDFeature_key").text = "modified_base"
                ET.SubElement(base_feature, "INSDFeature_location").text = str(n_pos)
                
                base_quals = ET.SubElement(base_feature, "INSDFeature_quals")
                
                # 检查freetext是否在预定义修饰中（使用缓存）
                if is_predefined_modifier(freetext):
                    add_qualifier(base_quals, "mod_base", freetext.lower())
                    # 如果包含"or"，同时添加note限定符
                    if 'or' in full_freetext:
                        add_qualifier_with_id(
                            base_quals, 
                            "note", 
                            english_part, 
                            f"q{qualifier_counter}",
                            chinese_part if chinese_part else None
                        )
                        qualifier_counter += 1
                else:
                    add_qualifier(base_quals, "mod_base", "OTHER")
                    add_qualifier_with_id(
                        base_quals, 
                        "note", 
                        english_part, 
                        f"q{qualifier_counter}",
                        chinese_part if chinese_part else None
                    )
                    qualifier_counter += 1

        # 处理环信息
        if moltype == "AA" and ring_infos:
            # 二硫键位置允许的含巯基特殊氨基酸关键词
            # 这些以X表示，在freetext中写明具体名称
            _CYS_KEYWORDS = ['cysteine', 'cys', 'penicillamine', 'pen']

            def _is_valid_disulfide_residue(pos):
                """检查指定位置是否可形成二硫键：C 直接通过，X 查freetext含半胱氨酸相关关键字"""
                seq_char = naked_sequence[pos - 1]
                if seq_char == 'C':
                    return True
                if seq_char == 'X':
                    for x_pos, ft in zip(special_positions, freetexts):
                        if x_pos == pos:
                            # freetext匹配到cys/pen关键字→通过
                            if any(kw in ft.lower() for kw in _CYS_KEYWORDS):
                                return True
                            # 有freetext但未匹配到关键字→给出提醒但不阻止
                            reminders.append(
                                f"序列{sequence_id_counter}位置{pos}是特殊氨基酸('{ft}')，"
                                f"请确认其是否含巯基"
                            )
                            return True
                    # X位置无对应freetext→无法判断，放行但给提醒
                    reminders.append(
                        f"序列{sequence_id_counter}位置{pos}为特殊氨基酸(X)，"
                        f"请确认其是否含巯基并可形成二硫键"
                    )
                    return True
                return False

            for ring in ring_infos:
                if 'disulfide' in ring['note'].lower():
                    errors = []
                    if not _is_valid_disulfide_residue(ring['start']):
                        errors.append(ring['start'])
                    if not _is_valid_disulfide_residue(ring['end']):
                        errors.append(ring['end'])
                    if errors:
                        raise ValueError(
                            f"序列{sequence_id_counter}的二硫键位置错误："
                            f"位置{errors}不是半胱氨酸或含半胱氨酸的特殊氨基酸"
                        )

                feature = ET.SubElement(insd_feature_table, "INSDFeature")
                ET.SubElement(feature, "INSDFeature_key").text = "REGION"
                ET.SubElement(feature, "INSDFeature_location").text = f"{ring['start']}..{ring['end']}"
                quals = ET.SubElement(feature, "INSDFeature_quals")
                qual = ET.SubElement(quals, "INSDQualifier")
                qual.set("id", f"q{qualifier_counter}")
                ET.SubElement(qual, "INSDQualifier_name").text = "note"
                ET.SubElement(qual, "INSDQualifier_value").text = ring['note']
                qualifier_counter += 1

        # 添加序列
        ET.SubElement(insd_seq, "INSDSeq_sequence").text = naked_sequence.lower() if moltype in ["DNA", "RNA"] else naked_sequence
        sequence_id_counter += 1
    
    # 返回XML根元素和提醒列表
    return root, reminders

def has_chinese(text):
    """检测文本中是否包含中文"""
    import re
    return bool(re.search(r'[\u4e00-\u9fff]', text))

def split_chinese_english(text):
    """分离中英文文本
    返回值：(english_part, chinese_part)
    """
    import re
    # 提取中文部分
    chinese_part = ''.join(re.findall(r'[\u4e00-\u9fff]+', text))
    # 提取英文部分（保留空格和标点）
    english_part = re.sub(r'[\u4e00-\u9fff]+', '', text).strip()
    return english_part, chinese_part

def add_qualifier_with_id(quals, name, value, id_value, non_english_value=None):
    """添加带ID的限定符，支持非英文值"""
    qual = ET.SubElement(quals, "INSDQualifier")
    qual.set("id", id_value)
    ET.SubElement(qual, "INSDQualifier_name").text = name
    ET.SubElement(qual, "INSDQualifier_value").text = value
    
    # 如果有非英文值，添加NonEnglishQualifier_value元素
    if non_english_value:
        ET.SubElement(qual, "NonEnglishQualifier_value").text = non_english_value

def add_qualifier(quals, name, value, non_english_value=None):
    """添加限定符，支持非英文值"""
    qual = ET.SubElement(quals, "INSDQualifier")
    ET.SubElement(qual, "INSDQualifier_name").text = name
    ET.SubElement(qual, "INSDQualifier_value").text = value
    
    # 如果有非英文值，添加NonEnglishQualifier_value元素
    if non_english_value:
        ET.SubElement(qual, "NonEnglishQualifier_value").text = non_english_value

def write_xml_to_file(root, filename):
    header = '<?xml version="1.0" encoding="UTF-8"?>\n'
    doctype = '<!DOCTYPE ST26SequenceListing PUBLIC "-//WIPO//DTD Sequence Listing 1.3//EN" "ST26SequenceListing_V1_3.dtd">\n'
    
    tree = ET.ElementTree(root)
    with open(filename, "wb") as f:
        f.write(header.encode('utf-8'))
        f.write(doctype.encode('utf-8'))
        tree.write(f, encoding='utf-8', xml_declaration=False)
