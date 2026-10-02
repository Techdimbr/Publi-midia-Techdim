import pytest

from seguranca import redigir
from texto import cortar, uma_linha


def test_uma_linha_junta_espacos_e_ignora_nao_texto():
    assert uma_linha("  a \n b\t c ") == "a b c"
    assert uma_linha(None) == ""
    assert uma_linha(123) == ""


def test_cortar_respeita_palavra_inteira_e_poe_reticencias():
    assert cortar("curto", 20) == "curto"
    saida = cortar("um texto bem comprido para cortar", 15)
    assert saida.endswith("…") and len(saida) <= 15
    assert " " not in saida[-2:]  # não corta no meio de palavra


@pytest.mark.parametrize(
    "segredo",
    [
        "EAAGm0PX4ZCpsBO" + "A" * 40,                    # token da Meta
        "AQV" + "x" * 60,                                # token do LinkedIn
        "WPL_AP1.abcDEF123.xyz==",                       # client secret do LinkedIn
        "sk-ant-api03-" + "a" * 30,                      # chave da Anthropic
        "ghp_" + "a" * 36,                               # token do GitHub
        "github_pat_" + "a" * 40,
    ],
)
def test_redigir_remove_credenciais(segredo):
    saida = redigir(f"antes {segredo} depois")
    assert segredo not in saida
    assert "[REDIGIDO]" in saida
    assert saida.startswith("antes ") and saida.endswith(" depois")


def test_redigir_nao_mexe_em_texto_comum():
    texto = "AQUILO é um texto normal, com https://www.techdim.com.br e #hashtags — 2026-10-02"
    assert redigir(texto) == texto
    assert redigir(None) == ""
