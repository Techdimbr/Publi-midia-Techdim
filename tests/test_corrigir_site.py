"""Troca do endereço do site nos posts já publicados: texto, lista de posts e edição nas redes."""
import json

import pytest

import config
import corrigir_site as cs
from publishers import linkedin
from publishers.common import PublishError

ANTIGO_URL = f"https://www.{config.SITE_FORA_DO_AR}"
ANTIGO = f"www.{config.SITE_FORA_DO_AR}"


@pytest.fixture(autouse=True)
def sem_pausa(monkeypatch):
    monkeypatch.setattr(cs.time, "sleep", lambda s: None)


# ------------------------------------------------------------------ o texto


@pytest.mark.parametrize(
    "antes, depois",
    [
        (f"Fale com a TECHDIM: {ANTIGO}", f"Fale com a TECHDIM: {config.SITE}"),
        (f"IA\n{ANTIGO_URL}", f"IA\n{config.SITE_URL}"),
        (f"Informe a sua em {ANTIGO}.", f"Informe a sua em {config.SITE}."),
        (f"Veja {ANTIGO_URL}/servicos, ok?", f"Veja {config.SITE_URL}, ok?"),
        (f"({ANTIGO_URL}/x)", f"({config.SITE_URL})"),
        (f"{ANTIGO_URL.upper()} e {config.SITE_FORA_DO_AR}", f"{config.SITE_URL} e {config.SITE}"),
        # não mexe em e-mail, subdomínio nem em outro domínio parecido
        (f"contato@{config.SITE_FORA_DO_AR}", f"contato@{config.SITE_FORA_DO_AR}"),
        (f"blog.{config.SITE_FORA_DO_AR}", f"blog.{config.SITE_FORA_DO_AR}"),
        (f"{config.SITE_FORA_DO_AR}asil", f"{config.SITE_FORA_DO_AR}asil"),
        (f"já certo: {config.SITE} e {config.SITE_URL}", f"já certo: {config.SITE} e {config.SITE_URL}"),
        ("", ""),
    ],
)
def test_corrigir_texto_troca_so_o_endereco_antigo(antes, depois):
    assert cs.corrigir_texto(antes) == depois
    assert cs.corrigir_texto(depois) == depois   # rodar de novo não muda nada


def test_linhas_trocadas_mostra_so_o_que_mudou():
    assert cs.linhas_trocadas("a\nb " + ANTIGO + "\nc", "a\nb " + config.SITE + "\nc") == [
        ("b " + ANTIGO, "b " + config.SITE)
    ]


# ------------------------------------------------------------------ o diário

REGISTRO = f"""# TECHDIM · Serviços — Título

- **Data:** 2026-10-14, 17:24 (horário de Brasília)

## Resultado

| Rede | Status | Link | 1º comentário |
|---|---|---|---|
| linkedin | ✅ publicado | https://www.linkedin.com/feed/update/urn:li:share:11/ | — |

## Fontes

- [a](https://a.com)

## Linkedin

```text
Texto do LinkedIn
{ANTIGO_URL}
```

![linkedin 1](../../posts/x.png)

## Facebook

```text
Texto do Facebook
```

Primeiro comentário:

```text
🌐 TECHDIM: {ANTIGO_URL}
```

## Instagram

```text
Texto do Instagram
Saiba mais: {ANTIGO}
```
"""


def test_blocos_do_registro_separa_legenda_e_primeiro_comentario():
    blocos = cs._blocos_do_registro(REGISTRO)
    assert blocos["linkedin"] == (f"Texto do LinkedIn\n{ANTIGO_URL}", "")
    assert blocos["facebook"] == ("Texto do Facebook", f"🌐 TECHDIM: {ANTIGO_URL}")
    assert blocos["instagram"][1] == ""
    assert "fontes" not in blocos


def entrada(hora, tema, arquivo, ids, comentou=(), status=None):
    return {
        "hora": hora, "tema": tema, "titulo": "t", "arquivo": arquivo,
        "redes": status or {"linkedin": "publicado", "facebook": "publicado", "instagram": "publicado"},
        "links": {r: f"https://rede/{r}/{i}" for r, i in ids.items()},
        "ids": ids, "comentou": list(comentou),
    }


