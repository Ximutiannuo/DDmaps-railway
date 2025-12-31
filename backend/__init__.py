"""
后端应用模块
"""
from backend.app_factory import create_app
from backend.models.system_state import system_state
from backend.config import Config

__all__ = ['create_app', 'system_state', 'Config']

