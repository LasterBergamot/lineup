from dataclasses import dataclass, field
from typing import List, Optional


class Player:
    pass


@dataclass
class WaterPoloLineupDTO:
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
    players: List[Player] = field(default_factory=list)

    class WaterPoloLineupDTOBuilder:
        def __init__(self):
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
            self.players: List[Player] = []

        def set_match(
            self, match: str
        ) -> "WaterPoloLineupDTO.WaterPoloLineupDTOBuilder":
            self.match = match
            return self

        def set_division(
            self, division: str
        ) -> "WaterPoloLineupDTO.WaterPoloLineupDTOBuilder":
            self.division = division
            return self

        def set_team_name(
            self, team_name: str
        ) -> "WaterPoloLineupDTO.WaterPoloLineupDTOBuilder":
            self.team_name = team_name
            return self

        def set_cap(self, cap: str) -> "WaterPoloLineupDTO.WaterPoloLineupDTOBuilder":
            self.cap = cap
            return self

        def set_date(self, date: str) -> "WaterPoloLineupDTO.WaterPoloLineupDTOBuilder":
            self.date = date
            return self

        def set_coach(
            self, coach: str
        ) -> "WaterPoloLineupDTO.WaterPoloLineupDTOBuilder":
            self.coach = coach
            return self

        def set_doctor(
            self, doctor: str
        ) -> "WaterPoloLineupDTO.WaterPoloLineupDTOBuilder":
            self.doctor = doctor
            return self

        def set_assistant_coach(
            self, assistant_coach: str
        ) -> "WaterPoloLineupDTO.WaterPoloLineupDTOBuilder":
            self.assistant_coach = assistant_coach
            return self

        def set_team_leader(
            self, team_leader: str
        ) -> "WaterPoloLineupDTO.WaterPoloLineupDTOBuilder":
            self.team_leader = team_leader
            return self

        def set_ball_thrower(
            self, ball_thrower: str
        ) -> "WaterPoloLineupDTO.WaterPoloLineupDTOBuilder":
            self.ball_thrower = ball_thrower
            return self

        def set_players(
            self, players: List[Player]
        ) -> "WaterPoloLineupDTO.WaterPoloLineupDTOBuilder":
            self.players = players
            return self

        def add_player(
            self, player: Player
        ) -> "WaterPoloLineupDTO.WaterPoloLineupDTOBuilder":
            if not isinstance(player, Player):
                raise ValueError("player must be an instance of Player")
            self.players.append(player)
            return self

        def build(self) -> "WaterPoloLineupDTO":
            if not all(
                [
                    self.match,
                    self.division,
                    self.team_name,
                    self.cap,
                    self.date,
                    self.coach,
                    self.doctor,
                    self.assistant_coach,
                    self.team_leader,
                    self.ball_thrower,
                ]
            ):
                raise ValueError("All fields must be set")
            return WaterPoloLineupDTO(
                match=self.match,
                division=self.division,
                team_name=self.team_name,
                cap=self.cap,
                date=self.date,
                coach=self.coach,
                doctor=self.doctor,
                assistant_coach=self.assistant_coach,
                team_leader=self.team_leader,
                ball_thrower=self.ball_thrower,
                players=self.players,
            )

    @dataclass
    class Player:
        cap_number: Optional[int] = None
        name: Optional[str] = None
        nssz_number: Optional[str] = None

        class PlayerBuilder:
            def __init__(self):
                self.cap_number = None
                self.name = None
                self.nssz_number = None

            def set_cap_number(
                self, cap_number: int
            ) -> "WaterPoloLineupDTO.Player.PlayerBuilder":
                self.cap_number = cap_number
                return self

            def set_name(self, name: str) -> "WaterPoloLineupDTO.Player.PlayerBuilder":
                self.name = name
                return self

            def set_nssz_number(
                self, nssz_number: str
            ) -> "WaterPoloLineupDTO.Player.PlayerBuilder":
                self.nssz_number = nssz_number
                return self

            def build(self) -> "WaterPoloLineupDTO.Player":
                if not all([self.cap_number, self.name, self.nssz_number]):
                    raise ValueError("All fields must be set")
                return WaterPoloLineupDTO.Player(
                    cap_number=self.cap_number,
                    name=self.name,
                    nssz_number=self.nssz_number,
                )
