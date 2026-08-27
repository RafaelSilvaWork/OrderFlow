import fitz

from modules.config import PALAVRAS_CHAVE
from modules.download_scraper import DownloadScraper


def _criar_pdf_sem_texto(caminho: str) -> None:
    """Gera um PDF de 1 página em branco - sem camada de texto embutida,
    simulando um PDF escaneado/imagem para os testes de OCR."""
    doc = fitz.open()
    doc.new_page()
    doc.save(caminho)
    doc.close()


def test_construtor_deduplica_requisicoes_preservando_ordem():
    """Uma requisição com 2 pedidos aparece 2x na lista importada da Aba 1 -
    o download é por requisição, então nunca deve processar a mesma 2x."""
    scraper = DownloadScraper(requisicoes=["100", "200", "100", "300", "200"], pasta_download=".")

    assert scraper.requisicoes == ["100", "200", "300"]


def test_construtor_ignora_espacos_e_strings_vazias():
    scraper = DownloadScraper(requisicoes=["  100  ", "100", "", "   ", "200"], pasta_download=".")

    assert scraper.requisicoes == ["100", "200"]


def test_analisar_arquivo_rejeita_de_acordo(tmp_path):
    """Arquivo cujo nome contém 'de acordo' deve ser rejeitado."""
    scraper = DownloadScraper(requisicoes=[], pasta_download=str(tmp_path))
    arquivo = tmp_path / 'de acordo.txt'
    arquivo.write_text('Orçamento conforme', encoding='utf-8')

    ok, result = scraper.analisar_arquivo(str(arquivo), '123', 'de acordo')

    assert ok is False
    assert result == 'nome'


def test_analisar_arquivo_aceita_orcamento_de_assistencia_tecnica_sem_a_palavra_orcamento(tmp_path):
    """Orçamentos de assistência técnica (O.S./O.C.) não usam nenhuma das
    palavras-chave "clássicas" (orçamento, proposta, cotação...), mas sempre
    trazem uma linha-resumo "Valor total: R$ X" - visto em amostras reais."""
    scraper = DownloadScraper(requisicoes=[], pasta_download=str(tmp_path))
    arquivo = tmp_path / 'os_7528.txt'
    arquivo.write_text(
        'O.S. 7528/26\nEletrocardiógrafo R$ 4.450,00\n'
        'Valor total: R$ 4.450,00 (Quatro mil quatrocentos e cinquenta reais)\n'
        'Entrega: 15 dias úteis após aprovação\nPagamento: 28 dias\n'
        'Garantia dos serviços executados: 90 dias',
        encoding='utf-8',
    )

    ok, result = scraper.analisar_arquivo(str(arquivo), '123', 'os_7528.txt')

    assert ok is True
    assert result is not None


def test_extrair_valor_total_encontra_o_valor():
    scraper = DownloadScraper(requisicoes=[], pasta_download='.')
    texto = scraper.normalizar_texto(
        'valor total: r$ 4.450,00 (quatro mil quatrocentos e cinquenta reais)'
    )

    assert scraper.extrair_valor_total(texto) == 4450.00


def test_extrair_valor_total_none_quando_nao_encontra():
    scraper = DownloadScraper(requisicoes=[], pasta_download='.')

    assert scraper.extrair_valor_total('nenhum valor aqui') is None


def test_manter_apenas_melhor_candidato_desempata_por_menor_valor_mesma_prioridade(tmp_path):
    """RC com valor antigo E valor novo negociado anexados, ambos só batendo
    em "valor total" (mesma prioridade) - negociação normalmente reduz o
    preço, então mantemos o de MENOR valor."""
    scraper = DownloadScraper(requisicoes=[], pasta_download=str(tmp_path))
    logs = []
    scraper._log_callback = logs.append

    caro = tmp_path / "111.txt"
    caro.write_text("Valor total: R$ 5.000,00 (cinco mil reais)", encoding="utf-8")
    barato = tmp_path / "111_1.txt"
    barato.write_text("Valor total: R$ 3.500,00 (tres mil e quinhentos reais)", encoding="utf-8")
    scraper.arquivos_salvos_na_execucao = [str(caro), str(barato)]

    scraper._manter_apenas_melhor_candidato([str(caro), str(barato)], "111")

    assert scraper.arquivos_salvos_na_execucao == [str(barato)]
    assert barato.exists()
    assert not caro.exists()
    assert any("menor valor" in msg for msg in logs)


def test_manter_apenas_melhor_candidato_sem_valor_extraivel_mantem_o_primeiro_da_mesma_prioridade(tmp_path):
    """Mesma prioridade ("orçamento" nos dois) e nenhum valor extraível -
    mantém o primeiro, sem quebrar."""
    scraper = DownloadScraper(requisicoes=[], pasta_download=str(tmp_path))
    logs = []
    scraper._log_callback = logs.append

    primeiro = tmp_path / "111.txt"
    primeiro.write_text("Orçamento sem valor legível aqui", encoding="utf-8")
    segundo = tmp_path / "111_1.txt"
    segundo.write_text("Orçamento também sem valor legível", encoding="utf-8")
    scraper.arquivos_salvos_na_execucao = [str(primeiro), str(segundo)]

    scraper._manter_apenas_melhor_candidato([str(primeiro), str(segundo)], "111")

    assert scraper.arquivos_salvos_na_execucao == [str(primeiro)]
    assert primeiro.exists()
    assert not segundo.exists()
    assert any("não foi possível extrair o valor" in msg for msg in logs)