@pytest.fixture
def assets(tmp_path):
    """Diário com dois dias: o do dia 14 tem os três posts; o do dia 13, um post sem id e um apagado."""
    reg = tmp_path / "registros"
    d14, d13 = reg / "2026-10-14", reg / "2026-10-13"
    d14.mkdir(parents=True), d13.mkdir(), (reg / "semanal").mkdir()
    (d14 / "17h24-servico.md").write_text(REGISTRO, encoding="utf-8")
    (d13 / "08h00-noticias.md").write_text(REGISTRO, encoding="utf-8")
    (d14 / "index.json").write_text(json.dumps([
        entrada("17:24", "servico", "17h24-servico.md",
                {"linkedin": "urn:li:share:11", "facebook": "1_22", "instagram": "333"}, comentou=["facebook"]),
    ]), encoding="utf-8")
    (d13 / "index.json").write_text(json.dumps([
        entrada("08:00", "noticias", "08h00-noticias.md", {"linkedin": "urn:li:share:7", "facebook": "1_apagado"},
                status={"linkedin": "publicado", "facebook": "publicado", "instagram": "publicado"}),
    ]), encoding="utf-8")
    (d13 / "movimentos.jsonl").write_text(
        json.dumps({"tipo": "apagou", "rede": "facebook", "detalhe": "1_apagado — motivo: teste"}) + "\n", encoding="utf-8")
    return tmp_path


def test_coletar_lista_do_mais_novo_ao_mais_antigo_sem_apagados_e_sem_id(assets):
    alvos, avisos = cs.coletar(assets)
    assert [(a.dia, a.rede, a.ident) for a in alvos] == [
        ("2026-10-14", "linkedin", "urn:li:share:11"),
        ("2026-10-14", "facebook", "1_22"),
        ("2026-10-14", "instagram", "333"),
        ("2026-10-13", "linkedin", "urn:li:share:7"),
    ]
    assert len(avisos) == 1 and "instagram 2026-10-13" in avisos[0] and "não guarda o id" in avisos[0]
    fb = alvos[1]
    assert fb.legenda == "Texto do Facebook" and fb.comentario.startswith("🌐 TECHDIM")
    assert alvos[2].comentario == ""   # o diário só marca "comentou" no Facebook


def test_coletar_filtra_por_rede_e_aguenta_diario_vazio(assets, tmp_path):
    assert {a.rede for a in cs.coletar(assets, ["linkedin"])[0]} == {"linkedin"}
    alvos, avisos = cs.coletar(tmp_path / "vazio")
    assert alvos == [] and "não existe" in avisos[0]


# ------------------------------------------------------------------ as redes (simuladas)


class Creds:
    linkedin_token = "l" * 12
    meta_token = "m" * 12
    fb_page_id = "1"
    ig_user_id = "2"
    has_linkedin = has_facebook = has_instagram = True


