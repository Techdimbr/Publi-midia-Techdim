"""Leitura da pauta, fallback e legendas."""
import json

import pytest

import content
from conftest import DIA, bloco_infografico, pauta
from content import Post


def test_pauta_valida_vira_post_com_infografico(conteudo):
    _, escrever = conteudo
    escrever("servico", pauta())
    post = content.build("servico", DIA)
    assert post.origem == "routine" and post.infografico["cena"] == "composta"
    assert post.fontes == [("techdim.com.br", "https://www.techdim.com.br")]


@pytest.mark.parametrize(
    "conteudo_ruim",
    ["{não é json", "[]", json.dumps({"titulo": "só título"}), json.dumps({"titulo": "", "pontos": ["a", "b"]}),
     json.dumps({"titulo": "x", "pontos": ["só um"]})],
)
def test_pauta_malformada_cai_na_reserva_em_vez_de_quebrar(conteudo, conteudo_ruim):
    _, escrever = conteudo
    escrever("servico", conteudo_ruim)
    post = content.build("servico", DIA)   # acervo autoral
    assert post.origem == "" and post.infografico is None and post.pontos


def test_bloco_infografico_ruim_nao_derruba_o_post(conteudo):
    _, escrever = conteudo
    escrever("servico", pauta(infografico={"titulo_branco": "sem lições"}))
    post = content.build("servico", DIA)
    assert post.origem == "routine"     # o texto da pauta é aproveitado
    assert post.infografico is None     # só a arte nova é descartada


def test_fontes_malformadas_sao_ignoradas(conteudo):
    _, escrever = conteudo
    escrever("hacker", pauta(fontes=[["ok.com", "https://ok.com"], ["sem-url", "ftp://x"], ["a"], "b", None, [1, 2]]))
    assert content.build("hacker", DIA).fontes == [("ok.com", "https://ok.com")]


def test_textos_absurdos_sao_cortados(conteudo):
    _, escrever = conteudo
    escrever("hacker", pauta(titulo="t " * 500, pontos=["p " * 500, "q " * 500], fecho="f " * 500))
    post = content.build("hacker", DIA)
    assert len(post.titulo) <= 160 and all(len(p) <= 260 for p in post.pontos) and len(post.fecho) <= 200


def test_pontos_alem_de_quatro_sao_descartados(conteudo):
    _, escrever = conteudo
    escrever("dica", pauta(pontos=[f"ponto {i}" for i in range(9)]))
    assert len(content.build("dica", DIA).pontos) == 4


# ------------------------------------------------------------------ legendas


def _post(**kw) -> Post:
    base = dict(theme="servico", titulo="Título", pontos=["a", "b", "c"], fecho="Fecho.",
                fontes=[("fonte.com", "https://fonte.com/x")])
    base.update(kw)
    return Post(**base)


def test_legenda_do_instagram_nao_manda_arrastar_quando_e_imagem_unica():
    assert "Arraste para o lado" in _post().caption("instagram")
    assert "Arraste para o lado" not in _post(infografico=bloco_infografico()).caption("instagram")


def test_legenda_do_story_e_vazia():
    assert _post().caption("instagram_stories") == ""


def test_hashtags_do_assunto_vem_primeiro_sem_acento_e_com_a_marca():
    post = _post(infografico=bloco_infografico(hashtags=["#IAGenerativa", "#GOVERNANÇA", "#TI", "#TECHDIM"]))
    assert post.hashtags("instagram").split()[:3] == ["#iagenerativa", "#governanca", "#ti"]
    assert post.hashtags("linkedin").split()[:2] == ["#IAGenerativa", "#Governanca"]   # CamelCase mantido; CAIXA ALTA vira Capitalizada
    for rede, limite in content.LIMITE_HASHTAGS.items():
        tags = post.hashtags(rede).split()
        assert len(tags) <= limite
        assert tags[-1].lower() == "#techdim" or "#techdim" in [t.lower() for t in tags]


def test_hashtags_sem_duplicata_de_acento_ou_caixa():
    post = _post(infografico=bloco_infografico(hashtags=["#Cibersegurança", "#CIBERSEGURANCA", "#ciberseguranca"]))
    tags = post.hashtags("instagram").split()
    assert len([t for t in tags if t == "#ciberseguranca"]) == 1


def test_legenda_antiga_continua_com_as_hashtags_do_tema():
    # posts sem infográfico (acervo, RSS) não mudam
    assert _post().hashtags("linkedin") == "#TECHDIM #InfraestruturaDeTI #CiberSeguranca #AutomacaoEmpresarial"


@pytest.mark.parametrize("rede", ["linkedin", "facebook", "instagram"])
def test_legenda_respeita_o_limite_de_caracteres(rede):
    post = _post(pontos=["x" * 260] * 4, fecho="y" * 200, titulo="z" * 160)
    assert len(post.caption(rede)) <= content.LIMITE_LEGENDA[rede]
    enorme = _post(pontos=["x " * 2000] * 4)
    assert len(enorme.caption(rede)) <= content.LIMITE_LEGENDA[rede]


def test_comentario_leva_fontes_e_site():
    c = _post().comentario("facebook")
    assert "fonte.com" in c and "techdim.com.br" in c
    assert _post(fontes=[]).comentario("instagram") == ""
    assert _post().comentario("linkedin") == ""


# ------------------------------------------------------------------ curadoria


def test_curadoria_que_quebra_nao_derruba_o_post(monkeypatch):
    monkeypatch.setattr(content.curator, "disponivel", lambda: True)
    monkeypatch.setattr(content, "_fetch_entries", lambda *a, **k: [])

    def quebra(*a, **k):
        raise TypeError("parâmetro que o SDK não conhece")

    monkeypatch.setattr(content.curator, "curar", quebra)
    assert content._from_feeds("noticias", 1) is None   # cai no filtro por palavra-chave, sem exceção


def test_feed_lento_ou_fora_do_ar_e_ignorado(monkeypatch):
    def falha(url):
        raise TimeoutError("sem resposta")

    monkeypatch.setattr(content, "_baixar_feed", falha)
    assert content._fetch_entries([("http://lento", "pt")]) == []


# ------------------------------------------------------------------ arquivos do repositório


def _todos_json(padrao):
    return sorted(content.CONTENT_DIR.glob(padrao))


@pytest.mark.parametrize("arq", _todos_json("diario/*/*.json") + _todos_json("destaques/*.json") + _todos_json("especiais/*.json"),
                         ids=lambda p: "/".join(p.parts[-3:]))
def test_pautas_do_repositorio_sao_validas(arq):
    """Toda pauta commitada precisa virar post e, se tiver bloco, o bloco precisa valer."""
    tema = arq.parent.parent.name if arq.parent.parent.name in ("destaques", "especiais") else arq.stem
    tema = {"destaques": "destaque", "especiais": "especial"}.get(tema, tema)
    post = content._post_do_json(tema, json.loads(arq.read_text(encoding="utf-8")))
    bruto = json.loads(arq.read_text(encoding="utf-8")).get("infografico")
    assert (post.infografico is not None) == (bruto is not None), "bloco infografico descartado por estar inválido"


@pytest.mark.parametrize("nome", ["dicas.json", "servicos.json"])
def test_acervo_autoral_esta_integro(nome):
    itens = json.loads((content.CONTENT_DIR / nome).read_text(encoding="utf-8"))
    assert len(itens) >= 5
    for it in itens:
        assert it["titulo"].strip() and len(it["pontos"]) >= 2
