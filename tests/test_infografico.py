"""Validação do bloco "infografico" e desenho do PNG."""
import copy

import pytest
from PIL import Image

import infografico
from conftest import bloco_infografico
from infografico import InfograficoInvalido, validar


def test_sem_bloco_devolve_none_e_usa_arte_antiga():
    assert validar(None, "servico") is None


def test_bloco_valido_e_normalizado():
    p = validar(bloco_infografico(), "servico")
    assert p["cena"] == "composta"
    assert p["cena_composta"]["fundo"] == "datacenter"
    assert p["cena_composta"]["elementos"] == ["rack", "nuvem"]
    assert len(p["licoes"]) == 3 and all(len(par) == 2 for par in p["licoes"])
    assert p["cor"] == infografico.COR_PADRAO["servico"]
    assert p["hashtags"][0] == "#Backup"


def test_validar_e_idempotente():
    primeira = validar(bloco_infografico(), "hacker")
    assert validar(copy.deepcopy(primeira), "hacker") == primeira


@pytest.mark.parametrize("ruim", ["texto", 3, [], ["a"]])
def test_bloco_que_nao_e_objeto_e_recusado(ruim):
    with pytest.raises(InfograficoInvalido):
        validar(ruim, "servico")


def test_sem_titulo_ou_sem_licoes_e_recusado():
    with pytest.raises(InfograficoInvalido, match="titulo"):
        validar(bloco_infografico(titulo_branco="", titulo_destaque=""), "servico")
    with pytest.raises(InfograficoInvalido, match="licoes"):
        validar(bloco_infografico(licoes=[]), "servico")
    with pytest.raises(InfograficoInvalido, match="licoes"):
        validar(bloco_infografico(licoes=[["só título"], "x", 3]), "servico")


def test_textos_longos_sao_cortados_com_reticencias():
    longo = "palavra " * 200
    p = validar(bloco_infografico(historia=longo, pergunta=longo, titulo_branco=longo), "servico")
    assert len(p["historia"]) <= 300 and p["historia"].endswith("…")
    assert len(p["pergunta"]) <= 100
    assert len(p["titulo_branco"]) <= 80


def test_licoes_alem_de_tres_sao_descartadas_e_pares_incompletos_ignorados():
    licoes = [["a", "1"], ["b", ""], ["c", "3"], ["d", "4"], ["e", "5"]]
    p = validar(bloco_infografico(licoes=licoes), "servico")
    assert [t for t, _ in p["licoes"]] == ["a", "c", "d"]


def test_cena_composta_descarta_o_que_nao_existe():
    cc = {"fundo": "marte", "elementos": ["rack", "dinossauro", "rack", "nuvem", "globo", "chip", "escudo"], "legenda": "x"}
    p = validar(bloco_infografico(cena_composta=cc), "servico")
    assert p["cena_composta"]["fundo"] == "escritorio"            # fundo desconhecido -> padrão
    assert p["cena_composta"]["elementos"] == ["rack", "nuvem", "globo", "chip"]  # sem repetir, máx. 4


def test_cena_composta_sem_elemento_valido_cai_na_cena_do_tema():
    cc = {"fundo": "cidade", "elementos": ["dinossauro"], "legenda": "x"}
    p = validar(bloco_infografico(cena_composta=cc), "dica")
    assert p["cena"] == "ensino" and "cena_composta" not in p


def test_painel_sem_terminal_cai_para_noticias():
    b = bloco_infografico(cena="painel")
    del b["cena_composta"]
    assert validar(b, "hacker")["cena"] == "noticias"


def test_painel_com_terminal_normaliza_linhas():
    b = bloco_infografico(cena="painel", terminal_titulo="alerta", terminal=[
        ["$ ", "comando", "cmd"], ["", "risco", "cor-inexistente"], "lixo", ["só um"], ["", "   ", "ok"],
    ] + [["", f"linha {i}", "txt"] for i in range(20)])
    del b["cena_composta"]
    p = validar(b, "hacker")
    assert p["cena"] == "painel" and p["terminal_titulo"] == "alerta"
    assert p["terminal"][1] == ["", "risco", "txt"]   # cor inválida vira txt
    assert len(p["terminal"]) == 8                    # no máximo 8 linhas


def test_cor_invalida_usa_a_do_tema_e_valida_e_mantida():
    assert validar(bloco_infografico(cor="vermelho"), "hacker")["cor"] == infografico.COR_PADRAO["hacker"]
    assert validar(bloco_infografico(cor="#00FF88"), "hacker")["cor"] == "#00FF88"


def test_hashtags_sao_normalizadas():
    p = validar(bloco_infografico(hashtags=["backup", "#Back up", 7, "#TI", "#ti", "#" * 3]), "servico")
    assert p["hashtags"] == ["#backup", "#TI"]   # sem duplicata (caixa ignorada), sem lixo
    assert all(h.startswith("#") and " " not in h for h in p["hashtags"])
    assert validar(bloco_infografico(hashtags=[]), "servico")["hashtags"] == ["#TI", "#TECHDIM"]


def test_desenhar_gera_png_1080x1350_deterministico(tmp_path):
    a = infografico.renderizar(bloco_infografico(), "servico", "slug", tmp_path / "a.png")
    b = infografico.renderizar(bloco_infografico(), "servico", "slug", tmp_path / "b.png")
    assert Image.open(a).size == (1080, 1350)
    assert a.read_bytes() == b.read_bytes()
    c = infografico.renderizar(bloco_infografico(), "servico", "outro-slug", tmp_path / "c.png")
    assert c.read_bytes() != a.read_bytes()   # o slug muda os detalhes aleatórios da cena


@pytest.mark.parametrize("cena", sorted(infografico.CENAS))
def test_toda_cena_registrada_desenha(tmp_path, cena):
    b = bloco_infografico(cena=cena, terminal=[["$ ", "linha", "cmd"]])
    del b["cena_composta"]
    arq = infografico.renderizar(b, "servico", f"t-{cena}", tmp_path / "x.png")
    assert arq.exists() and Image.open(arq).size == (1080, 1350)


@pytest.mark.parametrize("fundo", sorted(infografico.FUNDOS))
def test_todo_fundo_com_todos_os_elementos_desenha(tmp_path, fundo):
    cc = {"fundo": fundo, "elementos": sorted(infografico.ELEMENTOS)[:4], "legenda": "teste"}
    arq = infografico.renderizar(bloco_infografico(cena_composta=cc), "servico", fundo, tmp_path / "x.png")
    assert arq.exists()


def test_texto_gigante_nao_estoura_nem_levanta_erro(tmp_path):
    """Pior caso que o validar deixa passar: tudo no limite, com palavras compridas."""
    palavra = "Supercalifragilístico" * 2
    b = bloco_infografico(
        titulo_branco=(palavra + " ") * 4, titulo_destaque=(palavra + " ") * 3,
        historia=(palavra + " ") * 20, pergunta=(palavra + " ") * 8,
        licoes=[[palavra, (palavra + " ") * 10]] * 3, hashtags=["#" + "a" * 25] * 6,
    )
    arq = infografico.renderizar(b, "servico", "pior-caso", tmp_path / "x.png")
    img = Image.open(arq).convert("RGB")
    assert img.size == (1080, 1350)
    # a faixa de rodapé (abaixo da linha em y=1282) continua só com a marca: nada invadiu
    faixa = img.crop((300, 1290, 800, 1340)).getcolors(maxcolors=1 << 20)
    assert faixa is not None and len(faixa) < 40   # fundo liso, sem texto passando por ali
