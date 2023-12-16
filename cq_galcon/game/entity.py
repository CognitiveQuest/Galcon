from __future__ import annotations

from typing import Optional, NamedTuple

import math

from cq_galcon.game.constants import MAX_FLEET_SPEED, Team


class MoveCommand:
    fleet: Fleet
    destination: Planet
    split: bool

    def __init__(self, fleet: Fleet, destination: Planet, split: bool = False):
        self.fleet = fleet
        self.destination = destination
        self.split = split


class Position(NamedTuple):
    x: float
    y: float

    def distance_to(self, other: Position):
        return math.dist(self, other)


class Entity:
    position: Position

    def __init__(self, position: Position):
        self.position = position


class Fleet(Entity):
    team: Team
    strength: int
    destination: Optional[Planet]

    def __init__(
        self,
        team: Team,
        position: Position,
        strength: int,
        destination: Optional[Planet],
    ):
        super().__init__(position)
        self.team = team
        self.strength = strength
        self.destination = destination

    def move(self, destination: Planet, split: bool = False) -> MoveCommand:
        return MoveCommand(self, destination, split)

    def can_dock(self, destination: Planet) -> bool:
        return (
            self.position.distance_to(destination.position)
            < destination.size + MAX_FLEET_SPEED
        )


class Planet(Entity):
    production_speed: int
    remaining_until_new_ship: int
    defending_fleet: Fleet

    @property
    def team(self) -> Team:
        return self.defending_fleet.team

    @property
    def size(self) -> int:
        return self.production_speed + 4

    def __init__(
        self,
        position: Position,
        production_speed: int,
        defending_fleet: Fleet,
    ):
        super().__init__(position)

        self.production_speed = production_speed
        self.remaining_until_new_ship = production_speed
        self.defending_fleet = defending_fleet
