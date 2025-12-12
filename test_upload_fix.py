#!/usr/bin/env python3
"""测试上传功能是否正常工作的脚本"""

import requests
import os
import time

# 应用URL
BASE_URL = 'http://127.0.0.1:5000'

# 测试文件路径
TEST_FILE_PATH = '/Users/zhaoyongjiang/Downloads/SAYHELLO/test_simple.xlsx'

def test_upload_file():
    """测试文件上传功能"""
    print(f"正在测试文件上传: {TEST_FILE_PATH}")
    
    # 检查测试文件是否存在
    if not os.path.exists(TEST_FILE_PATH):
        print(f"错误: 测试文件 {TEST_FILE_PATH} 不存在")
        return False
    
    # 创建会话来保持cookie
    session = requests.Session()
    
    # 打开文件并上传
    with open(TEST_FILE_PATH, 'rb') as f:
        files = {'file': ('test_simple.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        response = session.post(f'{BASE_URL}/upload', files=files)
    
    if response.status_code != 200:
        print(f"上传失败: HTTP状态码 {response.status_code}")
        print(f"响应内容: {response.text[:500]}...")
        return False
    
    print("上传成功！")
    
    # 获取任务ID和页面内容
    html_content = response.text
    
    # 检查是否有JavaScript错误
    if 'ReferenceError' in html_content:
        print("错误: 页面中包含ReferenceError")
        return False
    
    if 'False is not defined' in html_content:
        print("错误: 页面中包含 'False is not defined' 错误")
        return False
    
    # 检查taskId和hasXmlFile是否正确渲染
    if 'const taskId = null;' in html_content or 'const hasXmlFile = false;' in html_content:
        print("JavaScript变量渲染正确")
    else:
        print("警告: 未找到预期的JavaScript变量")
        
    # 保存页面内容用于调试
    with open('debug_upload_response.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return True

if __name__ == '__main__':
    success = test_upload_file()
    if success:
        print("\n🎉 测试通过！文件上传功能正常工作")
    else:
        print("\n❌ 测试失败")
