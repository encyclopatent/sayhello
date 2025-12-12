import json
from flask import Flask, jsonify, session
from app import task_status, clear_task

# 创建一个测试Flask应用
app = Flask(__name__)
app.secret_key = 'test_secret_key'

# 测试正常情况下的JSON响应
@app.route('/test_success')
def test_success():
    return jsonify({'status': 'success', 'message': 'Test message'})

# 测试错误情况下的JSON响应
@app.route('/test_error')
def test_error():
    try:
        # 模拟一个会抛出异常的操作
        1 / 0
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# 启动测试服务器
if __name__ == '__main__':
    print("测试服务器启动在 http://127.0.0.1:5001")
    print("请访问以下URL测试JSON响应:")
    print("1. 正常响应: http://127.0.0.1:5001/test_success")
    print("2. 错误响应: http://127.0.0.1:5001/test_error")
    app.run(debug=False, port=5001)