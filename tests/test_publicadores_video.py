"""Publicadores de vídeo: LinkedIn (partes, finalize, post), Reel do Facebook e Reel do Instagram. Sem rede."""
import pytest
from requests.structures import CaseInsensitiveDict

import config
from publishers import facebook, instagram, linkedin
from publishers.common import PublishError

VIDEO = b"0123456789"


class Resp:
    def __init__(self, dados=None, headers=None, texto="{}"):
        # cabeçalhos HTTP não diferenciam maiúsculas, como na resposta real do requests
        self._d, self.headers, self.text = dados if dados is not None else {}, CaseInsensitiveDict(headers or {}), texto

    def json(self):
        return self._d


def casa(url, trecho):
    """Trecho da URL; terminado em $ vale só no fim dela (a URL do container é prefixo da do media_publish)."""
    return url.endswith(trecho[:-1]) if trecho.endswith("$") else trecho in url


class Rede:
    """Responde por (método, trecho da URL); resposta pode ser função (recebe os kwargs) ou exceção."""

    def __init__(self, *regras):
        self.regras, self.chamadas = list(regras), []

    def __call__(self, method, url, **kw):
        self.chamadas.append((method, url, kw))
        for metodo, trecho, resp in self.regras:
            if metodo == method and casa(url, trecho):
                r = resp(kw) if callable(resp) else resp
                if isinstance(r, Exception):
                    raise r
                return r
        raise AssertionError(f"chamada inesperada: {method} {url}")

    def de(self, metodo, trecho):
        return [(u, kw) for m, u, kw in self.chamadas if m == metodo and casa(u, trecho)]

    def nao_repetiveis(self):
        return [u.rsplit("/", 1)[-1].split("?")[0] for m, u, kw in self.chamadas if kw.get("idempotent") is False]


def sequencia(*respostas):
    """Devolve uma resposta por chamada; a última se repete."""
    fila = list(respostas)
    return lambda kw: fila.pop(0) if len(fila) > 1 else fila[0]


def creds():
    c = config.Credentials()
    c.meta_token, c.fb_page_id, c.ig_user_id = "tok" * 5, "111", "222"
    c.linkedin_token, c.linkedin_urn = "li" * 20, "urn:li:person:abc"
    return c


@pytest.fixture
def mp4(tmp_path):
    caminho = tmp_path / "v.mp4"
    caminho.write_bytes(VIDEO)
    return caminho


@pytest.fixture(autouse=True)
def sem_espera(monkeypatch):
    for modulo in (linkedin, facebook, instagram):
        monkeypatch.setattr(modulo.time, "sleep", lambda s: None)


# ------------------------------------------------------------------ LinkedIn


def plano(partes=((0, 3), (4, 9))):
    return Resp({"value": {
        "video": "urn:li:video:V1",
        "uploadToken": "tok-envio",
        "uploadInstructions": [
            {"uploadUrl": f"https://www.linkedin.com/dms-uploads/V1?sau=SEGREDO{i}", "firstByte": a, "lastByte": b}
            for i, (a, b) in enumerate(partes, 1)
        ],
    }})


def linkedin_ok(**mudancas):
    regras = {
        "init": ("POST", "action=initializeUpload", plano()),
        "put1": ("PUT", "SEGREDO1", Resp({}, {"ETag": '"etag-1"'})),
        "put2": ("PUT", "SEGREDO2", Resp({}, {"etag": "etag-2"})),
        "final": ("POST", "action=finalizeUpload", Resp({})),
        "status": ("GET", "/rest/videos/", Resp({"status": "AVAILABLE"})),
        "post": ("POST", "/rest/posts", Resp({}, {"x-restli-id": "urn:li:share:9"})),
    }
    regras.update(mudancas)
    return Rede(*regras.values())


