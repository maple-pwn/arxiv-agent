"""配置模块测试"""

import os
import pytest
import tempfile
import yaml


class TestEnvVarResolution:
    """环境变量解析测试"""

    def test_resolve_env_var_with_braces(self):
        from src.config import _resolve_env_vars

        os.environ["TEST_API_KEY"] = "test-key-123"
        result = _resolve_env_vars("${TEST_API_KEY}")
        assert result == "test-key-123"
        del os.environ["TEST_API_KEY"]

    def test_resolve_env_var_without_braces(self):
        from src.config import _resolve_env_vars

        os.environ["TEST_VAR"] = "value"
        result = _resolve_env_vars("$TEST_VAR")
        assert result == "value"
        del os.environ["TEST_VAR"]

    def test_unset_env_var_keeps_original(self):
        from src.config import _resolve_env_vars

        result = _resolve_env_vars("${UNDEFINED_VAR}")
        assert result == "${UNDEFINED_VAR}"

    def test_non_string_passthrough(self):
        from src.config import _resolve_env_vars

        assert _resolve_env_vars(123) == 123
        assert _resolve_env_vars(True) is True


class TestConfigManager:
    """ConfigManager 测试"""

    def test_load_default_config_when_file_missing(self):
        from src.config import ConfigManager

        manager = ConfigManager("nonexistent.yaml")
        assert "arxiv" in manager.config
        assert "logging" in manager.config

    def test_get_nested_config(self):
        from src.config import ConfigManager

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"arxiv": {"max_results": 100}}, f)
            f.flush()
            manager = ConfigManager(f.name)
            assert manager.get("arxiv.max_results") == 100
            os.unlink(f.name)

    def test_env_var_override(self):
        from src.config import ConfigManager

        os.environ["ARXIV_OPENAI_API_KEY"] = "env-api-key"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"ai": {"openai": {"api_key": "file-key"}}}, f)
            f.flush()
            manager = ConfigManager(f.name)
            assert manager.get("ai.openai.api_key") == "env-api-key"
            os.unlink(f.name)

        del os.environ["ARXIV_OPENAI_API_KEY"]

    def test_set_and_get(self):
        from src.config import ConfigManager

        manager = ConfigManager("nonexistent.yaml")
        manager.set("custom.key", "value")
        assert manager.get("custom.key") == "value"


class TestConfigValidation:
    """配置验证测试"""

    def test_invalid_max_results_uses_default(self):
        from src.config import ConfigManager

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"arxiv": {"max_results": -1}}, f)
            f.flush()
            manager = ConfigManager(f.name)
            assert manager.get("arxiv.max_results") == 50
            os.unlink(f.name)

    def test_invalid_sort_by_uses_default(self):
        from src.config import ConfigManager

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"arxiv": {"sort_by": "invalid"}}, f)
            f.flush()
            manager = ConfigManager(f.name)
            assert manager.get("arxiv.sort_by") == "submittedDate"
            os.unlink(f.name)
