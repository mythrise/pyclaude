"""工作目录管理"""
import os

_current_cwd: str = os.getcwd()


def get_cwd() -> str:
    return _current_cwd


def set_cwd(path: str) -> None:
    global _current_cwd
    _current_cwd = os.path.abspath(path)