def test_linkedin_video_envia_as_partes_finaliza_e_publica(monkeypatch, mp4):
    rede = linkedin_ok()
    monkeypatch.setattr(linkedin, "request", rede)
    assert linkedin.publish_video(creds(), "legenda #TECHDIM", mp4, title="Título") == "urn:li:share:9"

    (url, kw), = rede.de("POST", "action=initializeUpload")
    assert kw["json"] == {"initializeUploadRequest": {
        "owner": "urn:li:person:abc", "fileSizeBytes": len(VIDEO), "uploadCaptions": False, "uploadThumbnail": False}}
    assert kw["headers"]["LinkedIn-Version"] == config.LINKEDIN_VERSION
    # cada parte leva exatamente a faixa de bytes pedida, na ordem
    corpos = [kw["data"] for m, u, kw in rede.chamadas if m == "PUT"]
    assert corpos == [b"0123", b"456789"]
    assert all(kw["headers"]["Content-Type"] == "application/octet-stream" for u, kw in rede.de("PUT", "dms-uploads"))
    # finalize: ETags sem aspas, na ordem das partes, com o token da sessão
    (_, kw), = rede.de("POST", "action=finalizeUpload")
    assert kw["json"] == {"finalizeUploadRequest": {
        "video": "urn:li:video:V1", "uploadToken": "tok-envio", "uploadedPartIds": ["etag-1", "etag-2"]}}
    # o post referencia o URN do vídeo, escapa a legenda e é o único que não pode ser repetido
    (_, kw), = rede.de("POST", "/rest/posts")
    assert kw["json"]["content"] == {"media": {"id": "urn:li:video:V1", "title": "Título"}}
    assert kw["json"]["commentary"] == "legenda \\#TECHDIM" and kw["json"]["author"] == "urn:li:person:abc"
    assert rede.nao_repetiveis() == ["posts"]
    # a ordem das etapas importa: envio -> finalize -> status -> post
    ordem = [(m, u.split("?")[-1] if "action" in u else u.rsplit("/", 1)[-1]) for m, u, _ in rede.chamadas]
    assert ordem.index(("POST", "action=finalizeUpload")) < [i for i, (m, u) in enumerate(ordem) if u == "posts"][0]


def test_linkedin_video_sem_titulo_usa_um_padrao(monkeypatch, mp4):
    rede = linkedin_ok()
    monkeypatch.setattr(linkedin, "request", rede)
    linkedin.publish_video(creds(), "x", mp4)
    assert rede.de("POST", "/rest/posts")[0][1]["json"]["content"]["media"]["title"] == "Vídeo TECHDIM"


def test_linkedin_video_a_assinatura_da_uploadurl_nao_vai_para_o_erro(monkeypatch, mp4):
    url = "https://www.linkedin.com/dms-uploads/V1?sau=SEGREDO1"
    rede = linkedin_ok(put1=("PUT", "SEGREDO1", PublishError(f"PUT {url} -> HTTP 403: negado")))
    monkeypatch.setattr(linkedin, "request", rede)
    with pytest.raises(PublishError) as exc:
        linkedin.publish_video(creds(), "x", mp4)
    assert "SEGREDO1" not in str(exc.value) and "dms-uploads/V1?…" in str(exc.value) and "403" in str(exc.value)
    assert not rede.de("POST", "/rest/posts")        # nada foi publicado


def test_linkedin_video_sem_plano_de_envio_ou_sem_etag(monkeypatch, mp4):
    monkeypatch.setattr(linkedin, "request", linkedin_ok(init=("POST", "action=initializeUpload", Resp({"value": {}}))))
    with pytest.raises(PublishError, match="plano de envio"):
        linkedin.publish_video(creds(), "x", mp4)
    monkeypatch.setattr(linkedin, "request", linkedin_ok(put2=("PUT", "SEGREDO2", Resp({}, {}))))
    with pytest.raises(PublishError, match="parte 2 .* sem ETag"):
        linkedin.publish_video(creds(), "x", mp4)


def test_linkedin_video_espera_o_processamento_e_aborta_se_falhar(monkeypatch, mp4):
    rede = linkedin_ok(status=("GET", "/rest/videos/", sequencia(
        Resp({"status": "WAITING_UPLOAD"}), Resp({"status": "PROCESSING"}), Resp({"status": "AVAILABLE"}))))
    monkeypatch.setattr(linkedin, "request", rede)
    linkedin.publish_video(creds(), "x", mp4)
    assert len(rede.de("GET", "/rest/videos/")) == 3 and len(rede.de("POST", "/rest/posts")) == 1

    rede = linkedin_ok(status=("GET", "/rest/videos/", Resp({"status": "PROCESSING_FAILED", "processingFailureReason": "codec"})))
    monkeypatch.setattr(linkedin, "request", rede)
    with pytest.raises(PublishError, match="não processou o vídeo: codec"):
        linkedin.publish_video(creds(), "x", mp4)
    assert not rede.de("POST", "/rest/posts")