class Redes:
    """Estado das redes em memória, no lugar das chamadas à API."""

    def __init__(self, monkeypatch):
        antigo_li = linkedin.escape_commentary(f"Texto do LinkedIn #TECHDIM\n{ANTIGO_URL}")
        self.linkedin = {"urn:li:share:11": antigo_li, "urn:li:share:7": antigo_li}
        self.facebook = {"1_22": "Texto do Facebook"}
        self.comentarios = {"1_22": [
            {"id": "c1", "message": "Ótimo post!"},
            {"id": "c2", "message": f"Vejam também: {ANTIGO_URL}"},   # de outra pessoa: nunca editar
            {"id": "c3", "message": f"🌐 TECHDIM: {ANTIGO_URL}"},
        ]}
        self.instagram = {"333": f"Texto do Instagram\nSaiba mais: {ANTIGO}"}
        self.edicoes: list[tuple] = []
        self.linkedin_leitura_recusada = False
        self.linkedin_edicao_recusada = False
        self.nao_existem: set[str] = set()
        self.instagram_recusa = ""
        self.ignora_edicao = False
        self.quebra_em: set[str] = set()
        self.perfil_fb = {"website": ANTIGO_URL, "about": "TECHDIM", "description": ""}
        self.perfil_ig = {"website": ANTIGO_URL, "biography": "Infra e segurança"}
        self.site_ignora_limpeza = False
        for nome in ("facebook_audiencia", "instagram_audiencia", "facebook_perfil", "facebook_editar_perfil", "instagram_perfil", "linkedin_ler", "linkedin_editar", "facebook_ler", "facebook_editar", "facebook_comentarios",
                     "facebook_editar_comentario", "instagram_ler", "instagram_editar"):
            monkeypatch.setattr(cs, nome, getattr(self, nome))

    def linkedin_ler(self, creds, urn):
        if self.linkedin_leitura_recusada:
            raise PublishError("GET x -> HTTP 403: Not enough permissions")
        if urn not in self.linkedin:
            raise PublishError("GET x -> HTTP 404: post not found")
        return self.linkedin[urn]

    def linkedin_editar(self, creds, urn, texto):
        self.edicoes.append(("linkedin", urn, texto))
        if self.linkedin_edicao_recusada:
            raise PublishError("POST x -> HTTP 403: Not enough permissions")
        if not self.ignora_edicao:
            self.linkedin[urn] = texto

    def facebook_ler(self, creds, post_id):
        if post_id in self.nao_existem:
            raise PublishError("GET x -> HTTP 400: Unsupported get request. Object with ID 'x' does not exist")
        if post_id in self.quebra_em:
            raise PublishError("GET x -> HTTP 500: erro")
        return self.facebook[post_id]

    def facebook_editar(self, creds, post_id, texto):
        self.edicoes.append(("facebook", post_id, texto))
        self.facebook[post_id] = texto

    def facebook_comentarios(self, creds, post_id):
        return [dict(c) for c in self.comentarios.get(post_id, [])]

    def facebook_editar_comentario(self, creds, cid, texto):
        self.edicoes.append(("comentario", cid, texto))
        for c in self.comentarios["1_22"]:
            if c["id"] == cid:
                c["message"] = texto

    def facebook_perfil(self, creds):
        return dict(self.perfil_fb)

    def facebook_editar_perfil(self, creds, campo, valor):
        self.edicoes.append(("perfil", campo, valor))
        if campo == "website" and valor == "" and self.site_ignora_limpeza:
            return   # como a API real: aceita e não muda
        self.perfil_fb[campo] = valor

    def facebook_audiencia(self, creds):
        return {"followers_count": 12, "fan_count": 10}

    def instagram_audiencia(self, creds):
        return {"followers_count": 34, "media_count": 59}   # follows_count recusado pela API

    def instagram_perfil(self, creds):
        return dict(self.perfil_ig)

    def instagram_ler(self, creds, media_id):
        if media_id in self.nao_existem:
            raise PublishError("GET x -> HTTP 400: Unsupported get request. Object with ID 'x' does not exist")
        return self.instagram[media_id]

    def instagram_editar(self, creds, media_id, texto):
        self.edicoes.append(("instagram", media_id, texto))
        if self.instagram_recusa:
            raise PublishError(self.instagram_recusa)
        self.instagram[media_id] = texto


@pytest.fixture
def redes(monkeypatch):
    return Redes(monkeypatch)


def rodar(assets, aplicar, tmp_path, **kw):
    alvos, _ = cs.coletar(assets)
    backup = cs.Backup(tmp_path / "backup.jsonl" if aplicar else None)
    return cs.corrigir(Creds(), alvos, aplicar, backup), backup


def situacoes(resultados):
    return [(r.alvo.rede, r.campo, r.situacao) for r in resultados]


def test_ensaio_mostra_o_que_mudaria_e_nao_edita_nada(assets, redes, tmp_path):
    resultados, _ = rodar(assets, False, tmp_path)
    assert redes.edicoes == []
    assert not (tmp_path / "backup.jsonl").exists()
    assert situacoes(resultados) == [
        ("linkedin", "legenda", "trocar"),
        ("facebook", "legenda", "sem mudança"),
        ("facebook", "comentário", "trocar"),
        ("instagram", "legenda", "trocar"),
        ("linkedin", "legenda", "trocar"),
    ]
    comentario = next(r for r in resultados if r.campo == "comentário")
    assert comentario.depois == f"🌐 TECHDIM: {config.SITE_URL}"


