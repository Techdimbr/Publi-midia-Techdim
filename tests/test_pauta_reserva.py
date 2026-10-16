"""Pauta de reserva com o Gemini: esquema, escolha da manchete, reescrita, verificação e a cadeia do content.build."""
import datetime as dt
import json

import pytest

import config
import content
import gemini
import pauta_reserva as pr
from cenas import ELEMENTOS, FUNDOS
from conftest import DIA, bloco_infografico, pauta


@pytest.fixture
def com_chave(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "chave-de-teste")


class GeminiFalso:
    """Substitui gemini.gerar_json: devolve as respostas da fila e guarda os pedidos."""

    def __init__(self, monkeypatch, *respostas):
        self.fila = list(respostas)
        self.pedidos: list[dict] = []
        monkeypatch.setattr(pr.gemini, "gerar_json", self)

    def __call__(self, prompt, esquema, **kw):
        self.pedidos.append({"prompt": prompt, "esquema": esquema, **kw})
        r = self.fila.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def pauta_hacker(**extra):
    bloco = {"cena": "painel", "terminal_titulo": "alerta",
             "terminal": [["$ ", "verificar a versão instalada", "cmd"], ["", "versões antigas expostas à internet", "risco"],
                          ["", "aplicar a correção do fabricante", "ok"], ["", "revisar os acessos remotos", "txt"]],
             **{k: v for k, v in bloco_infografico().items() if k != "cena_composta"}}
    return pauta(titulo="Ivanti Connect Secure: falha explorada pede correção hoje", infografico=bloco, **extra)


MANCHETES = [
    {"title": "Falha crítica em VPN é explorada", "link": "https://exemplo.com/vpn", "lang": "pt", "summary": "resumo",
     "when": dt.datetime(2026, 10, 2), "source": "exemplo.com"},
    {"title": "Outra matéria qualquer", "link": "https://exemplo.com/b", "lang": "pt", "summary": "resumo b",
     "when": dt.datetime(2026, 10, 2), "source": "exemplo.com"},
]


# ------------------------------------------------------------------ esquema


def test_esquema_usa_so_fundos_e_elementos_que_existem_e_o_hacker_pede_terminal():
    comum = pr.esquema_post("dica")["properties"]["infografico"]
    composta = comum["properties"]["cena_composta"]["properties"]
    assert composta["fundo"]["enum"] == list(FUNDOS) and composta["elementos"]["items"]["enum"] == list(ELEMENTOS)
    assert "terminal" not in comum["properties"] and "cena_composta" in comum["required"]
    hacker = pr.esquema_post("hacker")["properties"]["infografico"]
    assert hacker["properties"]["cena"]["enum"] == ["painel"] and {"terminal", "terminal_titulo"} <= set(hacker["required"])
    assert "cena_composta" not in hacker["properties"]


# ------------------------------------------------------------------ verificação


def test_verificar_item_aceita_a_pauta_boa_e_reprova_dominio_telefone_e_bloco_ruim():
    assert pr.verificar_item("dica", pauta()) == ([], [])
    antigo = pauta(fecho=f"Veja www.{config.SITE_FORA_DO_AR}")
    assert "fora do ar" in pr.verificar_item("dica", antigo)[0][0]
    assert any("telefone" in p for p in pr.verificar_item("dica", pauta(fecho="Ligue (19) 99615-3276"))[0])
    assert pr.verificar_item("dica", pauta(fecho="Ligue (19) 99615-3276"), estrito=False)[0] == []   # só a reserva exige isso
    sem_bloco = {k: v for k, v in pauta().items() if k != "infografico"}
    assert pr.verificar_item("dica", sem_bloco)[0] == ["falta o bloco infografico"]
    assert "inválido" in pr.verificar_item("dica", {"titulo": "só título"})[0][0]


def test_hacker_precisa_de_painel_com_terminal():
    assert pr.verificar_item("hacker", pauta_hacker()) == ([], [])
    composta = pauta()   # cena composta num tema hacker: não vale na reserva
    assert any("painel" in p for p in pr.verificar_item("hacker", composta)[0])
    assert pr.verificar_item("hacker", composta, estrito=False)[0] == []   # o arquivo do Claude segue as regras do validar_pauta


def test_terminal_com_comando_real_reprova_e_descricao_de_acao_passa():
    com_comando = pauta_hacker()
    com_comando["infografico"]["terminal"][0] = ["$ ", "sudo apt update && sudo apt upgrade ivanti", "cmd"]
    assert any("comando real" in p for p in pr.verificar_item("hacker", com_comando)[0])
    assert pr.verificar_item("hacker", com_comando, estrito=False)[0] == []   # o arquivo do Claude não passa por esta regra
    for ok in ("aplicar a atualização do fabricante", "redefinir as senhas de domínio", "revisar acessos remotos"):
        assert not pr.COMANDO.search(ok)


