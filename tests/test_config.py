import config


def test_agora_esta_em_brasilia():
    agora = config.agora()
    assert agora.utcoffset().total_seconds() == -3 * 3600
    assert config.hoje() == agora.date()


def test_site_divulgado_esta_no_ar_e_nao_e_o_dominio_fora_do_ar():
    assert config.SITE_URL.startswith("https://") and config.SITE in config.SITE_URL
    assert config.SITE_FORA_DO_AR not in config.SITE and config.SITE_FORA_DO_AR not in config.SITE_URL