def test_aplicar_edita_confere_guarda_o_original_e_nao_repete(assets, redes, tmp_path):
    resultados, backup = rodar(assets, True, tmp_path)
    assert [s for _, _, s in situacoes(resultados)] == ["ok", "sem mudança", "ok", "ok", "ok"]

    # LinkedIn: o texto segue no formato escapado e só o endereço muda
    assert redes.linkedin["urn:li:share:11"] == linkedin.escape_commentary(f"Texto do LinkedIn #TECHDIM\n{config.SITE_URL}")
    # Facebook: só o comentário da página; o de outra pessoa fica como estava
    assert {c["id"]: c["message"] for c in redes.comentarios["1_22"]} == {
        "c1": "Ótimo post!", "c2": f"Vejam também: {ANTIGO_URL}", "c3": f"🌐 TECHDIM: {config.SITE_URL}",
    }
    assert redes.instagram["333"] == f"Texto do Instagram\nSaiba mais: {config.SITE}"

    # o original de cada edição fica guardado
    linhas = [json.loads(x) for x in backup.caminho.read_text(encoding="utf-8").splitlines()]
    tentativas = [x for x in linhas if x["estado"] == "tentando"]
    assert len(tentativas) == 4 and all(ANTIGO in x["antes"] or ANTIGO_URL in x["antes"] for x in tentativas)
    assert [x["estado"] for x in linhas].count("ok") == 4

    # segunda rodada: nada a trocar, nenhuma edição nova
    antes = len(redes.edicoes)
    de_novo, _ = rodar(assets, True, tmp_path)
    assert {s for _, _, s in situacoes(de_novo)} == {"sem mudança"} and len(redes.edicoes) == antes


def test_desfazer_restaura_os_textos_originais(assets, redes, tmp_path):
    originais = (dict(redes.linkedin), dict(redes.facebook), {k: [dict(c) for c in v] for k, v in redes.comentarios.items()},
                 dict(redes.instagram))
    _, backup = rodar(assets, True, tmp_path)
    assert redes.linkedin != originais[0]
    restaurados = cs.desfazer(Creds(), backup.caminho)
    assert {r.situacao for r in restaurados} == {"ok"}
    assert (redes.linkedin, redes.facebook, redes.comentarios, redes.instagram) == originais


def test_linkedin_texto_sem_escapes_e_reescapado_ao_gravar(assets, redes, tmp_path):
    redes.linkedin["urn:li:share:11"] = f"Texto do LinkedIn #TECHDIM (teste)\n{ANTIGO_URL}"
    rodar(assets, True, tmp_path)
    assert redes.linkedin["urn:li:share:11"] == linkedin.escape_commentary(
        f"Texto do LinkedIn #TECHDIM (teste)\n{config.SITE_URL}")


def test_linkedin_sem_permissao_de_leitura_usa_o_texto_do_diario(assets, redes, tmp_path):
    redes.linkedin_leitura_recusada = True
    resultados, _ = rodar(assets, True, tmp_path)
    li = [r for r in resultados if r.alvo.rede == "linkedin" and r.alvo.ident == "urn:li:share:11"][0]
    assert li.situacao == "ok" and "diário" in li.detalhe
    assert redes.linkedin["urn:li:share:11"] == linkedin.escape_commentary(f"Texto do LinkedIn\n{config.SITE_URL}")


def test_post_que_sumiu_no_linkedin_nao_e_falha(assets, redes, tmp_path):
    del redes.linkedin["urn:li:share:7"]
    resultados, _ = rodar(assets, False, tmp_path)
    assert ("linkedin", "legenda", "não existe mais") in situacoes(resultados)


def test_rede_aceita_a_edicao_mas_o_texto_nao_muda_e_falha(assets, redes, tmp_path):
    redes.ignora_edicao = True
    resultados, backup = rodar(assets, True, tmp_path)
    li = resultados[0]
    assert li.situacao == "falhou" and "não mudou" in li.detalhe
    assert '"estado": "falhou"' in backup.caminho.read_text(encoding="utf-8")


