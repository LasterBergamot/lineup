"""Writes a `WaterPoloLineupDTO` into the lineup template.

The `INDEX_*`, `COLUMN_*` and `ROW_*` constants are positions in `resources/rajtlista.docx`:
change the template and these must move with it.
"""

import logging
from pathlib import Path

from lineup.document.document_manager import (
    DocumentManager,
    update_cell_text,
    align_cell_vertically,
    align_cell_horizontally,
)
from lineup.document.pdf_converter import PdfConverter
from lineup.water_polo.water_polo_lineup_dto import WaterPoloLineupDTO

# Anchored to this file, not the working directory, so the template is found wherever the
# process is started from (uvicorn in the container, pytest, the CLI).
BACKEND_DIR = Path(__file__).resolve().parents[2]
FILE_NAME = str(BACKEND_DIR / "resources" / "rajtlista.docx")
RESULT_FILE_NAME = str(BACKEND_DIR / "resources" / "modified_rajtlista.docx")

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
    """Fills the lineup template from a `WaterPoloLineupDTO`.

    The template is opened once per instance and edited in place, so create a new creator for
    each document.
    """

    def __init__(self):
        """Open the template; raises `FileNotFoundError` (logged first) if it is missing."""
        try:
            self.manager = DocumentManager(FILE_NAME)
        except FileNotFoundError:
            logging.error(f"File not found: {FILE_NAME}")
            raise

    def create_document(self, dto: WaterPoloLineupDTO):
        """Fill the template and save it to `RESULT_FILE_NAME` (used by the command-line demo)."""
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
        """Fill the template and return the `.docx` bytes without touching the disk."""
        try:
            self.manager.setup_style()
            self.manager.remove_non_space_tab_stops()
            self.__update_paragraphs(dto)
            self.__update_player_table(dto)
            return self.manager.to_bytes()
        except Exception as e:
            logging.error(f"Error creating document bytes: {e}")
            raise

    def create_pdf_bytes(self, dto: WaterPoloLineupDTO) -> bytes:
        """Fill the template and convert it to PDF bytes (needs LibreOffice, so container only)."""
        docx_bytes = self.create_document_bytes(dto)
        return PdfConverter().convert(docx_bytes)

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
