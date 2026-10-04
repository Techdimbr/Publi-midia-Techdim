"""Geração do conteúdo de cada post: notícia real (RSS) ou peça autoral."""
from __future__ import annotations

import datetime as dt
import html
import json
import logging
import pathlib
import random
import re
import unicodedata
from dataclasses import dataclass, field

import feedparser
import requests

import config
import curator
import infografico
import links
from texto import cortar, uma_linha

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

# Hashtags.
#
# O Instagram limita cada post e Reel a 5 hashtags (anunciado em 18/12/2025; o
# que passa disso não conta) e diz que poucas hashtags específicas rendem mais
# que muitas genéricas. Por isso cada rede tem vagas contadas — praça, assunto e
# marca — em vez de uma lista longa que o Instagram ignoraria justamente na
# parte que importa.
#
# Praça: conta nova não é achada por hashtag de marca (#TECHDIM só alcança quem
# já conhece) nem por hashtag gigante (#tecnologia tem milhões de posts e o
# nosso afunda em segundos). Quem compra é dono de PME de Campinas, e é ele que
# procura por praça. Vem uma local de nicho e uma ampla no Instagram; no
# Facebook e no LinkedIn a descoberta por cidade é menor, então uma só.
PRACA = {
    "instagram": ["#ticampinas", "#campinas"],
    "facebook": ["#Campinas"],
    "linkedin": ["#Campinas"],
}

# (vagas de praça, vagas de assunto); a marca fecha a lista, então a soma + 1 é
# o limite da rede. Instagram: 2 + 2 + 1 = 5, o teto oficial dele.
VAGAS_HASHTAG = {"instagram": (2, 2), "facebook": (1, 2), "linkedin": (1, 3)}

# Hashtags de assunto de RESERVA: valem quando a pauta não traz as suas (acervo
# autoral e RSS). As da pauta do dia, escritas pela Routine, têm prioridade.
HASHTAGS = {
    "noticias": {
        "linkedin": "#Tecnologia #InteligenciaArtificial #GestaoDeTI",
        "facebook": "#TIparaEmpresas #Tecnologia #IAparaEmpresas",
        "instagram": "#tiparaempresas #tecnologia #inteligenciaartificial #pequenaempresa",
    },
    "hacker": {
        "linkedin": "#CiberSeguranca #SegurancaDaInformacao #GestaoDeTI",
        "facebook": "#SegurancaDigital #TIparaEmpresas #CiberSeguranca",
        "instagram": "#segurancadigital #ciberseguranca #tiparaempresas #protecaodedados",
    },
    "dica": {
        "linkedin": "#GestaoDeTI #CiberSeguranca #Produtividade",
        "facebook": "#DicaDeTI #TIparaEmpresas #SegurancaDigital",
        "instagram": "#dicadeti #tiparaempresas #segurancadigital #pequenaempresa",
    },
    "especial": {
        "linkedin": "#TransformacaoDigital #GestaoDeTI #InteligenciaArtificial",
        "facebook": "#TIparaEmpresas #SuporteDeTI #Tecnologia",
        "instagram": "#tiparaempresas #suportedeti #transformacaodigital #pequenaempresa",
    },
    # Genéricas de propósito: o assunto do destaque muda todo dia.
    "destaque": {
        "linkedin": "#Tecnologia #CiberSeguranca #GestaoDeTI",
        "facebook": "#SegurancaDigital #Tecnologia #TIparaEmpresas",
        "instagram": "#segurancadigital #tiparaempresas #tecnologia #protecaodedados",
    },
    "servico": {
        "linkedin": "#SuporteDeTI #InfraestruturaDeTI #CiberSeguranca",
        "facebook": "#SuporteDeTI #TIparaEmpresas #InfraestruturaDeTI",
        "instagram": "#suportedeti #tiparaempresas #infraestrutura #pequenaempresa",
    },
}

# Genéricas demais para ocupar uma das poucas vagas de assunto: #TI tem milhões
# de posts, e a marca já fecha a lista por conta própria.
HASHTAGS_GENERICAS = {"#ti", "#techdim"}

