import sys
import os
from pathlib import Path

import pytest

_real_unlink = os.unlink


def _windows_safe_unlink(path, *args, **kwargs):
    try:
        return _real_unlink(path, *args, **kwargs)
    except PermissionError:
        return None


os.unlink = _windows_safe_unlink


def warp_to(direct_vm, iso: str) -> None:
    direct_vm.warp(iso)
    gl = sys.modules.get("genlayer.gl")
    if gl is None:
        return
    raw = getattr(gl, "message_raw", None)
    if isinstance(raw, dict):
        raw["datetime"] = iso
    nested = getattr(getattr(gl, "message", None), "raw", None)
    if isinstance(nested, dict):
        nested["datetime"] = iso


def _find_contract_file() -> str:
    """Locates AuthorshipRegistry.py relative to this conftest.py, independent of whichever
    repo layout it ends up living in."""
    here = Path(__file__).resolve().parent

    candidates = [
        here.parent.parent / "contracts" / "AuthorshipRegistry.py",
        here / "AuthorshipRegistry.py",
        here.parent / "AuthorshipRegistry.py",
        here.parent / "contracts" / "AuthorshipRegistry.py",
        here.parent.parent / "AuthorshipRegistry.py",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)

    root = here
    for _ in range(5):
        if root.parent == root:
            break
        root = root.parent
    matches = list(root.rglob("AuthorshipRegistry.py"))
    if matches:
        return str(matches[0])

    raise FileNotFoundError(
        "Could not locate AuthorshipRegistry.py near conftest.py at "
        f"{here} -- checked {[str(c) for c in candidates]} and searched under {root}."
    )


_CONTRACT_PATH = _find_contract_file()


@pytest.fixture
def contract(direct_deploy, direct_vm, direct_alice):
    direct_vm.sender = direct_alice
    deployed = direct_deploy(_CONTRACT_PATH)
    direct_vm.sender = direct_alice
    return deployed
