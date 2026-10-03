import pytest

from lineup.water_polo.water_polo_lineup_dto import WaterPoloLineupDTO


def test_player_builder_raises_without_fields():
    with pytest.raises(ValueError):
        WaterPoloLineupDTO.Player.PlayerBuilder().build()


def test_dto_builder_raises_without_fields():
    with pytest.raises(ValueError):
        WaterPoloLineupDTO.WaterPoloLineupDTOBuilder().build()


def test_add_player_appends():
    player = (
        WaterPoloLineupDTO.Player.PlayerBuilder()
        .set_cap_number(1)
        .set_name("Török András")
        .set_nssz_number("MVLSZ123456789")
        .build()
    )
    builder = WaterPoloLineupDTO.WaterPoloLineupDTOBuilder()
    result = builder.add_player(player)
    assert result is builder
    assert len(builder.players) == 1


def test_add_player_raises_for_non_player():
    builder = WaterPoloLineupDTO.WaterPoloLineupDTOBuilder()
    with pytest.raises(ValueError):
        builder.add_player("not a player")


def test_dto_builder_defaults_missing_staff_fields_to_empty():
    dto = (
        WaterPoloLineupDTO.WaterPoloLineupDTOBuilder()
        .set_match("SZVTK - Csongrád")
        .set_division("OB II.")
        .set_team_name("SZVTK")
        .set_cap("Fehér")
        .set_date("2024. 12. 21.")
        .set_coach("Török András")
        .build()
    )
    assert dto.doctor == ""
    assert dto.assistant_coach == ""
    assert dto.team_leader == ""
    assert dto.ball_thrower == ""
