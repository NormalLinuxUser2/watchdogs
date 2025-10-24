import sys
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

import pygame


SCREEN_WIDTH = 960
SCREEN_HEIGHT = 640
BACKGROUND_COLOR = (26, 29, 33)
PLAYER_COLOR = (90, 200, 250)
PLAYER_SPEED = 200  # pixels per second
HACK_RADIUS = 200
HIGHLIGHT_COLOR = (255, 215, 0)
TEXT_COLOR = (240, 240, 240)
ACTION_TEXT_COLOR = (140, 200, 255)
STATUS_TEXT_COLOR = (255, 180, 70)


Vector2 = pygame.math.Vector2


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(min(value, maximum), minimum)


@dataclass
class Action:
    key: int
    label: str
    handler: Callable[["Hackable"], Optional[str]]


class Hackable:
    name: str = "Hackable"

    def __init__(self, position: Tuple[float, float]):
        self.position = Vector2(position)

    def distance_to(self, point: Vector2) -> float:
        return self.position.distance_to(point)

    def get_actions(self) -> List[Action]:
        return []

    def draw(self, surface: pygame.Surface, highlighted: bool = False) -> None:
        raise NotImplementedError

    def update(self, dt: float) -> None:
        pass


class Door(Hackable):
    name = "Door"

    def __init__(self, rect: pygame.Rect, locked: bool = False, opened: bool = False):
        super().__init__(rect.center)
        self.rect = rect
        self.locked = locked
        self.opened = opened

    def toggle_open(self) -> Optional[str]:
        if self.locked:
            return "Door is locked. Unlock it first."
        self.opened = not self.opened
        state = "opened" if self.opened else "closed"
        return f"Door {state}."

    def toggle_lock(self) -> Optional[str]:
        self.locked = not self.locked
        state = "locked" if self.locked else "unlocked"
        return f"Door {state}."

    def get_actions(self) -> List[Action]:
        label = "Close door" if self.opened else "Open door"
        lock_label = "Unlock door" if self.locked else "Lock door"
        return [
            Action(pygame.K_1, label, lambda obj: obj.toggle_open()),
            Action(pygame.K_2, lock_label, lambda obj: obj.toggle_lock()),
        ]

    def draw(self, surface: pygame.Surface, highlighted: bool = False) -> None:
        color = (120, 120, 130)
        if self.locked:
            color = (200, 70, 70)
        elif self.opened:
            color = (120, 200, 120)

        door_rect = self.rect.copy()
        if self.opened:
            # Slide the door open visually by shrinking it toward one side
            if door_rect.width > door_rect.height:
                door_rect.width = max(6, door_rect.width // 4)
                door_rect.x = self.rect.x if (self.rect.y // 32) % 2 == 0 else self.rect.right - door_rect.width
            else:
                door_rect.height = max(6, door_rect.height // 4)
                door_rect.y = self.rect.y if (self.rect.x // 32) % 2 == 0 else self.rect.bottom - door_rect.height

        pygame.draw.rect(surface, color, door_rect)

        if highlighted:
            pygame.draw.rect(surface, HIGHLIGHT_COLOR, door_rect, 3)


class NPC(Hackable):
    name = "NPC"

    def __init__(self, position: Tuple[float, float]):
        super().__init__(position)
        self.distracted = False
        self.distract_timer = 0.0

    def distract(self) -> Optional[str]:
        if self.distracted:
            return "NPC is already distracted."
        self.distracted = True
        self.distract_timer = 3.5
        return "NPC distracted with phone."

    def get_actions(self) -> List[Action]:
        return [
            Action(pygame.K_1, "Distract with phone", lambda obj: obj.distract()),
        ]

    def update(self, dt: float) -> None:
        if self.distracted:
            self.distract_timer = max(0.0, self.distract_timer - dt)
            if self.distract_timer <= 0:
                self.distracted = False

    def draw(self, surface: pygame.Surface, highlighted: bool = False) -> None:
        base_color = (80, 180, 90)
        if self.distracted:
            base_color = (240, 210, 60)
        pygame.draw.circle(surface, base_color, self.position, 18)
        if highlighted:
            pygame.draw.circle(surface, HIGHLIGHT_COLOR, self.position, 22, 3)


class Player:
    def __init__(self, position: Tuple[float, float]):
        self.position = Vector2(position)

    def handle_input(self, dt: float) -> None:
        keys = pygame.key.get_pressed()
        movement = Vector2(0, 0)
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            movement.y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            movement.y += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            movement.x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            movement.x += 1

        if movement.length_squared() > 0:
            movement = movement.normalize()
        self.position += movement * PLAYER_SPEED * dt
        self.position.x = clamp(self.position.x, 16, SCREEN_WIDTH - 16)
        self.position.y = clamp(self.position.y, 16, SCREEN_HEIGHT - 16)

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.circle(surface, PLAYER_COLOR, self.position, 16)


class HUD:
    def __init__(self, font: pygame.font.Font):
        self.font = font
        self.status_message = ""
        self.status_timer = 0.0

    def show_status(self, message: str) -> None:
        if message:
            self.status_message = message
            self.status_timer = 2.5

    def update(self, dt: float) -> None:
        if self.status_timer > 0:
            self.status_timer = max(0.0, self.status_timer - dt)
            if self.status_timer == 0:
                self.status_message = ""

    def draw(self, surface: pygame.Surface, hackable: Optional[Hackable], actions: List[Action]) -> None:
        header = self.font.render("2D Watchdogs Prototype", True, TEXT_COLOR)
        surface.blit(header, (20, 16))

        if hackable:
            info_text = f"Nearest: {hackable.name}"
            distance_text = self.font.render(info_text, True, TEXT_COLOR)
            surface.blit(distance_text, (20, 56))
            for index, action in enumerate(actions):
                prefix = pygame.key.name(action.key).upper()
                label = f"[{prefix}] {action.label}"
                action_surface = self.font.render(label, True, ACTION_TEXT_COLOR)
                surface.blit(action_surface, (20, 90 + index * 28))
        else:
            prompt = self.font.render("Move closer to a hackable object.", True, TEXT_COLOR)
            surface.blit(prompt, (20, 56))

        if self.status_message:
            status_surface = self.font.render(self.status_message, True, STATUS_TEXT_COLOR)
            surface.blit(status_surface, (20, SCREEN_HEIGHT - 48))


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("2D Watchdogs Prototype")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.player = Player((SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2))
        self.hackables: List[Hackable] = self._create_world()
        self.font = pygame.font.Font(None, 28)
        self.hud = HUD(self.font)

    def _create_world(self) -> List[Hackable]:
        hackables: List[Hackable] = []

        # Doors arranged in a simple grid layout
        door_positions = [
            pygame.Rect(200, 180, 60, 18),
            pygame.Rect(600, 140, 18, 80),
            pygame.Rect(400, 420, 70, 18),
        ]
        for index, rect in enumerate(door_positions):
            hackables.append(Door(rect, locked=index == 1, opened=False))

        npc_positions = [
            (280, 360),
            (520, 260),
            (720, 460),
        ]
        for position in npc_positions:
            hackables.append(NPC(position))

        return hackables

    def _get_nearest_hackable(self) -> Tuple[Optional[Hackable], List[Action]]:
        nearest: Optional[Hackable] = None
        min_distance = float("inf")
        for hackable in self.hackables:
            distance = hackable.distance_to(self.player.position)
            if distance < min_distance and distance <= HACK_RADIUS:
                min_distance = distance
                nearest = hackable

        if nearest:
            return nearest, nearest.get_actions()
        return None, []

    def run(self) -> None:
        while True:
            dt = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()

            self.player.handle_input(dt)

            nearest, actions = self._get_nearest_hackable()

            for hackable in self.hackables:
                hackable.update(dt)

            pressed = pygame.key.get_pressed()
            if nearest:
                for action in actions:
                    if pressed[action.key]:
                        message = action.handler(nearest)
                        if message:
                            self.hud.show_status(message)

            self.hud.update(dt)
            self._draw(nearest, actions)

    def _draw(self, highlighted: Optional[Hackable], actions: List[Action]) -> None:
        self.screen.fill(BACKGROUND_COLOR)

        for hackable in self.hackables:
            hackable.draw(self.screen, highlighted is hackable)

        self.player.draw(self.screen)
        self.hud.draw(self.screen, highlighted, actions)

        pygame.display.flip()


def main() -> None:
    Game().run()


if __name__ == "__main__":
    main()
