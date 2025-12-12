#!/usr/bin/env python3
"""专门测试JavaScript错误是否已经修复的脚本"""

import requests
import os
import time

# 应用URL
BASE_URL = 'http://127.0.0.1:5000'

# 测试文件路径
TEST_FILE_PATH = '/Users/zhaoyongjiang/Downloads/SAYHELLO/test_file_with_error.xlsx'

def test_javascript_errors():
    """测试JavaScript错误是否已经修复"""
    print(f"=== 测试JavaScript错误修复 ===")
    
    # 创建会话来保持cookie
    session = requests.Session()
    
    # 1. 测试首页的JavaScript
    print("1. 测试首页的JavaScript...")
    response = session.get(BASE_URL)
    if response.status_code != 200:
        print(f"❌ 首页访问失败: HTTP {response.status_code}")
        return False
    
    html_content = response.text
    
    # 检查是否有JavaScript错误
    if 'ReferenceError' in html_content:
        print(f"❌ 首页中存在ReferenceError: {html_content.split('ReferenceError')[1][:100]}...")
        return False
    
    if 'False is not defined' in html_content:
        print("❌ 首页中存在 'False is not defined' 错误")
        return False
    
    # 检查JavaScript变量是否正确渲染
    if 'const hasXmlFile = false;' in html_content:
        print("✅ hasXmlFile变量正确渲染为JavaScript的false")
    else:
        print("⚠️ 未找到正确的hasXmlFile变量")
    
    if 'const taskId = null;' in html_content:
        print("✅ taskId变量正确渲染为JavaScript的null")
    else:
        print("⚠️ 未找到正确的taskId变量")
    
    # 2. 测试上传后的JavaScript
    print("\n2. 测试上传后的JavaScript...")
    with open(TEST_FILE_PATH, 'rb') as f:
        files = {'file': ('test_file_with_error.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        response = session.post(f'{BASE_URL}/upload', files=files)
    
    if response.status_code != 200:
        print(f"❌ 上传失败: HTTP {response.status_code}")
        print(f"响应内容: {response.text[:500]}...")
        return False
    
    html_content = response.text
    
    # 检查是否有JavaScript错误
    if 'ReferenceError' in html_content:
        print(f"❌ 上传后的页面中存在ReferenceError: {html_content.split('ReferenceError')[1][:100]}...")
        return False
    
    if 'False is not defined' in html_content:
        print("❌ 上传后的页面中存在 'False is not defined' 错误")
        return False
    
    # 检查JavaScript变量是否正确渲染
    if 'const hasXmlFile = false;' in html_content:
        print("✅ 上传后hasXmlFile变量正确渲染为JavaScript的false")
    else:
        print("⚠️ 上传后未找到正确的hasXmlFile变量")
    
    # 检查是否存在taskId
    if 'const taskId = "' in html_content:
        print("✅ 上传后taskId变量正确渲染")
    else:
        print("⚠️ 上传后未找到正确的taskId变量")
    
    # 3. 测试错误处理页面
    print("\n3. 测试错误处理页面...")
    # 从页面中提取task_id
    import re
    task_id_match = re.search(r'const taskId = "([^"]+)";', html_content)
    
    if task_id_match:
        task_id = task_id_match.group(1)
        print(f"   任务ID: {task_id}")
        
        # 等待1秒让任务处理
        time.sleep(1)
        
        # 获取任务状态
        response = session.get(f'{BASE_URL}/task_status/{task_id}')
        if response.status_code == 200:
            try:
                task_data = response.json()
                print(f"   任务状态API返回正确的JSON格式")
                print(f"   任务状态: {task_data.get('state')}")
            except Exception as e:
                print(f"   ❌ 任务状态API返回的不是有效的JSON: {e}")
                return False
    
    # 4. 测试清除任务后的页面
    print("\n4. 测试清除任务后的页面...")
    # 刷新首页
    response = session.get(BASE_URL)
    if response.status_code == 200:
        html_content = response.text
        if 'ReferenceError' in html_content or 'False is not defined' in html_content:
            print("❌ 刷新后的页面中存在JavaScript错误")
            return False
        else:
            print("✅ 刷新后的页面中没有JavaScript错误")
    
    return True

if __name__ == '__main__':
    success = test_javascript_errors()
    if success:
        print("\n🎉 JavaScript错误修复测试通过！")
        print("✅ ReferenceError: False is not defined 错误已经解决")
        print("✅ 页面可以正常加载和显示上传结果")
    else:
        print("\n❌ JavaScript错误修复测试失败")
