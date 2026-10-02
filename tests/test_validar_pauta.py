import json

import pytest

import validar_pauta
from conftest import DIA, bloco_infografico, pauta


def tudo_certo(escrever):
    hacker = bloco_infografico(cena="painel", terminal=[["$ ", "x", "cmd"]])
    del hacker["cena_composta"]
    escrever("noticias", pauta(infografico=bloco_infografico(cena_composta={"fundo": "cidade", "elementos": ["chip"], "legenda": "A"})))
    escrever("hacker", pauta(infografico=hacker))
    escrever("dica", pauta(infografico=bloco_infografico(cena_composta={"fundo": "laboratorio", "elementos": ["notebook", "escudo"], "legenda": "B"})))
    escrever("servico", pauta(infografico=bloco_infografico(cena_composta={"fundo": "datacenter", "elementos": ["rack", "nuvem"], "legenda": "C"})))


def rodar(conteudo):
    return validar_pauta.verificar(DIA, conteudo[0].parent.parent / "diario")


def test_pauta_completa_e_sem_problemas(conteudo):
    tudo_certo(conteudo[1])
    assert rodar(conteudo) == ([], [])


def test_arquivo_ausente_e_aviso_e_nao_problema(conteudo):
    conteudo[1]("noticias", pauta())
    problemas, avisos = rodar(conteudo)
    assert problemas == [] and any("hacker: sem arquivo" in a for a in avisos)


def test_json_quebrado_e_pauta_incompleta_sao_problemas(conteudo):
    tudo_certo(conteudo[1])
    conteudo[1]("dica", "{quebrado")
    conteudo[1]("servico", json.dumps({"titulo": "x", "pontos": ["só um"]}))
    problemas, _ = rodar(conteudo)
    assert sum("arquivo inválido" in p for p in problemas) == 2


def test_bloco_que_perderia_a_arte_nova_e_problema(conteudo):
    tudo_certo(conteudo[1])
    sem_bloco = pauta()
    del sem_bloco["infografico"]
    conteudo[1]("dica", sem_bloco)
    conteudo[1]("servico", pauta(infografico={"titulo_branco": "sem lições"}))
    problemas, _ = rodar(conteudo)
    assert any(p.startswith("dica: sem bloco infografico") for p in problemas)
    assert any(p.startswith("servico: bloco infografico inválido") for p in problemas)


def test_avisos_de_tamanho_e_de_cena_repetida(conteudo):
    tudo_certo(conteudo[1])
    longo = bloco_infografico(historia="x " * 150, cena_composta={"fundo": "cidade", "elementos": ["chip"], "legenda": "A"})
    conteudo[1]("servico", pauta(infografico=longo))
    _, avisos = rodar(conteudo)
    assert any("infografico.historia" in a and "recomendado até 230" in a for a in avisos)
    assert any(a.startswith("cena repetida entre noticias, servico") for a in avisos)


def test_elemento_invalido_vira_aviso(conteudo):
    tudo_certo(conteudo[1])
    cc = {"fundo": "cidade", "elementos": ["chip", "dinossauro"], "legenda": "A"}
    conteudo[1]("dica", pauta(infografico=bloco_infografico(cena_composta=cc)))
    _, avisos = rodar(conteudo)
    assert any("elementos de cena inválidos" in a for a in avisos)


def test_hacker_sem_painel_gera_aviso(conteudo):
    tudo_certo(conteudo[1])
    conteudo[1]("hacker", pauta())
    _, avisos = rodar(conteudo)
    assert any(a.startswith("hacker: sem 'cena': 'painel'") for a in avisos)


def test_cli_codigo_de_saida(conteudo, capsys, monkeypatch):
    tudo_certo(conteudo[1])
    monkeypatch.setattr(validar_pauta.content, "CONTENT_DIR", conteudo[0].parent.parent)
    assert validar_pauta.main([DIA.isoformat()]) == 0
    assert "ok" in capsys.readouterr().out
    conteudo[1]("dica", "{quebrado")
    assert validar_pauta.main([DIA.isoformat()]) == 1
    assert "PROBLEMA" in capsys.readouterr().out


@pytest.mark.parametrize("dia", ["2026-10-02"])
def test_pauta_real_de_hoje_passa(dia, monkeypatch):
    import datetime as dt
    problemas, _ = validar_pauta.verificar(dt.date.fromisoformat(dia))
    assert problemas == []