# Pergunta de fecho quando a pauta não traz uma. Comentário é a única interação
# que abre conversa com alguém que pode virar cliente — é onde nasce o lead. Não
# é o sinal que o Instagram nomeia como mais pesado para o alcance (esse é o
# envio por DM; ver a legenda do Instagram), então não se vende como tal.
PERGUNTA_PADRAO = {
    "noticias": "Isso muda alguma coisa no dia a dia da sua empresa?",
    "hacker": "Sua empresa está exposta a isso?",
    "dica": "Sua empresa já faz isso?",
    "servico": "Como sua empresa resolve isso hoje?",
    "destaque": "Sua empresa usa essa tecnologia?",
    "especial": "Qual é o maior gargalo de TI da sua empresa hoje?",
}


def _chave_tag(tag: str) -> str:
    """Hashtag sem acento e sem caixa: duas grafias da mesma hashtag têm a mesma chave."""
    base = unicodedata.normalize("NFKD", tag)
    return "".join(c for c in base if not unicodedata.combining(c)).lower()


def _forma_tag(tag: str, network: str) -> str:
    """Hashtag do assunto na forma que a rede pede (ver Post.hashtags)."""
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFKD", tag) if not unicodedata.combining(c)
    )
    sem_acento = "#" + sem_acento.lstrip("#")
    if _chave_tag(sem_acento) == "#techdim":
        return "#techdim" if network == "instagram" else "#TECHDIM"
    if network == "instagram":
        return sem_acento.lower()
    if sem_acento.isupper() and len(sem_acento) > 4:  # #BACKUP -> #Backup
        return "#" + sem_acento[1:].capitalize()
    return sem_acento  # CamelCase digitado (#IAGenerativa) e curtas (#TI) ficam como vieram


# Quantas hashtags cada rede comporta: as vagas de praça e de assunto + a marca.
LIMITE_HASHTAGS = {rede: praca + assunto + 1 for rede, (praca, assunto) in VAGAS_HASHTAG.items()}
# Limite de caracteres da legenda em cada rede.
LIMITE_LEGENDA = {"linkedin": 3000, "facebook": 5000, "instagram": 2200}


