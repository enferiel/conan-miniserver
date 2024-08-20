# import packages
import re
import datetime
import pathlib
import dataclasses
import enum


class PlayerEventType(enum.Enum):
    JOIN = 0
    DISCONNECT = 1


@dataclasses.dataclass
class PlayerEvent:
    type: PlayerEventType
    player: str
    timestamp: datetime.datetime


@dataclasses.dataclass
class Log:
    events: list[PlayerEvent]
    end_timestamp: datetime.datetime

    def get_durations(self) -> dict[str, float]:
        durations: dict[str, float] = {}
        joins: dict[str, datetime.datetime] = {}
        for event in self.events:
            if event.type == PlayerEventType.JOIN:
                joins[event.player] = event.timestamp
            elif event.type == PlayerEventType.DISCONNECT and event.player in joins:
                duration = event.timestamp - joins[event.player]
                durations[event.player] = durations.get(event.player, 0.0) + duration.total_seconds()
                del joins[event.player]
        for player, timestamp in joins.items():
            duration = self.end_timestamp - timestamp
            durations[player] = durations.get(player, 0.0) + duration.total_seconds()

        return durations

    @staticmethod
    def get_total_durations(logs: list["Log"]) -> dict[str, float]:
        durations: dict[str, float] = {}
        for log in logs:
            for player, duration in log.get_durations().items():
                durations[player] = durations.get(player, 0.0) + duration
        return durations


def _parse_player(line: str) -> str:
    return line.strip().split()[-1]


def _parse_timestamp(line: str) -> datetime.datetime:
    pattern = r"^\[(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}:\d{3})\].*"
    match = re.search(pattern, line.strip())

    if not match:
        return None

    timestamp = datetime.datetime.strptime(match.group(1), "%Y.%m.%d-%H.%M.%S:%f")

    return timestamp


def parse_logs(db_dir: pathlib.Path) -> list[Log]:
    logs: list[Log] = []
    for log_file in db_dir.rglob("*.log"):
        events: list[PlayerEvent] = []
        with open(log_file, "r") as file:
            for line in file.readlines():
                if "Join succeeded" in line or "Player disconnected" in line:
                    player = _parse_player(line)
                    if player == "Unknown":
                        continue

                    timestamp = _parse_timestamp(line)
                    event_type = PlayerEventType.JOIN if "Join succeeded" in line else PlayerEventType.DISCONNECT
                    event = PlayerEvent(event_type, player, timestamp)
                    events.append(event)

            end_timestamp = _parse_timestamp(line)
            logs.append(Log(events, end_timestamp))

    return logs
