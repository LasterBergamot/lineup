import pytest

import lineup.water_polo.water_polo_lineup_dto as dto_module
from lineup.water_polo.water_polo_lineup_dto import WaterPoloLineupDTO


def test_player_builder_raises_without_fields():
    with pytest.raises(ValueError):
        WaterPoloLineupDTO.Player.PlayerBuilder().build()


def test_dto_builder_raises_without_fields():
    with pytest.raises(ValueError):
        WaterPoloLineupDTO.WaterPoloLineupDTOBuilder().build()


def test_add_player_appends():
    player = dto_module.Player()
    builder = WaterPoloLineupDTO.WaterPoloLineupDTOBuilder()
    result = builder.add_player(player)
    assert result is builder
    assert len(builder.players) == 1


def test_add_player_raises_for_non_player():
    builder = WaterPoloLineupDTO.WaterPoloLineupDTOBuilder()
    with pytest.raises(ValueError):
        builder.add_player("not a player")