@dataclass
class Post:
    """Uma publicação pronta: texto por rede + slides para renderizar."""

    theme: str
    titulo: str
    pontos: list[str]
    fecho: str = ""
    fontes: list[tuple[str, str]] = field(default_factory=list)  # (nome, url)
    pergunta_propria: str = ""  # escrita pela curadoria por IA
    curado_por_ia: bool = False
    motivo: str = ""  # por que esta pauta foi escolhida (curadoria)
    origem: str = ""  # "routine" quando veio da pauta do dia escrita pelo Claude
    infografico: dict | None = None  # padrão visual novo (src/infografico.py); None = arte antiga

    @property
    def label(self) -> str:
        return config.THEME_LABELS.get(self.theme, self.theme)

    @property
    def pergunta(self) -> str:
        """Pergunta que fecha a legenda e pede comentário.

        A Routine já escreve uma por pauta no bloco "infografico"; quando não
        escreve, usa-se a do tema. Nunca fica vazia: legenda sem pergunta é
        legenda que ninguém responde.
        """
        return (
            uma_linha((self.infografico or {}).get("pergunta", ""))
            or uma_linha(self.pergunta_propria)
            or PERGUNTA_PADRAO.get(self.theme, "O que você acha disso?")
        )

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

    def hashtags(self, network: str) -> str:
        """Hashtags da legenda, em vagas contadas: assunto, praça e a marca.

        O assunto vem da pauta do dia (as hashtags que a Routine escreveu) e,
        se faltar, das de reserva do tema. #TI e #TECHDIM não gastam vaga de
        assunto: a primeira é genérica demais e a segunda fecha a lista sempre.
        Sem acento (como as do tema), para casar com o que as pessoas digitam;
        minúsculas no Instagram, como é costume, e capitalizadas nas demais,
        porque TUDOMAIÚSCULO é ruim para quem usa leitor de tela. A soma nunca
        passa de LIMITE_HASHTAGS, que no Instagram é o teto de 5 da plataforma.
        """
        vagas_praca, vagas_assunto = VAGAS_HASHTAG.get(network, (1, 3))
        marca = "#techdim" if network == "instagram" else "#TECHDIM"
        usadas = {_chave_tag(marca)}

        def pegar(candidatas: list[str], quantas: int) -> list[str]:
            out: list[str] = []
            for tag in candidatas:
                chave = _chave_tag(tag)
                if len(out) == quantas:
                    break
                if chave in usadas or chave in HASHTAGS_GENERICAS:
                    continue
                usadas.add(chave)
                out.append(tag)
            return out

        proprias = [_forma_tag(t, network) for t in (self.infografico or {}).get("hashtags", [])]
        reserva = HASHTAGS.get(self.theme, {}).get(network, "").split()
        assunto = pegar(proprias + reserva, vagas_assunto)
        praca = pegar(PRACA.get(network, []), vagas_praca)
        return " ".join(assunto + praca + [marca])

    def caption(self, network: str) -> str:
        """Legenda por rede, dentro do limite de caracteres dela.

        Links ficam no primeiro comentário (ver comentario()): link no corpo do
        post reduz o alcance no Facebook e no LinkedIn."""
        if network == "instagram_stories":
            return ""  # a API de Stories não aceita legenda
        texto = self._legenda(network)
        limite = LIMITE_LEGENDA.get(network, 2000)
        return texto if len(texto) <= limite else texto[: limite - 1].rstrip() + "…"

    def _legenda(self, network: str) -> str:
        """Monta a legenda da rede.

        A ordem é de propósito. Título primeiro, porque é o único pedaço que
        aparece antes do "ver mais". Pergunta antes do contato, porque pedir
        comentário vale mais para o alcance do que pedir clique. Hashtags por
        último, porque atrapalham a leitura e não atrapalham o algoritmo.
        """
        tags = self.hashtags(network)
        pontos = self.pontos[:4]

        if network == "linkedin":
            corpo = "\n".join(f"{i:02d}. {p}" for i, p in enumerate(pontos, 1))
            partes = [f"{self.titulo}", "", corpo]
            if self.fecho:
                partes += ["", self.fecho]
            partes += ["", f"💬 {self.pergunta}"]
            # A API de comentários do LinkedIn exige o produto Community
            # Management API; sem ele o comentário dá 403. Enquanto isso, fontes
            # e site vão no próprio texto do post.
            if self.fontes:
                partes += ["", "Fontes: " + " · ".join(url for _, url in self.fontes[:2])]
            partes += [
                "",
                f"TECHDIM — {config.TAGLINE} · {config.REGIAO}",
                links.site(self.theme, "linkedin"),
                "",
                tags,
            ]
            return "\n".join(partes)

        if network == "facebook":
            corpo = "\n".join(f"• {p}" for p in pontos)
            partes = [f"{self.titulo}", "", corpo]
            if self.fecho:
                partes += ["", self.fecho]
            partes += [
                "",
                f"💬 {self.pergunta} Comenta aqui 👇" if not self.pergunta.endswith("?") else f"💬 {self.pergunta}",
                f"📍 TECHDIM — TI para empresas de {config.REGIAO}",
                "📎 Fontes e contato no primeiro comentário" if self.fontes
                else "📎 Contato no primeiro comentário",
                "",
                tags,
            ]
            return "\n".join(partes)

        # instagram: link não é clicável nem na legenda nem no comentário, então
        # aqui o endereço vai limpo e o clique de verdade acontece no Story e na
        # bio. O pedido é "manda" porque envio por DM, por alcance, está entre os
        # três sinais que o próprio Instagram diz pesar mais (os outros são o
        # tempo de exibição e as curtidas, também por alcance). Também é como o
        # post chega a quem decide a compra de TI na empresa, que raramente é
        # quem o viu primeiro.
        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
        corpo = "\n".join(f"{emojis[i]} {p}" for i, p in enumerate(pontos))
        partes = [f"{self.titulo}", ""]
        if not self.infografico:
            partes += ["Arraste para o lado →", ""]
        partes += [corpo]
        if self.fecho:
            partes += ["", self.fecho]
        partes += [
            "",
            f"💬 {self.pergunta}",
            "📲 Manda para quem cuida da TI da sua empresa",
            f"➕ Segue {config.IG_HANDLE} — TI para empresas de {config.REGIAO}",
            f"🔗 {config.SITE} (link na bio)",
        ]
        if self.fontes:
            partes += ["Fontes no primeiro comentário 👇"]
        partes += ["", tags]
        return "\n".join(partes)

    def comentario(self, network: str) -> str:
        """Primeiro comentário: fontes e o caminho mais curto até a conversa.

        No Facebook é aqui que mora o link clicável, com UTM, porque link no
        corpo do post derruba o alcance. No Instagram o link não é clicável em
        lugar nenhum, então o comentário só credita as fontes e aponta a bio.
        """
        if network in ("instagram_stories", "linkedin"):
            return ""  # LinkedIn: tudo no texto do post (ver caption)

        if network == "instagram":
            linhas = []
            if self.fontes:
                linhas.append("📎 Fontes: " + " · ".join(n for n, _ in self.fontes[:3]))
            linhas.append(f"🔗 Orçamento e contato no link da bio — {config.SITE}")
            return "\n".join(linhas)

        linhas = []
        if self.fontes:
            linhas.append("📎 Fontes:")
            linhas += [f"• {nome}: {url}" for nome, url in self.fontes[:3]]
            linhas.append("")
        zap = links.whatsapp(self.titulo, self.theme)
        if zap:
            linhas.append(f"💬 Fale agora com a TECHDIM no WhatsApp: {zap}")
        linhas.append(
            f"🌐 TECHDIM — {config.TAGLINE} · {config.REGIAO}: "
            f"{links.site(self.theme, network)}"
        )
        return "\n".join(linhas)


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


