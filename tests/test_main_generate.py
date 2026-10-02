"""Geração do dia: arquivo único do infográfico, nomes com hash e fallback."""
import json

import pytest
from PIL import Image

import main
import render
from conftest import DIA, pauta


@pytest.fixture
def saida(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "OUT", tmp_path / "out")
    monkeypatch.setattr(main, "MANIFEST", tmp_path / "out" / "manifest.json")
    return tmp_path / "out"


def test_infografico_e_desenhado_uma_vez_e_compartilhado_pelas_redes(conteudo, saida):
    conteudo[1]("servico", pauta())
    m = main.generate("servico", ["linkedin", "facebook", "instagram"])
    arquivos = {tuple(d["files"]) for d in m["networks"].values()}
    assert len(arquivos) == 1                       # as três redes usam o mesmo arquivo
    (rel,) = next(iter(arquivos))
    assert rel.startswith(f"posts/{DIA.isoformat()}/servico/servico-") and rel.endswith(".png")
    assert Image.open(saida / rel).size == (1080, 1350)
    assert len(list(saida.rglob("*.png"))) == 1     # e só um PNG foi gravado
    assert json.loads((saida / "manifest.json").read_text())["networks"].keys() == m["networks"].keys()


def test_nome_da_imagem_muda_quando_a_imagem_muda(conteudo, saida):
    conteudo[1]("servico", pauta())
    nome1 = main.generate("servico", ["facebook"])["networks"]["facebook"]["files"][0]
    conteudo[1]("servico", pauta(infografico={**pauta()["infografico"], "titulo_destaque": "outro texto."}))
    nome2 = main.generate("servico", ["facebook"])["networks"]["facebook"]["files"][0]
    assert nome1 != nome2                           # URL nova: o CDN não entrega a imagem antiga
    conteudo[1]("servico", pauta(infografico={**pauta()["infografico"], "titulo_destaque": "outro texto."}))
    assert main.generate("servico", ["facebook"])["networks"]["facebook"]["files"][0] == nome2  # mesmo conteúdo, mesmo nome


def test_story_continua_na_arte_propria_e_nao_usa_o_infografico(conteudo, saida):
    conteudo[1]("hacker", pauta())
    m = main.generate("hacker", ["facebook", "instagram_stories"])
    story = m["networks"]["instagram_stories"]["files"][0]
    assert "instagram_stories" in story and Image.open(saida / story).size == (1080, 1920)
    assert story != m["networks"]["facebook"]["files"][0]


def test_so_story_pendente_nao_desenha_infografico(conteudo, saida):
    conteudo[1]("hacker", pauta())
    m = main.generate("hacker", ["instagram_stories"])
    assert list(m["networks"]) == ["instagram_stories"]
    assert len(list(saida.rglob("*.png"))) == 1


def test_falha_no_desenho_cai_na_arte_antiga_sem_perder_o_horario(conteudo, saida, monkeypatch):
    conteudo[1]("servico", pauta())

    def quebra(*a, **k):
        raise RuntimeError("fonte corrompida")

    monkeypatch.setattr(render.infografico, "renderizar", quebra)
    m = main.generate("servico", ["linkedin", "facebook", "instagram"])
    assert len(m["networks"]["instagram"]["files"]) == 4      # carrossel antigo
    assert len(m["networks"]["linkedin"]["files"]) == 1
    for d in m["networks"].values():
        assert d["caption"] and all((saida / f).exists() for f in d["files"])


def test_post_sem_bloco_usa_a_arte_antiga_por_rede(conteudo, saida):
    d = pauta()
    del d["infografico"]
    conteudo[1]("servico", d)
    m = main.generate("servico", ["linkedin", "facebook"])
    assert m["networks"]["linkedin"]["files"] != m["networks"]["facebook"]["files"]
    assert Image.open(saida / m["networks"]["linkedin"]["files"][0]).size == (1200, 1200)
    assert Image.open(saida / m["networks"]["facebook"]["files"][0]).size == (1200, 1500)


def test_com_hash_renomeia_pelo_conteudo(tmp_path):
    a = tmp_path / "arte.png"
    a.write_bytes(b"conteudo-1")
    novo = main._com_hash(a)
    assert not a.exists() and novo.name.startswith("arte-") and novo.suffix == ".png" and len(novo.stem) == len("arte-") + 8
