import parser

try:
    # 测试包含非法字符的RNA序列
    sequence = "AGCU#GUAC"
    result = parser.parse_sequence(sequence, "RNA", line_number=1)
    print("解析成功:", result)
except ValueError as e:
    print("检测到非法字符:", e)
    
    # 验证错误信息格式
    error_msg = str(e)
    print(f"错误消息: {error_msg}")
    
    # 检查是否包含位置信息
    if "位置" in error_msg:
        print("✅ 错误消息包含位置信息")
    
    # 检查是否包含非法字符
    if "非法字符" in error_msg:
        print("✅ 错误消息包含非法字符信息")
