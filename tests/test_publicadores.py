"""Os publicadores só marcam como não-repetível o que cria algo."""
import pathlib

import config
from publishers import facebook, instagram, linkedin


class Resp:
    def __init__(self, dados=None, headers=None):
        self._d, self.headers, self.text = dados or {}, headers or {}, "{}"

    def json(self):
        return self._d


class Gravador:
    def __init__(self, respostas=None):
        self.chamadas = []
        self.respostas = respostas or {}

    def __call__(self, method, url, **kw):
        self.chamadas.append((method, url, kw))
        for trecho, resp in self.respostas.items():
            if trecho in url or trecho in str(kw.get("params", "")):
                return resp
        return Resp({"id": "123"}, {"x-restli-id": "urn:li:share:1"})


def creds():
    c = config.Credentials()
    c.meta_token, c.fb_page_id, c.ig_user_id = "tok" * 5, "111", "222"
    c.linkedin_token, c.linkedin_urn = "li" * 20, "urn:li:person:abc"
    return c


def nao_repetiveis(g):
    return sorted(u.rsplit("/", 1)[-1] for m, u, kw in g.chamadas if kw.get("idempotent") is False)


def test_facebook_publicar_e_comentar_nao_repetem(monkeypatch):
    g = Gravador()
    monkeypatch.setattr(facebook, "request", g)
    monkeypatch.setattr(facebook, "page_token", lambda *a: "pagina")
    facebook.publish(creds(), "legenda", ["https://x/a.png"])
    facebook.comment(creds(), "111_9", "oi")
    assert nao_repetiveis(g) == ["comments", "feed"]
    upload = [kw for m, u, kw in g.chamadas if u.endswith("/photos")][0]
    assert "idempotent" not in upload  # subir foto não publicada pode repetir


def test_instagram_publicar_story_e_comentar_nao_repetem(monkeypatch):
    g = Gravador({"status_code": Resp({"status_code": "FINISHED"})})
    monkeypatch.setattr(instagram, "request", g)
    monkeypatch.setattr(instagram, "page_token", lambda *a: "pagina")
    monkeypatch.setattr(instagram.time, "sleep", lambda s: None)
    instagram.publish(creds(), "legenda", ["https://x/a.png"])
    instagram.publish_story(creds(), "https://x/s.png")
    instagram.comment(creds(), "9", "oi")
    assert nao_repetiveis(g) == ["comments", "media_publish", "media_publish"]
    containers = [kw for m, u, kw in g.chamadas if u.endswith("/media")]
    assert containers and all("idempotent" not in kw for kw in containers)


def test_linkedin_publicar_e_comentar_nao_repetem(monkeypatch, tmp_path: pathlib.Path):
    g = Gravador({"initializeUpload": Resp({"value": {"uploadUrl": "https://up", "image": "urn:li:image:1"}})})
    monkeypatch.setattr(linkedin, "request", g)
    img = tmp_path / "a.png"
    img.write_bytes(b"png")
    linkedin.publish(creds(), "legenda #TECHDIM", [img], alt="alt")
    linkedin.comment(creds(), "urn:li:share:1", "oi")
    assert nao_repetiveis(g) == ["comments", "posts"]


def test_linkedin_escapa_caracteres_reservados():
    assert linkedin.escape_commentary("a (b) #c") == r"a \(b\) \#c"
