from rdkit import Chem
from rdkit.Chem import Draw, AllChem
import pandas as pd
import os
import re
from collections import defaultdict
import requests
import cirpy
import pubchempy as pcp
from datetime import datetime

def sanitize_smiles(smiles):
    """清洗连接位点标记的正则处理"""
    # 匹配所有类似[*:n]、[n*]、[*] 的标记
    sanitized = re.sub(r'\[(\d*\*:?\d*)\]', '', smiles)
    # 处理纯连接点的情况
    if sanitized == '[*]':
        return 'C'  # 返回甲烷结构作为示例
    return sanitized


def fix_smiles(smiles):
    """尝试修复SMILES字符串中的N四价问题"""
    mol = Chem.MolFromSmiles(smiles, sanitize=False)
    if not mol:
        raise ValueError(f"无法解析SMILES: {smiles}")
    
    for atom in mol.GetAtoms():
        if atom.GetAtomicNum() == 7 and atom.GetTotalValence() == 4:
            # 如果N原子的价态为四价，增加一个正电荷
            atom.SetFormalCharge(1)
    
    # 重新生成SMILES字符串
    fixed_smiles = Chem.MolToSmiles(mol)
    return fixed_smiles


def get_fragment_name(frag_smiles):
    """根据用户新需求重新设计的片段命名函数：
    1. 首先使用清洁SMILES（去除*）查询PubChem获取化合物名称
    2. 根据原始片段的取代个数，标注（基）或（亚基）
    3. 如果未返回值则标注为空
    4. 然后运行字典查找方式，如果能够找到合适的，就替代
    5. 如果没有找到，则维持上一步的名称或空"""
    try:
        import re
        
        # 1. 检查是否是取代基（包含连接位点）
        is_substituent = '[*]' in frag_smiles or '[' in frag_smiles and '*' in frag_smiles
        
        # 2. 提取连接位点数量
        attachment_points = re.findall(r'\[(\d*\*:?\d*)\]', frag_smiles)
        num_attachments = len(attachment_points)
        
        # 3. 清洗SMILES（去除*和连接位点标记）
        clean_smi = sanitize_smiles(frag_smiles)
        
        # 4. 定义结构匹配字典
        structure_special_cases = {
            # 烷烃类取代基
            'C': 'methyl',
            'CC': 'ethyl',
            'CCC': 'propyl',
            'CCCC': 'butyl',
            'CCCCC': 'pentyl',
            'CCCCCC': 'hexyl',
            'CCO': 'ethoxymethyl',
            'OC(=O)CCNC(=O)': 'alanyl',
            'CC(=O)': 'acetyl',
            'C(=O)O': 'carboxy',
            'c1ccccc1': 'phenyl',
            'c1ccccc1C': 'benzyl'
        }
        
        # 5. 首先尝试结构字典匹配（优先级最高）
        if clean_smi in structure_special_cases:
            return structure_special_cases[clean_smi]
        
        # 6. 如果结构匹配失败，使用清洁SMILES查询PubChem
        pubchem_name = None
        try:
            # 添加超时参数，避免长时间阻塞
            compound = pcp.get_compounds(clean_smi, 'smiles', timeout=5)
            if compound and hasattr(compound[0], 'iupac_name') and compound[0].iupac_name:
                pubchem_name = compound[0].iupac_name
        except requests.exceptions.Timeout:
            print(f"PubChem查询超时: {clean_smi}")
        except Exception as e:
            print(f"PubChem查询失败: {clean_smi} -> {str(e)}")
        
        # 7. 根据取代基情况生成基础名称
        base_name = ""
        if is_substituent:
            if pubchem_name:
                # 根据连接位点数量添加（基）或（亚基）
                if num_attachments == 1:
                    base_name = f"{pubchem_name}（基）"
                elif num_attachments == 2:
                    base_name = f"{pubchem_name}（亚基）"
                else:
                    base_name = f"{pubchem_name}（多取代基）"
            else:
                base_name = ""
        else:
            # 不是取代基，直接使用PubChem名称
            base_name = pubchem_name or ""
        
        # 8. 如果PubChem没有返回名称，尝试使用结构特征推断
        if not base_name and is_substituent:
            # 简单的碳链长度判断
            if clean_smi.startswith('C') and all(c == 'C' or c == 'c' for c in clean_smi if c.isalpha()):
                carbon_count = clean_smi.count('C') + clean_smi.count('c')
                if carbon_count == 1:
                    return 'methyl'
                elif carbon_count == 2:
                    return 'ethyl'
                elif carbon_count == 3:
                    return 'propyl'
                elif carbon_count == 4:
                    return 'butyl'
                elif carbon_count == 5:
                    return 'pentyl'
                elif carbon_count == 6:
                    return 'hexyl'
                else:
                    base_name = f'C{carbon_count}（基）'
            else:
                base_name = f"{clean_smi}（基）"
        
        # 9. 返回最终结果
        return base_name if base_name else frag_smiles
        
    except Exception as e:
        print(f"命名失败: {frag_smiles} -> {str(e)}")
        return frag_smiles  # 返回原始SMILES作为备用


