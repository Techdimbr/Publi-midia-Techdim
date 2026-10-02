"""Os exemplos de padrão visual continuam gerando (são a vitrine do estilo)."""
import exemplos_infograficos as ex


def test_historias_geram_cinco_pngs(tmp_path):
    ex.historias(tmp_path)
    assert len(list(tmp_path.glob("*.png"))) == len(ex.PECAS) == 5


def test_variantes_de_windows_geram_cinco_pngs(tmp_path):
    ex.windows(tmp_path)
    assert len(list(tmp_path.glob("*.png"))) == len(ex.VARIANTES) == 5


def test_modo_invalido_mostra_ajuda(capsys):
    assert ex.main(["nada"]) == 1
    assert "historias" in capsys.readouterr().out
