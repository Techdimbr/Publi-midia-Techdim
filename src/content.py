"""Geração do conteúdo de cada post: notícia real (RSS) ou peça autoral."""
from __future__ import annotations

import datetime as dt
import html
import json
import logging
import pathlib
import random
import re
from dataclasses import dataclass, field

import feedparser

import config
import curator

log = logging.getLogger(__name__)

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content"

# (url, idioma) — fontes em português vêm primeiro na escolha do conteúdo.
FEEDS = {
    "noticias": [
        ("https://tecnoblog.net/feed/", "pt"),
        ("https://canaltech.com.br/rss/", "pt"),
        ("https://olhardigital.com.br/feed/", "pt"),
        ("https://www.tecmundo.com.br/feed", "pt"),
        ("https://9to5google.com/feed/", "en"),
        ("https://techcrunch.com/category/artificial-intelligence/feed/", "en"),
        ("https://feeds.arstechnica.com/arstechnica/technology-lab", "en"),
    ],
    "hacker": [
        ("https://www.cisoadvisor.com.br/feed/", "pt"),
        ("https://thehack.com.br/feed/", "pt"),
        ("https://canaltech.com.br/rss/seguranca/", "pt"),
        ("https://feeds.feedburner.com/TheHackersNews", "en"),
        ("https://www.bleepingcomputer.com/feed/", "en"),
        ("https://krebsonsecurity.com/feed/", "en"),
    ],
}

HASHTAGS = {
    "noticias": {
        "linkedin": "#Tecnologia #InteligenciaArtificial #InovacaoDigital #TECHDIM",
        "facebook": "#TECHDIM #Tecnologia #IA #Campinas",
        "instagram": "#tecnologia #inteligenciaartificial #ia #inovacao #techdim #campinas #ti",
    },
    "hacker": {
        "linkedin": "#CiberSeguranca #SegurancaDaInformacao #InfraestruturaDeTI #TECHDIM",
        "facebook": "#TECHDIM #Seguranca #TI #Campinas",
        "instagram": "#ciberseguranca #seguranca #hacker #ti #infraestrutura #techdim #campinas",
    },
    "dica": {
        "linkedin": "#CiberSeguranca #InfraestruturaDeTI #GestaoDeTI #TECHDIM",
        "facebook": "#TECHDIM #DicaDeTI #Seguranca #Campinas",
        "instagram": "#dicadeti #ciberseguranca #ti #infraestrutura #techdim #campinas #devsecops",
    },
    "destaque": {
        "linkedin": "#InteligenciaArtificial #CiberSeguranca #AgentesDeIA #TECHDIM",
        "facebook": "#TECHDIM #IA #Seguranca #Campinas",
        "instagram": "#inteligenciaartificial #ia #ciberseguranca #agentesdeia #techdim #campinas #ti",
    },
    "servico": {
        "linkedin": "#TECHDIM #InfraestruturaDeTI #CiberSeguranca #AutomacaoEmpresarial",
        "facebook": "#TECHDIM #TI #Campinas #Seguranca",
        "instagram": "#ti #suportetecnico #ciberseguranca #automacao #techdim #campinas",
    },
}


@dataclass
class Post:
    """Uma publicação pronta: texto por rede + slides para renderizar."""

    theme: str
    titulo: str
    pontos: list[str]
    fecho: str = ""
    fontes: list[tuple[str, str]] = field(default_factory=list)  # (nome, url)
    curado_por_ia: bool = False

    @property
    def label(self) -> str:
        return config.THEME_LABELS.get(self.theme, self.theme)

    @property
    def slides(self) -> list[dict]:
        """Até 4 slides: capa + um por ponto, preenchendo o que faltar."""
        fonte = " · ".join(nome for nome, _ in self.fontes[:2])
        out = [{"kind": "capa", "titulo": self.titulo, "label": self.label, "fonte": fonte}]
        for i, ponto in enumerate(self.pontos[: config.CAROUSEL_SLIDES - 1], start=1):
            out.append({"kind": "ponto", "n": i, "texto": ponto, "titulo": self.titulo})
        if len(out) < config.CAROUSEL_SLIDES:
            out.append({"kind": "cta", "fecho": self.fecho or "Fale com a TECHDIM."})
        return out[: config.CAROUSEL_SLIDES]

    def caption(self, network: str) -> str:
        tags = HASHTAGS.get(self.theme, {}).get(network, "#TECHDIM")
        pontos = self.pontos[:4]
        fontes = " · ".join(url for _, url in self.fontes[:2])

        if network == "linkedin":
            corpo = "\n".join(f"{i:02d}. {p}" for i, p in enumerate(pontos, 1))
            partes = [f"{self.titulo}", "", corpo]
            if self.fecho:
                partes += ["", self.fecho]
            if fontes:
                partes += ["", f"Fontes: {fontes}"]
            partes += ["", f"TECHDIM — {config.TAGLINE}", config.SITE, "", tags]
            return "\n".join(partes)

        if network == "facebook":
            corpo = "\n".join(f"• {p}" for p in pontos)
            partes = [f"{self.titulo}", "", corpo]
            if self.fecho:
                partes += ["", self.fecho]
            if fontes:
                partes += ["", f"Fontes: {fontes}"]
            partes += ["", f"Fale com a TECHDIM → {config.SITE}", "", tags]
            return "\n".join(partes)

        # instagram
        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
        corpo = "\n".join(f"{emojis[i]} {p}" for i, p in enumerate(pontos))
        partes = [f"{self.titulo}", "", "Arraste para o lado →", "", corpo]
        if self.fecho:
            partes += ["", self.fecho]
        partes += ["", f"Saiba mais: {config.SITE}", "", tags]
        return "\n".join(partes)



