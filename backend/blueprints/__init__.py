"""
Flask Blueprint 路由模块
"""
from backend.blueprints.health import bp as health_bp
from backend.blueprints.vehicles import bp as vehicles_bp
from backend.blueprints.drivers import bp as drivers_bp
from backend.blueprints.nodes import bp as nodes_bp
from backend.blueprints.edges import bp as edges_bp
from backend.blueprints.monitor import bp as monitor_bp
from backend.blueprints.dispatch import bp as dispatch_bp
from backend.blueprints.map_labels import bp as map_labels_bp
from backend.blueprints.dqn import bp as dqn_bp
from backend.blueprints.travel_time import bp as travel_time_bp
from backend.blueprints.map_import import bp as map_import_bp
from backend.blueprints.system import bp as system_bp

__all__ = [
    'health_bp',
    'vehicles_bp',
    'drivers_bp',
    'nodes_bp',
    'edges_bp',
    'monitor_bp',
    'dispatch_bp',
    'map_labels_bp',
    'dqn_bp',
    'travel_time_bp',
    'map_import_bp',
    'system_bp'
]

