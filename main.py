from lineup.water_polo.water_polo_start_list_creator import WaterPoloStartListCreator
from lineup.water_polo.water_polo_start_list_dto import WaterPoloStartListDTO

NSSZ_NUMBER = "MVLSZ123456789"

NAME = "Török András"


def main():
    players = [
        WaterPoloStartListDTO.Player.PlayerBuilder()
        .set_name(NAME)
        .set_nssz_number(NSSZ_NUMBER)
        .set_cap_number(cap_number)
        .build()
        for cap_number in range(1, 15)
    ]
    dto = (
        WaterPoloStartListDTO.WaterPoloStartListDTOBuilder()
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
    WaterPoloStartListCreator().create_document(dto)


if __name__ == "__main__":
    main()