def test_erro_num_post_nao_impede_os_outros(assets, redes, tmp_path):
    redes.quebra_em = {"1_22"}
    resultados, _ = rodar(assets, True, tmp_path)
    assert ("facebook", "legenda", "falhou") in situacoes(resultados)
    assert ("instagram", "legenda", "ok") in situacoes(resultados)


def test_facebook_sem_o_primeiro_comentario_no_post_falha(assets, redes, tmp_path):
    redes.comentarios["1_22"] = [{"id": "c1", "message": "Ótimo post!"}]
    resultados, _ = rodar(assets, False, tmp_path)
    assert ("facebook", "comentário", "falhou") in situacoes(resultados)


def test_instagram_que_recusa_edicao_para_de_ser_consultado(assets, redes, tmp_path):
    """Vários posts do Instagram; a API recusa: duas tentativas e o resto vira "não editável"."""
    redes.instagram_recusa = "POST x -> HTTP 400: (#100) Param caption is not supported"
    reg = assets / "registros" / "2026-10-14"
    entradas = []
    for i in range(5):
        redes.instagram[f"9{i}"] = f"Legenda {i} {ANTIGO}"
        entradas.append(entrada(f"1{i}:00", "servico", "17h24-servico.md", {"instagram": f"9{i}"},
                                status={"instagram": "publicado"}))
    (reg / "index.json").write_text(json.dumps(entradas), encoding="utf-8")
    resultados, _ = rodar(assets, True, tmp_path)
    ig = [r for r in resultados if r.alvo.rede == "instagram"]
    assert [r.situacao for r in ig] == ["falhou", "falhou", "não editável", "não editável", "não editável"]
    assert len([e for e in redes.edicoes if e[0] == "instagram"]) == 2   # não insistiu nos outros
    assert "recusou" in ig[-1].detalhe


def test_linkedin_que_recusa_a_edicao_para_de_insistir_e_vira_um_aviso_no_diario(assets, redes, tmp_path):
    """Como no ambiente real: o LinkedIn não deixa ler e, sem a permissão, também recusa editar."""
    redes.linkedin_leitura_recusada = True
    redes.linkedin_edicao_recusada = True
    entradas = [entrada(f"1{i}:00", "servico", "17h24-servico.md", {"linkedin": f"urn:li:share:2{i}"},
                        status={"linkedin": "publicado"}) for i in range(4)]
    (assets / "registros" / "2026-10-14" / "index.json").write_text(json.dumps(entradas), encoding="utf-8")
    resultados, _ = rodar(assets, True, tmp_path)
    # os 4 novos mais o post de 13/10 que o diário de teste já tinha
    assert [r.situacao for r in resultados] == ["falhou", "falhou", "não editável", "não editável", "não editável"]
    assert len(redes.edicoes) == 2   # depois de duas recusas não tentou mais
    eventos = cs._eventos(resultados, "teste")
    assert [e["tipo"] for e in eventos] == ["falhou", "falhou", "observacao"]
    assert "3 posts" in eventos[-1]["detalhe"] and "LinkedIn" in eventos[-1]["detalhe"]


def test_post_que_a_graph_api_diz_nao_existir_nao_e_falha(assets, redes, tmp_path):
    redes.nao_existem = {"333", "1_22"}
    resultados, _ = rodar(assets, False, tmp_path)
    assert ("instagram", "legenda", "não existe mais") in situacoes(resultados)
    assert ("facebook", "legenda", "não existe mais") in situacoes(resultados)
    assert "falhou" not in {s for _, _, s in situacoes(resultados)}


# ------------------------------------------------------------------ linha de comando


@pytest.fixture
def ambiente(monkeypatch):
    for nome, valor in {"META_ACCESS_TOKEN": "m" * 12, "FB_PAGE_ID": "1", "IG_USER_ID": "2",
                        "LINKEDIN_ACCESS_TOKEN": "l" * 12}.items():
        monkeypatch.setenv(nome, valor)


