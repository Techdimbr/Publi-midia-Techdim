"""Leitura da pauta, fallback e legendas."""
import json

import pytest

import config
import content
import links
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
    assert post.hashtags("instagram").split()[:2] == ["#iagenerativa", "#governanca"]   # #TI não gasta vaga de assunto
    assert post.hashtags("linkedin").split()[:2] == ["#IAGenerativa", "#Governanca"]   # CamelCase mantido; CAIXA ALTA vira Capitalizada
    for rede, limite in content.LIMITE_HASHTAGS.items():
        tags = post.hashtags(rede).split()
        assert len(tags) <= limite
        assert tags[-1].lower() == "#techdim" or "#techdim" in [t.lower() for t in tags]


def test_hashtags_sem_duplicata_de_acento_ou_caixa():
    post = _post(infografico=bloco_infografico(hashtags=["#Cibersegurança", "#CIBERSEGURANCA", "#ciberseguranca"]))
    tags = post.hashtags("instagram").split()
    assert len([t for t in tags if t == "#ciberseguranca"]) == 1


def test_post_sem_hashtags_proprias_usa_as_de_reserva_do_tema():
    # acervo e RSS não trazem hashtags: valem as de reserva, mais a praça e a marca
    assert _post().hashtags("linkedin") == "#SuporteDeTI #InfraestruturaDeTI #CiberSeguranca #Campinas #TECHDIM"
    assert _post().hashtags("instagram") == "#suportedeti #tiparaempresas #ticampinas #campinas #techdim"


# Hashtags como a Routine realmente escreve: 5 próprias, com #TI e #TECHDIM no fim.
HASHTAGS_DA_ROUTINE = ["#GitLab", "#DevSecOps", "#IASegura", "#TI", "#TECHDIM"]


@pytest.mark.parametrize("rede,praca", [
    ("instagram", {"#ticampinas", "#campinas"}),
    ("facebook", {"#campinas"}),
    ("linkedin", {"#campinas"}),
])
def test_praca_entra_mesmo_quando_a_pauta_traz_cinco_hashtags_proprias(rede, praca):
    """Regressão: a praça ficava depois das hashtags da pauta e era cortada.

    Com 5 hashtags próprias a lista enchia e nenhuma de Campinas sobrava — no
    Instagram, onde só as 5 primeiras contam, e nas outras redes também.
    """
    post = _post(infografico=bloco_infografico(hashtags=HASHTAGS_DA_ROUTINE))
    tags = [content._chave_tag(t) for t in post.hashtags(rede).split()]
    assert praca <= set(tags), f"{rede}: {tags}"


def test_instagram_nunca_passa_de_cinco_hashtags():
    """O Instagram limita a 5 desde dez/2025; mais que isso ele ignora."""
    for tema in content.HASHTAGS:
        for proprias in ([], HASHTAGS_DA_ROUTINE, [f"#tag{i}" for i in range(30)]):
            bloco = bloco_infografico(hashtags=proprias) if proprias else None
            post = Post(theme=tema, titulo="t", pontos=["a", "b"], infografico=bloco)
            assert len(post.hashtags("instagram").split()) <= 5, (tema, proprias[:2])
    assert content.LIMITE_HASHTAGS["instagram"] == 5


def test_hashtag_generica_nao_gasta_vaga_de_assunto():
    post = _post(infografico=bloco_infografico(hashtags=["#TI", "#GitLab", "#DevSecOps", "#TECHDIM"]))
    tags = post.hashtags("instagram").split()
    assert tags[:2] == ["#gitlab", "#devsecops"]          # as do assunto
    assert tags.count("#techdim") == 1 and tags[-1] == "#techdim"
    assert "#ti" not in tags


def test_hashtag_da_marca_fecha_a_lista_e_nao_abre():
    for rede in ("instagram", "facebook", "linkedin"):
        tags = _post(infografico=bloco_infografico(hashtags=HASHTAGS_DA_ROUTINE)).hashtags(rede).split()
        assert tags[-1].lower() == "#techdim" and tags[0].lower() != "#techdim"


def test_pergunta_segue_a_ordem_pauta_curadoria_reserva():
    """A pauta manda; depois a curadoria por IA; por último a reserva do tema."""
    assert _post(pergunta_propria="Vocês têm servidor próprio?").pergunta == "Vocês têm servidor próprio?"
    da_pauta = _post(pergunta_propria="da IA", infografico=bloco_infografico(pergunta="da pauta"))
    assert da_pauta.pergunta == "da pauta"


def test_pergunta_vem_da_pauta_e_tem_reserva_por_tema():
    com_bloco = _post(infografico=bloco_infografico(pergunta="Quando você testou o backup?"))
    assert com_bloco.pergunta == "Quando você testou o backup?"
    assert _post(theme="dica").pergunta == content.PERGUNTA_PADRAO["dica"]
    # nunca vazia: legenda sem pergunta é legenda que ninguém responde
    assert all(Post(theme=t, titulo="t", pontos=["a", "b"]).pergunta for t in content.HASHTAGS)


@pytest.mark.parametrize("rede", ["linkedin", "facebook", "instagram"])
def test_toda_legenda_pede_interacao(rede):
    assert _post().pergunta in _post().caption(rede)


def test_legenda_do_instagram_pede_enviar_e_seguir():
    """Envio por DM está entre os 3 sinais que o Instagram diz pesar mais; seguir é a meta."""
    legenda = _post().caption("instagram")
    assert "Manda para quem cuida da TI" in legenda
    assert config.IG_HANDLE in legenda
    assert config.REGIAO in legenda


def test_link_clicavel_leva_utm_e_o_do_instagram_nao():
    """UTM só onde o clique existe; no Instagram o link não é clicável em lugar nenhum."""
    assert "utm_source=facebook" in _post().comentario("facebook")
    assert "utm_source=linkedin" in _post().caption("linkedin")
    assert "utm_" not in _post().caption("instagram")


def test_whatsapp_entra_no_comentario_do_facebook_quando_ha_numero(monkeypatch):
    monkeypatch.setattr(config, "WHATSAPP", "5519999998888")
    c = _post().comentario("facebook")
    assert "wa.me/5519999998888" in c
    assert "TECHDIM" in links.whatsapp("x") and "wa.me" in links.whatsapp("x")
    monkeypatch.setattr(config, "WHATSAPP", "")
    assert "wa.me" not in _post().comentario("facebook")   # sem número, cai no site


@pytest.mark.parametrize("rede", ["linkedin", "facebook", "instagram"])
def test_legenda_respeita_o_limite_de_caracteres(rede):
    post = _post(pontos=["x" * 260] * 4, fecho="y" * 200, titulo="z" * 160)
    assert len(post.caption(rede)) <= content.LIMITE_LEGENDA[rede]
    enorme = _post(pontos=["x " * 2000] * 4)
    assert len(enorme.caption(rede)) <= content.LIMITE_LEGENDA[rede]


def test_comentario_leva_fontes_e_site():
    c = _post().comentario("facebook")
    assert "fonte.com" in c and "techdim.com.br" in c
    # o comentário do Instagram nunca é vazio: é onde mora o convite para a bio
    assert "link da bio" in _post(fontes=[]).comentario("instagram")
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
