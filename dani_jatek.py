import pygame
import sys
import json
import os
import tkinter as tk
from tkinter import simpledialog, messagebox
from PIL import Image, ImageTk
import threading
import time
import random

# Helper function for resource paths (PyInstaller compatibility)
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Helper function for executable directory paths
def executable_dir_path(relative_path):
    """Get path relative to executable directory (for external files like maps)"""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller executable
        exe_dir = os.path.dirname(sys.executable)
    else:
        # Running as script
        exe_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(exe_dir, relative_path)

# Initialize Pygame
pygame.init()
pygame.mixer.init()
# Jumpscare
Jumpscare = True
safe_mode = False

# Music settings
BG_MUSIC_VOLUME = 0.2  # Volume from 0.0 to 1.0 (edit this value to change volume)

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
GRAVITY = 0.8
JUMP_STRENGTH = -15
PLAYER_SPEED = 5
CAMERA_SPEED = 3
TILE_SIZE = 20
GROUND_Y = 560

# Animation constants
MOVE_ANIMATION_SPEED = 60  # pixels per second

# Colors
WHITE = (255, 255, 255)
SKY_BLUE_TOP = (87, 138, 230)
SKY_BLUE_BOTTOM = (135, 206, 235)
GREEN = (34, 139, 34)
BROWN = (101, 67, 33)
YELLOW = (255, 215, 0)
DARK_YELLOW = (218, 165, 32)
BLACK = (0, 0, 0)
RED = (255, 0, 0)

# Create screen
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Dani's Platformer Adventure")
clock = pygame.time.Clock()

class Camera:
    def __init__(self):
        self.x = 0
        self.y = 0
        
    def update(self, target):
        # Follow the player with some offset
        self.x = target.rect.x - SCREEN_WIDTH // 3
        # Keep camera within bounds
        if self.x < 0:
            self.x = 0

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        try:
            self.image = pygame.image.load(resource_path('char.png')).convert_alpha()
            self.image = pygame.transform.scale(self.image, (40, 60))
        except:
            self.image = pygame.Surface((40, 60))
            self.image.fill(RED)
        
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.vel_y = 0
        self.on_ground = False
    
    def update(self, platforms, camera, game_objects=None):
        keys = pygame.key.get_pressed()
        
        # Combine platforms and game_objects for collision detection
        all_platforms = list(platforms)
        if game_objects:
            # Add visible game objects that can be collided with
            for obj in game_objects.values():
                if getattr(obj, 'is_visible', True) and getattr(obj, 'visible', True):
                    # Create a temporary platform-like object for collision
                    temp_platform = type('TempPlatform', (), {
                        'rect': pygame.Rect(getattr(obj, 'current_x', obj.world_x), 
                                          getattr(obj, 'current_y', obj.world_y), 
                                          obj.width, obj.height),
                        'obj_type': getattr(obj, 'obj_type', 'platform'),
                        'is_visible': True,
                        'is_moving': getattr(obj, 'is_moving', False),
                        'move_velocity_y': getattr(obj, 'move_velocity_y', 0),
                        'move_velocity_x': getattr(obj, 'move_velocity_x', 0),
                        'spike': getattr(obj, 'spike', False)
                    })()
                    all_platforms.append(temp_platform)
        
        # Store old position for collision detection
        old_rect = self.rect.copy()
        
        # Handle input and movement
        horizontal_input = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            horizontal_input = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            horizontal_input = 1
            
        # Jumping
        if (keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]) and self.on_ground:
            self.vel_y = JUMP_STRENGTH
            self.on_ground = False
        
        # Apply gravity
        self.vel_y += GRAVITY
        
        # Move horizontally first
        if horizontal_input != 0:
            self.rect.x += horizontal_input * PLAYER_SPEED
            
        # Check for horizontal collisions and wall pushing
        collision_result = self._handle_horizontal_collisions(all_platforms, old_rect, horizontal_input)
        if collision_result == "death":
            return "death"
        
        # Move vertically
        self.rect.y += self.vel_y
        
        # Check for vertical collisions
        collision_result = self._handle_vertical_collisions(all_platforms, old_rect)
        if collision_result == "death":
            return "death"
        
        # Check for pinch detection (being squeezed by moving platforms)
        if self._check_pinch_detection(all_platforms, old_rect):
            return "pinch"
        
        # Prevent player from going too far left
        if self.rect.left < 0:
            self.rect.left = 0
        
        # Death by falling
        if self.rect.top > SCREEN_HEIGHT + 100:
            return "death"
            
        return False
    
    def _handle_horizontal_collisions(self, platforms, old_rect, horizontal_input):
        """Handle horizontal movement collisions and wall pushing"""
        for platform in platforms:
            if not getattr(platform, 'is_visible', True):
                continue
                
            if self.rect.colliderect(platform.rect):
                # Check for spike collision
                if hasattr(platform, 'obj_type') and platform.obj_type == "spikes":
                    return "death"
                
                # Determine collision side based on movement direction and overlap
                if horizontal_input > 0:  # Moving right, hit left side of platform
                    self.rect.right = platform.rect.left
                elif horizontal_input < 0:  # Moving left, hit right side of platform
                    self.rect.left = platform.rect.right
                else:
                    # Player not moving but platform might be pushing
                    # Check if platform is moving and pushing player
                    if hasattr(platform, 'is_moving') and platform.is_moving:
                        # Platform is moving, check which side it's pushing from
                        platform_center_x = platform.rect.centerx
                        player_center_x = self.rect.centerx
                        
                        if platform_center_x < player_center_x:  # Platform pushing from left
                            self.rect.left = platform.rect.right
                        else:  # Platform pushing from right
                            self.rect.right = platform.rect.left
        
        return None
    
    def _handle_vertical_collisions(self, platforms, old_rect):
        """Handle vertical movement collisions"""
        self.on_ground = False
        
        for platform in platforms:
            if not getattr(platform, 'is_visible', True):
                continue
                
            if self.rect.colliderect(platform.rect):
                # Check for spike collision
                if hasattr(platform, 'obj_type') and platform.obj_type == "spikes":
                    return "death"
                
                # Determine collision direction
                if self.vel_y > 0:  # Falling down, hit top of platform
                    self.rect.bottom = platform.rect.top
                    self.vel_y = 0
                    self.on_ground = True
                elif self.vel_y < 0:  # Moving up, hit bottom of platform
                    self.rect.top = platform.rect.bottom
                    self.vel_y = 0
                else:
                    # No vertical velocity but still colliding - platform might be moving
                    if hasattr(platform, 'is_moving') and platform.is_moving:
                        # Use platform's movement velocity to determine proper collision response
                        platform_velocity_y = getattr(platform, 'move_velocity_y', 0)
                        
                        # Determine which side of the platform the player is on
                        player_bottom = old_rect.bottom
                        player_top = old_rect.top
                        platform_top = platform.rect.top
                        platform_bottom = platform.rect.bottom
                        
                        # If player was above platform before collision and platform is moving up
                        if player_bottom <= platform_top + 5 and platform_velocity_y < 0:
                            # Platform moving up, carry player with it
                            self.rect.bottom = platform.rect.top
                            self.vel_y = platform_velocity_y  # Match platform's upward velocity
                            self.on_ground = True
                        # If player was below platform before collision and platform is moving down
                        elif player_top >= platform_bottom - 5 and platform_velocity_y > 0:
                            # Platform moving down, push player down
                            self.rect.top = platform.rect.bottom
                            self.vel_y = max(1, platform_velocity_y)  # Push player down
                        else:
                            # Fallback to position-based logic for stationary or horizontal movement
                            platform_center_y = platform.rect.centery
                            player_center_y = self.rect.centery
                            
                            if platform_center_y < player_center_y:  # Platform above
                                self.rect.top = platform.rect.bottom
                                self.vel_y = 1
                            else:  # Platform below
                                self.rect.bottom = platform.rect.top
                                self.vel_y = 0
                                self.on_ground = True
        
        return None
    
    def _check_pinch_detection(self, platforms, old_rect):
        """Check if player is being pinched between moving platforms"""
        # Get all platforms currently colliding with player
        colliding_platforms = []
        for platform in platforms:
            if (getattr(platform, 'is_visible', True) and 
                self.rect.colliderect(platform.rect) and
                hasattr(platform, 'is_moving') and platform.is_moving):
                colliding_platforms.append(platform)
        
        # If colliding with 2 or more moving platforms, check for pinch
        if len(colliding_platforms) >= 2:
            return True
            
        # Check if player is squeezed between a moving platform and a static one
        for moving_platform in colliding_platforms:
            for static_platform in platforms:
                if (static_platform != moving_platform and 
                    getattr(static_platform, 'is_visible', True) and
                    self.rect.colliderect(static_platform.rect)):
                    
                    # Calculate if platforms are on opposite sides
                    moving_center = moving_platform.rect.center
                    static_center = static_platform.rect.center
                    player_center = self.rect.center
                    
                    # Check for horizontal pinch
                    if ((moving_center[0] < player_center[0] < static_center[0]) or 
                        (static_center[0] < player_center[0] < moving_center[0])):
                        # Check if platforms are close enough horizontally to cause pinch
                        gap = abs(moving_platform.rect.right - static_platform.rect.left)
                        if gap == 0:  # No gap, definite pinch
                            gap = abs(static_platform.rect.right - moving_platform.rect.left)
                        if gap <= self.rect.width:
                            return True
                    
                    # Check for vertical pinch
                    if ((moving_center[1] < player_center[1] < static_center[1]) or 
                        (static_center[1] < player_center[1] < moving_center[1])):
                        # Check if platforms are close enough vertically to cause pinch
                        gap = abs(moving_platform.rect.bottom - static_platform.rect.top)
                        if gap == 0:  # No gap, definite pinch
                            gap = abs(static_platform.rect.bottom - moving_platform.rect.top)
                        if gap <= self.rect.height:
                            return True
        
        return False

