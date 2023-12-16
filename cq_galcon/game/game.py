from typing import List, Optional, Iterable, Tuple
import math

import vectormath as vmath

import random
from cq_galcon.game.entity import Entity, Fleet, Planet, MoveCommand, Position
from cq_galcon.game.constants import (
    MAX_FLEET_SPEED,
    Team,
    MAP_WIDTH,
    MAP_HEIGHT,
    MAX_PRODUCTION_SPEED,
    MIN_PRODUCTION_SPEED,
    MAX_ATTACK_SPEED,
)


class Game:
    state: List[Entity]

    @staticmethod
    def init_random_game_state() -> List[Entity]:
        state: List[Entity] = []

        for i in Team:
            x_rand = random.randint(0, MAP_WIDTH)
            y_rand = random.randint(0, MAP_HEIGHT)

            fleet = Fleet(i, Position(x_rand, y_rand), 10, None)

            planet = Planet(
                Position(x_rand, y_rand),
                random.randint(MAX_PRODUCTION_SPEED, MIN_PRODUCTION_SPEED),
                fleet,
            )
            state.append(fleet)
            state.append(planet)
        return state

    def __init__(self, seed) -> None:
        random.seed(seed)
        self.state = Game.init_random_game_state()

    def step(self, commands: List[MoveCommand]) -> None:
        self._handle_commands(commands)
        self._handle_already_defending_fleets()
        created_fleets = self._handle_departures()
        moved_fleets = self._handle_movement()  # noqa F841
        merging_fleet, merged_fleets = self._handle_reinforce()
        destroyed_fleets = self._handle_combat()
        self._handle_production()

        # Update the game state by 1: adding newly created fleet and 2: deleting destroyed/merged fleet
        self.state.extend(created_fleets)

        to_remove = []
        to_remove.extend(merged_fleets)
        to_remove.extend(destroyed_fleets)

        for fleet in to_remove:
            self.state.remove(fleet)

    def _handle_already_defending_fleets(self):
        # Error Check : Ignore those that wants to defend where they're already where they want to defend
        for fleet in self.all_player_fleets:
            if fleet.destination.defending_fleet == fleet:
                fleet.destination = None

    def _handle_commands(self, commands: List[MoveCommand]):
        for command in commands:
            command.fleet.destination = command.destination

    def _handle_movement(self) -> List[Fleet]:
        moved_fleets: List[Fleet] = []
        for fleet in self.all_player_fleets:
            # fleet does not want to move (already docked somewhere)
            if not fleet.destination:
                continue

            # Handle docking/combat in another phase
            if fleet.can_dock(fleet.destination):
                continue

            self._move_fleet(fleet)
            moved_fleets.append(fleet)

        return moved_fleets

    def _handle_reinforce(self) -> Tuple[List[Fleet], List[Fleet]]:
        merging_fleets: List[Fleet] = []
        merged_fleets: List[Fleet] = []
        for fleet in self.all_player_fleets:
            if not fleet.destination:
                continue

            if fleet.team != fleet.destination.team:
                continue

            if not fleet.can_dock(fleet.destination):
                continue

            reinforcement_value = min(fleet.strength, MAX_ATTACK_SPEED)

            fleet.destination.defending_fleet.strength += reinforcement_value
            fleet.strength -= reinforcement_value

            if fleet.strength == 0:
                merged_fleets.append(fleet)
            else:
                merging_fleets.append(fleet)

        return merging_fleets, merged_fleets

    def _handle_departures(self) -> List[Fleet]:
        created_fleets: List[Fleet] = []
        for planet in self.all_player_planets:
            # does not wish to depart
            if not planet.defending_fleet.destination:
                continue

            # already at destination
            if planet.defending_fleet.destination == planet:
                continue

            new_fleet = self._handle_departure(
                planet, planet.defending_fleet.destination
            )

            created_fleets.append(new_fleet)
        return created_fleets

    def _handle_departure(
        self, origin: Planet, destination: Planet, split: bool = False
    ):
        strenght_of_new_fleet = origin.defending_fleet.strength
        if split:
            strenght_of_new_fleet = math.ceil(origin.defending_fleet.strength / 2)

        new_fleet = Fleet(
            origin.team, origin.position, strenght_of_new_fleet, destination
        )

        origin.defending_fleet.strength -= new_fleet.strength
        return new_fleet

    def _handle_combat(self) -> List[Fleet]:
        destroyed_fleets: List[Fleet] = []
        for fleet in self.all_player_fleets:
            # Does not have a destination (fleets not moving)
            if not fleet.destination:
                continue

            # Not yet arrived at destination
            if not fleet.can_dock(fleet.destination):
                continue

            defending_fleet_dmg = min(fleet.strength, MAX_ATTACK_SPEED)
            attacking_fleet_dmg = min(
                fleet.destination.defending_fleet.strength, MAX_ATTACK_SPEED
            )

            fleet.destination.defending_fleet.strength -= defending_fleet_dmg
            fleet.strength -= attacking_fleet_dmg

            # In case of draw, defending fleet keep 1 strength
            if fleet.destination.defending_fleet.strength == 0:
                fleet.destination.defending_fleet.strength = 1

            if fleet.destination.defending_fleet.strength < 0:
                destroyed_fleets.append(fleet.destination.defending_fleet)
                fleet.destination.defending_fleet = fleet

            if fleet.strength <= 0:
                destroyed_fleets.append(fleet)

        return destroyed_fleets

    def _handle_production(self):
        for planet in self.all_player_planets:
            planet.remaining_until_new_ship -= 1
            if planet.remaining_until_new_ship <= 0:
                planet.remaining_until_new_ship = planet.production_speed
                planet.defending_fleet.strength += 1

    @property
    def all_player_planets(self) -> List[Planet]:
        return [
            planet
            for planet in self.state
            if isinstance(planet, Planet) and planet.team != Team.NEUTREAL
        ]

    @property
    def all_fleets(self) -> Iterable[Fleet]:
        return [fleet for fleet in self.state if isinstance(fleet, Fleet)]

    @property
    def all_player_fleets(self) -> Iterable[Fleet]:
        return [
            fleet
            for fleet in self.state
            if isinstance(fleet, Fleet) and fleet.team != Team.NEUTREAL
        ]

    def find_planet(self, defender: Fleet) -> Optional[Planet]:
        for planet in self.all_player_planets:
            if planet.defending_fleet == defender:
                return planet

        return None

    def _move_fleet(self, fleet: Fleet):
        if not fleet.destination:
            raise ValueError(fleet, "Fleet should have a destination")

        fleet_pos = vmath.Vector2(fleet.position.x, fleet.position.y)
        dest_pos = vmath.Vector2(
            fleet.destination.position.x, fleet.destination.position.y
        )

        toward = dest_pos - fleet_pos

        max_speed = min(toward.length - fleet.destination.size, MAX_FLEET_SPEED)

        newpos = toward.normalize() * max_speed

        fleet.position = Position(newpos.x, newpos.y)
