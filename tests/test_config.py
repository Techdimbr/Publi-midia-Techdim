import config


def test_agora_esta_em_brasilia():
    agora = config.agora()
    assert agora.utcoffset().total_seconds() == -3 * 3600
    assert config.hoje() == agora.date()