def test_linkedin_video_consulta_que_falha_nao_impede_o_post(monkeypatch, mp4):
    rede = linkedin_ok(status=("GET", "/rest/videos/", PublishError("GET -> HTTP 403")))
    monkeypatch.setattr(linkedin, "request", rede)
    assert linkedin.publish_video(creds(), "x", mp4) == "urn:li:share:9"


def test_linkedin_video_que_nunca_fica_pronto_para_de_esperar(monkeypatch, mp4):
    monkeypatch.setattr(linkedin, "VIDEO_TENTATIVAS", 3)
    monkeypatch.setattr(linkedin, "request", linkedin_ok(status=("GET", "/rest/videos/", Resp({"status": "PROCESSING"}))))
    with pytest.raises(PublishError, match="a tempo"):
        linkedin.publish_video(creds(), "x", mp4)


# ------------------------------------------------------------------ Facebook (Reel)


def fase(nome):
    return lambda kw: kw["data"]["upload_phase"] == nome


def facebook_ok(**mudancas):
    def video_reels(kw):
        fase_ = kw["data"]["upload_phase"]
        return Resp({"video_id": "55", "upload_url": "https://rupload.facebook.com/video-upload/v21.0/55"}
                    if fase_ == "start" else {"success": True})

    regras = {
        "reels": ("POST", "/111/video_reels", video_reels),
        "envio": ("POST", "rupload.facebook.com/video-upload", Resp({"success": True})),
        "status": ("GET", "/55", sequencia(
            Resp({"status": {"video_status": "uploading"}}),
            Resp({"status": {"video_status": "upload_complete"}}),
            Resp({"status": {"video_status": "processing", "publishing_phase": {"publish_status": "draft"}}}),
            Resp({"status": {"video_status": "ready", "publishing_phase": {"publish_status": "published"}}}))),
    }
    regras.update(mudancas)
    return Rede(*regras.values())


@pytest.fixture
def fb(monkeypatch):
    monkeypatch.setattr(facebook, "page_token", lambda *a: "pagina")


def test_facebook_reel_abre_sessao_envia_o_arquivo_e_publica(monkeypatch, fb, mp4):
    rede = facebook_ok()
    monkeypatch.setattr(facebook, "request", rede)
    assert facebook.publish_reel(creds(), "legenda", mp4, title="Título") == "55"

    inicio, fim = [kw["data"] for u, kw in rede.de("POST", "/111/video_reels")]
    assert inicio == {"upload_phase": "start", "access_token": "pagina"}
    assert fim == {"video_id": "55", "upload_phase": "finish", "video_state": "PUBLISHED",
                   "description": "legenda", "access_token": "pagina", "title": "Título"}
    (_, kw), = rede.de("POST", "rupload.facebook.com")
    assert kw["data"] == VIDEO
    assert kw["headers"] == {"Authorization": "OAuth pagina", "offset": "0", "file_size": str(len(VIDEO))}
    assert kw["timeout"][1] >= 300                       # envio de arquivo precisa de leitura longa
    assert rede.nao_repetiveis() == ["video_reels"]       # só o "finish" não pode ser repetido
    finish = [kw for u, kw in rede.de("POST", "/111/video_reels") if kw["data"]["upload_phase"] == "finish"][0]
    assert finish["idempotent"] is False
    assert len(rede.de("GET", "/55")) == 4                # esperou o envio terminar e o Reel aparecer como publicado


def test_facebook_reel_sem_titulo_nao_manda_title(monkeypatch, fb, mp4):
    rede = facebook_ok()
    monkeypatch.setattr(facebook, "request", rede)
    facebook.publish_reel(creds(), "legenda", mp4)
    assert "title" not in rede.de("POST", "/111/video_reels")[1][1]["data"]


