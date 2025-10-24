import math
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
HACK_COOLDOWN_DURATION = 1.0
FLOOR_TILE_SIZE = 64
HIGHLIGHT_COLOR = (255, 215, 0)
TEXT_COLOR = (240, 240, 240)
ACTION_TEXT_COLOR = (140, 200, 255)
STATUS_TEXT_COLOR = (255, 180, 70)


Vector2 = pygame.math.Vector2


def vector_to_int_pair(vec: "Vector2") -> Tuple[int, int]:
    """Return a rounded integer pair for pygame APIs expecting pixel centers."""
    return (int(round(vec.x)), int(round(vec.y)))


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
        self._horizontal = rect.width >= rect.height

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
        frame_rect = self.rect.copy()
        pygame.draw.rect(surface, (40, 45, 56), frame_rect, border_radius=6)

        panel_rect = frame_rect.inflate(-8, -8)
        panel_rect.width = max(panel_rect.width, 8)
        panel_rect.height = max(panel_rect.height, 8)

        if self.opened:
            if self._horizontal:
                panel_rect.width = max(10, panel_rect.width // 3)
                panel_rect.x = frame_rect.right - panel_rect.width - 4
            else:
                panel_rect.height = max(10, panel_rect.height // 3)
                panel_rect.y = frame_rect.bottom - panel_rect.height - 4

        door_color = (120, 120, 140)
        if self.locked:
            door_color = (210, 80, 80)
        elif self.opened:
            door_color = (140, 210, 140)

        pygame.draw.rect(surface, door_color, panel_rect, border_radius=4)

        shade_color = tuple(min(255, c + 35) for c in door_color)
        inner_rect = panel_rect.inflate(-8, -8)
        if inner_rect.width > 0 and inner_rect.height > 0:
            pygame.draw.rect(surface, shade_color, inner_rect, border_radius=4)

            # add subtle stripes for texture
            if self._horizontal:
                for offset in range(inner_rect.left + 4, inner_rect.right - 3, 10):
                    pygame.draw.line(surface, (30, 35, 40), (offset, inner_rect.top + 2), (offset, inner_rect.bottom - 2), 1)
            else:
                for offset in range(inner_rect.top + 4, inner_rect.bottom - 3, 10):
                    pygame.draw.line(surface, (30, 35, 40), (inner_rect.left + 2, offset), (inner_rect.right - 2, offset), 1)

        # handle/lock indicator
        handle_color = (235, 210, 120) if not self.locked else (255, 120, 120)
        if self._horizontal:
            handle_rect = pygame.Rect(panel_rect.right - 10, panel_rect.centery - 4, 6, 8)
        else:
            handle_rect = pygame.Rect(panel_rect.centerx - 4, panel_rect.bottom - 10, 8, 6)
        pygame.draw.rect(surface, handle_color, handle_rect, border_radius=3)

        if highlighted:
            highlight_rect = frame_rect.inflate(8, 8)
            pygame.draw.rect(surface, HIGHLIGHT_COLOR, highlight_rect, width=3, border_radius=9)


class NPC(Hackable):
    name = "NPC"

    def __init__(self, position: Tuple[float, float]):
        super().__init__(position)
        self.distracted = False
        self.distract_timer = 0.0
        self._glow_timer = 0.0
        self.base_sprite = self._create_sprite((80, 180, 90))
        self.distracted_sprite = self._create_sprite((240, 210, 60))

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
        self._glow_timer = (self._glow_timer + dt) % 1.0

    def draw(self, surface: pygame.Surface, highlighted: bool = False) -> None:
        sprite = self.distracted_sprite if self.distracted else self.base_sprite
        sprite_rect = sprite.get_rect(center=vector_to_int_pair(self.position))
        surface.blit(sprite, sprite_rect)

        if self.distracted:
            pulse = 1.0 + 0.15 * math.sin(self._glow_timer * math.tau)
            glow_radius = int(22 * pulse)
            glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surface, (255, 240, 120, 60), (glow_radius, glow_radius), glow_radius)
            glow_rect = glow_surface.get_rect(
                center=vector_to_int_pair(self.position + Vector2(10, -6))
            )
            surface.blit(glow_surface, glow_rect)

        if highlighted:
            pygame.draw.circle(
                surface, HIGHLIGHT_COLOR, vector_to_int_pair(self.position), 28, 3
            )

    def _create_sprite(self, base_color: Tuple[int, int, int]) -> pygame.Surface:
        sprite = pygame.Surface((42, 48), pygame.SRCALPHA)
        pygame.draw.ellipse(sprite, (32, 36, 48), pygame.Rect(4, 4, 34, 40))
        pygame.draw.ellipse(sprite, base_color, pygame.Rect(6, 6, 30, 36))
        pygame.draw.rect(sprite, (220, 235, 255), pygame.Rect(14, 16, 14, 12), border_radius=4)
        pygame.draw.rect(sprite, (60, 75, 90), pygame.Rect(16, 30, 10, 6), border_radius=3)
        # phone in hand
        pygame.draw.rect(sprite, (45, 50, 70), pygame.Rect(26, 30, 8, 12), border_radius=2)
        pygame.draw.rect(sprite, (160, 220, 255), pygame.Rect(27, 31, 6, 8), border_radius=2)
        return sprite


class Player:
    def __init__(self, position: Tuple[float, float]):
        self.position = Vector2(position)
        self.sprite = self._create_sprite()

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
        sprite_rect = self.sprite.get_rect(center=vector_to_int_pair(self.position))
        surface.blit(self.sprite, sprite_rect)

    def _create_sprite(self) -> pygame.Surface:
        sprite = pygame.Surface((44, 44), pygame.SRCALPHA)
        body_rect = pygame.Rect(8, 10, 28, 26)
        pygame.draw.rect(sprite, (18, 34, 46), sprite.get_rect(), border_radius=12)
        pygame.draw.rect(sprite, (36, 72, 96), pygame.Rect(4, 4, 36, 36), border_radius=12)
        pygame.draw.rect(sprite, PLAYER_COLOR, body_rect, border_radius=8)
        pygame.draw.rect(sprite, (180, 220, 255), pygame.Rect(12, 14, 20, 10), border_radius=4)
        pygame.draw.rect(sprite, (45, 52, 66), pygame.Rect(14, 28, 16, 6), border_radius=3)
        return sprite


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

    def draw(
        self,
        surface: pygame.Surface,
        hackable: Optional[Hackable],
        actions: List[Action],
        cooldown: float,
    ) -> None:
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

        if cooldown > 0:
            cooldown_text = self.font.render(
                f"Hacking systems rebooting: {cooldown:.1f}s", True, (200, 120, 120)
            )
            surface.blit(cooldown_text, (20, SCREEN_HEIGHT - 80))


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
        self.hack_cooldown = 0.0
        self.floor_tile = self._create_floor_tile()

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
            events = pygame.event.get()

            for event in events:
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

            self.player.handle_input(dt)

            nearest, actions = self._get_nearest_hackable()

            for hackable in self.hackables:
                hackable.update(dt)

            if self.hack_cooldown > 0:
                self.hack_cooldown = max(0.0, self.hack_cooldown - dt)

            for event in events:
                if event.type == pygame.KEYDOWN and nearest:
                    action = next((a for a in actions if a.key == event.key), None)
                    if action:
                        if self.hack_cooldown <= 0.0:
                            message = action.handler(nearest)
                            if message:
                                self.hud.show_status(message)
                            self.hack_cooldown = HACK_COOLDOWN_DURATION
                        else:
                            self.hud.show_status("Systems cooling down...")
                        break

            self.hud.update(dt)
            self._draw(nearest, actions)

    def _draw(self, highlighted: Optional[Hackable], actions: List[Action]) -> None:
        self.screen.fill(BACKGROUND_COLOR)
        for x in range(0, SCREEN_WIDTH, FLOOR_TILE_SIZE):
            for y in range(0, SCREEN_HEIGHT, FLOOR_TILE_SIZE):
                self.screen.blit(self.floor_tile, (x, y))

        for hackable in self.hackables:
            hackable.draw(self.screen, highlighted is hackable)

        self.player.draw(self.screen)
        self.hud.draw(self.screen, highlighted, actions, self.hack_cooldown)

        pygame.display.flip()

    def _create_floor_tile(self) -> pygame.Surface:
        tile = pygame.Surface((FLOOR_TILE_SIZE, FLOOR_TILE_SIZE))
        tile.fill((36, 39, 48))
        pygame.draw.rect(tile, (30, 32, 40), tile.get_rect(), width=2)
        for offset in range(0, FLOOR_TILE_SIZE, 8):
            color = (45, 49, 60) if (offset // 8) % 2 == 0 else (40, 44, 54)
            pygame.draw.line(tile, color, (0, offset), (FLOOR_TILE_SIZE, offset), 1)
        for offset in range(0, FLOOR_TILE_SIZE, 8):
            color = (26, 28, 34) if (offset // 8) % 2 == 0 else (30, 32, 40)
            pygame.draw.line(tile, color, (offset, 0), (offset, FLOOR_TILE_SIZE), 1)
        pygame.draw.circle(tile, (50, 56, 70), (FLOOR_TILE_SIZE // 2, FLOOR_TILE_SIZE // 2), 6, 1)
        return tile


def main() -> None:
    Game().run()


if __name__ == "__main__":
    main()
