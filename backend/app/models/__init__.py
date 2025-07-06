# Re-export auth and database models
from .auth import *
from .database import *

# Import the legacy models from parent module
import importlib.util
import os
import sys

# Add parent directory to path temporarily
parent_dir = os.path.dirname(os.path.dirname(__file__))
models_path = os.path.join(parent_dir, 'models.py')

if os.path.exists(models_path):
    spec = importlib.util.spec_from_file_location("legacy_models", models_path)
    legacy_models = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy_models)
    
    # Re-export the needed models
    ChatMessage = legacy_models.ChatMessage
    User = legacy_models.User
    
    __all__ = ['ChatMessage', 'User']