import os
import sys
import tempfile
import pandas as pd
from sirna_analysis import check_sirna_match, perform_sirna_analysis


def test_blastn_basic_functionality():
    """测试blastn基本功能"""
    print("测试blastn基本功能...")
    
    # 测试序列
    query = "GTGCAGAAGAAGAGCAGAGTA"
    target = "ATCGGTGCAGAAGAAGAGCAGAGTAATCG"
    
    # 使用原始算法
    strand_original, pos_original = check_sirna_match(query, target, use_blastn=False)
    
    # 使用blastn
    strand_blastn, pos_blastn = check_sirna_match(query, target, use_blastn=True)
    
    print(f"原始算法: {strand_original}, {pos_original}")
    print(f"BLASTN: {strand_blastn}, {pos_blastn}")
    
    # 验证两种方法都能找到匹配
    assert strand_original == "正义链" or strand_original == "反义链", "原始算法应找到匹配"
    assert strand_blastn == "正义链" or strand_blastn == "反义链", "BLASTN应找到匹配"
    
    print("✓ blastn基本功能测试通过")



def test_blastn_integration_with_excel():
    """测试blastn与Excel分析流程的集成"""
    print("\n测试blastn与Excel分析流程的集成...")
    
    # 创建测试Excel文件
    test_data = {
        'Query': ['GTGCAGAAGAAGAGCAGAGTA', 'CTGCAGAAGAAGAGCAGAGTA'],  # 第一条是匹配的，第二条有一个错配
        'Target': ['ATCGGTGCAGAAGAAGAGCAGAGTAATCG'] * 2
    }
    
    df = pd.DataFrame(test_data)
    
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.xlsx', delete=False) as f:
        df.to_excel(f, index=False)
        excel_path = f.name
    
    # 创建测试FASTA文件
    fasta_content = ">test_seq\nGTGCAGAAGAAGAGCAGAGTA"
    with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as f:
        f.write(fasta_content)
        fasta_path = f.name
    
    try:
        # 使用原始算法
        print("执行原始算法分析...")
        results_original, output_path_original = perform_sirna_analysis(
            excel_path, [fasta_path], use_blastn=False
        )
        
        # 使用blastn
        print("执行BLASTN算法分析...")
        results_blastn, output_path_blastn = perform_sirna_analysis(
            excel_path, [fasta_path], use_blastn=True
        )
        
        # 验证结果
        print(f"原始算法结果数量: {len(results_original)}")
        print(f"BLASTN算法结果数量: {len(results_blastn)}")
        
        assert len(results_original) == len(results_blastn), "结果数量应相同"
        
        # 检查第一条序列（完全匹配）
        assert results_original[0]['strand_type'] != "非siRNA", "原始算法应找到第一条序列的匹配"
        assert results_blastn[0]['strand_type'] != "非siRNA", "BLASTN应找到第一条序列的匹配"
        
        print("✓ blastn与Excel分析流程集成测试通过")
        
    finally:
        # 清理临时文件
        os.unlink(excel_path)
        os.unlink(fasta_path)
        if 'output_path_original' in locals() and os.path.exists(output_path_original):
            os.unlink(output_path_original)
        if 'output_path_blastn' in locals() and os.path.exists(output_path_blastn):
            os.unlink(output_path_blastn)



def test_blastn_antisense_strand():
    """测试blastn对反义链的检测"""
    print("\n测试blastn对反义链的检测...")
    
    # 测试序列
    query = "TACTCTGCTCTTCTTCTGCAC"  # 前一个测试序列的反向互补
    target = "ATCGGTGCAGAAGAAGAGCAGAGTAATCG"
    
    # 使用原始算法
    strand_original, pos_original = check_sirna_match(query, target, use_blastn=False)
    
    # 使用blastn
    strand_blastn, pos_blastn = check_sirna_match(query, target, use_blastn=True)
    
    print(f"原始算法: {strand_original}, {pos_original}")
    print(f"BLASTN: {strand_blastn}, {pos_blastn}")
    
    # 验证两种方法都能找到反义链匹配
    assert strand_original == "反义链", "原始算法应检测到反义链"
    assert strand_blastn == "反义链", "BLASTN应检测到反义链"
    
    print("✓ blastn反义链检测测试通过")



def test_blastn_no_match():
    """测试blastn对不匹配序列的处理"""
    print("\n测试blastn对不匹配序列的处理...")
    
    # 测试序列
    query = "ATCGATCGATCGATCGATCG"
    target = "GTGCAGAAGAAGAGCAGAGTA"
    
    # 使用原始算法
    strand_original, pos_original = check_sirna_match(query, target, use_blastn=False)
    
    # 使用blastn
    strand_blastn, pos_blastn = check_sirna_match(query, target, use_blastn=True)
    
    print(f"原始算法: {strand_original}, {pos_original}")
    print(f"BLASTN: {strand_blastn}, {pos_blastn}")
    
    # 验证两种方法都能正确识别不匹配
    assert strand_original == "非siRNA", "原始算法应识别为非siRNA"
    assert strand_blastn == "非siRNA", "BLASTN应识别为非siRNA"
    
    print("✓ blastn不匹配序列处理测试通过")


if __name__ == "__main__":
    print("开始blastn集成测试...")
    
    try:
        test_blastn_basic_functionality()
        test_blastn_antisense_strand()
        test_blastn_no_match()
        test_blastn_integration_with_excel()
        
        print("\n🎉 所有blastn集成测试通过！")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)