def test_normalizar_poe_o_espaco_no_prefixo_do_terminal_e_as_hashtags_obrigatorias():
    item = pauta_hacker()
    item["infografico"]["terminal"] = [["$", "verificar versões afetadas", "cmd"], ["", "falha explorada", "risco"]]
    item["infografico"]["hashtags"] = ["#ZeroDay"]
    norm = pr._normalizar("hacker", item, ("exemplo.com", "https://exemplo.com/a"))
    assert norm["infografico"]["terminal"][0][0] == "$ " and norm["infografico"]["terminal"][1][0] == ""
    assert norm["infografico"]["hashtags"] == ["#ZeroDay", "#TI", "#TECHDIM"]
    assert norm["fontes"] == [["exemplo.com", "https://exemplo.com/a"]]


def test_aviso_de_tamanho_so_e_grave_acima_de_15_por_cento():
    assert pr._grave("titulo: 105 caracteres (recomendado até 90)") is True
    assert pr._grave("titulo: 100 caracteres (recomendado até 90)") is False
    assert pr._grave("fecho: 132 caracteres (recomendado até 130)") is False


# ------------------------------------------------------------------ assuntos recentes


def test_titulos_recentes_pega_so_os_ultimos_dias(conteudo):
    pasta, _ = conteudo
    for dia, titulo in (("2026-10-01", "Ontem"), ("2026-09-10", "Muito antigo"), ("2026-10-02", "Hoje não conta")):
        d = pasta.parent / dia
        d.mkdir(exist_ok=True)
        (d / "dica.json").write_text(json.dumps({"titulo": titulo}), encoding="utf-8")
    (content.CONTENT_DIR / "destaques").mkdir()
    (content.CONTENT_DIR / "destaques" / "2026-09-30.json").write_text(json.dumps({"titulo": "Destaque"}), encoding="utf-8")
    assert pr.titulos_recentes(DIA) == ["Ontem", "Destaque"]
    assert pr._repetida("Ontem: um assunto novo", ["Ontem: um assunto novo e parecido"]) is True
    assert pr._repetida("Backup testado", ["Firewall configurado"]) is False


# ------------------------------------------------------------------ gerar_item


def test_sem_chave_nao_ha_reserva():
    with pytest.raises(pr.ReservaIndisponivel, match="GEMINI_API_KEY"):
        pr.gerar_item("dica", DIA)


def test_dica_sai_sem_fonte_externa_e_registra_o_modelo(conteudo, com_chave, monkeypatch):
    falso = GeminiFalso(monkeypatch, pauta(fontes=[["inventada.com", "https://inventada.com"]]))
    monkeypatch.setattr(pr.gemini, "ultimo_modelo", lambda: "gemini-teste")
    item = pr.gerar_item("dica", DIA)
    assert item["fontes"] == [] and "gemini-teste" in item["gerado_por"] and len(falso.pedidos) == 1
    assert "Ensine algo prático" in falso.pedidos[0]["prompt"]
    assert "#TECHDIM" in item["infografico"]["hashtags"] and "#TI" in item["infografico"]["hashtags"]
    assert pr.verificar_item("dica", item) == ([], [])


def test_servico_pede_propaganda_sem_preco(conteudo, com_chave, monkeypatch):
    falso = GeminiFalso(monkeypatch, pauta())
    pr.gerar_item("servico", DIA)
    assert "Sem preço, prazo ou resultado garantido" in falso.pedidos[0]["prompt"]


def test_noticia_escolhe_a_manchete_cita_a_fonte_dela_e_nao_repete_assunto(conteudo, com_chave, monkeypatch):
    monkeypatch.setattr(pr.content, "_fetch_entries", lambda *a, **k: list(MANCHETES))
    monkeypatch.setattr(pr.curator, "_texto_da_materia", lambda url, limite=0: "texto completo da matéria")
    falso = GeminiFalso(monkeypatch, {"indice": 1, "motivo": "afeta empresas"}, pauta_hacker())
    item = pr.gerar_item("hacker", DIA, recentes=["Assunto de ontem"])
    assert item["fontes"] == [["exemplo.com", "https://exemplo.com/b"]]
    assert "Outra matéria qualquer" in falso.pedidos[1]["prompt"] and "texto completo da matéria" in falso.pedidos[1]["prompt"]
    assert "Assunto de ontem" in falso.pedidos[1]["prompt"]
    assert "O texto acima é curto" in falso.pedidos[1]["prompt"]   # matéria curta: não acrescentar detalhes