class Tile:
    """Individual tile for tile-based rendering"""
    @staticmethod
    def draw_ground_tile(surface, x, y):
        """Draw a single ground tile"""
        pygame.draw.rect(surface, BROWN, (x, y, TILE_SIZE, TILE_SIZE))
        # Add grass on top
        pygame.draw.rect(surface, GREEN, (x, y, TILE_SIZE, 4))
        # Add grass texture
        for i in range(0, TILE_SIZE, 5):
            pygame.draw.line(surface, (0, 100, 0), (x + i, y), (x + i, y + 3), 1)
    
    @staticmethod
    def draw_yellow_tile(surface, x, y):
        """Draw a single yellow block tile"""
        pygame.draw.rect(surface, YELLOW, (x, y, TILE_SIZE, TILE_SIZE))
        pygame.draw.rect(surface, DARK_YELLOW, (x, y, TILE_SIZE, TILE_SIZE), 1)
        
        # Add rivet in center
        center_x = x + TILE_SIZE // 2
        center_y = y + TILE_SIZE // 2
        pygame.draw.circle(surface, DARK_YELLOW, (center_x, center_y), 2)
        pygame.draw.circle(surface, BLACK, (center_x, center_y), 2, 1)
    
    @staticmethod
    def draw_spike_tile(surface, x, y):
        """Draw a single spike tile"""
        # Draw spike base
        pygame.draw.rect(surface, (64, 64, 64), (x, y + TILE_SIZE - 4, TILE_SIZE, 4))
        
        # Draw spikes
        spike_width = TILE_SIZE // 4
        for i in range(4):
            spike_x = x + (i * spike_width)
            points = [
                (spike_x, y + TILE_SIZE),
                (spike_x + spike_width // 2, y),
                (spike_x + spike_width, y + TILE_SIZE)
            ]
            pygame.draw.polygon(surface, (128, 128, 128), points)
            pygame.draw.polygon(surface, BLACK, points, 1)

class GameObject(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, obj_type="yellow_block", obj_id=None):
        super().__init__()
        self.obj_type = obj_type
        self.width = width
        self.height = height
        self.original_x = x
        self.original_y = y
        self.world_x = x
        self.world_y = y
        self.obj_id = obj_id or f"{obj_type}_{x}_{y}"
        
        # Animation properties
        self.target_x = x
        self.target_y = y
        self.move_duration = 0
        self.move_start_time = 0
        self.is_moving = False
        self.is_visible = True
        
        # Movement direction tracking
        self.prev_x = x
        self.prev_y = y
        self.move_velocity_x = 0
        self.move_velocity_y = 0
        
        # Create collision rect
        self.rect = pygame.Rect(x, y, width, height)
    
    def update_position(self, dt):
        """Update position if object is moving"""
        if self.is_moving:
            elapsed = pygame.time.get_ticks() - self.move_start_time
            progress = min(elapsed / (self.move_duration * 1000), 1.0)
            
            # Store previous position
            self.prev_x = self.world_x
            self.prev_y = self.world_y
            
            # Linear interpolation
            new_x = self.original_x + (self.target_x - self.original_x) * progress
            new_y = self.original_y + (self.target_y - self.original_y) * progress
            
            # Calculate movement velocity (pixels per frame)
            self.move_velocity_x = new_x - self.world_x
            self.move_velocity_y = new_y - self.world_y
            
            # Update positions
            self.world_x = new_x
            self.world_y = new_y
            
            # Update all position attributes for consistency
            self.current_x = self.world_x
            self.current_y = self.world_y
            
            # Update collision rect only if object is visible
            if getattr(self, 'is_visible', True) and getattr(self, 'visible', True):
                self.rect.x = self.world_x
                self.rect.y = self.world_y
            
            if progress >= 1.0:
                self.is_moving = False
                self.original_x = self.target_x
                self.original_y = self.target_y
    
    def trigger_action(self, action, **kwargs):
        """Execute triggered action"""
        if action == "appear":
            self.is_visible = True
            self.visible = True
            # Restore collision by putting rect back in place
            if hasattr(self, 'rect'):
                self.rect.x = self.world_x
                self.rect.y = self.world_y
            # Make sure current position is also updated
            self.current_x = self.world_x
            self.current_y = self.world_y
        elif action == "disappear":
            self.is_visible = False
            self.visible = False
            # Disable collision by moving rect off screen
            if hasattr(self, 'rect'):
                self.rect.x = -1000
                self.rect.y = -1000
            print(f"Object {getattr(self, 'obj_id', 'unknown')} disappeared (visibility: {self.is_visible}, {self.visible})")
        elif action == "move":
            self.target_x = kwargs.get("target_x", self.world_x)
            self.target_y = kwargs.get("target_y", self.world_y)
            self.move_duration = kwargs.get("duration", 2.0)
            self.move_start_time = pygame.time.get_ticks()
            self.is_moving = True
            # Reset movement tracking
            self.prev_x = self.world_x
            self.prev_y = self.world_y
            self.move_velocity_x = 0
            self.move_velocity_y = 0

class Platform(GameObject):
    def __init__(self, x, y, width, height, platform_type="yellow_block", obj_id=None):
        super().__init__(x, y, width, height, platform_type, obj_id)
        self.platform_type = platform_type
        # Ensure position attributes exist for collision detection
        self.current_x = x
        self.current_y = y

class TextElement(GameObject):
    def __init__(self, x, y, width, height, text, obj_id=None):
        super().__init__(x, y, width, height, "text", obj_id)
        self.text = text
        self.font = pygame.font.Font(None, 24)
        # Ensure position attributes exist
        self.current_x = x
        self.current_y = y
    
    def draw(self, screen, camera):
        """Draw the text element"""
        if not (getattr(self, 'visible', True) and getattr(self, 'is_visible', True)):
            return
            
        screen_x = self.current_x - camera.x
        screen_y = self.current_y - camera.y
        
        # Only draw if visible on screen
        if -100 < screen_x < SCREEN_WIDTH + 100 and -100 < screen_y < SCREEN_HEIGHT + 100:
            # Draw only the text (no background or border)
            text_surface = self.font.render(self.text, True, (255, 255, 255))
            screen.blit(text_surface, (screen_x, screen_y))

class TriggerBox(GameObject):
    def __init__(self, x, y, width, height, obj_id=None):
        super().__init__(x, y, width, height, "trigger", obj_id)
        self.linked_objects = []  # IDs of objects this trigger affects
        self.triggered = False
        self.enabled = True  # Whether this trigger is currently active
        self.trigger_actions = {}  # obj_id: {"action": "move", "target_x": x, "target_y": y, "duration": 2.0}
        # Ensure position attributes exist
        self.current_x = x
        self.current_y = y
        self.world_x = x
        self.world_y = y

class Flag(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((40, 80), pygame.SRCALPHA)
        self.image.fill((0, 0, 0, 0))  # Transparent background
        
        # Draw flag pole
        pygame.draw.rect(self.image, BROWN, (18, 0, 4, 80))
        
        # Draw flag
        flag_points = [(22, 10), (38, 10), (38, 30), (30, 25), (22, 30)]
        pygame.draw.polygon(self.image, RED, flag_points)
        
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

class Menu:
    def __init__(self, screen):
        self.screen = screen
        self.font_large = pygame.font.Font(None, 72)
        self.font_medium = pygame.font.Font(None, 48)
        self.font_small = pygame.font.Font(None, 36)
        self.selected_level = 1
        self.levels = self.load_available_levels()
    
    def load_available_levels(self):
        levels = []
        try:
            maps_dir = executable_dir_path("maps")
            if not os.path.exists(maps_dir):
                raise FileNotFoundError("Maps directory not found")
            map_files = [f for f in os.listdir(maps_dir) if f.endswith(".json")]
            for map_file in sorted(map_files):
                map_path = os.path.join(maps_dir, map_file)
                try:
                    with open(map_path, 'r') as f:
                        map_data = json.load(f)
                    level_name = map_data.get("name", map_file.replace(".json", "").replace("_", " ").title())
                    file_name = map_file.replace(".json", "")
                    levels.append({"name": level_name, "file": file_name})
                except:
                    # Fallback if JSON is invalid
                    file_name = map_file.replace(".json", "")
                    levels.append({"name": file_name.replace("_", " ").title(), "file": file_name})
        except:
            # Fallback levels if maps directory doesn't exist
            levels = [
                {"name": "Level 1 - Getting Started", "file": "level1"},
                {"name": "Level 2 - Jumping Challenge", "file": "level2"},
                {"name": "Level 3 - Advanced Platforming", "file": "level3"}
            ]
        return levels
    
    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP or event.key == pygame.K_w:
                self.selected_level = max(1, self.selected_level - 1)
            elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                self.selected_level = min(len(self.levels), self.selected_level + 1)
            elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                if self.levels:
                    return self.levels[self.selected_level - 1]["file"]
        return None
    
    def draw(self):
        # Draw gradient sky background
        for y in range(SCREEN_HEIGHT):
            ratio = y / SCREEN_HEIGHT
            r = int(SKY_BLUE_TOP[0] * (1 - ratio) + SKY_BLUE_BOTTOM[0] * ratio)
            g = int(SKY_BLUE_TOP[1] * (1 - ratio) + SKY_BLUE_BOTTOM[1] * ratio)
            b = int(SKY_BLUE_TOP[2] * (1 - ratio) + SKY_BLUE_BOTTOM[2] * ratio)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (SCREEN_WIDTH, y))
        
        # Draw title
        title_text = self.font_large.render("Dani's Platformer Adventure", True, WHITE)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, 100))
        self.screen.blit(title_text, title_rect)
        
        # Draw subtitle
        subtitle_text = self.font_medium.render("Choose Your Level", True, WHITE)
        subtitle_rect = subtitle_text.get_rect(center=(SCREEN_WIDTH // 2, 160))
        self.screen.blit(subtitle_text, subtitle_rect)
        
        # Draw level options
        start_y = 250
        if self.levels:
            for i, level in enumerate(self.levels, 1):
                color = YELLOW if i == self.selected_level else WHITE
                level_text = self.font_small.render(f"{i}. {level['name']}", True, color)
                level_rect = level_text.get_rect(center=(SCREEN_WIDTH // 2, start_y + (i - 1) * 60))
                self.screen.blit(level_text, level_rect)
                
                # Draw selection indicator
                if i == self.selected_level:
                    pygame.draw.rect(self.screen, YELLOW, 
                                   (level_rect.left - 10, level_rect.top - 5, 
                                    level_rect.width + 20, level_rect.height + 10), 3)
        else:
            # Show message if no levels found
            no_levels_text = self.font_small.render("No levels found in maps directory", True, WHITE)
            no_levels_rect = no_levels_text.get_rect(center=(SCREEN_WIDTH // 2, start_y))
            self.screen.blit(no_levels_text, no_levels_rect)
        
        # Draw instructions
        instruction_text = self.font_small.render("Use UP/DOWN arrows to select, ENTER/SPACE to start", True, WHITE)
        instruction_rect = instruction_text.get_rect(center=(SCREEN_WIDTH // 2, 500))
        self.screen.blit(instruction_text, instruction_rect)

def prompt_password():
    """Show password dialog and return True if correct password entered"""
    try:
        # Create a root window and hide it
        root = tk.Tk()
        root.withdraw()
        
        # Show password input dialog
        password = simpledialog.askstring("Safe Mode", "Enter password:", show='*')
        
        # Clean up
        root.destroy()
        
        return password == "Faurka112"
    except:
        return False

def activate_safe_mode():
    """Activate safe mode by disabling jumpscare"""
    global Jumpscare, safe_mode
    Jumpscare = False
    safe_mode = True
    print("SAFE MODE ACTIVATED")

def load_background_music():
    """Load and start background music"""
    try:
        pygame.mixer.music.load(resource_path("bg_music.mp3"))
        pygame.mixer.music.set_volume(BG_MUSIC_VOLUME)
        pygame.mixer.music.play(-1)  # -1 means loop indefinitely
        print(f"Background music loaded with volume {BG_MUSIC_VOLUME}")
    except pygame.error:
        print("Warning: Could not load bg_music.mp3")
    except FileNotFoundError:
        print("Warning: bg_music.mp3 not found")

def stop_background_music():
    """Stop background music"""
    pygame.mixer.music.stop()

def set_music_volume(volume):
    """Set music volume (0.0 to 1.0)"""
    global BG_MUSIC_VOLUME
    BG_MUSIC_VOLUME = max(0.0, min(1.0, volume))
    pygame.mixer.music.set_volume(BG_MUSIC_VOLUME)
    print(f"Music volume set to {BG_MUSIC_VOLUME}")

class Game:
    def __init__(self):
        self.camera = Camera()
        self.player = Player(100, 300)
        self.platforms = []
        self.trigger_boxes = []
        self.text_elements = []
        self.game_objects = {}  # obj_id: GameObject mapping
        self.flag = None
        self.current_map = "level1"
        self.level_completed = False
        self.game_state = "menu"  # "menu" or "playing"
        self.menu = Menu(screen)
        self.lives = 3
        self.max_lives = 3
        self.debug_mode = False
        
        # Load health icon
        try:
            char_image = pygame.image.load(resource_path('char.png')).convert_alpha()
            self.health_icon = pygame.transform.scale(char_image, (25, 25))
        except:
            print("Warning: Could not load char.png for health display")
            self.health_icon = None
        
        # Delayed action system
        self.delayed_actions = []  # List of (execution_time, action_data, obj_id_str)
    
    def check_if_should_start_invisible(self, obj_id, map_data):
        """Check if an object should start invisible because it has an 'appear' action"""
        trigger_boxes = map_data.get("trigger_boxes", [])
        for trigger in trigger_boxes:
            actions = trigger.get("actions", {})
            for target_id, action_data in actions.items():
                if str(target_id) == str(obj_id):
                    # Handle both single action (dict) and multiple actions (list)
                    actions_list = []
                    if isinstance(action_data, dict):
                        actions_list = [action_data]
                    elif isinstance(action_data, list):
                        actions_list = action_data
                    
                    # Check if any action is "appear"
                    for action in actions_list:
                        if action.get("action") == "appear":
                            return True
        return False
        
    def load_map(self, map_name):
        map_path = os.path.join(executable_dir_path("maps"), f"{map_name}.json")
        try:
            with open(map_path, 'r') as f:
                map_data = json.load(f)
            
            # Clear existing objects
            self.platforms.clear()
            self.trigger_boxes.clear()
            self.text_elements.clear()
            self.game_objects.clear()
            
            # Get level width from flag position or use default
            flag_data = map_data.get("flag", {"x": 2000})
            level_width = flag_data["x"] + 300  # Add some extra space after flag
            
            # Create continuous ground with pits
            self.create_ground_with_pits(level_width, map_data.get("pits", []))
            
            # Load yellow block platforms
            for platform_data in map_data.get("yellow_blocks", []):
                height = platform_data.get("height", 40)
                obj_id = platform_data.get("id", f"block_{platform_data['x']}_{platform_data['y']}")
                platform = Platform(
                    platform_data["x"],
                    platform_data["y"],
                    platform_data["width"],
                    height,
                    "yellow_block",
                    obj_id
                )
                # Check if this object has an 'appear' action - if so, start invisible
                should_start_invisible = self.check_if_should_start_invisible(obj_id, map_data)
                if should_start_invisible:
                    platform.is_visible = False
                    platform.visible = False
                    platform.rect.x = -1000  # Move off screen
                    platform.rect.y = -1000
                    print(f"Object {obj_id} starting invisible (has appear action)")
                
                self.platforms.append(platform)
                self.game_objects[obj_id] = platform
            
            # Load spikes
            for spike_data in map_data.get("spikes", []):
                height = spike_data.get("height", 20)
                obj_id = spike_data.get("id", f"spike_{spike_data['x']}_{spike_data['y']}")
                spike = Platform(
                    spike_data["x"],
                    spike_data["y"],
                    spike_data["width"],
                    height,
                    "spikes",
                    obj_id
                )
                spike.spike = True  # Mark as spike for collision detection
                
                # Check if this object has an 'appear' action - if so, start invisible
                should_start_invisible = self.check_if_should_start_invisible(obj_id, map_data)
                if should_start_invisible:
                    spike.is_visible = False
                    spike.visible = False
                    spike.rect.x = -1000  # Move off screen
                    spike.rect.y = -1000
                    print(f"Spike {obj_id} starting invisible (has appear action)")
                
                self.platforms.append(spike)
                self.game_objects[obj_id] = spike
            
            # Load trigger boxes
            for trigger_data in map_data.get("trigger_boxes", []):
                obj_id = trigger_data.get("id", f"trigger_{trigger_data['x']}_{trigger_data['y']}")
                trigger = TriggerBox(
                    trigger_data["x"],
                    trigger_data["y"],
                    trigger_data["width"],
                    trigger_data["height"],
                    obj_id
                )
                trigger.trigger_actions = trigger_data.get("actions", {})
                trigger.enabled = trigger_data.get("enabled", True)  # Load enabled state from JSON
                trigger.triggered = False
                self.trigger_boxes.append(trigger)
                # Don't add to game_objects as they're invisible
            
            # Load text elements
            for text_data in map_data.get("text_elements", []):
                obj_id = text_data.get("id", f"text_{text_data['x']}_{text_data['y']}")
                text_element = TextElement(
                    text_data["x"],
                    text_data["y"],
                    text_data["width"],
                    text_data["height"],
                    text_data["text"],
                    obj_id
                )
                # Check if this text has an 'appear' action - if so, start invisible
                should_start_invisible = self.check_if_should_start_invisible(obj_id, map_data)
                if should_start_invisible:
                    text_element.is_visible = False
                    text_element.visible = False
                    print(f"Text element {obj_id} starting invisible (has appear action)")
                
                self.text_elements.append(text_element)
                self.game_objects[obj_id] = text_element
            
            # Load flag
            if flag_data:
                self.flag = Flag(flag_data["x"], SCREEN_HEIGHT - 120)
            
            # Set player start position
            start_pos = map_data.get("start_position", {"x": 100, "y": SCREEN_HEIGHT - 100})
            self.player.rect.x = start_pos["x"]
            self.player.rect.y = start_pos["y"]
            self.player.vel_y = 0
            self.camera.x = 0  # Reset camera position
            
            print(f"Loaded map: {map_name}")
            
        except FileNotFoundError:
            print(f"Map file {map_path} not found. Creating default map.")
            self.create_default_map()
        except json.JSONDecodeError:
            print(f"Error reading map file {map_path}. Creating default map.")
            self.create_default_map()
    
    def create_ground_with_pits(self, level_width, pits):
        """Create continuous ground with gaps for pits"""
        ground_height = 40
        ground_y = SCREEN_HEIGHT - ground_height
        
        # Sort pits by x position
        sorted_pits = sorted(pits, key=lambda p: p["x"])
        
        # Create ground segments between pits
        current_x = 0
        
        for pit in sorted_pits:
            pit_start = pit["x"]
            pit_width = pit["width"]
            
            # Create ground segment before this pit
            if current_x < pit_start:
                segment_width = pit_start - current_x
                self.platforms.append(Platform(current_x, ground_y, segment_width, ground_height, "ground"))
            
            # Skip the pit area
            current_x = pit_start + pit_width
        
        # Create final ground segment after last pit
        if current_x < level_width:
            final_width = level_width - current_x
            self.platforms.append(Platform(current_x, ground_y, final_width, ground_height, "ground"))
    
    def start_level(self, level_name):
        self.current_map = level_name
        self.level_completed = False
        self.game_state = "playing"
        self.lives = self.max_lives  # Reset lives when starting new level
        self.load_map(level_name)
    
    def return_to_menu(self):
        self.game_state = "menu"
        self.level_completed = False
    
    def resolve_player_wall_collision(self, appearing_object):
        """Resolve collision when a wall appears inside the player by moving player to nearest safe position"""
        if not appearing_object or not hasattr(appearing_object, 'rect'):
            return
        
        # Check if player is actually colliding with the appearing object
        if not self.player.rect.colliderect(appearing_object.rect):
            return
        
        print(f"Player inside appearing object at {appearing_object.rect.x}, {appearing_object.rect.y}")
        
        # Calculate distances to each side of the object
        player_center_x = self.player.rect.centerx
        player_center_y = self.player.rect.centery
        
        # Distances to each edge
        dist_to_left = abs(player_center_x - appearing_object.rect.left)
        dist_to_right = abs(player_center_x - appearing_object.rect.right)
        dist_to_top = abs(player_center_y - appearing_object.rect.top)
        dist_to_bottom = abs(player_center_y - appearing_object.rect.bottom)
        
        # Find the minimum distance and corresponding position
        distances = [
            (dist_to_left, 'left'),
            (dist_to_right, 'right'),
            (dist_to_top, 'top'),
            (dist_to_bottom, 'bottom')
        ]
        
        min_dist, closest_side = min(distances)
        
        # Position player at the closest safe side
        if closest_side == 'left':
            self.player.rect.right = appearing_object.rect.left
            print("Moved player to left side of object")
        elif closest_side == 'right':
            self.player.rect.left = appearing_object.rect.right
            print("Moved player to right side of object")
        elif closest_side == 'top':
            self.player.rect.bottom = appearing_object.rect.top
            self.player.vel_y = 0
            self.player.on_ground = True
            print("Moved player to top of object")
        elif closest_side == 'bottom':
            self.player.rect.top = appearing_object.rect.bottom
            self.player.vel_y = 0
            print("Moved player to bottom of object")
        
        # Ensure player doesn't go off screen
        if self.player.rect.left < 0:
            self.player.rect.left = 0
        if self.player.rect.top < 0:
            self.player.rect.top = 0
        
    def respawn_player(self):
        """Respawn player at start position without resetting lives"""
        # Store current lives before reloading
        current_lives = self.lives
        
        # Reload the map to reset object positions
        try:
            self.load_map(self.current_map)
        except:
            # Fallback position if loading fails
            self.player.rect.x = 100
            self.player.rect.y = SCREEN_HEIGHT - 100
            self.player.vel_y = 0
            self.camera.x = 0
        
        # Restore the lives count
        self.lives = current_lives
        
    def create_humor_window(self):
        """Create a new tkinter window with horher.png image"""
        try:
            window = tk.Toplevel()
            window.title("Horher")
            
            # Random position on screen
            x = random.randint(0, 800)
            y = random.randint(0, 600)
            window.geometry(f"+{x}+{y}")
            
            try:
                # Load and display the image
                image = Image.open(resource_path("horher.png"))
                image = image.resize((200, 200))
                photo = ImageTk.PhotoImage(image)
                
                label = tk.Label(window, image=photo)
                label.image = photo  # Keep a reference
                label.pack()
            except FileNotFoundError:
                # Fallback if image not found
                label = tk.Label(window, text="HORHER", font=("Arial", 24), fg="red")
                label.pack(padx=50, pady=50)
            
            # Make window stay on top
            window.attributes('-topmost', True)
            return window
        except:
            return None
    
    def spam_humor_windows(self):
        """Continuously create new windows (humor2 functionality)"""
        # Create a hidden tkinter root window for the spam windows
        try:
            spam_root = tk.Tk()
            spam_root.withdraw()  # Hide the main window
            
            # Create windows continuously for the duration
            start_time = time.time()
            while (time.time() - start_time) < 10:  # Run for 10 seconds
                try:
                    self.create_humor_window()
                    time.sleep(0.01)  # Small delay between windows
                except:
                    break
            
            # Clean up
            try:
                spam_root.quit()
                spam_root.destroy()
            except:
                pass
        except Exception as e:
            print(f"Error in window spam: {e}")
    
    def run_humor_screen(self):
        """Run the fullscreen humor display with window spam (humor + humor2)"""
        try:
            # Get native screen dimensions for fullscreen
            screen_info = pygame.display.Info()
            native_width = screen_info.current_w
            native_height = screen_info.current_h
            
            # Create fullscreen display
            humor_screen = pygame.display.set_mode((native_width, native_height), pygame.FULLSCREEN)
            pygame.display.set_caption("Game Over")
            
            # Load and play sound
            try:
                humor_sound = pygame.mixer.Sound(resource_path('humor.mp3'))
                humor_sound.play()
            except:
                print("Could not load or play humor.mp3")
            
            # Load humor.png and stretch to native resolution
            try:
                humor_image = pygame.image.load(resource_path('humor.png'))
                # Force stretch to exact native resolution
                humor_image = pygame.transform.scale(humor_image, (native_width, native_height))
                print(f"Humor image stretched to native resolution: {native_width}x{native_height}")
            except:
                print("humor.png not found!")
                # Create fallback red screen
                humor_image = pygame.Surface((native_width, native_height))
                humor_image.fill((255, 0, 0))  # Red fallback
            
            # Start window spam in separate thread (humor2 functionality)
            spam_thread = threading.Thread(target=self.spam_humor_windows, daemon=True)
            spam_thread.start()
            print("Window spam started (humor2 integrated)")
            
            # Main humor loop
            humor_clock = pygame.time.Clock()
            humor_running = True
            start_time = pygame.time.get_ticks()
            
            while humor_running and (pygame.time.get_ticks() - start_time) < 10000:  # 10 seconds
                for event in pygame.event.get():
                    if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                        humor_running = False
                
                # Draw the stretched image to cover entire screen
                humor_screen.blit(humor_image, (0, 0))
                pygame.display.flip()
                humor_clock.tick(30)
            
            print("Humor sequence completed")
            pygame.quit()
            sys.exit()
            
        except Exception as e:
            print(f"Error in humor screen: {e}")
            pygame.quit()
            sys.exit()
    
    def launch_humor(self):
        """Launch integrated humor when game over"""
        global Jumpscare
        try:
            if Jumpscare:
                self.run_humor_screen()
            else:
                messagebox.showinfo("Game Over", "You have run out of lives! (Safe Mode: Humor disabled)")
                self.lives = self.max_lives
                self.respawn_player()
        except Exception as e:
            print(f"Error launching humor: {e}")
            self.lives = self.max_lives
            self.respawn_player()
    
    def create_default_map(self):
        # Create a simple default map with proper ground and pits
        level_width = 1600
        default_pits = [
            {"x": 400, "width": 100},
            {"x": 800, "width": 120}
        ]
        
        # Create ground with pits
        self.create_ground_with_pits(level_width, default_pits)
        
        # Add yellow block platforms
        default_yellow_blocks = [
            {"x": 200, "y": SCREEN_HEIGHT - 120, "width": 100},
            {"x": 350, "y": SCREEN_HEIGHT - 200, "width": 100},
            {"x": 550, "y": SCREEN_HEIGHT - 180, "width": 100},
            {"x": 700, "y": SCREEN_HEIGHT - 240, "width": 100},
            {"x": 950, "y": SCREEN_HEIGHT - 160, "width": 100},
            {"x": 1100, "y": SCREEN_HEIGHT - 220, "width": 100}
        ]
        
        for block_data in default_yellow_blocks:
            platform = Platform(
                block_data["x"],
                block_data["y"],
                block_data["width"],
                40,
                "yellow_block"
            )
            self.platforms.append(platform)
        
        self.flag = Flag(1400, SCREEN_HEIGHT - 120)
    
    def draw_hearts(self):
        """Draw character icons for lives in top right corner"""
        icon_size = 25
        icon_spacing = 30
        start_x = SCREEN_WIDTH - (self.max_lives * icon_spacing) - 10
        start_y = 10
        
        for i in range(self.max_lives):
            x = start_x + (i * icon_spacing)
            y = start_y
            
            if hasattr(self, 'health_icon') and self.health_icon:
                if i < self.lives:
                    # Full color character icon
                    screen.blit(self.health_icon, (x, y))
                else:
                    # Grayed out character icon
                    gray_icon = self.health_icon.copy()
                    gray_icon.fill((128, 128, 128), special_flags=pygame.BLEND_MULT)
                    screen.blit(gray_icon, (x, y))
            else:
                # Fallback to colored rectangles if image failed to load
                if i < self.lives:
                    color = GREEN
                else:
                    color = (100, 100, 100)
                pygame.draw.rect(screen, color, (x, y, icon_size, icon_size))
    
    def draw_sky(self):
        # Draw gradient sky
        for y in range(SCREEN_HEIGHT):
            ratio = y / SCREEN_HEIGHT
            r = int(SKY_BLUE_TOP[0] * (1 - ratio) + SKY_BLUE_BOTTOM[0] * ratio)
            g = int(SKY_BLUE_TOP[1] * (1 - ratio) + SKY_BLUE_BOTTOM[1] * ratio)
            b = int(SKY_BLUE_TOP[2] * (1 - ratio) + SKY_BLUE_BOTTOM[2] * ratio)
            pygame.draw.line(screen, (r, g, b), (0, y), (SCREEN_WIDTH, y))
    
    def update(self):
        if self.game_state == "playing":
            dt = clock.get_time() / 1000.0  # Delta time in seconds
            
            # Process delayed actions
            current_time = pygame.time.get_ticks()
            actions_to_execute = [action for action in self.delayed_actions if current_time >= action[0]]
            for execution_time, action_data, obj_id_str in actions_to_execute:
                self.execute_trigger_action(action_data, obj_id_str)
                self.delayed_actions.remove((execution_time, action_data, obj_id_str))
            
            # Update all game objects
            for obj in self.game_objects.values():
                obj.update_position(dt)
            
            # Update player
            player_collision_result = self.player.update(self.platforms, self.camera, self.game_objects)
            
            # Check spike collisions from all sides (additional check for game objects)
            spike_death = False
            for obj in self.game_objects.values():
                if hasattr(obj, 'spike') and obj.spike:
                    is_visible = getattr(obj, 'visible', True) and getattr(obj, 'is_visible', True)
                    if is_visible:
                        spike_rect = pygame.Rect(obj.current_x, obj.current_y, obj.width, obj.height)
                        if self.player.rect.colliderect(spike_rect):
                            print(f"Player hit spike at {obj.current_x}, {obj.current_y}!")
                            spike_death = True
                            break
            
            # Handle player death from various causes
            player_died = False
            death_message = "Player died!"
            
            if player_collision_result == "death":
                player_died = True
                death_message = "Player died from collision!"
            elif player_collision_result == "pinch":
                player_died = True
                death_message = "Player was crushed by moving platforms!"
            elif player_collision_result:  # Any other truthy value (like True for falling)
                player_died = True
                death_message = "Player died from falling!"
            elif spike_death:
                player_died = True
                death_message = "Player hit spikes!"
            
            if player_died:
                self.lives -= 1
                print(f"{death_message} Lives remaining: {self.lives}")
                
                # Check if player is on 1 health and safe mode is not enabled
                if self.lives == 1 and not safe_mode:
                    for _ in range(5):
                        print("!! WARNING !! SAFE MODE NOT ENABLED !! JUMPSCARE IMMINENT !!")
                
                if self.lives <= 0:
                    print("Game Over - launching humor")
                    # Game over - launch humor.py
                    self.launch_humor()
                else:
                    # Respawn player
                    print("Respawning player")
                    self.respawn_player()
            
            # Check trigger boxes
            for trigger in self.trigger_boxes:
                # Only process enabled triggers
                if not trigger.enabled:
                    continue
                    
                # Create trigger rect for collision detection
                trigger_rect = pygame.Rect(trigger.current_x, trigger.current_y, trigger.width, trigger.height)
                if self.player.rect.colliderect(trigger_rect) and not trigger.triggered:
                    trigger.triggered = True
                    print(f"Trigger {trigger.obj_id} activated!")
                    # Execute all trigger actions
                    for obj_id_str, action_data in trigger.trigger_actions.items():
                        # Handle both single action (old format) and multiple actions (new format)
                        actions_list = []
                        if isinstance(action_data, dict):
                            actions_list = [action_data]  # Single action
                        elif isinstance(action_data, list):
                            actions_list = action_data  # Multiple actions
                        
                        for single_action in actions_list:
                            action_type = single_action.get("action", "appear")
                            delay = single_action.get("delay", 0.0)
                            
                            # Schedule action with delay if needed
                            if delay > 0:
                                self.schedule_delayed_action(single_action, obj_id_str, delay)
                                continue
                            
                            # Execute immediately if no delay
                            self.execute_trigger_action(single_action, obj_id_str)
            
            # Update camera
            self.camera.update(self.player)
            
            # Check flag collision
            if self.flag and self.player.rect.colliderect(self.flag.rect):
                if not self.level_completed:
                    self.level_completed = True
                    print("Level completed! Press R to restart or ESC for menu.")
    
    def schedule_delayed_action(self, action_data, obj_id_str, delay):
        """Schedule an action to be executed after a delay"""
        execution_time = pygame.time.get_ticks() + int(delay * 1000)  # Convert seconds to milliseconds
        self.delayed_actions.append((execution_time, action_data, obj_id_str))
        print(f"Scheduled {action_data['action']} for object {obj_id_str} in {delay} seconds")
    
    def execute_trigger_action(self, action_data, obj_id_str):
        """Execute a single trigger action immediately"""
        action_type = action_data.get("action", "appear")
        
        # Handle trigger enable/disable actions
        if action_type in ["enable", "disable"]:
            target_trigger = None
            for t in self.trigger_boxes:
                if hasattr(t, 'obj_id') and str(t.obj_id) == str(obj_id_str):
                    target_trigger = t
                    break
            
            if target_trigger:
                if action_type == "enable":
                    target_trigger.enabled = True
                    target_trigger.triggered = False  # Reset triggered state when enabled
                    print(f"Enabled trigger {obj_id_str}")
                elif action_type == "disable":
                    target_trigger.enabled = False
                    print(f"Disabled trigger {obj_id_str}")
            return
        
        # Handle regular object actions
        target_obj = None
        for obj in self.game_objects.values():
            if hasattr(obj, 'obj_id') and str(obj.obj_id) == str(obj_id_str):
                target_obj = obj
                break
        
        if target_obj:
            print(f"Executing {action_type} on object {obj_id_str}")
            target_obj.trigger_action(
                action_type,
                target_x=action_data.get("target_x", target_obj.current_x),
                target_y=action_data.get("target_y", target_obj.current_y),
                duration=action_data.get("duration", 2.0)
            )
            

        else:
            print(f"Warning: Target object {obj_id_str} not found for action {action_type}")
    
    def draw(self):
        if self.game_state == "menu":
            self.menu.draw()
        else:
            # Draw sky
            self.draw_sky()
            
            # Draw all game objects with tile-based rendering
            for obj in self.game_objects.values():
                # Ensure objects have current position attributes for compatibility
                if not hasattr(obj, 'current_x'):
                    obj.current_x = obj.world_x if hasattr(obj, 'world_x') else obj.x
                if not hasattr(obj, 'current_y'):
                    obj.current_y = obj.world_y if hasattr(obj, 'world_y') else obj.y
                    
                # Check if object is visible (both visibility flags)
                is_obj_visible = getattr(obj, 'visible', True) and getattr(obj, 'is_visible', True)
                if not is_obj_visible:
                    continue  # Skip invisible objects entirely
                    
                # Check if object is visible on screen
                screen_left = obj.current_x - self.camera.x
                screen_right = screen_left + obj.width
                
                if (screen_right > -TILE_SIZE and screen_left < SCREEN_WIDTH + TILE_SIZE):
                    # Calculate tile positions
                    tiles_x = obj.width // TILE_SIZE
                    tiles_y = obj.height // TILE_SIZE
                    
                    for tile_y in range(tiles_y):
                        for tile_x in range(tiles_x):
                            world_x = obj.current_x + (tile_x * TILE_SIZE)
                            world_y = obj.current_y + (tile_y * TILE_SIZE)
                            
                            screen_x = world_x - self.camera.x
                            screen_y = world_y - self.camera.y
                            
                            # Only draw if tile is visible
                            if (screen_x > -TILE_SIZE and screen_x < SCREEN_WIDTH and
                                screen_y > -TILE_SIZE and screen_y < SCREEN_HEIGHT):
                                
                                if hasattr(obj, 'spike') and obj.spike:
                                    Tile.draw_spike_tile(screen, screen_x, screen_y)
                                elif hasattr(obj, 'platform_type'):
                                    if obj.platform_type == "ground":
                                        Tile.draw_ground_tile(screen, screen_x, screen_y)
                                    elif obj.platform_type == "yellow_block":
                                        Tile.draw_yellow_tile(screen, screen_x, screen_y)
            
            # Draw legacy platforms (for backwards compatibility)
            for platform in self.platforms:
                # Only draw if not already in game_objects AND is visible
                if (platform not in self.game_objects.values() and 
                    getattr(platform, 'visible', True) and getattr(platform, 'is_visible', True)):
                    # Ensure platform has current position attributes
                    if not hasattr(platform, 'current_x'):
                        platform.current_x = platform.world_x
                        platform.current_y = platform.world_y
                    
                    screen_left = platform.current_x - self.camera.x
                    screen_right = screen_left + platform.width
                    
                    if screen_right > -TILE_SIZE and screen_left < SCREEN_WIDTH + TILE_SIZE:
                        tiles_x = platform.width // TILE_SIZE
                        tiles_y = platform.height // TILE_SIZE
                        
                        for tile_y in range(tiles_y):
                            for tile_x in range(tiles_x):
                                world_x = platform.current_x + (tile_x * TILE_SIZE)
                                world_y = platform.current_y + (tile_y * TILE_SIZE)
                                
                                screen_x = world_x - self.camera.x
                                screen_y = world_y - self.camera.y
                                
                                if (screen_x > -TILE_SIZE and screen_x < SCREEN_WIDTH and
                                    screen_y > -TILE_SIZE and screen_y < SCREEN_HEIGHT):
                                    
                                    if platform.platform_type == "ground":
                                        Tile.draw_ground_tile(screen, screen_x, screen_y)
                                    elif platform.platform_type == "yellow_block":
                                        Tile.draw_yellow_tile(screen, screen_x, screen_y)
            
            # Draw trigger boxes in debug mode (uncomment to visualize)
            # for trigger in self.trigger_boxes:
            #     trigger_screen_x = trigger.current_x - self.camera.x
            #     trigger_screen_y = trigger.current_y - self.camera.y
            #     if (trigger_screen_x > -trigger.width and trigger_screen_x < SCREEN_WIDTH and
            #         trigger_screen_y > -trigger.height and trigger_screen_y < SCREEN_HEIGHT):
            #         pygame.draw.rect(screen, (255, 0, 0, 100), 
            #                        (trigger_screen_x, trigger_screen_y, trigger.width, trigger.height))
            
            # Draw text elements
            for text_element in self.text_elements:
                text_element.draw(screen, self.camera)
            
            # Draw flag with camera offset
            if self.flag:
                flag_screen_rect = self.flag.rect.copy()
                flag_screen_rect.x -= self.camera.x
                if -100 < flag_screen_rect.x < SCREEN_WIDTH + 100:
                    screen.blit(self.flag.image, flag_screen_rect)
            
            # Draw player with camera offset
            player_screen_rect = self.player.rect.copy()
            player_screen_rect.x -= self.camera.x
            screen.blit(self.player.image, player_screen_rect)
            
            # Debug mode visualizations
            if self.debug_mode:
                # Draw player hitbox (Green)
                debug_rect = self.player.rect.copy()
                debug_rect.x -= self.camera.x
                pygame.draw.rect(screen, (0, 255, 0), debug_rect, 3)
                
                # Draw platform hitboxes (Cyan for yellow blocks)
                for platform in self.platforms:
                    if hasattr(platform, 'rect'):
                        platform_rect = platform.rect.copy()
                        platform_rect.x -= self.camera.x
                        pygame.draw.rect(screen, (0, 255, 255), platform_rect, 2)
                
                # Draw game object hitboxes
                for obj in self.game_objects.values():
                    if hasattr(obj, 'rect'):
                        obj_rect = obj.rect.copy()
                        obj_rect.x = obj.current_x - self.camera.x
                        obj_rect.y = obj.current_y - self.camera.y
                        # Red for spikes, Cyan for yellow blocks
                        if hasattr(obj, 'platform_type') and obj.platform_type == 'spike':
                            color = (255, 0, 0)  # Red for spikes
                        else:
                            color = (0, 255, 255)  # Cyan for yellow blocks
                        pygame.draw.rect(screen, color, obj_rect, 2)
                

                
                # Draw trigger boxes (Orange translucent with TRIGGER text like editor)
                for trigger in self.trigger_boxes:
                    trigger_screen_x = trigger.current_x - self.camera.x
                    trigger_screen_y = trigger.current_y - self.camera.y
                    trigger_rect = pygame.Rect(trigger_screen_x, trigger_screen_y, trigger.width, trigger.height)
                    
                    # Draw orange translucent box
                    surface = pygame.Surface((trigger.width, trigger.height), pygame.SRCALPHA)
                    color = (255, 200, 0, 120) if trigger.triggered else (255, 165, 0, 100)
                    surface.fill(color)
                    screen.blit(surface, (trigger_screen_x, trigger_screen_y))
                    
                    # Draw border and text
                    pygame.draw.rect(screen, (255, 165, 0), trigger_rect, 2)
                    trigger_text = pygame.font.Font(None, 24).render("TRIGGER", True, (0, 0, 0))
                    text_rect = trigger_text.get_rect(center=(trigger_screen_x + trigger.width//2, trigger_screen_y + trigger.height//2))
                    screen.blit(trigger_text, text_rect)
                    
                    # Draw trigger ID
                    id_text = pygame.font.Font(None, 18).render(f"T{trigger.obj_id}", True, (0, 0, 0))
                    screen.blit(id_text, (trigger_screen_x + 2, trigger_screen_y + 2))
            
            # Draw hearts (lives) in top right
            self.draw_hearts()
            
            # Draw safe mode indicator
            if safe_mode:
                font = pygame.font.Font(None, 36)
                safe_text = font.render("SAFE MODE", True, (0, 255, 0))
                text_rect = safe_text.get_rect(center=(SCREEN_WIDTH // 2, 30))
                screen.blit(safe_text, text_rect)
            
            # Draw UI
            if self.level_completed:
                font = pygame.font.Font(None, 36)
                text = font.render("Level Complete! Press R to restart or ESC for menu", True, WHITE)
                text_rect = text.get_rect(center=(SCREEN_WIDTH//2, 50))
                screen.blit(text, text_rect)

# Create game instance
game = Game()

# Start background music
load_background_music()

# Game loop
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if game.game_state == "menu":
                # Handle menu input
                selected_level = game.menu.handle_input(event)
                if selected_level:
                    game.start_level(selected_level)
            elif game.game_state == "playing":
                # Handle game input
                keys = pygame.key.get_pressed()
                if event.key == pygame.K_r:
                    game.level_completed = False
                    game.load_map(game.current_map)
                elif event.key == pygame.K_ESCAPE:
                    game.return_to_menu()
                elif event.key == pygame.K_o and keys[pygame.K_LCTRL] and keys[pygame.K_LALT]:
                    game.debug_mode = not game.debug_mode
                    print(f"Debug mode: {'ON' if game.debug_mode else 'OFF'}")
                elif event.key == pygame.K_s and keys[pygame.K_LCTRL] and keys[pygame.K_LALT]:
                    # Safe mode password prompt
                    if prompt_password():
                        activate_safe_mode()
                    else:
                        print("Incorrect password")
                elif event.key == pygame.K_1:
                    game.start_level("level1")
                elif event.key == pygame.K_2:
                    game.start_level("level2")
                elif event.key == pygame.K_3:
                    game.start_level("level3")
    
    # Update
    game.update()
    
    # Draw
    game.draw()
    
    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()