def test_main_ensaio_nao_grava_nada(assets, redes, ambiente, capsys):
    assert cs.main(["--dest", str(assets)]) == 0
    saida = capsys.readouterr().out
    assert "ensaio" in saida and "trocar" in saida and f"+ Saiba mais: {config.SITE}" in saida
    assert redes.edicoes == []
    assert list((assets / "registros").glob("*/correcao-site-*.jsonl")) == []
    assert not any(json.loads(x)["tipo"] == "editou" for f in (assets / "registros").glob("*/movimentos.jsonl")
                   for x in f.read_text(encoding="utf-8").splitlines())


def test_main_aplicar_so_nos_posts_pedidos_e_registra_no_diario(assets, redes, ambiente, capsys):
    assert cs.main(["--dest", str(assets), "--aplicar", "--so", "instagram:333,linkedin:urn:li:share:11"]) == 0
    assert {(e[0], e[1]) for e in redes.edicoes} == {("instagram", "333"), ("linkedin", "urn:li:share:11")}
    backups = list((assets / "registros").glob("*/correcao-site-*.jsonl"))
    assert len(backups) == 1
    eventos = [json.loads(x) for f in (assets / "registros").glob("*/movimentos.jsonl")
               for x in f.read_text(encoding="utf-8").splitlines()]
    editou = [e for e in eventos if e["tipo"] == "editou"]
    assert len(editou) == 2 and all(e["origem"] == "workflow Corrigir site" for e in editou)
    assert any(config.SITE in e["detalhe"] for e in editou)


def test_main_limite_e_rede_desconhecida(assets, redes, ambiente, capsys):
    assert cs.main(["--dest", str(assets), "--limite", "1"]) == 0
    assert "1 post(s)" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        cs.main(["--dest", str(assets), "--redes", "tiktok"])


def test_main_desfazer(assets, redes, ambiente, capsys):
    original = dict(redes.instagram)
    cs.main(["--dest", str(assets), "--aplicar", "--so", "instagram:333"])
    assert redes.instagram != original
    backup = next((assets / "registros").glob("*/correcao-site-*.jsonl"))
    assert cs.main(["--dest", str(assets), "--desfazer", str(backup.relative_to(assets))]) == 0
    assert redes.instagram == original


# ------------------------------------------------------------------ perfis e versão da API


def test_perfis_no_ensaio_mostram_o_site_antigo_e_nao_editam(redes):
    resultados = [r for r in cs.corrigir_perfis(Creds(), False, cs.Backup(None)) if r.campo != "audiência"]
    assert [(r.alvo.rede, r.campo, r.situacao) for r in resultados] == [
        ("facebook", "perfil:website", "não editável"), ("facebook", "perfil:about", "sem mudança"),
        ("facebook", "perfil:description", "sem mudança"),
        ("instagram", "perfil:website", "não editável"), ("instagram", "perfil:biography", "sem mudança"),
    ]
    assert resultados[1].detalhe == "hoje: 'TECHDIM'" and resultados[2].detalhe == "vazio"
    assert config.SITE_URL in resultados[0].detalhe and config.SITE_URL in resultados[3].detalhe and redes.edicoes == []


def test_perfis_aplicar_corrige_o_sobre_guarda_o_original_e_so_avisa_do_resto(redes, tmp_path):
    redes.perfil_fb["about"] = ANTIGO
    backup = cs.Backup(tmp_path / "b.jsonl")
    resultados = [r for r in cs.corrigir_perfis(Creds(), True, backup) if r.campo != "audiência"]
    assert redes.perfil_fb["about"] == config.SITE
    assert redes.perfil_fb["website"] == ANTIGO_URL and redes.perfil_ig["website"] == ANTIGO_URL   # só se trocam no app
    assert [(e[0], e[1]) for e in redes.edicoes] == [("perfil", "about")]
    eventos = cs._eventos(resultados, "teste")
    assert {(e["tipo"], e["rede"]) for e in eventos} == {("observacao", "instagram"), ("observacao", "facebook"),
                                                         ("editou", "facebook")}
    assert any("do perfil" in e["detalhe"] for e in eventos if e["tipo"] == "editou")
    cs.desfazer(Creds(), backup.caminho)   # o backup restaura o campo do perfil
    assert redes.perfil_fb["about"] == ANTIGO