def test_facebook_reel_monta_a_url_de_envio_quando_a_api_nao_a_devolve(monkeypatch, fb, mp4):
    rede = facebook_ok(reels=("POST", "/111/video_reels",
                              lambda kw: Resp({"video_id": "55"} if kw["data"]["upload_phase"] == "start" else {"success": True})))
    monkeypatch.setattr(facebook, "request", rede)
    facebook.publish_reel(creds(), "x", mp4)
    assert rede.de("POST", "rupload.facebook.com")[0][0] == f"{config.RUPLOAD}/video-upload/{config.GRAPH_VERSION}/55"


@pytest.mark.parametrize("quebra, trecho", [
    ({"reels": ("POST", "/111/video_reels", Resp({}))}, "video_id"),
    ({"envio": ("POST", "rupload.facebook.com", Resp({"success": False}))}, "recusou o envio"),
    ({"status": ("GET", "/55", Resp({"status": {"video_status": "upload_failed"}}))}, "envio do Reel falhou"),
])
def test_facebook_reel_falhas_antes_de_publicar_nao_publicam(monkeypatch, fb, mp4, quebra, trecho):
    rede = facebook_ok(**quebra)
    monkeypatch.setattr(facebook, "request", rede)
    with pytest.raises(PublishError, match=trecho):
        facebook.publish_reel(creds(), "x", mp4)
    assert not any(kw["data"].get("upload_phase") == "finish" for u, kw in rede.de("POST", "/111/video_reels"))


def test_facebook_reel_publicacao_nao_confirmada_ou_rejeitada(monkeypatch, fb, mp4):
    def sem_sucesso(kw):
        return Resp({"video_id": "55"} if kw["data"]["upload_phase"] == "start" else {"success": False})

    monkeypatch.setattr(facebook, "request", facebook_ok(reels=("POST", "/111/video_reels", sem_sucesso)))
    with pytest.raises(PublishError, match="não confirmou"):
        facebook.publish_reel(creds(), "x", mp4)

    rejeitado = Resp({"status": {"video_status": "error", "processing_phase": {"error": {"message": "formato"}}}})
    monkeypatch.setattr(facebook, "request", facebook_ok(status=("GET", "/55", sequencia(
        Resp({"status": {"video_status": "upload_complete"}}), rejeitado))))
    with pytest.raises(PublishError, match="rejeitou o Reel.*formato"):
        facebook.publish_reel(creds(), "x", mp4)


def test_facebook_reel_que_demora_demais_para_de_esperar(monkeypatch, fb, mp4):
    monkeypatch.setattr(facebook, "REEL_TENTATIVAS", 3)
    monkeypatch.setattr(facebook, "request", facebook_ok(
        status=("GET", "/55", Resp({"status": {"video_status": "uploading"}}))))
    with pytest.raises(PublishError, match="não terminou a tempo"):
        facebook.publish_reel(creds(), "x", mp4)

    # processamento lento depois de publicar não é erro: o post sai quando terminar
    monkeypatch.setattr(facebook, "request", facebook_ok(
        status=("GET", "/55", sequencia(Resp({"status": {"video_status": "upload_complete"}}),
                                        Resp({"status": {"video_status": "processing"}})))))
    assert facebook.publish_reel(creds(), "x", mp4) == "55"


def test_facebook_link_de_video_vem_relativo_e_o_de_post_completo(monkeypatch, fb):
    monkeypatch.setattr(facebook, "request", lambda *a, **k: Resp({"permalink_url": "/reel/55"}))
    assert facebook.permalink(creds(), "55") == "https://www.facebook.com/reel/55"
    monkeypatch.setattr(facebook, "request", lambda *a, **k: Resp({"permalink_url": "https://www.facebook.com/p/1"}))
    assert facebook.permalink(creds(), "111_1") == "https://www.facebook.com/p/1"
    monkeypatch.setattr(facebook, "request", lambda *a, **k: Resp({}))
    assert facebook.permalink(creds(), "1") == ""


# ------------------------------------------------------------------ Instagram (Reel)


def instagram_ok(**mudancas):
    regras = {
        "container": ("POST", "/222/media$", Resp({"id": "C1", "uri": "https://rupload.facebook.com/ig-api-upload/v21.0/C1"})),
        "envio": ("POST", "rupload.facebook.com/ig-api-upload", Resp({"success": True, "message": "Upload successful."})),
        "status": ("GET", "/C1", Resp({"status_code": "FINISHED"})),
        "publicar": ("POST", "/222/media_publish", Resp({"id": "M1"})),
    }
    regras.update(mudancas)
    return Rede(*regras.values())


