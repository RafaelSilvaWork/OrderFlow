from pathlib import Path

import pytest

from modules.organizador import Organizador, ler_cabecalho_planilha


@pytest.fixture
def setup_dirs(tmp_path):
    propostas = tmp_path / "propostas"
    pedidos = tmp_path / "pedidos"
    destino = tmp_path / "destino"
    propostas.mkdir()
    pedidos.mkdir()
    destino.mkdir()
    return propostas, pedidos, destino


def make_xlsx(path: Path, rows: list, cabecalho: list | None = None):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(cabecalho or ["RC", "PO", "FORNECEDOR"])
    for row in rows:
        ws.append(row)
    wb.save(path)


def test_sanitizar_nome():
    org = Organizador("", "", "", "", "RC", "PO", "FORNECEDOR", lambda m: None)
    # caracteres inválidos viram espaço; espaços duplos são colapsados
    assert org.sanitizar_nome("Forn/Esc:*") == "Forn Esc"
    assert org.sanitizar_nome("  ") == "SEM_NOME"


def test_sanitizar_nome_remove_ponto_final():
    # Windows remove ponto/espaço final de pastas e arquivos ao criá-los -
    # sem isso, o Path usado no código nunca bate com o que existe em disco
    # (ver bug real: cópia falhando com "caminho não encontrado").
    org = Organizador("", "", "", "", "RC", "PO", "FORNECEDOR", lambda m: None)
    assert org.sanitizar_nome("DATAMELO ELETROELETRONICA LTDA .") == "DATAMELO ELETROELETRONICA LTDA"
    assert org.sanitizar_nome("Fornecedor..") == "Fornecedor"
    assert org.sanitizar_nome("Fornecedor . . ") == "Fornecedor"
    assert org.sanitizar_nome("...") == "SEM_NOME"


def test_buscar_arquivo_por_codigo(tmp_path):
    (tmp_path / "123456_proposta.pdf").write_bytes(b"")
    (tmp_path / "outro.pdf").write_bytes(b"")
    org = Organizador("", "", "", "", "RC", "PO", "FORNECEDOR", lambda m: None)
    arquivos = [f for f in tmp_path.rglob("*") if f.is_file()]
    result = org.buscar_arquivo_por_codigo(arquivos, "123456")
    assert len(result) == 1
    assert result[0].name == "123456_proposta.pdf"


def test_executar_copia_arquivos(setup_dirs, tmp_path):
    propostas, pedidos, destino = setup_dirs
    planilha = tmp_path / "plan.xlsx"
    make_xlsx(planilha, [["RC001", "PO001", "Fornecedor A"]])
    (propostas / "RC001_orcamento.pdf").write_bytes(b"pdf")

    logs = []
    org = Organizador(
        propostas=str(propostas),
        pedidos="",
        destino=str(destino),
        planilha=str(planilha),
        col_rc="RC",
        col_po="PO",
        col_fornecedor="FORNECEDOR",
        logger=logs.append,
    )
    org.executar()

    pasta_forn = destino / "Fornecedor A"
    assert pasta_forn.is_dir()
    arquivos = list(pasta_forn.iterdir())
    assert len(arquivos) == 1
    assert "RC001" in arquivos[0].name


def test_ler_cabecalho_planilha_xlsx_retorna_colunas_reais(tmp_path):
    # Cabeçalho com nomes diferentes de RC/PO/FORNECEDOR - a função deve
    # devolver exatamente o que está na planilha, sem tentar adivinhar.
    planilha = tmp_path / "plan.xlsx"
    make_xlsx(planilha, [["1", "2", "3"]], cabecalho=["Requisição", "Pedido Coupa", "Nome Fornecedor"])
    assert ler_cabecalho_planilha(planilha) == ["Requisição", "Pedido Coupa", "Nome Fornecedor"]


def test_ler_cabecalho_planilha_csv_retorna_colunas_reais(tmp_path):
    planilha = tmp_path / "plan.csv"
    planilha.write_text("Requisição;Pedido Coupa;Nome Fornecedor\n1;2;3\n", encoding="utf-8-sig")
    assert ler_cabecalho_planilha(planilha) == ["Requisição", "Pedido Coupa", "Nome Fornecedor"]


def test_ler_cabecalho_planilha_vazia_gera_erro(tmp_path):
    planilha = tmp_path / "vazio.csv"
    planilha.write_text("", encoding="utf-8-sig")
    with pytest.raises(ValueError):
        ler_cabecalho_planilha(planilha)


def test_ler_cabecalho_planilha_formato_invalido_gera_erro(tmp_path):
    planilha = tmp_path / "plan.txt"
    planilha.write_text("RC,PO,FORNECEDOR\n", encoding="utf-8")
    with pytest.raises(ValueError):
        ler_cabecalho_planilha(planilha)
