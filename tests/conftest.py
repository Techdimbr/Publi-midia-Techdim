"""Fixtures comuns: pauta de exemplo, data fixa e nada de rede."""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import shutil

import pytest

import config
import content

DIA = dt.date(2026, 10, 2)
CONTENT_REAL = content.CONTENT_DIR


def bloco_infografico(**extra) -> dict:
    """Bloco "infografico" mínimo e válido, como a Routine escreve."""
    base = {
        "cena_composta": {"fundo": "datacenter", "elementos": ["rack", "nuvem"], "legenda": "BACKUP QUE RESTAURA"},
        "titulo_branco": "Backup que ninguém restaurou",
        "titulo_destaque": "é extintor sem teste.",
        "historia": "Ter backup não é o mesmo que conseguir voltar. Só a restauração testada mostra se os dados voltam.",
        "licoes": [
            ["Defina o essencial", "Liste sistemas e dados críticos."],
            ["Copie fora do local", "Mantenha cópias em nuvem ou em outro lugar."],
            ["Teste a restauração", "Restaure arquivos de verdade em intervalos fixos."],
        ],
        "pergunta": "Quando foi a última vez que você restaurou um backup?",
        "hashtags": ["#Backup", "#Continuidade", "#TI", "#TECHDIM"],
    }
    base.update(extra)
    return base


def pauta(**extra) -> dict:
    base = {
        "titulo": "Backup que nunca foi restaurado é como extintor que ninguém testou",
        "pontos": ["O problema do cliente", "O que a TECHDIM faz", "O resultado esperado"],
        "fecho": "Fale com a TECHDIM.",
        "motivo": "Serviço de backup testado.",
        "fontes": [["techdim.com.br", "https://www.techdim.com.br"]],
        "infografico": bloco_infografico(),
    }
    base.update(extra)
    return base


@pytest.fixture
def conteudo(tmp_path, monkeypatch):
    """CONTENT_DIR temporário com a pauta do dia; devolve (pasta_do_dia, escrever)."""
    for acervo in ("dicas.json", "servicos.json"):   # reserva usada quando a pauta falha
        shutil.copy(CONTENT_REAL / acervo, tmp_path / acervo)
    monkeypatch.setattr(content, "CONTENT_DIR", tmp_path)
    monkeypatch.setattr(config, "hoje", lambda: DIA)
    pasta = tmp_path / "diario" / DIA.isoformat()
    pasta.mkdir(parents=True)

    def escrever(tema: str, dados: object) -> pathlib.Path:
        arq = pasta / f"{tema}.json"
        arq.write_text(dados if isinstance(dados, str) else json.dumps(dados, ensure_ascii=False), encoding="utf-8")
        return arq

    return pasta, escrever