# ---------------------------------------------------------------- relevância

# Feeds generalistas trazem loteria, eleição e entretenimento. Descarta-se tudo
# isso antes de escolher a manchete do dia.
BLOCK = (
    "lotofácil", "lotofacil", "mega-sena", "megasena", "quina", "loteria",
    "concurso 3", "horóscopo", "horoscopo", "signo", "novela", "bbb",
    "futebol", "campeonato", "escalação", "eleições", "eleicoes", "eleitoral",
    "candidat", "cupom", "desconto", "promoção", "promocao", "black friday",
    "melhores filmes", "melhores séries", "melhores series", "netflix",
    "resultado da", "receita federal", "imposto de renda",
    # listas de compra, review e entretenimento não são pauta institucional
    "melhor ", "melhores ", "mais baratos", "para comprar", "vale a pena",
    "review", "análise:", "analise:", "unboxing", "comparativo",
    "na íntegra", "na integra", "playstation", "xbox", "nintendo",
    "jogos", "gamer", "game pass", "steam", "filme", "série", "serie",
    "despenca", "mais barato", "oferta", "r$ ", "preço", "preco",
    # utilidade doméstica e consumo: pauta de portal, não de empresa de TI
    "geladeira", "chuveiro", "ar-condicionado", "conta de luz", "energia elétrica",
    "energia eletrica", "economizar energia", "receita", "saúde", "saude",
    "signo", "carro", "veículo", "veiculo", "viagem", "turismo",
    "whatsapp status", "como fazer no", "truque", "dica de celular",
    # console, celular de consumo e pauta social: não é infraestrutura corporativa
    "ps5", "ps4", "console", "upscaling", "pixel ", "iphone", "galaxy",
    "moto g", "redmi", "tablet", "smartwatch", "fone de ouvido",
    "democracia", "eleitor", "censura", "política", "politica",
)

ALLOW = {
    "noticias": (
        "ia ", " ia", "inteligência artificial", "inteligencia artificial",
        "openai", "anthropic", "claude", "gemini", "chatgpt", "copilot", "llm",
        "google", "microsoft", "apple", "amazon", "meta", "nvidia", "intel", "amd",
        "chip", "processador", "nuvem", "cloud", "datacenter", "data center",
        "software", "hardware", "android", "windows", "linux", "ios",
        "startup", "tecnologia", "automação", "automacao", "robô", "robo",
        "programação", "programacao", "desenvolvedor", "api", "quântic", "quantic",
    ),
    "hacker": (
        "segurança", "seguranca", "ciberataque", "cibernétic", "cibernetic",
        "hacker", "invas", "vazamento", "ransomware", "malware", "phishing",
        "vulnerabilidad", "falha", "exploit", "zero-day", "zero day", "cve",
        "ataque", "golpe", "fraude", "credencia", "senha", "backdoor",
        "botnet", "ddos", "spyware", "trojan", "patch", "correção", "correcao",
        "lgpd", "dados pessoais", "criptografia", "firewall", "apt", "breach",
    ),
}


def _relevant(theme: str, title: str, summary: str = "") -> bool:
    """Pauta relevante: o termo precisa estar no TÍTULO.

    Casar com o resumo deixava passar matéria de utilidade doméstica que
    apenas citava tecnologia de passagem. O título é o sinal forte.
    """
    titulo = title.lower()
    blob = f"{title} {summary}".lower()
    if any(bad in blob for bad in BLOCK):
        return False
    terms = ALLOW.get(theme, ())
    return not terms or any(term in titulo for term in terms)


# ---------------------------------------------------------------- RSS

_TAGS = re.compile(r"<[^>]+>")


