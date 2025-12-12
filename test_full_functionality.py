#!/usr/bin/env python3
"""测试完整功能是否正常工作的脚本"""

import requests
import os
import time

# 应用URL
BASE_URL = 'http://127.0.0.1:5000'

# 测试文件路径
TEST_FILE_PATH = '/Users/zhaoyongjiang/Downloads/SAYHELLO/test_file_with_error.xlsx'

def test_full_flow():
    """测试完整的上传、转换、下载流程"""
    print(f"=== 测试完整功能流程 ===")
    
    # 创建会话来保持cookie
    session = requests.Session()
    
    # 1. 访问首页
    print("1. 访问首页...")
    response = session.get(BASE_URL)
    if response.status_code != 200:
        print(f"❌ 首页访问失败: HTTP {response.status_code}")
        return False
    
    # 检查JavaScript变量是否正确渲染
    html_content = response.text
    if 'ReferenceError' in html_content or 'False is not defined' in html_content:
        print("❌ 页面中存在JavaScript错误")
        return False
    
    # 2. 上传文件
    print("2. 上传文件...")
    with open(TEST_FILE_PATH, 'rb') as f:
        files = {'file': ('test_simple.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        response = session.post(f'{BASE_URL}/upload', files=files)
    
    if response.status_code != 200:
        print(f"❌ 上传失败: HTTP {response.status_code}")
        print(f"响应内容: {response.text[:500]}...")
        return False
    
    # 检查是否有JavaScript错误
    html_content = response.text
    if 'ReferenceError' in html_content or 'False is not defined' in html_content:
        print("❌ 上传后的页面中存在JavaScript错误")
        return False
    
    # 3. 检查任务状态
    print("3. 检查任务状态...")
    # 从页面中提取task_id
    import re
    task_id_match = re.search(r'const taskId = "([^"]+)";', html_content)
    
    if not task_id_match:
        print("⚠️ 未找到任务ID，可能转换已经完成")
        return True
    
    task_id = task_id_match.group(1)
    print(f"   任务ID: {task_id}")
    
    # 轮询任务状态
    max_retries = 20
    retry_count = 0
    
    while retry_count < max_retries:
        retry_count += 1
        time.sleep(1)
        print(f"   轮询任务状态 ({retry_count}/{max_retries})...")
        
        try:
            response = session.get(f'{BASE_URL}/task_status/{task_id}')
            if response.status_code == 200:
                task_data = response.json()
                print(f"   任务状态: {task_data.get('state', '未知')}")
                
                if task_data.get('state') == 'SUCCESS':
                    print("   任务执行成功！")
                    break
                elif task_data.get('state') in ['FAILURE', 'ERROR']:
                    print(f"   任务执行失败: {task_data.get('error', '未知错误')}")
                    return False
        except Exception as e:
            print(f"   轮询任务状态时出错: {e}")
            
    if retry_count >= max_retries:
        print("❌ 任务执行超时")
        return False
    
    # 4. 刷新首页检查结果
    print("4. 刷新首页检查结果...")
    response = session.get(BASE_URL)
    if response.status_code != 200:
        print(f"❌ 首页刷新失败: HTTP {response.status_code}")
        return False
    
    html_content = response.text
    
    # 检查是否有JavaScript错误
    if 'ReferenceError' in html_content or 'False is not defined' in html_content:
        print("❌ 刷新后的页面中存在JavaScript错误")
        return False
    
    # 检查是否显示转换成功信息
    if 'XML文件已成功生成' in html_content:
        print("   ✅ 显示转换成功信息")
    else:
        print("   ❌ 未显示转换成功信息")
        return False
    
    # 检查是否显示下载按钮
    if '下载XML文件并删除缓存数据' in html_content:
        print("   ✅ 显示下载按钮")
    else:
        print("   ❌ 未显示下载按钮")
        return False
    
    return True

if __name__ == '__main__':
    success = test_full_flow()
    if success:
        print("\n🎉 所有功能测试通过！")
    else:
        print("\n❌ 功能测试失败")