def test_manter_apenas_melhor_candidato_prioridade_de_palavra_vence_mesmo_com_valor_maior(tmp_path):
    """"Orçamento" tem prioridade maior que "valor total" (ver PALAVRAS_CHAVE
    em config.py) - o candidato batido em "orçamento" deve vencer mesmo tendo
    preço maior que o batido só em "valor total"."""
    scraper = DownloadScraper(requisicoes=[], pasta_download=str(tmp_path))
    logs = []
    scraper._log_callback = logs.append

    prioritario = tmp_path / "111.txt"
    prioritario.write_text("Orçamento Nº 55\nValor total: R$ 9.000,00 (nove mil reais)", encoding="utf-8")
    generico_mais_barato = tmp_path / "111_1.txt"
    generico_mais_barato.write_text(
        "Documento de assistência técnica\nValor total: R$ 100,00 (cem reais)", encoding="utf-8"
    )
    scraper.arquivos_salvos_na_execucao = [str(prioritario), str(generico_mais_barato)]

    scraper._manter_apenas_melhor_candidato([str(prioritario), str(generico_mais_barato)], "111")

    assert scraper.arquivos_salvos_na_execucao == [str(prioritario)]
    assert prioritario.exists()
    assert not generico_mais_barato.exists()
    assert any("prioridade" in msg for msg in logs)


def test_prioridade_palavra_chave_respeita_ordem_de_config(tmp_path):
    """"budget" é a última palavra da lista (prioridade mais baixa) - qualquer
    palavra em português listada antes dela deve vencer."""
    scraper = DownloadScraper(requisicoes=[], pasta_download=str(tmp_path))

    assert scraper._prioridade_palavra_chave("este e o budget do projeto") > (
        scraper._prioridade_palavra_chave("segue a cotacao solicitada")
    )
    assert scraper._prioridade_palavra_chave("texto sem nenhuma palavra chave") == len(PALAVRAS_CHAVE)


def test_analisar_arquivo_sem_palavra_chave(tmp_path):
    """Arquivo sem palavra-chave no texto nem no nome deve ser rejeitado."""
    scraper = DownloadScraper(requisicoes=[], pasta_download=str(tmp_path))
    arquivo = tmp_path / 'sample.txt'
    arquivo.write_text('Texto qualquer sem palavra chave', encoding='utf-8')

    ok, result = scraper.analisar_arquivo(str(arquivo), '123', 'sample')

    assert ok is False
    assert result == 'palavra'


def test_extrair_texto_pdf_sem_texto_tenta_ocr(tmp_path, monkeypatch):
    """PDF sem camada de texto (escaneado/imagem) deve cair no fallback de OCR."""
    scraper = DownloadScraper(requisicoes=[], pasta_download=str(tmp_path))
    caminho = tmp_path / "scan.pdf"
    _criar_pdf_sem_texto(str(caminho))
    monkeypatch.setattr(scraper, "_ocr_pdf", lambda caminho_arquivo: "Orçamento Nº 123")

    texto = scraper.extrair_texto(str(caminho))

    assert texto == "orçamento nº 123"


def test_ocr_pdf_retorna_vazio_quando_pacote_nao_instalado(tmp_path, monkeypatch):
    scraper = DownloadScraper(requisicoes=[], pasta_download=str(tmp_path))
    monkeypatch.setattr("modules.download_scraper.pytesseract", None)
    monkeypatch.setattr("modules.download_scraper.Image", None)

    assert scraper._ocr_pdf(str(tmp_path / "qualquer.pdf")) == ""


def test_ocr_pdf_retorna_vazio_quando_tesseract_nao_encontrado(tmp_path, monkeypatch):
    scraper = DownloadScraper(requisicoes=[], pasta_download=str(tmp_path))
    caminho = tmp_path / "scan.pdf"
    _criar_pdf_sem_texto(str(caminho))

    class _FakeTesseractModule:
        class TesseractNotFoundError(Exception):
            pass

        @staticmethod
        def image_to_string(*args, **kwargs):
            raise _FakeTesseractModule.TesseractNotFoundError()

    monkeypatch.setattr("modules.download_scraper.pytesseract", _FakeTesseractModule)

    assert scraper._ocr_pdf(str(caminho)) == ""


def test_ocr_pdf_concatena_texto_de_todas_as_paginas(tmp_path, monkeypatch):
    scraper = DownloadScraper(requisicoes=[], pasta_download=str(tmp_path))
    caminho = tmp_path / "scan.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.new_page()
    doc.save(str(caminho))
    doc.close()

    textos_por_pagina = iter(["Página 1", "Página 2"])

    class _FakeTesseractModule:
        class TesseractNotFoundError(Exception):
            pass

        @staticmethod
        def image_to_string(*args, **kwargs):
            return next(textos_por_pagina)

    monkeypatch.setattr("modules.download_scraper.pytesseract", _FakeTesseractModule)

    assert scraper._ocr_pdf(str(caminho)) == "Página 1\nPágina 2"