def _clean(text: str, limit: int = 180) -> str:
    text = html.unescape(_TAGS.sub(" ", text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        text = text[: limit - 1].rsplit(" ", 1)[0] + "…"
    return text


def _domain(url: str) -> str:
    m = re.match(r"https?://(?:www\.)?([^/]+)", url or "")
    return m.group(1) if m else "fonte"


def _fetch_entries(sources: list[tuple[str, str]], max_age_hours: int = 48) -> list[dict]:
    """Coleta manchetes recentes de todos os feeds, tolerando feed fora do ar."""
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=max_age_hours)
    items: list[dict] = []
    for url, lang in sources:
        try:
            feed = feedparser.parse(url)
        except Exception as exc:  # feed malformado ou rede instável
            log.warning("feed falhou %s: %s", url, exc)
            continue
        if getattr(feed, "bozo", 0) and not feed.entries:
            log.warning("feed vazio ou inválido: %s", url)
            continue
        for entry in feed.entries[:10]:
            stamp = entry.get("published_parsed") or entry.get("updated_parsed")
            when = None
            if stamp:
                when = dt.datetime(*stamp[:6], tzinfo=dt.timezone.utc)
                if when < cutoff:
                    continue
            title = _clean(entry.get("title", ""), 120)
            link = entry.get("link", "")
            if not title or not link:
                continue
            items.append(
                {
                    "title": title,
                    "link": link,
                    "lang": lang,
                    "summary": _clean(entry.get("summary", ""), 200),
                    "when": when or dt.datetime.now(dt.timezone.utc),
                    "source": _domain(link),
                }
            )
    # mais recente primeiro, mas português sempre antes de inglês
    items.sort(key=lambda i: (0 if i["lang"] == "pt" else 1, -i["when"].timestamp()))
    return items


def _from_feeds(theme: str, seed: int) -> Post | None:
    if curator.disponivel():
        candidatos = [
            e for e in _fetch_entries(FEEDS[theme])
            if not any(bad in f"{e['title']} {e['summary']}".lower() for bad in BLOCK)
        ][:25]
        try:
            c = curator.curar(theme, candidatos)
        except curator.CuradoriaIndisponivel as exc:
            log.warning("curadoria por IA indisponível (%s); usando filtro por palavra-chave", exc)
        else:
            return Post(theme=theme, titulo=c["titulo"], pontos=c["pontos"],
                        fecho=c["fecho"], fontes=[c["fonte"]], curado_por_ia=True)
    return _from_feeds_palavra_chave(theme, seed)


def _from_feeds_palavra_chave(theme: str, seed: int) -> Post | None:
    entries = [
        e
        for e in _fetch_entries(FEEDS[theme])
        if _relevant(theme, e["title"], e["summary"])
    ]
    if len(entries) < 2:
        log.warning("tema %s: só %d manchete(s) relevante(s)", theme, len(entries))
        return None

    # dedup por título, mantendo o mais recente
    seen: set[str] = set()
    unique: list[dict] = []
    for item in entries:
        key = item["title"].lower()[:60]
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)

    rng = random.Random(seed)
    destaque = unique[0]
    resto = unique[1:8]
    rng.shuffle(resto)
    escolhidos = [destaque] + resto[:3]
    if len(escolhidos) < 2:
        return None

    titulo = (
        "Resumo do dia — Tecnologia & IA"
        if theme == "noticias"
        else "Alerta de segurança — o que saiu hoje"
    )
    pontos = [i["title"] for i in escolhidos]
    fontes = [(i["source"], i["link"]) for i in escolhidos[:2]]
    fecho = (
        "A TECHDIM acompanha o mercado para manter sua infraestrutura à frente."
        if theme == "noticias"
        else "Precisa avaliar se sua empresa está exposta? Fale com a TECHDIM."
    )
    return Post(theme=theme, titulo=titulo, pontos=pontos, fecho=fecho, fontes=fontes)


# ---------------------------------------------------------------- autoral


def _from_pool(theme: str, filename: str, seed: int) -> Post:
    pool = json.loads((CONTENT_DIR / filename).read_text(encoding="utf-8"))
    item = pool[seed % len(pool)]
    return Post(
        theme=theme,
        titulo=item["titulo"],
        pontos=list(item["pontos"]),
        fecho=item.get("fecho", ""),
    )


# ---------------------------------------------------------------- fallback


_FALLBACK = {
    "noticias": ("dica", "dicas.json"),
    "hacker": ("dica", "dicas.json"),
}


def _destaque(today: dt.date) -> Post:
    """Notícia curada à mão para o dia: content/destaques/AAAA-MM-DD.json."""
    path = CONTENT_DIR / "destaques" / f"{today.isoformat()}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"nenhum destaque curado para {today.isoformat()} — crie {path.relative_to(ROOT)}"
        )
    item = json.loads(path.read_text(encoding="utf-8"))
    return Post(
        theme="destaque",
        titulo=item["titulo"],
        pontos=list(item["pontos"]),
        fecho=item.get("fecho", ""),
        fontes=[tuple(f) for f in item.get("fontes", [])],
    )


def build(theme: str, today: dt.date | None = None) -> Post:
    """Monta o post do tema para a data dada (determinístico por dia)."""
    today = today or dt.date.today()
    seed = today.toordinal()

    if theme in FEEDS:
        post = _from_feeds(theme, seed)
        if post:
            return post
        # Nenhum feed respondeu: não deixa o horário vazio, publica peça autoral.
        log.warning("tema %s sem notícia disponível; usando conteúdo autoral", theme)
        alt_theme, alt_file = _FALLBACK[theme]
        return _from_pool(alt_theme, alt_file, seed + hash(theme) % 7)

    if theme == "dica":
        return _from_pool("dica", "dicas.json", seed)
    if theme == "servico":
        return _from_pool("servico", "servicos.json", seed)
    if theme == "destaque":
        return _destaque(today)

    raise ValueError(f"tema desconhecido: {theme}")