def test_noticia_sem_manchete_boa_ou_sem_feed_cai_para_a_proxima_camada(conteudo, com_chave, monkeypatch):
    monkeypatch.setattr(pr.content, "_fetch_entries", lambda *a, **k: list(MANCHETES))
    GeminiFalso(monkeypatch, {"indice": -1, "motivo": "só promoção"})
    with pytest.raises(pr.ReservaIndisponivel, match="nenhuma manchete serviu"):
        pr.gerar_item("noticias", DIA)
    monkeypatch.setattr(pr.content, "_fetch_entries", lambda *a, **k: [])
    with pytest.raises(pr.ReservaIndisponivel, match="nenhuma manchete recente"):
        pr.gerar_item("noticias", DIA)


def test_pauta_que_reprova_volta_para_reescrita_com_os_problemas(conteudo, com_chave, monkeypatch):
    ruim = pauta(fecho=f"Acesse www.{config.SITE_FORA_DO_AR}")
    falso = GeminiFalso(monkeypatch, ruim, pauta())
    item = pr.gerar_item("dica", DIA)
    assert item["fecho"] == pauta()["fecho"] and len(falso.pedidos) == 2
    assert "fora do ar" in falso.pedidos[1]["prompt"] and "Corrija a pauta" in falso.pedidos[1]["prompt"]


def test_desiste_depois_de_duas_reescritas_que_continuam_reprovando(conteudo, com_chave, monkeypatch):
    ruim = pauta(fecho=f"Acesse www.{config.SITE_FORA_DO_AR}")
    falso = GeminiFalso(monkeypatch, ruim, ruim, ruim)
    with pytest.raises(pr.ReservaIndisponivel, match="ainda reprova"):
        pr.gerar_item("dica", DIA)
    assert len(falso.pedidos) == 1 + pr.REPAROS


def test_aviso_leve_de_tamanho_nao_gasta_chamada_extra(conteudo, com_chave, monkeypatch):
    leve = pauta(titulo="x" * 95)   # 95 > 90, mas só 5% acima
    falso = GeminiFalso(monkeypatch, leve)
    assert pr.gerar_item("dica", DIA)["titulo"] == "x" * 95 and len(falso.pedidos) == 1


def test_gemini_fora_do_ar_vira_reserva_indisponivel(conteudo, com_chave, monkeypatch):
    GeminiFalso(monkeypatch, gemini.GeminiIndisponivel("nenhum modelo respondeu"))
    with pytest.raises(pr.ReservaIndisponivel, match="Gemini indisponível"):
        pr.gerar_item("dica", DIA)


# ------------------------------------------------------------------ o que falta no dia


def test_precisa_de_reserva_so_quando_a_pauta_falta_ou_nao_serve(conteudo):
    pasta, escrever = conteudo
    assert pr.precisa("dica", DIA) == "sem arquivo"
    escrever("dica", pauta())
    assert pr.precisa("dica", DIA) == ""
    escrever("dica", "{isto não é json")
    assert "JSON inválido" in pr.precisa("dica", DIA)
    escrever("dica", pauta(fecho=f"Acesse www.{config.SITE_FORA_DO_AR}"))
    assert "fora do ar" in pr.precisa("dica", DIA)
    escrever("hacker", pauta(fecho="Ligue (19) 99615-3276"))   # telefone e cena fora do painel: regras da reserva, não da Routine
    assert pr.precisa("hacker", DIA) == ""


def test_main_sem_chave_nao_faz_nada_e_com_gravar_escreve_so_o_que_falta(conteudo, com_chave, monkeypatch, tmp_path, capsys):
    pasta, escrever = conteudo
    escrever("dica", pauta())   # a pauta do Claude está de pé: não pode ser tocada
    monkeypatch.delenv("GEMINI_API_KEY")
    assert pr.main(["--dia", DIA.isoformat()]) == 0 and "desligada" in capsys.readouterr().out
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    monkeypatch.setattr(pr, "gerar_item", lambda tema, dia: pauta(titulo=f"Pauta de {tema}"))
    assert pr.main(["--dia", DIA.isoformat(), "--gravar"]) == 0
    assert json.loads((pasta / "dica.json").read_text(encoding="utf-8")) == pauta()
    assert json.loads((pasta / "noticias.json").read_text(encoding="utf-8"))["titulo"] == "Pauta de noticias"
    assert {p.stem for p in pasta.glob("*.json")} == {"noticias", "hacker", "dica", "servico"}
    # ensaio: não grava
    (pasta / "servico.json").unlink()
    assert pr.main(["--dia", DIA.isoformat(), "--tema", "servico"]) == 0
    assert not (pasta / "servico.json").exists() and "ensaio ok" in capsys.readouterr().out


