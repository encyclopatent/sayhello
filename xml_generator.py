# xml_generator.py
import xml.etree.ElementTree as ET
import pandas as pd
import os
from parser import parse_sequence
from datetime import datetime
from parser import BASE_NAMES, PREDEFINED_MODS

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

def generate_xml(sequences, basic_data, output_folder):
    # 创建提醒列表
    reminders = []
    
    root = ET.Element("ST26SequenceListing", {
        "originalFreeTextLanguageCode": "en",
        "nonEnglishFreeTextLanguageCode": "zh",
        "dtdVersion": "V1_3",
        "fileName": f"{basic_data['ApplicantFileReference']}.xml",
        "softwareName": "WIPO Sequence",
        "softwareVersion": "2.3.0",
        "productionDate": datetime.now().strftime("%Y-%m-%d")
    })

    ET.SubElement(root, "ApplicantFileReference").text = basic_data['ApplicantFileReference']
    
    if (basic_data.get('earliestpriorityIPOfficeCode') and 
        basic_data.get('ApplicationNumberText') and 
        basic_data.get('earliestpriorityFilingDate')):
        earliest_priority = ET.SubElement(root, "EarliestPriorityApplicationIdentification")
        ET.SubElement(earliest_priority, "IPOfficeCode").text = basic_data['earliestpriorityIPOfficeCode']
        ET.SubElement(earliest_priority, "ApplicationNumberText").text = basic_data['ApplicationNumberText']
        ET.SubElement(earliest_priority, "FilingDate").text = basic_data['earliestpriorityFilingDate']
    
    ET.SubElement(root, "ApplicantName", {"languageCode": "zh"}).text = basic_data['ApplicantName']
    ET.SubElement(root, "ApplicantNameLatin").text = basic_data['ApplicantNameLatin']
    ET.SubElement(root, "InventorName", {"languageCode": "zh"}).text = basic_data['InventorName']
    ET.SubElement(root, "InventorNameLatin").text = basic_data['InventorNameLatin']
    ET.SubElement(root, "InventionTitle", {"languageCode": "zh"}).text = basic_data['InventionTitle']
    ET.SubElement(root, "SequenceTotalQuantity").text = str(len(sequences))
    sequence_id_counter = 1
    qualifier_counter = 2

    for seq_data in sequences:
        sequence, raw_moltype, organism, qual_moltype, freetexts, ring_infos, hybrid_segments, _ = seq_data
        hybrid_segments = hybrid_segments or []
        
        # 获取当前序列的行号（从1开始计数）
        line_number = sequences.index(seq_data) + 1
        
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
        
        # 检查是否使用了默认限定符分子类型
        if pd.isnull(qual_moltype):
            qual_moltype = "other RNA" if moltype in ["DNA", "RNA"] else "protein"
            reminders.append(f"第{line_number}行：未指定限定符分子类型，使用了默认值'{qual_moltype}'")
        naked_sequence, modifications, special_positions, original_moltype, has_degenerate_bases, ligand_removed = parse_sequence(sequence, raw_moltype, line_number)
        
        # 检查是否移除了L96配体
        if ligand_removed:
            reminders.append(f"第{line_number}行：检测到并移除了L96配体，未将其加工为注释")
        
        # 检查是否包含简并碱基
        if has_degenerate_bases:
            reminders.append(f"第{line_number}行：序列包含简并碱基（M/R/W/S/Y/K/V/H/D/B），请核查是否为预期使用")
        
        if moltype in ["DNA", "RNA"] and len(special_positions) > 0:
            seq_list = list(naked_sequence)
            for idx, pos in enumerate(special_positions):
                if idx >= len(freetexts):
                    continue
                freetext = freetexts[idx].lower()
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
        
        sequence_data = ET.SubElement(root, "SequenceData", {"sequenceIDNumber": str(sequence_id_counter)})
        insd_seq = ET.SubElement(sequence_data, "INSDSeq")
        ET.SubElement(insd_seq, "INSDSeq_length").text = str(len(naked_sequence))
        ET.SubElement(insd_seq, "INSDSeq_moltype").text = original_moltype if pd.notnull(original_moltype) else "RNA"
        ET.SubElement(insd_seq, "INSDSeq_division").text = "PAT"

        insd_feature_table = ET.SubElement(insd_seq, "INSDSeq_feature-table")
        
        # 必须的source特征
        insd_feature_source = ET.SubElement(insd_feature_table, "INSDFeature")
        ET.SubElement(insd_feature_source, "INSDFeature_key").text = "source"
        ET.SubElement(insd_feature_source, "INSDFeature_location").text = f"1..{len(naked_sequence)}"
        insd_feature_quals_source = ET.SubElement(insd_feature_source, "INSDFeature_quals")
        
        if moltype == "DNA" and hybrid_segments:
            add_qualifier(insd_feature_quals_source, "mol_type", "other DNA")
        else:
            add_qualifier(insd_feature_quals_source, "mol_type", qual_moltype)
        
        organism_id = f"q{qualifier_counter}"
        add_qualifier_with_id(insd_feature_quals_source, "organism", organism, organism_id)
        qualifier_counter += 1

        # 处理杂合DNA序列的区段特征
        if moltype == "DNA" and hybrid_segments:
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
                ET.SubElement(feature, "INSDFeature_location").text = f"{seg['start']}..{seg['end']}"
                
                quals = ET.SubElement(feature, "INSDFeature_quals")
                qual = ET.SubElement(quals, "INSDQualifier")
                qual.set("id", f"q{qualifier_counter}")
                ET.SubElement(qual, "INSDQualifier_name").text = "note"
                ET.SubElement(qual, "INSDQualifier_value").text = seg['type']
                qualifier_counter += 1

        # 处理修饰碱基
        for mod_info in modifications:
            location, mod_type, base = mod_info
            feature = ET.SubElement(insd_feature_table, "INSDFeature")
            
            if mod_type in ['m', 'f', 'e', 'pv']:
                ET.SubElement(feature, "INSDFeature_key").text = "modified_base"
            elif mod_type == 's':
                ET.SubElement(feature, "INSDFeature_key").text = "misc_feature"
            
            ET.SubElement(feature, "INSDFeature_location").text = str(location)
            
            quals = ET.SubElement(feature, "INSDFeature_quals")
            
            if mod_type == 'pv':
                add_qualifier(quals, "mod_base", "OTHER")
                note_id = f"q{qualifier_counter}"
                qual = ET.SubElement(quals, "INSDQualifier")
                qual.set("id", note_id)
                ET.SubElement(qual, "INSDQualifier_name").text = "note"
                ET.SubElement(qual, "INSDQualifier_value").text = "5prime-vinylphosphonate"
                qualifier_counter += 1
            elif mod_type == 'm':
                base_name = BASE_NAMES.get(base.upper(), {}).get('en', 'base')
                if base == 'a':
                    add_qualifier(quals, "mod_base", "OTHER")
                    note_id = f"q{qualifier_counter}"
                    qual = ET.SubElement(quals, "INSDQualifier")
                    qual.set("id", note_id)
                    ET.SubElement(qual, "INSDQualifier_name").text = "note"
                    ET.SubElement(qual, "INSDQualifier_value").text = "2prime-O-methyl " + base_name
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
                ET.SubElement(qual, "INSDQualifier_value").text = "2prime-fluoro " + base_name
                qualifier_counter += 1
            elif mod_type == 'e':
                base_name = BASE_NAMES.get(base.upper(), {}).get('en', 'base')
                add_qualifier(quals, "mod_base", "OTHER")
                note_id = f"q{qualifier_counter}"
                qual = ET.SubElement(quals, "INSDQualifier")
                qual.set("id", note_id)
                ET.SubElement(qual, "INSDQualifier_name").text = "note"
                ET.SubElement(qual, "INSDQualifier_value").text = "2prime-methoxyethyl " + base_name
                qualifier_counter += 1
            elif mod_type == 's':
                note_id = f"q{qualifier_counter}"
                qual = ET.SubElement(quals, "INSDQualifier")
                qual.set("id", note_id)
                ET.SubElement(qual, "INSDQualifier_name").text = "note"
                ET.SubElement(qual, "INSDQualifier_value").text = "phosphorothioate linkage"
                qualifier_counter += 1

        # 处理特殊位置
        if moltype == "AA":
            for x_pos, freetext in zip(special_positions, freetexts):
                feature = ET.SubElement(insd_feature_table, "INSDFeature")
                ET.SubElement(feature, "INSDFeature_key").text = "SITE"
                ET.SubElement(feature, "INSDFeature_location").text = str(x_pos)
                
                quals = ET.SubElement(feature, "INSDFeature_quals")
                qual = ET.SubElement(quals, "INSDQualifier")
                qual.set("id", f"q{qualifier_counter}")
                ET.SubElement(qual, "INSDQualifier_name").text = "note"
                ET.SubElement(qual, "INSDQualifier_value").text = freetext
                qualifier_counter += 1
        else:
            for n_pos, freetext in zip(special_positions, freetexts):
                feature = ET.SubElement(insd_feature_table, "INSDFeature")
                ET.SubElement(feature, "INSDFeature_key").text = "modified_base"
                ET.SubElement(feature, "INSDFeature_location").text = str(n_pos)
                
                quals = ET.SubElement(feature, "INSDFeature_quals")
                if freetext.lower() in PREDEFINED_MODS:
                    add_qualifier(quals, "mod_base", freetext.lower())
                else:
                    add_qualifier(quals, "mod_base", "OTHER")
                    qual = ET.SubElement(quals, "INSDQualifier")
                    qual.set("id", f"q{qualifier_counter}")
                    ET.SubElement(qual, "INSDQualifier_name").text = "note"
                    ET.SubElement(qual, "INSDQualifier_value").text = freetext
                    qualifier_counter += 1

        # 处理环信息
        if moltype == "AA" and ring_infos:
            for ring in ring_infos:
                if 'disulfide' in ring['note'].lower():
                    start_idx = ring['start'] - 1
                    end_idx = ring['end'] - 1
                    errors = []
                    if naked_sequence[start_idx] not in {'C','X'}:
                        errors.append(ring['start'])
                    if naked_sequence[end_idx] not in {'C','X' }:
                        errors.append(ring['end'])
                    if errors:
                        raise ValueError(f"序列{sequence_id_counter}的二硫键位置错误：位置{errors}不是半胱氨酸")

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

def add_qualifier(quals, name, value):
    qual = ET.SubElement(quals, "INSDQualifier")
    ET.SubElement(qual, "INSDQualifier_name").text = name
    ET.SubElement(qual, "INSDQualifier_value").text = value

def add_qualifier_with_id(quals, name, value, id_value):
    qual = ET.SubElement(quals, "INSDQualifier")
    qual.set("id", id_value)
    ET.SubElement(qual, "INSDQualifier_name").text = name
    ET.SubElement(qual, "INSDQualifier_value").text = value

def write_xml_to_file(root, filename):
    header = '<?xml version="1.0" encoding="UTF-8"?>\n'
    doctype = '<!DOCTYPE ST26SequenceListing PUBLIC "-//WIPO//DTD Sequence Listing 1.3//EN" "ST26SequenceListing_V1_3.dtd">\n'
    
    tree = ET.ElementTree(root)
    with open(filename, "wb") as f:
        f.write(header.encode('utf-8'))
        f.write(doctype.encode('utf-8'))
        tree.write(f, encoding='utf-8', xml_declaration=False)
