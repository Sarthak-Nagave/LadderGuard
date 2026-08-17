import json
import logging
import sys
import shutil
from pathlib import Path
from typing import Any
import jsonschema

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Centralized Configuration Manager for the Ladder Release Validator.
    This is the ONLY class allowed to read JSON configuration files directly.
    """
    _instance = None
    
    if getattr(sys, 'frozen', False):
        _base_dir: Path = Path(sys.executable).parent
    else:
        _base_dir: Path = Path(__file__).resolve().parent.parent
        
    _config_dir: Path = _base_dir / "config"

    @classmethod
    def get_base_dir(cls) -> Path:
        """Returns the absolute base directory of the application."""
        return cls._base_dir

        
    _cache: dict[str, dict] = {}
    
    # Core files
    CONFIG_FILE = "config.json"
    SIGNATURES_FILE = "signatures.json"
    USER_SETTINGS_FILE = "user_settings.json"
    DEFAULTS_FILE = "defaults.json"
    SCHEMA_FILE = "schema.json"

    @classmethod
    def load(cls) -> None:
        """Loads and caches configuration strictly once at startup."""
        if not cls._config_dir.exists():
            cls._config_dir.mkdir(parents=True)
            
        cls._cache.clear()
        cls._load_file("config", cls.CONFIG_FILE)
        cls._load_file("signatures", cls.SIGNATURES_FILE)
        cls._load_file("user_settings", cls.USER_SETTINGS_FILE)
        
    @classmethod
    def reload(cls) -> None:
        """Reloads configuration from disk."""
        cls.load()

    @classmethod
    def _load_file(cls, key: str, filename: str) -> None:
        file_path = cls._config_dir / filename
        
        if not file_path.exists():
            logger.warning(f"Configuration file missing: {filename}. Attempting to restore from defaults.")
            cls._restore_from_defaults(key, file_path)

        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if cls._validate(key, data):
                cls._cache[key] = data
            else:
                logger.error(f"Validation failed for {filename}. Restoring defaults.")
                cls._restore_from_defaults(key, file_path)
                with file_path.open("r", encoding="utf-8") as f:
                    cls._cache[key] = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Error reading {filename}: {e}. Restoring defaults.")
            cls._restore_from_defaults(key, file_path)
            with file_path.open("r", encoding="utf-8") as f:
                cls._cache[key] = json.load(f)

    @classmethod
    def _restore_from_defaults(cls, key: str, target_path: Path) -> None:
        defaults_path = cls._config_dir / cls.DEFAULTS_FILE
        if not defaults_path.exists():
            logger.critical("defaults.json is missing! Cannot restore configuration safely.")
            cls._cache[key] = {}
            return
            
        try:
            with defaults_path.open("r", encoding="utf-8") as f:
                defaults_data = json.load(f)
                
            if key in defaults_data:
                with target_path.open("w", encoding="utf-8") as tf:
                    json.dump(defaults_data[key], tf, indent=2)
                logger.info(f"Successfully restored {target_path.name} from defaults.")
            else:
                logger.error(f"No default section found for '{key}' in defaults.json.")
                cls._cache[key] = {}
        except Exception as e:
            logger.critical(f"Failed to restore {target_path.name} from defaults: {e}")
            cls._cache[key] = {}

    @classmethod
    def _validate(cls, key: str, data: dict) -> bool:
        """
        Validates the configuration using jsonschema.
        """
        schema_path = cls._config_dir / cls.SCHEMA_FILE
        if not schema_path.exists():
            return True
            
        try:
            with schema_path.open("r", encoding="utf-8") as f:
                schemas = json.load(f)
                
            if key not in schemas:
                return True # No schema for this key
                
            jsonschema.validate(instance=data, schema=schemas[key])
            return True
        except jsonschema.exceptions.ValidationError as e:
            logger.error(f"Validation failed for {key}: {e.message}")
            return False
        except Exception as e:
            logger.error(f"Error validating {key}: {e}")
            return True

    @classmethod
    def get(cls, path: str, default: Any = None) -> Any:
        """
        Retrieve a configuration value using dot notation (e.g. 'config.app.name').
        If no prefix is provided (e.g. 'app.name'), it defaults to looking in 'config'.
        """
        if not cls._cache:
            cls.load()
            
        parts = path.split('.')
        # If the first part isn't a known top-level key, assume 'config'
        if parts[0] not in ["config", "signatures", "user_settings"]:
            parts.insert(0, "config")
            
        current = cls._cache
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        return current

    @classmethod
    def save(cls, key: str) -> None:
        """Saves a cached configuration dict back to its file."""
        if key not in cls._cache:
            return
            
        filename = {
            "config": cls.CONFIG_FILE,
            "signatures": cls.SIGNATURES_FILE,
            "user_settings": cls.USER_SETTINGS_FILE
        }.get(key)
        
        if not filename:
            return
            
        file_path = cls._config_dir / filename
        try:
            with file_path.open("w", encoding="utf-8") as f:
                json.dump(cls._cache[key], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save {filename}: {e}")

    @classmethod
    def reset(cls) -> None:
        """Resets all configuration to defaults."""
        cls._restore_from_defaults("config", cls._config_dir / cls.CONFIG_FILE)
        cls._restore_from_defaults("signatures", cls._config_dir / cls.SIGNATURES_FILE)
        cls._restore_from_defaults("user_settings", cls._config_dir / cls.USER_SETTINGS_FILE)
        cls.load()


