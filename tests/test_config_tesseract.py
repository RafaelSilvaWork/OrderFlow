import sys

from modules.config import resolve_tesseract_executable


def test_resolve_tesseract_executable_retorna_none_fora_do_executavel_empacotado(monkeypatch):
    monkeypatch.setattr(sys, "frozen", False, raising=False)

    assert resolve_tesseract_executable() is None


def test_resolve_tesseract_executable_encontra_bundle_junto_do_exe(tmp_path, monkeypatch):
    exe_dir = tmp_path
    tesseract_dir = exe_dir / "_internal" / "tesseract"
    tesseract_dir.mkdir(parents=True)
    tesseract_exe = tesseract_dir / "tesseract.exe"
    tesseract_exe.write_text("")

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe_dir / "CoupaFramework.exe"))

    assert resolve_tesseract_executable() == str(tesseract_exe)


def test_resolve_tesseract_executable_retorna_none_quando_bundle_nao_existe(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "CoupaFramework.exe"))

    assert resolve_tesseract_executable() is None
