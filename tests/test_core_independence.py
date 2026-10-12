"""Regressão arquitetural: o núcleo não pode exigir o MJ nem o backend antigo."""

import subprocess
import sys


def test_core_imports_without_mj_or_backend_packages():
    script = r"""
import importlib.abc
import sys

class BlockLegacyLayers(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "integrations" or fullname.startswith("integrations."):
            raise ModuleNotFoundError("MJ/integrations are intentionally absent")
        if fullname == "backend" or fullname.startswith("backend."):
            raise ModuleNotFoundError("backend is intentionally absent")
        return None

sys.meta_path.insert(0, BlockLegacyLayers())
import rule_engine
import orchestrator
from rule_engine import build_default_engine
from orchestrator import OrquestradorAcoes

engine = build_default_engine()
OrquestradorAcoes(engine)
print("core-import-ok")
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "core-import-ok" in result.stdout
