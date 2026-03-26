"""
Core functionality package
"""

from .context_manager import ContextManager
from .notification import ProactiveNotifier
from .local_server import start_local_server
__all__ = [
    'ContextManager',
    'ProactiveNotifier',
    'start_local_server'
]