@pytest.fixture
def ig(monkeypatch):
    monkeypatch.setattr(instagram, "page_token", lambda *a: "pagina")


def test_instagram_reel_cria_container_resumivel_envia_o_arquivo_e_publica(monkeypatch, ig, mp4):
    rede = instagram_ok()
    monkeypatch.setattr(instagram, "request", rede)
    assert instagram.publish_reel(creds(), "legenda", mp4, ai_generated=True, thumb_offset_ms=2500) == "M1"

    (_, kw), = rede.de("POST", "/222/media$")
    assert kw["data"] == {
        "media_type": "REELS", "upload_type": "resumable", "caption": "legenda", "share_to_feed": "true",
        "is_ai_generated": "true", "thumb_offset": "2500", "access_token": "pagina"}
    (url, kw), = rede.de("POST", "rupload.facebook.com")
    assert url.endswith("/ig-api-upload/v21.0/C1") and kw["data"] == VIDEO
    assert kw["headers"] == {"Authorization": "OAuth pagina", "offset": "0", "file_size": str(len(VIDEO))}
    (_, kw), = rede.de("POST", "/222/media_publish")
    assert kw["data"]["creation_id"] == "C1" and kw["idempotent"] is False
    assert rede.nao_repetiveis() == ["media_publish"]


def test_instagram_reel_sem_ia_e_sem_capa_nao_manda_esses_campos(monkeypatch, ig, mp4):
    rede = instagram_ok()
    monkeypatch.setattr(instagram, "request", rede)
    instagram.publish_reel(creds(), "legenda", mp4)
    campos = rede.de("POST", "/222/media$")[0][1]["data"]
    assert "is_ai_generated" not in campos and "thumb_offset" not in campos and campos["share_to_feed"] == "true"


def test_instagram_reel_espera_mais_que_a_imagem_pelo_processamento(monkeypatch, ig, mp4):
    esperas = []
    monkeypatch.setattr(instagram, "request", instagram_ok())
    monkeypatch.setattr(instagram, "_wait_ready", lambda cid, tok, maximo=instagram.POLL_MAX: esperas.append((cid, maximo)))
    instagram.publish_reel(creds(), "x", mp4)
    assert esperas == [("C1", instagram.REEL_POLL_MAX)] and instagram.REEL_POLL_MAX > instagram.POLL_MAX


def test_instagram_reel_monta_a_url_de_envio_quando_a_api_nao_a_devolve(monkeypatch, ig, mp4):
    rede = instagram_ok(container=("POST", "/222/media$", Resp({"id": "C1"})))
    monkeypatch.setattr(instagram, "request", rede)
    instagram.publish_reel(creds(), "x", mp4)
    assert rede.de("POST", "rupload.facebook.com")[0][0] == f"{config.RUPLOAD}/ig-api-upload/{config.GRAPH_VERSION}/C1"


@pytest.mark.parametrize("quebra, trecho", [
    ({"container": ("POST", "/222/media$", Resp({}, texto="{}"))}, "não devolveu container"),
    ({"envio": ("POST", "rupload.facebook.com", Resp({"success": False}))}, "recusou o envio"),
    ({"status": ("GET", "/C1", Resp({"status_code": "ERROR", "status": "Erro: vídeo inválido"}))}, "rejeitou o container"),
])
def test_instagram_reel_falhas_nao_publicam(monkeypatch, ig, mp4, quebra, trecho):
    rede = instagram_ok(**quebra)
    monkeypatch.setattr(instagram, "request", rede)
    with pytest.raises(PublishError, match=trecho):
        instagram.publish_reel(creds(), "x", mp4)
    assert not rede.de("POST", "media_publish")


def test_instagram_reel_container_que_nao_fica_pronto_para_de_esperar(monkeypatch, ig, mp4):
    monkeypatch.setattr(instagram, "REEL_POLL_MAX", 2)
    rede = instagram_ok(status=("GET", "/C1", Resp({"status_code": "IN_PROGRESS"})))
    monkeypatch.setattr(instagram, "request", rede)
    with pytest.raises(PublishError, match="não ficou pronto a tempo"):
        instagram.publish_reel(creds(), "x", mp4)
    assert len(rede.de("GET", "/C1")) == 2