# 以下是可能需要的其他函数，保持不变
# （这里可以保留原来文件中的其他函数）

def process_compounds(excel_path, output_folder):
    """处理化合物拆解的主函数
    
    参数：
        excel_path: Excel文件路径
        output_folder: 输出文件夹路径
        
    返回：
        result_path: 处理结果Excel文件路径
        stats_path: 统计结果Excel文件路径
        images_dir: 图片文件夹路径
        summary: 处理摘要信息
    """
    import re
    # 获取当前日期并格式化
    current_date = datetime.now().strftime('%Y%m%d')
    
    # 创建输出目录
    fragments_images_dir = os.path.join(output_folder, f"fragments_images_{current_date}")
    fragment_stats_images_dir = os.path.join(output_folder, f"fragment_stats_images_{current_date}")
    os.makedirs(fragments_images_dir, exist_ok=True)
    os.makedirs(fragment_stats_images_dir, exist_ok=True)

    # 读取数据
    df = pd.read_excel(excel_path, engine='openpyxl', header=0)
    
    # 提取核心结构
    core_row = df[df['化合物编号'] == 'core'].iloc[0]
    core_smiles = core_row['SMILES']
    core = Chem.MolFromSmiles(core_smiles)
    if not core:
        raise ValueError(f"核心结构解析失败: {core_smiles}")
    
    # 生成核心结构图片（显示碳原子编号）
    core_img_name = 'core_structure.png'
    core_img_path = f"{fragment_stats_images_dir}/{core_img_name}"
    try:
        # 创建绘图选项，显示碳原子编号
        for atom in core.GetAtoms():
            if atom.GetAtomicNum() == 6:  # 6是碳原子的原子序数
                atom.SetProp("atomLabel", str(atom.GetIdx()))
        
        Draw.MolToFile(core, core_img_path, size=(500, 500))
        
        # 计算相对于static目录的路径，用于前端访问
        if core_img_path.startswith('static/'):
            core_img_path_relative = core_img_path
        else:
            # 尝试提取static目录开始的部分
            static_pos = core_img_path.find('static/')
            if static_pos != -1:
                core_img_path_relative = core_img_path[static_pos:]
            else:
                # 如果没有找到static目录，保留原始路径
                core_img_path_relative = core_img_path
    except Exception as e:
        print(f"⚠️ 核心结构图片生成失败: {str(e)}")
        core_img_path_relative = ""

    # 初始化数据结构
    processed_data = []
    skip_count = 0
    no_core_compounds = []  # 记录无核心结构的化合物编号
    invalid_smiles_compounds = []  # 记录无效SMILES的化合物编号
    fragment_records = {}
    fragment_stats = defaultdict(lambda: defaultdict(lambda: {'count': 0, 'cpd_ids': []}))

    # 处理化合物
    for idx, row in df.iloc[1:].iterrows():
        cpd_id = str(row['化合物编号'])
        target_smiles = row['SMILES']
        
        # 解析分子
        mol = Chem.MolFromSmiles(target_smiles)
        if not mol:
            print(f"🟡 警告：化合物 {cpd_id} SMILES无效，尝试修复")
            # 尝试修复N四价问题
            try:
                fixed_smiles = fix_smiles(target_smiles)
                mol = Chem.MolFromSmiles(fixed_smiles)
                if not mol:
                    print(f"🔴 错误：化合物 {cpd_id} 修复后的SMILES无效")
                    invalid_smiles_compounds.append(cpd_id)
                    skip_count += 1
                    continue
                else:
                    target_smiles = fixed_smiles
                    print(f"修复成功，新的SMILES: {fixed_smiles}")
            except Exception as e:
                print(f"🔴 错误：化合物 {cpd_id} 修复失败 - {str(e)}")
                invalid_smiles_compounds.append(cpd_id)
                skip_count += 1
                continue

        # 核心替换验证
        modified = Chem.ReplaceCore(mol, core, labelByIndex=True)
        if modified is None:
            print(f"🔴 错误：化合物 {cpd_id} 无核心结构")
            no_core_compounds.append(cpd_id)
            skip_count += 1
            continue

        try:
            # 片段处理
            fragments_mol = Chem.GetMolFrags(modified, asMols=True)
            fragments = [Chem.MolToSmiles(m) for m in fragments_mol]
            
            for frag_mol, frag_smiles in zip(fragments_mol, fragments):
                # 清洗并记录原始SMILES
                orig_smiles = frag_smiles
                clean_smiles = sanitize_smiles(frag_smiles)
                
                # 提取位点信息（使用原始SMILES）
                sites = re.findall(r'\[(\d+)\*\]', orig_smiles)
                site_key = '-'.join(sites) if len(sites) else 'unknown'
                
                # 更新统计（使用原始SMILES）
                frag_stat = fragment_stats[site_key][orig_smiles]
                frag_stat['count'] += 1
                if cpd_id not in frag_stat['cpd_ids']:
                    frag_stat['cpd_ids'].append(cpd_id)
                
                # 注册片段信息
                if orig_smiles not in fragment_records:
                    # 生成化学名称（使用清洗后SMILES）
                    chem_name = get_fragment_name(clean_smiles)
                    
                    # 生成安全文件名（使用原始SMILES）
                    safe_name = re.sub(r'[^\w]', '_', orig_smiles)[:50]
                    img_path = f"{fragment_stats_images_dir}/{safe_name}.png"
                    # 计算相对于static目录的路径，用于前端访问
                    if img_path.startswith('static/'):
                        img_path_relative = img_path
                    else:
                        # 尝试提取static目录开始的部分
                        static_pos = img_path.find('static/')
                        if static_pos != -1:
                            img_path_relative = img_path[static_pos:]
                        else:
                            # 如果没有找到static目录，保留原始路径
                            img_path_relative = img_path
                    
                    # 生成并保存图片（使用原始结构）
                    try:
                        Draw.MolToFile(frag_mol, img_path, size=(300, 300))
                    except Exception as e:
                        print(f"⚠️ 片段图片生成失败: {orig_smiles} - {str(e)}")
                        img_path = ""
                    
                    # 记录全局信息
                    fragment_records[orig_smiles] = {
                        'chem_name': chem_name,
                        'img_path': img_path_relative
                    }
            
            # 生成化合物级图片（使用原始结构）
            if fragments_mol:
                safe_id = re.sub(r'[^\w]', '_', cpd_id)
                img = Draw.MolsToGridImage(
                    fragments_mol,
                    molsPerRow=3,
                    subImgSize=(300, 300),
                    legends=[f"Fragment {i+1}" for i in range(len(fragments_mol))],
                    returnPNG=False
                )
                img.save(f"{fragments_images_dir}/{safe_id}.png")
                
        except Exception as e:
            print(f"⚠️ 处理异常: {cpd_id} - {str(e)}")
            skip_count += 1
            continue
        
        processed_data.append([cpd_id, target_smiles] + fragments)
    
    # 生成处理结果表
    max_frags = max((len(row)-2 for row in processed_data), default=0)
    result_df = pd.DataFrame(
        [row + ['']*(max_frags-len(row)+2) for row in processed_data],
        columns=['化合物编号', 'SMILES'] + [f'片段_{i+1}' for i in range(max_frags)]
    )
    result_path = os.path.join(output_folder, f'processed_results_{current_date}.xlsx')
    result_df.to_excel(result_path, index=False, engine='openpyxl')
    
    # 构建统计结果表
    stats_data = []
    for site_key, frags in fragment_stats.items():
        for frag_smiles, data in frags.items():
            record = fragment_records.get(frag_smiles, {})
            stats_data.append([
                site_key,
                record.get('chem_name', frag_smiles),
                record.get('img_path', ""),
                ', '.join(data['cpd_ids']),
                frag_smiles,  # 保留原始SMILES
                data['count']
            ])
    
    stats_df = pd.DataFrame(
        stats_data,
        columns=['连接位点', '化学名称', '图片路径', '关联化合物', 'SMILES结构', '出现频次']
    )
    stats_path = os.path.join(output_folder, f'fragment_statistics2_{current_date}.xlsx')
    stats_df.to_excel(stats_path, index=False, engine='openpyxl')

    # 输出摘要
    print(f"\n✅ 完成处理: 成功 {len(processed_data)} 项 / 失败 {skip_count} 项")
    print(f"🖼️ 结构图片路径: {os.path.abspath(fragments_images_dir)}")
    print(f"📷 统计图片路径: {os.path.abspath(fragment_stats_images_dir)}")
    print(f"📊 统计结果文件: {os.path.abspath(stats_path)}")
    
    # 构建返回结果
    # 计算总片段数
    total_fragments = sum(len(frags) for frags in fragment_stats.values())
    
    # 转换defaultdict为普通字典以便JSON序列化
    fragment_stats_dict = {}
    for site_key, frags in fragment_stats.items():
        fragment_stats_dict[site_key] = {}
        for frag_smiles, data in frags.items():
            fragment_stats_dict[site_key][frag_smiles] = {
                'count': data['count'],
                'cpd_ids': data['cpd_ids']
            }
    
    # 提取核心结构中的位点信息
    core_sites = re.findall(r'\[(\d+)\*\]', core_smiles)
    core_sites_sorted = sorted(list(set(core_sites)), key=lambda x: int(x))
    
    summary = {
        'total_compounds': len(processed_data) + skip_count,
        'processed_compounds': len(processed_data),
        'skip_count': skip_count,
        'no_core_compounds': no_core_compounds,  # 记录无核心结构的化合物编号
        'invalid_smiles_compounds': invalid_smiles_compounds,  # 记录无效SMILES的化合物编号
        'total_fragments': total_fragments,
        'fragment_stats': fragment_stats_dict,
        'fragment_records': fragment_records,
        'core_structure': {
            'smiles': core_smiles,
            'img_path': core_img_path_relative,
            'sites': core_sites_sorted
        }
    }
    
    return result_path, stats_path, fragments_images_dir, summary