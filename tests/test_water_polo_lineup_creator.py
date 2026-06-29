import pytest

from lineup.water_polo.water_polo_lineup_creator import WaterPoloLineupCreator
from lineup.water_polo.water_polo_lineup_dto import WaterPoloLineupDTO


def _make_player(cap_number: int) -> WaterPoloLineupDTO.Player:
    return (
        WaterPoloLineupDTO.Player.PlayerBuilder()
        .set_cap_number(cap_number)
        .set_name("Török András")
        .set_nssz_number("MVLSZ123456789")
        .build()
    )


def _make_dto(players: list) -> WaterPoloLineupDTO:
    return (
        WaterPoloLineupDTO.WaterPoloLineupDTOBuilder()
        .set_match("SZVTK - Csongrád")
        .set_division("OB II.")
        .set_team_name("SZVTK")
        .set_cap("Fehér")
        .set_date("2024. 12. 21.")
        .set_coach("Török András")
        .set_doctor("Török András")
        .set_assistant_coach("Török András")
        .set_team_leader("Török András")
        .set_ball_thrower("Török András")
        .set_players(players)
        .build()
    )


def test_create_document_bytes_returns_bytes():
    dto = _make_dto([_make_player(i) for i in range(1, 16)])
    result = WaterPoloLineupCreator().create_document_bytes(dto)
    assert isinstance(result, bytes)


def test_create_document_bytes_is_valid_docx():
    dto = _make_dto([_make_player(i) for i in range(1, 16)])
    result = WaterPoloLineupCreator().create_document_bytes(dto)
    assert result[:2] == b"PK"


def test_create_document_bytes_partial_players():
    dto = _make_dto([_make_player(1), _make_player(7)])
    result = WaterPoloLineupCreator().create_document_bytes(dto)
    assert isinstance(result, bytes)
    assert result[:2] == b"PK"


def test_create_document_bytes_kek_cap():
    dto_kek = (
        WaterPoloLineupDTO.WaterPoloLineupDTOBuilder()
        .set_match("SZVTK - Csongrád")
        .set_division("OB II.")
        .set_team_name("SZVTK")
        .set_cap("Kék")
        .set_date("2024. 12. 21.")
        .set_coach("Török András")
        .set_doctor("Török András")
        .set_assistant_coach("Török András")
        .set_team_leader("Török András")
        .set_ball_thrower("Török András")
        .set_players([_make_player(1)])
        .build()
    )
    result = WaterPoloLineupCreator().create_document_bytes(dto_kek)
    assert isinstance(result, bytes)


def test_creator_raises_on_missing_template(tmp_path, monkeypatch):
    from docx.opc.exceptions import PackageNotFoundError
    import lineup.water_polo.water_polo_lineup_creator as creator_module

    monkeypatch.setattr(creator_module, "FILE_NAME", str(tmp_path / "missing.docx"))
    with pytest.raises(PackageNotFoundError):
        WaterPoloLineupCreator()


def test_creator_init_raises_file_not_found():
    from unittest.mock import patch
    import lineup.water_polo.water_polo_lineup_creator as creator_module

    with patch.object(creator_module, "DocumentManager", side_effect=FileNotFoundError):
        with pytest.raises(FileNotFoundError):
            WaterPoloLineupCreator()


def test_create_document_saves_file(tmp_path, monkeypatch):
    import lineup.water_polo.water_polo_lineup_creator as creator_module

    monkeypatch.setattr(
        creator_module, "RESULT_FILE_NAME", str(tmp_path / "output.docx")
    )
    dto = _make_dto([_make_player(i) for i in range(1, 16)])
    WaterPoloLineupCreator().create_document(dto)
    assert (tmp_path / "output.docx").exists()


def test_create_document_bytes_raises_on_error():
    from unittest.mock import patch

    dto = _make_dto([_make_player(1)])
    creator = WaterPoloLineupCreator()
    with patch.object(
        creator.manager, "setup_style", side_effect=RuntimeError("forced")
    ):
        with pytest.raises(RuntimeError):
            creator.create_document_bytes(dto)


def test_create_document_raises_on_error():
    from unittest.mock import patch

    dto = _make_dto([_make_player(1)])
    creator = WaterPoloLineupCreator()
    with patch.object(
        creator.manager, "setup_style", side_effect=RuntimeError("forced")
    ):
        with pytest.raises(RuntimeError):
            creator.create_document(dto)


def test_create_pdf_bytes_returns_pdf():
    from unittest.mock import patch

    dto = _make_dto([_make_player(i) for i in range(1, 16)])
    fake_pdf = b"%PDF-1.4 fake"
    with patch(
        "lineup.water_polo.water_polo_lineup_creator.PdfConverter.convert",
        return_value=fake_pdf,
    ):
        result = WaterPoloLineupCreator().create_pdf_bytes(dto)
    assert result == fake_pdf