FEED_TIMEOUT = (5, 15)  # (conexão, leitura): feed lento não pode travar o job


def _baixar_feed(url: str):
    """Baixa o feed com tempo limite (o feedparser, sozinho, espera sem limite)."""
    resp = requests.get(url, timeout=FEED_TIMEOUT, headers={"User-Agent": feedparser.USER_AGENT})
    resp.raise_for_status()
    return feedparser.parse(resp.content)


def _fetch_entries(sources: list[tuple[str, str]], max_age_hours: int = 48) -> list[dict]:
    """Coleta manchetes recentes de todos os feeds, tolerando feed fora do ar."""
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=max_age_hours)
    items: list[dict] = []
    for url, lang in sources:
        try:
            feed = _baixar_feed(url)
        except Exception as exc:  # feed malformado, fora do ar ou lento
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
        except Exception:  # noqa: BLE001 — a curadoria é um extra, nunca pode derrubar o post
            log.exception("curadoria por IA falhou; usando filtro por palavra-chave")
        else:
            return Post(theme=theme, titulo=c["titulo"], pontos=c["pontos"],
                        fecho=c["fecho"], fontes=[c["fonte"]], curado_por_ia=True,
                        pergunta_propria=c.get("pergunta", ""), motivo=c.get("motivo", ""))
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


def _fontes(valor: object) -> list[tuple[str, str]]:
    """Pares (nome, url) válidos; qualquer item fora do formato é ignorado."""
    out: list[tuple[str, str]] = []
    for f in valor if isinstance(valor, list) else []:
        if isinstance(f, (list, tuple)) and len(f) == 2 and all(isinstance(x, str) for x in f):
            nome, url = uma_linha(f[0]), f[1].strip()
            if nome and url.startswith(("http://", "https://")):
                out.append((nome, url))
    return out


