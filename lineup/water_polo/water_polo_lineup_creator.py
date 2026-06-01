import logging

from lineup.document.document_manager import (
    DocumentManager,
    update_cell_text,
    align_cell_vertically,
    align_cell_horizontally,
)
from lineup.water_polo.water_polo_lineup_dto import WaterPoloLineupDTO

FILE_NAME = "resources/rajtlista.docx"
RESULT_FILE_NAME = "resources/modified_rajtlista.docx"

INDEX_MATCH = 5
INDEX_DIVISION = 6
INDEX_TEAM_NAME_AND_CAP = 7
INDEX_DATE = 8
INDEX_COACH_AND_DOCTOR = 15
INDEX_ASSISTANT_COACH = 16
INDEX_TEAM_LEADER = 17
INDEX_BALL_THROWER = 18

COLUMN_NAME = 1
COLUMN_NSSZ = 2

ROW_FIRST = 1
ROW_LAST = 14

logging.basicConfig(level=logging.INFO)


class WaterPoloLineupCreator:
    def __init__(self):
        try:
            self.manager = DocumentManager(FILE_NAME)
        except FileNotFoundError:
            logging.error(f"File not found: {FILE_NAME}")
            raise

    def create_document(self, dto: WaterPoloLineupDTO):
        try:
            self.manager.setup_style()
            self.manager.remove_non_space_tab_stops()
            self.__update_paragraphs(dto)
            self.__update_player_table(dto)
            self.manager.save(RESULT_FILE_NAME)
            logging.info(f"Document saved as {RESULT_FILE_NAME}")
        except Exception as e:
            logging.error(f"Error creating document: {e}")
            raise

    def create_document_bytes(self, dto: WaterPoloLineupDTO) -> bytes:
        try:
            self.manager.setup_style()
            self.manager.remove_non_space_tab_stops()
            self.__update_paragraphs(dto)
            self.__update_player_table(dto)
            return self.manager.to_bytes()
        except Exception as e:
            logging.error(f"Error creating document bytes: {e}")
            raise

    def __update_paragraphs(self, dto):
        self.manager.update_paragraph_text(INDEX_MATCH, f"Mérkőzés:\t{dto.match}")
        self.manager.update_paragraph_text(INDEX_DIVISION, f"Osztály:\t{dto.division}")
        self.__update_team_name_and_cap_paragraph(dto)
        self.manager.update_paragraph_text(INDEX_DATE, f"Dátum:\t{dto.date}")
        self.manager.update_paragraph_text(
            INDEX_COACH_AND_DOCTOR,
            f"Edző:\t{dto.coach}\t\tHivatalos orvos:\t{dto.doctor}",
        )
        self.manager.update_paragraph_text(
            INDEX_ASSISTANT_COACH, f"Segédedző:\t{dto.assistant_coach}"
        )
        self.manager.update_paragraph_text(
            INDEX_TEAM_LEADER, f"Csapatvezető:\t{dto.team_leader}"
        )
        self.manager.update_paragraph_text(
            INDEX_BALL_THROWER, f"Labdabedobó:\t{dto.ball_thrower}"
        )

    def __update_team_name_and_cap_paragraph(self, dto):
        self.manager.update_paragraph_text(
            INDEX_TEAM_NAME_AND_CAP, f"Csapat neve:\t{dto.team_name}\t\t"
        )
        self.manager.add_run(INDEX_TEAM_NAME_AND_CAP, "Fehér")
        self.manager.add_run(INDEX_TEAM_NAME_AND_CAP, "  /  ")
        self.manager.add_run(INDEX_TEAM_NAME_AND_CAP, "Kék")
        self.manager.underline_run(INDEX_TEAM_NAME_AND_CAP, dto.cap)
        self.manager.make_run_bold(INDEX_TEAM_NAME_AND_CAP, dto.cap)

    def __update_player_table(self, dto):
        for player in dto.players:
            cap_number = player.cap_number
            self.__update_cell_text_and_align_name(cap_number, player)
            self.__update_cell_text_and_align_nssz(cap_number, player)

    def __update_cell_text_and_align_name(self, cap_number, player):
        cell = self.manager.get_table_cell(row=cap_number, column=COLUMN_NAME)
        update_cell_text(cell, player.name)
        align_cell_vertically(cell)
        align_cell_horizontally(cell)

    def __update_cell_text_and_align_nssz(self, cap_number, player):
        cell = self.manager.get_table_cell(row=cap_number, column=COLUMN_NSSZ)
        update_cell_text(cell, player.nssz_number)
        align_cell_vertically(cell)
        align_cell_horizontally(cell)
