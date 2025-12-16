# app.py
from flask import Flask
import os
import sys
import importlib
import config # 导入配置
from utils import logger

app = Flask(__name__)

def register_blueprints(app):
    """自动扫描 modules 目录并注册所有蓝图"""
    modules_dir = os.path.join(os.path.dirname(__file__), 'modules')
    if modules_dir not in sys.path:
        sys.path.append(modules_dir)

    logger.info(f"开始扫描模块目录: {modules_dir}")

    if not os.path.exists(modules_dir):
        return

    for filename in os.listdir(modules_dir):
        if filename.endswith('.py') and filename != '__init__.py':
            module_name = filename[:-3]
            try:
                module = importlib.import_module(f"modules.{module_name}")
                if hasattr(module, 'bp'):
                    app.register_blueprint(module.bp)
                    logger.info(f"✅ 成功加载模块: {module_name}")
            except Exception as e:
                logger.error(f"❌ 加载模块 {module_name} 失败: {e}")

if __name__ == '__main__':
    register_blueprints(app)
    logger.info(f"服务启动，监听端口 {config.PORT}")
    app.run(host='0.0.0.0', port=config.PORT)