def test_site_da_pagina_nunca_e_editado_pela_api(redes):
    """A API do Facebook acrescenta em vez de substituir no campo Site; por isso ele só é avisado."""
    redes.perfil_fb["website"] = f"http://{ANTIGO}/, http://{ANTIGO}/"
    resultados = cs.corrigir_perfis(Creds(), True, cs.Backup(None), ["facebook"])
    assert resultados[0].situacao == "não editável" and redes.edicoes == []
    redes.perfil_fb["website"] = f"{config.SITE_URL}, {config.SITE_URL}"
    assert cs.corrigir_perfis(Creds(), True, cs.Backup(None), ["facebook"])[0].situacao == "sem mudança"


def test_main_perfis_e_versao_da_graph_api(redes, ambiente, tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(config, "GRAPH", config.GRAPH)   # devolve o valor original ao fim do teste
    assert cs.main(["--dest", str(tmp_path), "--perfis", "--graph-versao", "v26.0"]) == 0
    saida = capsys.readouterr().out
    assert "Graph API: v26.0" in saida and "perfil:website" in saida and "trocar" in saida
    assert config.GRAPH == "https://graph.facebook.com/v26.0"
    assert redes.edicoes == [] and not list(tmp_path.rglob("*.jsonl"))


def test_perfis_mostram_os_seguidores_e_o_que_a_api_recusou(redes):
    linhas = {r.alvo.rede: r.detalhe for r in cs.corrigir_perfis(Creds(), False, cs.Backup(None)) if r.campo == "audiência"}
    assert linhas["facebook"] == "seguidores 12 · curtidas 10"
    assert linhas["instagram"] == "seguidores 34 · posts 59"   # "seguindo" ficou de fora: a API não devolveu


def test_limpar_site_da_pagina_limpa_e_grava_so_um(redes, tmp_path):
    redes.perfil_fb["website"] = f"{config.SITE_URL}, {config.SITE_URL}, http://{ANTIGO}/"
    backup = cs.Backup(tmp_path / "b.jsonl")
    r = cs.limpar_site_da_pagina(Creds(), backup)
    assert r.situacao == "ok" and redes.perfil_fb["website"] == config.SITE_URL
    assert redes.edicoes == [("perfil", "website", ""), ("perfil", "website", config.SITE_URL)]
    assert r.antes.endswith(f"http://{ANTIGO}/") and '"estado": "ok"' in backup.caminho.read_text(encoding="utf-8")


def test_limpar_site_da_pagina_para_quando_a_api_ignora_a_limpeza(redes):
    redes.perfil_fb["website"] = f"{config.SITE_URL}, http://{ANTIGO}/"
    redes.site_ignora_limpeza = True
    r = cs.limpar_site_da_pagina(Creds(), cs.Backup(None))
    assert r.situacao == "não editável" and "troque no app" in r.detalhe
    assert redes.edicoes == [("perfil", "website", "")]   # não gravou nada por cima


def test_limpar_site_da_pagina_ja_certa_nao_faz_nada(redes):
    redes.perfil_fb["website"] = f"{config.SITE_URL}, {config.SITE_URL}"
    assert cs.limpar_site_da_pagina(Creds(), cs.Backup(None)).situacao == "sem mudança"
    assert redes.edicoes == []


def test_corrigir_perfis_so_limpa_o_site_com_o_pedido_e_com_aplicar(redes):
    redes.perfil_fb["website"] = f"http://{ANTIGO}/"
    cs.corrigir_perfis(Creds(), False, cs.Backup(None), limpar_site=True)   # ensaio: nada
    cs.corrigir_perfis(Creds(), True, cs.Backup(None))                      # aplicar sem o pedido: nada no Site
    assert not [e for e in redes.edicoes if e[1] == "website"]
    cs.corrigir_perfis(Creds(), True, cs.Backup(None), limpar_site=True)
    assert redes.perfil_fb["website"] == config.SITE_URL

