from app import app

# 测试日志记录
app.logger.info('Test log message from test_logger.py')
app.logger.warning('Test warning message from test_logger.py')
app.logger.error('Test error message from test_logger.py')
print('Test logs written to app_20251212.log')