def _post_do_json(theme: str, item: object, origem: str = "") -> Post:
    """Post a partir do JSON de uma pauta. Levanta ValueError se faltar o essencial.

    O essencial é título e ao menos 2 pontos. O bloco "infografico" é opcional:
    se estiver malformado, o post sai com a arte antiga em vez de não sair.
    """
    if not isinstance(item, dict):
        raise ValueError("a pauta precisa ser um objeto JSON")
    titulo = cortar(item.get("titulo"), 160)
    pontos = [cortar(p, 260) for p in item.get("pontos", []) if isinstance(p, str)]
    pontos = [p for p in pontos if p]
    if not titulo or len(pontos) < 2:
        raise ValueError("a pauta precisa de titulo e ao menos 2 pontos")
    try:
        bloco = infografico.validar(item.get("infografico"), theme)
    except infografico.InfograficoInvalido as exc:
        log.warning("pauta de %s: bloco infografico inválido (%s); usando a arte antiga", theme, exc)
        bloco = None
    return Post(
        theme=theme,
        titulo=titulo,
        pontos=pontos[:4],
        fecho=cortar(item.get("fecho"), 200),
        fontes=_fontes(item.get("fontes")),
        motivo=cortar(item.get("motivo"), 300),
        infografico=bloco,
        origem=origem,
    )


def _destaque(today: dt.date, theme: str = "destaque", pasta: str = "destaques") -> Post:
    """Post escrito para o dia: content/<pasta>/AAAA-MM-DD.json.

    "destaques" é a notícia curada pela Routine; "especiais" são anúncios
    escritos sob demanda.
    """
    path = CONTENT_DIR / pasta / f"{today.isoformat()}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"nenhum destaque curado para {today.isoformat()} — crie {path.relative_to(ROOT)}"
        )
    return _post_do_json(theme, json.loads(path.read_text(encoding="utf-8")))


# ---------------------------------------------------------------- pauta do dia

PAUTA = ("noticias", "hacker", "dica", "servico")


def _da_pauta(theme: str, today: dt.date) -> Post | None:
    """Post escrito pela Routine em content/diario/AAAA-MM-DD/<tema>.json.

    Arquivo ausente ou malformado devolve None: quem chama cai no conteúdo de
    reserva (RSS ou acervo), para o horário nunca ficar vazio.
    """
    path = CONTENT_DIR / "diario" / today.isoformat() / f"{theme}.json"
    if not path.exists():
        return None
    try:
        return _post_do_json(theme, json.loads(path.read_text(encoding="utf-8")), origem="routine")
    except (json.JSONDecodeError, ValueError) as exc:
        log.warning("pauta do dia %s inválida (%s); usando reserva", path.name, exc)
        return None


def _semente(texto: str) -> int:
    """Número estável a partir de um texto (hash() do Python muda a cada execução)."""
    return sum(ord(c) for c in texto)


def build(theme: str, today: dt.date | None = None) -> Post:
    """Monta o post do tema para a data dada (determinístico por dia).

    Ordem: pauta do dia escrita pela Routine; depois a curadoria por IA ou o
    filtro de RSS (notícias); por fim o acervo autoral (conhecimento e serviços).
    """
    today = today or config.hoje()
    seed = today.toordinal()

    if theme in PAUTA:
        post = _da_pauta(theme, today)
        if post:
            return post

    if theme in FEEDS:
        post = _from_feeds(theme, seed)
        if post:
            return post
        # Nenhum feed respondeu: não deixa o horário vazio, publica peça autoral.
        log.warning("tema %s sem notícia disponível; usando conteúdo autoral", theme)
        alt_theme, alt_file = _FALLBACK[theme]
        return _from_pool(alt_theme, alt_file, seed + _semente(theme) % 7)

    if theme == "dica":
        return _from_pool("dica", "dicas.json", seed)
    if theme == "servico":
        return _from_pool("servico", "servicos.json", seed)
    if theme == "destaque":
        return _destaque(today)
    if theme == "especial":
        return _destaque(today, "especial", "especiais")

    raise ValueError(f"tema desconhecido: {theme}")
