"""Diário do dia, anti-duplicidade e registro de execução ignorada."""
import json

import main
import movimentos
import registro


def entrada(tema, **redes):
    return {"hora": "08:00", "tema": tema, "titulo": "t", "curadoria": "-", "arquivo": "x.md",
            "redes": {"facebook": "-", "instagram": "-", "instagram_stories": "-", "linkedin": "-", **redes},
            "links": {}, "ids": {}, "comentou": []}


def test_ler_indice_tolera_ausente_invalido_e_formato_errado(tmp_path):
    assert registro.ler_indice("") == []
    assert registro.ler_indice(tmp_path / "nao-existe.json") == []
    ruim = tmp_path / "ruim.json"
    ruim.write_text("{não é json")
    assert registro.ler_indice(ruim) == []
    ruim.write_text('{"nao": "lista"}')
    assert registro.ler_indice(ruim) == []
    ruim.write_text('[1, "a", {"tema": "hacker", "redes": {"facebook": "publicado"}}]')
    assert registro.ler_indice(ruim) == [{"tema": "hacker", "redes": {"facebook": "publicado"}}]


def test_redes_publicadas_so_conta_o_tema_pedido_e_status_publicado():
    entradas = [
        entrada("hacker", facebook="publicado", instagram="falhou", linkedin="não configurado"),
        entrada("noticias", facebook="publicado", instagram="publicado"),
        entrada("hacker", instagram_stories="publicado"),
    ]
    assert registro.redes_publicadas(entradas, "hacker") == {"facebook", "instagram_stories"}
    assert registro.redes_publicadas(entradas, "dica") == set()
    assert registro.redes_publicadas([{"tema": "hacker", "redes": None}], "hacker") == set()


def rodar_pendentes(capsys, tmp_path, entradas, tema="hacker", redes=""):
    idx = tmp_path / "index.json"
    idx.write_text(json.dumps(entradas))
    args = ["pendentes", "--theme", tema, "--indice", str(idx)] + (["--networks", redes] if redes else [])
    assert main.main(args) == 0
    saida = dict(linha.split("=", 1) for linha in capsys.readouterr().out.strip().splitlines())
    return saida["redes"], saida["pular"]


def test_pendentes_tema_novo_publica_em_todas_as_redes(capsys, tmp_path):
    redes, pular = rodar_pendentes(capsys, tmp_path, [])
    assert redes == "linkedin,facebook,instagram,instagram_stories" and pular == "false"


def test_pendentes_tema_completo_e_pulado(capsys, tmp_path):
    todas = dict(facebook="publicado", instagram="publicado", instagram_stories="publicado", linkedin="publicado")
    redes, pular = rodar_pendentes(capsys, tmp_path, [entrada("hacker", **todas)])
    assert redes == "" and pular == "true"


def test_pendentes_repete_so_a_rede_que_falhou(capsys, tmp_path):
    parcial = entrada("hacker", facebook="publicado", instagram="falhou", instagram_stories="publicado", linkedin="publicado")
    redes, pular = rodar_pendentes(capsys, tmp_path, [parcial])
    assert redes == "instagram" and pular == "false"


def test_pendentes_respeita_as_redes_pedidas(capsys, tmp_path):
    ja = entrada("hacker", facebook="publicado")
    redes, pular = rodar_pendentes(capsys, tmp_path, [ja], redes="facebook,linkedin")
    assert redes == "linkedin" and pular == "false"
    redes, pular = rodar_pendentes(capsys, tmp_path, [ja], redes="facebook")
    assert redes == "" and pular == "true"


def test_execucao_ignorada_entra_no_diario_como_pulado(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "MANIFEST", tmp_path / "nao-existe.json")
    monkeypatch.setattr(main, "RESULTADO", tmp_path / "nao-existe-2.json")
    assert main.registrar(tmp_path, "hacker", pulado="tema já publicado hoje") == 0
    dia = movimentos.agora_brasilia().strftime("%Y-%m-%d")
    linhas = [json.loads(x) for x in (tmp_path / "registros" / dia / "movimentos.jsonl").read_text().splitlines()]
    assert [e["tipo"] for e in linhas] == ["iniciado", "pulado"]
    assert "já publicado" in linhas[1]["detalhe"]
    assert not list((tmp_path / "registros" / dia).glob("*-hacker.md"))   # sem registro de post


def test_registro_redige_credenciais_e_mantem_indice(tmp_path):
    manifest = {
        "theme": "servico", "date": "2026-10-02", "titulo": "Título com EAA" + "A" * 30, "curadoria": "x", "motivo": "",
        "fontes": [], "networks": {"facebook": {"caption": "legenda", "comentario": "", "files": ["posts/x.png"]}},
    }
    resultado = {"redes": {"facebook": {"status": "publicado", "id": "1_2", "link": "https://fb/1", "comentario": "ok"}}}
    arq = registro.escrever(manifest, resultado, tmp_path, "https://run")
    texto = arq.read_text(encoding="utf-8")
    assert "EAAAAAA" not in texto and "[REDIGIDO]" in texto
    indice = json.loads((arq.parent / "index.json").read_text())
    assert indice[0]["redes"]["facebook"] == "publicado" and indice[0]["ids"] == {"facebook": "1_2"}
    # o que o registro grava é exatamente o que a anti-duplicidade lê
    assert registro.redes_publicadas(registro.ler_indice(arq.parent / "index.json"), "servico") == {"facebook"}