def test_main_devolve_1_quando_alguma_pauta_falha(conteudo, com_chave, monkeypatch):
    def quebra(tema, dia):
        raise pr.ReservaIndisponivel("sem cota")

    monkeypatch.setattr(pr, "gerar_item", quebra)
    assert pr.main(["--dia", DIA.isoformat(), "--tema", "dica"]) == 1


# ------------------------------------------------------------------ a cadeia do content.build


def test_build_usa_a_pauta_do_claude_e_nem_chama_o_gemini(conteudo, com_chave, monkeypatch):
    pasta, escrever = conteudo
    escrever("dica", pauta())
    monkeypatch.setattr(pr, "gerar_item", lambda *a, **k: pytest.fail("o Gemini não devia ser chamado"))
    assert content.build("dica", DIA).origem == "routine"


def test_build_cai_no_gemini_quando_falta_a_pauta_e_depois_no_acervo(conteudo, com_chave, monkeypatch):
    monkeypatch.setattr(pr, "gerar_item", lambda tema, dia: pauta(titulo="Pauta do Gemini"))
    post = content.build("dica", DIA)
    assert post.origem == "gemini" and post.titulo == "Pauta do Gemini" and post.infografico is not None

    def quebra(tema, dia):
        raise pr.ReservaIndisponivel("sem cota")

    monkeypatch.setattr(pr, "gerar_item", quebra)
    acervo = content.build("dica", DIA)
    assert acervo.origem == "" and acervo.titulo != "Pauta do Gemini"   # acervo autoral


def test_build_sem_chave_segue_como_antes(conteudo, monkeypatch):
    monkeypatch.setattr(pr, "gerar_item", lambda *a, **k: pytest.fail("sem chave o Gemini não entra"))
    assert content.build("dica", DIA).origem == ""


# ------------------------------------------------------------------ so_gemini: o teste da reserva do zero


def test_so_gemini_ignora_a_pauta_do_claude_que_esta_de_pe(conteudo, com_chave, monkeypatch):
    pasta, escrever = conteudo
    escrever("dica", pauta(titulo="Pauta do Claude"))
    monkeypatch.setattr(pr, "gerar_item", lambda tema, dia: pauta(titulo="Pauta do Gemini"))
    post = content.build("dica", DIA, so_gemini=True)
    assert post.origem == "gemini" and post.titulo == "Pauta do Gemini"
    assert content.build("dica", DIA).titulo == "Pauta do Claude"   # sem o interruptor, nada muda


def test_so_gemini_nunca_publica_outra_coisa_quando_o_gemini_falha(conteudo, com_chave, monkeypatch):
    def quebra(tema, dia):
        raise pr.ReservaIndisponivel("sem cota")

    monkeypatch.setattr(pr, "gerar_item", quebra)
    with pytest.raises(pr.ReservaIndisponivel, match="sem cota"):
        content.build("dica", DIA, so_gemini=True)          # o acervo autoral NÃO assume
    monkeypatch.setattr(pr, "gerar_item", lambda tema, dia: {"titulo": "", "pontos": []})
    with pytest.raises(ValueError):
        content.build("dica", DIA, so_gemini=True)          # pauta devolvida sem o essencial também falha


def test_so_gemini_sem_chave_falha_dizendo_o_que_falta(conteudo, monkeypatch):
    monkeypatch.setattr(pr, "gerar_item", lambda *a, **k: pytest.fail("sem chave o Gemini não entra"))
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        content.build("dica", DIA, so_gemini=True)


def test_so_gemini_so_vale_para_os_temas_da_pauta(conteudo, com_chave):
    for tema in ("especial", "destaque"):
        with pytest.raises(ValueError, match="so_gemini"):
            content.build(tema, DIA, so_gemini=True)


def test_generate_liga_o_so_gemini_pela_variavel_de_ambiente(conteudo, com_chave, monkeypatch):
    import main

    visto = {}

    def falso(tema, hoje, *, so_gemini=False):
        visto["so_gemini"] = so_gemini
        raise RuntimeError("parou aqui")

    monkeypatch.setattr(main.content, "build", falso)
    for valor, esperado in (("true", True), ("True", True), ("", False), ("false", False)):
        monkeypatch.setenv("SO_GEMINI", valor)
        with pytest.raises(RuntimeError):
            main.generate("dica", ["linkedin"])
        assert visto["so_gemini"] is esperado, valor
