import sys
print("Python版本:", sys.version)
print("当前工作目录:", sys.path[0])

# 添加Downloads目录到sys.path
sys.path.append('/Users/zhaoyongjiang/Downloads')
print("修改后的sys.path:", sys.path)

try:
    from peptide2fragment import process_compounds
    print("成功导入process_compounds函数")
    print("函数签名:", process_compounds.__doc__)
except Exception as e:
    print(f"导入失败: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()