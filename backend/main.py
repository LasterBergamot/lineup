from lineup.water_polo.water_polo_lineup_creator import WaterPoloLineupCreator
from lineup.water_polo.water_polo_lineup_dto import WaterPoloLineupDTO

NSSZ_NUMBER = "MVLSZ123456789"

NAME = "Török András"


def main():
    players = [
        WaterPoloLineupDTO.Player.PlayerBuilder()
        .set_name(NAME)
        .set_nssz_number(NSSZ_NUMBER)
        .set_cap_number(cap_number)
        .build()
        for cap_number in range(1, 16)
    ]
    dto = (
        WaterPoloLineupDTO.WaterPoloLineupDTOBuilder()
        .set_match("SZVTK - Csongrád")
        .set_division("OB II.")
        .set_team_name("SZVTK")
        .set_cap("Fehér")
        .set_date("2024. 12. 21.")
        .set_coach(NAME)
        .set_doctor(NAME)
        .set_assistant_coach(NAME)
        .set_team_leader(NAME)
        .set_ball_thrower(NAME)
        .set_players(players)
        .build()
    )
    WaterPoloLineupCreator().create_document(dto)


if __name__ == "__main__":
    main()
