"""Data objects and builders for a water polo lineup sheet."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class WaterPoloLineupDTO:
    """Plain data object for one lineup sheet, independent of HTTP and the database.

    Both the one-off endpoint and saved lineups are turned into this before rendering. Build it
    with `WaterPoloLineupDTOBuilder`, which checks the required fields.
    """

    match: str
    division: str
    team_name: str
    cap: str
    date: str
    coach: str
    doctor: str
    assistant_coach: str
    team_leader: str
    ball_thrower: str
    players: List["WaterPoloLineupDTO.Player"] = field(default_factory=list)

    class WaterPoloLineupDTOBuilder:
        """Step-by-step construction of a `WaterPoloLineupDTO`; `build()` validates it."""

        def __init__(self):
            """Start with every field unset and no players."""
            self.match: Optional[str] = None
            self.division: Optional[str] = None
            self.team_name: Optional[str] = None
            self.cap: Optional[str] = None
            self.date: Optional[str] = None
            self.coach: Optional[str] = None
            self.doctor: Optional[str] = None
            self.assistant_coach: Optional[str] = None
            self.team_leader: Optional[str] = None
            self.ball_thrower: Optional[str] = None
            self.players: List["WaterPoloLineupDTO.Player"] = []

        def set_match(
            self, match: str
        ) -> "WaterPoloLineupDTO.WaterPoloLineupDTOBuilder":
            """Set the match title ("Home - Away")."""
            self.match = match
            return self

        def set_division(
            self, division: str
        ) -> "WaterPoloLineupDTO.WaterPoloLineupDTOBuilder":
            """Set the division / class (Osztály)."""
            self.division = division
            return self

        def set_team_name(
            self, team_name: str
        ) -> "WaterPoloLineupDTO.WaterPoloLineupDTOBuilder":
            """Set the name of the team the sheet is for."""
            self.team_name = team_name
            return self

        def set_cap(self, cap: str) -> "WaterPoloLineupDTO.WaterPoloLineupDTOBuilder":
            """Set the cap colour: "Fehér" or "Kék"."""
            self.cap = cap
            return self

        def set_date(self, date: str) -> "WaterPoloLineupDTO.WaterPoloLineupDTOBuilder":
            """Set the match date, as the text to print."""
            self.date = date
            return self

        def set_coach(
            self, coach: str
        ) -> "WaterPoloLineupDTO.WaterPoloLineupDTOBuilder":
            """Set the coach (Edző)."""
            self.coach = coach
            return self

        def set_doctor(
            self, doctor: Optional[str]
        ) -> "WaterPoloLineupDTO.WaterPoloLineupDTOBuilder":
            """Set the official doctor (Hivatalos orvos); optional, printed blank when unset."""
            self.doctor = doctor
            return self

        def set_assistant_coach(
            self, assistant_coach: Optional[str]
        ) -> "WaterPoloLineupDTO.WaterPoloLineupDTOBuilder":
            """Set the assistant coach (Segédedző); optional."""
            self.assistant_coach = assistant_coach
            return self

        def set_team_leader(
            self, team_leader: Optional[str]
        ) -> "WaterPoloLineupDTO.WaterPoloLineupDTOBuilder":
            """Set the team leader (Csapatvezető); optional."""
            self.team_leader = team_leader
            return self

        def set_ball_thrower(
            self, ball_thrower: Optional[str]
        ) -> "WaterPoloLineupDTO.WaterPoloLineupDTOBuilder":
            """Set the ball thrower (Labdabedobó); optional."""
            self.ball_thrower = ball_thrower
            return self

        def set_players(
            self, players: List["WaterPoloLineupDTO.Player"]
        ) -> "WaterPoloLineupDTO.WaterPoloLineupDTOBuilder":
            """Replace the whole player list."""
            self.players = players
            return self

        def add_player(
            self, player: "WaterPoloLineupDTO.Player"
        ) -> "WaterPoloLineupDTO.WaterPoloLineupDTOBuilder":
            """Append one `Player`; raises `ValueError` for anything else."""
            if not isinstance(player, WaterPoloLineupDTO.Player):
                raise ValueError("player must be an instance of Player")
            self.players.append(player)
            return self

        def build(self) -> "WaterPoloLineupDTO":
            """Return the DTO; raises `ValueError` unless match, division, team name, cap, date and coach are set.

            Staff fields are optional (saved lineups may omit them) and default to empty strings, which
            render as blank lines on the sheet.
            """
            # Staff fields are optional (saved lineups may omit them) and render
            # as blank lines on the sheet; only the match details are required.
            if not all(
                [
                    self.match,
                    self.division,
                    self.team_name,
                    self.cap,
                    self.date,
                    self.coach,
                ]
            ):
                raise ValueError(
                    "Match, division, team name, cap, date and coach must be set"
                )
            return WaterPoloLineupDTO(
                match=self.match,
                division=self.division,
                team_name=self.team_name,
                cap=self.cap,
                date=self.date,
                coach=self.coach,
                doctor=self.doctor or "",
                assistant_coach=self.assistant_coach or "",
                team_leader=self.team_leader or "",
                ball_thrower=self.ball_thrower or "",
                players=self.players,
            )

    @dataclass
    class Player:
        """One row of the player table: cap number, name and NSSZ (federation registration) number."""

        cap_number: Optional[int] = None
        name: Optional[str] = None
        nssz_number: Optional[str] = None

        class PlayerBuilder:
            """Step-by-step construction of a `Player`; `build()` requires all three fields."""

            def __init__(self):
                """Start with every field unset."""
                self.cap_number = None
                self.name = None
                self.nssz_number = None

            def set_cap_number(
                self, cap_number: int
            ) -> "WaterPoloLineupDTO.Player.PlayerBuilder":
                """Set the cap number (the table row the player is written to)."""
                self.cap_number = cap_number
                return self

            def set_name(self, name: str) -> "WaterPoloLineupDTO.Player.PlayerBuilder":
                """Set the player's full name."""
                self.name = name
                return self

            def set_nssz_number(
                self, nssz_number: str
            ) -> "WaterPoloLineupDTO.Player.PlayerBuilder":
                """Set the player's NSSZ registration number."""
                self.nssz_number = nssz_number
                return self

            def build(self) -> "WaterPoloLineupDTO.Player":
                """Return the `Player`; raises `ValueError` if the cap number, name or NSSZ number is missing."""
                if not all([self.cap_number, self.name, self.nssz_number]):
                    raise ValueError("All fields must be set")
                return WaterPoloLineupDTO.Player(
                    cap_number=self.cap_number,
                    name=self.name,
                    nssz_number=self.nssz_number,
                )
