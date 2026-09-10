from pathlib import Path

INSTALLER = Path(__file__).resolve().parents[1] / "installer.iss"


def test_installer_migra_dados_antes_de_limpar_internal():
    script = INSTALLER.read_text(encoding="utf-8")

    assert "function PrepareToInstall" in script
    for nome in (
        "coupa_profiles.json",
        "coupa_profiles.salt",
        "coupa_fw.secret",
        "coupa_instance.json",
        "coupa_power_automate.json",
    ):
        assert f"PreserveLegacyUserFile('{nome}')" in script
    assert "{userappdata}\\{#MyAppDirName}" in script


def test_limpeza_de_atualizacao_restringe_se_a_binarios_internal():
    script = INSTALLER.read_text(encoding="utf-8")
    install_delete = script.split("\n[InstallDelete]\n", 1)[1].split("\n[Files]\n", 1)[0]

    assert 'Name: "{app}\\_internal"' in install_delete
    assert "{userappdata}" not in install_delete
