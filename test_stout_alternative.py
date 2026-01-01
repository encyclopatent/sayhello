#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试STOUT替代方案：使用RDKit和PubChemPy实现SMILES到IUPAC名称转换
特别是带[*]连接点的片段命名功能
"""

import rdkit
from rdkit import Chem
from rdkit.Chem import Draw
import pubchempy as pcp

def get_iupac_name(smiles):
    """
    使用PubChemPy获取SMILES的IUPAC名称
    """
    try:
        compounds = pcp.get_compounds(smiles, 'smiles')
        if compounds:
            return compounds[0].iupac_name
        return None
    except Exception as e:
        print(f"PubChem查询失败: {smiles} -> {str(e)}")
        return None

def get_fragment_name(frag_smiles):
    """
    为带[*]连接点的片段生成取代基名称
    策略：
    1. 移除[*]连接点
    2. 查询完整化合物名称
    3. 应用转换规则将完整化合物名称转换为取代基名称
    """
    # 移除[*]连接点
    mol_smiles = frag_smiles.replace('[*]', '')
    
    # 简单结构优先匹配
    simple_fragments = {
        'C': 'methyl',
        'CC': 'ethyl',
        'CCC': 'propyl',
        'CCCC': 'butyl',
        'OC': 'hydroxymethyl',
        'OCC': '2-hydroxyethyl',
        'NCC': '2-aminoethyl',
        'ClC': 'chloromethyl',
        'BrC': 'bromomethyl',
        'FC': 'fluoromethyl',
        'IC': 'iodomethyl'
    }
    
    if mol_smiles in simple_fragments:
        return simple_fragments[mol_smiles]
    
    # PubChem查询
    iupac_name = get_iupac_name(mol_smiles)
    if not iupac_name:
        return None
    
    # 应用转换规则
    name_conversions = {
        'methane': 'methyl',
        'ethane': 'ethyl',
        'propane': 'propyl',
        'butane': 'butyl',
        'pentane': 'pentyl',
        'hexane': 'hexyl',
        'heptane': 'heptyl',
        'octane': 'octyl',
        'nonane': 'nonyl',
        'decane': 'decyl',
        'methanol': 'hydroxymethyl',
        'ethanol': 'hydroxyethyl',
        'propanol': 'hydroxypropyl',
        'butanol': 'hydroxybutyl',
        'methylamine': 'aminomethyl',
        'ethylamine': 'aminoethyl',
        'propylamine': 'aminopropyl',
        'fluoromethane': 'fluoromethyl',
        'chloromethane': 'chloromethyl',
        'bromomethane': 'bromomethyl',
        'iodomethane': 'iodomethyl',
    }
    
    # 尝试直接替换
    for full_name, substituent in name_conversions.items():
        if iupac_name == full_name:
            return substituent
    
    # 尝试后缀替换
    if iupac_name.endswith('ane'):
        # 烷烃 -> 烷基
        return iupac_name[:-3] + 'yl'
    elif iupac_name.endswith('ol'):
        # 醇 -> 羟基烷基
        if iupac_name.endswith('ethanol'):
            return 'hydroxyethyl'
        elif iupac_name.endswith('methanol'):
            return 'hydroxymethyl'
    elif iupac_name.endswith('amine'):
        # 胺 -> 氨基烷基
        if iupac_name.endswith('methylamine'):
            return 'aminomethyl'
        elif iupac_name.endswith('ethylamine'):
            return 'aminoethyl'
    
    # 如果没有匹配的转换规则，返回原始名称
    return iupac_name

def test_basic_conversion():
    """
    测试基本的SMILES到IUPAC名称转换
    """
    print("=== 测试基本SMILES到IUPAC名称转换 ===")
    test_cases = [
        "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",  # 咖啡因
        "C",  # 甲烷
        "CC",  # 乙烷
        "OC",  # 甲醇
        "NCC",  # 乙胺
    ]
    
    for smiles in test_cases:
        iupac_name = get_iupac_name(smiles)
        print(f"SMILES: {smiles} -> IUPAC: {iupac_name}")

def test_fragment_naming():
    """
    测试带[*]连接点的片段命名
    """
    print("\n=== 测试带[*]连接点的片段命名 ===")
    test_cases = [
        "C[*]",  # 甲基片段
        "CC[*]",  # 乙基片段
        "OC[*]",  # 羟甲基片段
        "OCC[*]",  # 2-羟乙基片段
        "NCC[*]",  # 2-氨乙基片段
        "ClC[*]",  # 氯甲基片段
        "BrC[*]",  # 溴甲基片段
        "FC[*]",  # 氟甲基片段
        "IC[*]",  # 碘甲基片段
        "CCC[*]",  # 丙基片段
    ]
    
    for frag_smiles in test_cases:
        fragment_name = get_fragment_name(frag_smiles)
        print(f"片段SMILES: {frag_smiles} -> 取代基名称: {fragment_name}")

if __name__ == "__main__":
    # 测试基本转换
    test_basic_conversion()
    
    # 测试片段命名
    test_fragment_naming()
