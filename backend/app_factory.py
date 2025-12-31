"""
Flask 应用工厂
"""
from flask import Flask, send_from_directory
from flask_cors import CORS
from backend.config import Config
from backend.utils.logger import setup_logger

def create_app():
    """创建并配置 Flask 应用"""
    app = Flask(__name__)
    CORS(app)
    
    # 配置日志
    setup_logger()
    
    # 注册 Blueprint
    from backend.blueprints import health
    app.register_blueprint(health.bp)
    
    # 其他 Blueprint 将在后续步骤中添加
    # from backend.blueprints import vehicles, drivers, nodes, edges
    # from backend.blueprints import monitor, dqn, travel_time, dispatch, map_import
    # app.register_blueprint(vehicles.bp)
    # ... 其他 Blueprint
    
    # 静态文件路由
    @app.route('/')
    def serve_index():
        return send_from_directory('.', 'traffic_system.html')
    
    @app.route('/driver')
    def serve_driver():
        return send_from_directory('.', 'driver.html')
    
    @app.route('/<path:filename>')
    def serve_static(filename):
        return send_from_directory('.', filename)
    
    return app

