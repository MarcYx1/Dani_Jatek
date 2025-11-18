import pygame
import json
import os
import sys
import tkinter as tk
from tkinter import messagebox, simpledialog

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

# Constants
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 60
GRID_SIZE = 20
CAMERA_SPEED = 10

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
LIGHT_GRAY = (200, 200, 200)
DARK_GRAY = (64, 64, 64)
GREEN = (34, 139, 34)
BROWN = (101, 67, 33)
YELLOW = (255, 215, 0)
DARK_YELLOW = (218, 165, 32)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
ORANGE = (255, 165, 0)
SKY_BLUE_TOP = (87, 138, 230)
SKY_BLUE_BOTTOM = (135, 206, 235)

# Create screen
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Dani's Platformer Level Editor")
clock = pygame.time.Clock()

# UI Constants
UI_HEIGHT = 100
GAME_HEIGHT = SCREEN_HEIGHT - UI_HEIGHT
GROUND_Y = 560  # Default ground level

class LevelEditor:
    def __init__(self):
        self.camera_x = 0
        self.camera_y = 0
        self.yellow_blocks = []
        self.pits = []
        self.spikes = []
        self.trigger_boxes = []
        self.flag_x = 2000
        self.start_x = 100  # Player start position
        self.grid_visible = True
        self.current_tool = "yellow_block"  # "yellow_block", "pit", "flag", "start", "spike", "trigger_box", "erase"
        self.next_object_id = 1
        self.selected_trigger = None
        self.selected_object = None
        self.action_mode = False  # When true, clicking objects sets trigger actions
        self.action_step = 0  # 0: select trigger, 1: select object, 2: select action
        self.move_duration = 2.0
        self.ghost_objects = []  # Store ghost positions for move actions
        self.connection_lines = []  # Store trigger-object connections
        self.ghost_cursor_object = None  # Object being positioned for move action
        self.mouse_world_pos = (0, 0)  # Current mouse position in world coordinates
        self.dragging = False
        self.drag_start = None
        self.level_name = "new_level"
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)
        
        # Ensure maps directory exists (use executable directory)
        self.maps_dir = executable_dir_path("maps")
        if not os.path.exists(self.maps_dir):
            os.makedirs(self.maps_dir)
    
    def screen_to_world(self, screen_x, screen_y):
        """Convert screen coordinates to world coordinates"""
        world_x = screen_x + self.camera_x
        world_y = screen_y + self.camera_y
        return world_x, world_y
    
    def world_to_screen(self, world_x, world_y):
        """Convert world coordinates to screen coordinates"""
        screen_x = world_x - self.camera_x
        screen_y = world_y - self.camera_y
        return screen_x, screen_y
    
    def snap_to_grid(self, x, y):
        """Snap coordinates to grid"""
        return (x // GRID_SIZE) * GRID_SIZE, (y // GRID_SIZE) * GRID_SIZE
    
    def handle_input(self, events):
        keys = pygame.key.get_pressed()
        
        # Track mouse position for ghost objects
        mouse_x, mouse_y = pygame.mouse.get_pos()
        if mouse_y < GAME_HEIGHT:
            self.mouse_world_pos = self.screen_to_world(mouse_x, mouse_y)
        
        # Camera movement
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.camera_x -= CAMERA_SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.camera_x += CAMERA_SPEED
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.camera_y -= CAMERA_SPEED
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.camera_y += CAMERA_SPEED
        
        # Keep camera within bounds
        self.camera_x = max(0, self.camera_x)
        self.camera_y = max(0, min(self.camera_y, 400))
        
        for event in events:
            if event.type == pygame.QUIT:
                return False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_g:
                    self.grid_visible = not self.grid_visible
                elif event.key == pygame.K_1:
                    self.current_tool = "yellow_block"
                    self.exit_action_mode()
                elif event.key == pygame.K_2:
                    self.current_tool = "pit"
                    self.exit_action_mode()
                elif event.key == pygame.K_3:
                    self.current_tool = "flag"
                    self.exit_action_mode()
                elif event.key == pygame.K_4:
                    self.current_tool = "start"
                    self.exit_action_mode()
                elif event.key == pygame.K_5:
                    self.current_tool = "spike"
                    self.exit_action_mode()
                elif event.key == pygame.K_6:
                    self.current_tool = "trigger_box"
                    self.exit_action_mode()
                elif event.key == pygame.K_7:
                    self.current_tool = "erase"
                    self.exit_action_mode()
                elif event.key == pygame.K_8:
                    # Exit placement modes when entering action mode
                    if not self.action_mode:
                        self.dragging = False
                        self.drag_start = None
                        self.current_tool = None  # Clear current tool when entering action mode
                    self.action_mode = not self.action_mode
                    if not self.action_mode:
                        self.selected_trigger = None
                        self.selected_object = None
                    print("Action mode:", "ON" if self.action_mode else "OFF")
                elif event.key == pygame.K_RETURN:
                    self.prompt_save_level()
                elif event.key == pygame.K_l:
                    self.prompt_load_level()
                elif event.key == pygame.K_n:
                    self.new_level()
                elif event.key == pygame.K_t:
                    self.test_level()
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    if mouse_y < GAME_HEIGHT:  # Only in game area, not UI
                        world_x, world_y = self.screen_to_world(mouse_x, mouse_y)
                        
                        if self.action_mode:
                            if self.action_step == 2:  # Setting move position
                                snapped_x, snapped_y = self.snap_to_grid(world_x, world_y)
                                self.add_trigger_action("move", target_x=snapped_x, target_y=snapped_y, duration=self.move_duration)
                                self.reset_action_mode()
                            else:
                                self.handle_action_mode_click(world_x, world_y)
                        else:
                            self.dragging = True
                            self.drag_start = self.snap_to_grid(world_x, world_y)
                            self.place_object(world_x, world_y)
            
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1 and self.dragging:
                    self.dragging = False
                    if self.current_tool in ["yellow_block", "pit", "spike", "trigger_box"] and self.drag_start:
                        mouse_x, mouse_y = pygame.mouse.get_pos()
                        if mouse_y < GAME_HEIGHT:
                            world_x, world_y = self.screen_to_world(mouse_x, mouse_y)
                            self.create_rectangle(self.drag_start, self.snap_to_grid(world_x, world_y))
                    self.drag_start = None
        
        return True
    
    def place_object(self, world_x, world_y):
        snapped_x, snapped_y = self.snap_to_grid(world_x, world_y)
        
        if self.current_tool == "flag":
            self.flag_x = snapped_x
        elif self.current_tool == "start":
            self.start_x = snapped_x
        elif self.current_tool == "spike":
            # Check if spike already exists at this position
            spike_exists = False
            for existing_spike in self.spikes:
                if existing_spike["x"] == snapped_x and existing_spike["y"] == snapped_y:
                    spike_exists = True
                    break
            
            # Only add spike if none exists at this position
            if not spike_exists:
                self.spikes.append({
                    "x": snapped_x,
                    "y": snapped_y,
                    "width": GRID_SIZE,
                    "height": GRID_SIZE,
                    "id": self.next_object_id
                })
                self.next_object_id += 1
        elif self.current_tool == "trigger_box":
            # Don't place immediately for trigger boxes - wait for rectangle drag
            pass
        elif self.current_tool == "erase":
            self.erase_at_position(snapped_x, snapped_y)
    
    def create_rectangle(self, start_pos, end_pos):
        if not start_pos:
            return
        
        x1, y1 = start_pos
        x2, y2 = end_pos
        
        # Ensure proper rectangle bounds
        left = min(x1, x2)
        right = max(x1, x2)
        top = min(y1, y2)
        bottom = max(y1, y2)
        
        width = right - left + GRID_SIZE
        height = bottom - top + GRID_SIZE
        
        if self.current_tool == "yellow_block":
            # Remove any overlapping blocks first
            self.yellow_blocks = [block for block in self.yellow_blocks 
                                if not self.rectangles_overlap(block, {"x": left, "y": top, "width": width, "height": height})]
            
            self.yellow_blocks.append({
                "x": left,
                "y": top,
                "width": width,
                "height": height,
                "id": self.next_object_id
            })
            self.next_object_id += 1
        
        elif self.current_tool == "pit":
            # Pits are only defined by x and width, at ground level
            pit_width = width
            
            # Remove overlapping pits
            self.pits = [pit for pit in self.pits 
                        if not (pit["x"] < left + pit_width and pit["x"] + pit["width"] > left)]
            
            self.pits.append({
                "x": left,
                "width": pit_width
            })
        
        elif self.current_tool == "spike":
            # Create multiple spikes in rectangle, avoiding duplicates
            for x in range(left, right + GRID_SIZE, GRID_SIZE):
                for y in range(top, bottom + GRID_SIZE, GRID_SIZE):
                    # Check if spike already exists at this position
                    spike_exists = False
                    for existing_spike in self.spikes:
                        if existing_spike["x"] == x and existing_spike["y"] == y:
                            spike_exists = True
                            break
                    
                    # Only add spike if none exists at this position
                    if not spike_exists:
                        self.spikes.append({
                            "x": x,
                            "y": y,
                            "width": GRID_SIZE,
                            "height": GRID_SIZE,
                            "id": self.next_object_id
                        })
                        self.next_object_id += 1
        
        elif self.current_tool == "trigger_box":
            # Create trigger box
            self.trigger_boxes.append({
                "x": left,
                "y": top,
                "width": width,
                "height": height,
                "id": self.next_object_id,
                "actions": {}
            })
            self.next_object_id += 1
    
    def rectangles_overlap(self, rect1, rect2):
        """Check if two rectangles overlap"""
        return not (rect1["x"] + rect1["width"] <= rect2["x"] or
                   rect2["x"] + rect2["width"] <= rect1["x"] or
                   rect1["y"] + rect1["height"] <= rect2["y"] or
                   rect2["y"] + rect2["height"] <= rect1["y"])
    
    def erase_at_position(self, x, y):
        """Remove objects at the given position"""
        erased_objects = []
        
        # Remove yellow blocks and track erased ones
        original_blocks = self.yellow_blocks.copy()
        self.yellow_blocks = [block for block in self.yellow_blocks 
                            if not (block["x"] <= x < block["x"] + block["width"] and
                                   block["y"] <= y < block["y"] + block["height"])]
        erased_objects.extend([block for block in original_blocks if block not in self.yellow_blocks])
        
        # Remove pits
        self.pits = [pit for pit in self.pits 
                    if not (pit["x"] <= x < pit["x"] + pit["width"])]
        
        # Remove spikes and track erased ones
        original_spikes = self.spikes.copy()
        self.spikes = [spike for spike in self.spikes 
                      if not (spike["x"] <= x < spike["x"] + spike["width"] and
                             spike["y"] <= y < spike["y"] + spike["height"])]
        erased_objects.extend([spike for spike in original_spikes if spike not in self.spikes])
        
        # Remove trigger boxes and track erased ones
        original_triggers = self.trigger_boxes.copy()
        self.trigger_boxes = [trigger for trigger in self.trigger_boxes 
                            if not (trigger["x"] <= x < trigger["x"] + trigger["width"] and
                                   trigger["y"] <= y < trigger["y"] + trigger["height"])]
        erased_triggers = [trigger for trigger in original_triggers if trigger not in self.trigger_boxes]
        
        # Clean up connection lines for erased objects
        for erased_obj in erased_objects + erased_triggers:
            # Remove connections where this object is the target
            self.connection_lines = [conn for conn in self.connection_lines 
                                   if conn["object"] != erased_obj]
            # Remove connections where this object is the trigger
            self.connection_lines = [conn for conn in self.connection_lines 
                                   if conn["trigger"] != erased_obj]
            
            # Remove ghost objects for this object
            self.ghost_objects = [ghost for ghost in self.ghost_objects 
                                if ghost.get("original") != erased_obj]
    
    def handle_action_mode_click(self, world_x, world_y):
        """Handle clicks in action mode for setting up trigger actions"""
        if self.action_step == 0:  # Select trigger
            for trigger in self.trigger_boxes:
                if (trigger["x"] <= world_x < trigger["x"] + trigger["width"] and
                    trigger["y"] <= world_y < trigger["y"] + trigger["height"]):
                    self.selected_trigger = trigger
                    self.action_step = 1
                    print(f"Trigger {trigger['id']} selected. Now click on an object to link.")
                    return
            print("Click on a trigger box to select it.")
        
        elif self.action_step == 1:  # Select object
            # Check yellow blocks
            for block in self.yellow_blocks:
                if (block["x"] <= world_x < block["x"] + block["width"] and
                    block["y"] <= world_y < block["y"] + block["height"]):
                    self.selected_object = block
                    self.show_action_dialog()
                    return
            
            # Check spikes
            for spike in self.spikes:
                if (spike["x"] <= world_x < spike["x"] + spike["width"] and
                    spike["y"] <= world_y < spike["y"] + spike["height"]):
                    self.selected_object = spike
                    self.show_action_dialog()
                    return
            
            print("Click on an object (yellow block or spike) to link it to the trigger.")
    
    def show_action_dialog(self):
        """Show dialog to select action type"""
        root = tk.Tk()
        root.withdraw()  # Hide main window
        
        # Ask for action type
        action = messagebox.askyesnocancel("Select Action", 
            f"What action should Object {self.selected_object['id']} perform when Trigger {self.selected_trigger['id']} is activated?\n\n"
            "YES = Appear/Disappear\n"
            "NO = Move\n"
            "CANCEL = Cancel")
        
        if action is None:  # Cancel
            self.reset_action_mode()
            return
        
        if action:  # Appear/Disappear
            appear = messagebox.askyesno("Action Type", "Should the object APPEAR or DISAPPEAR?\n\nYES = Appear\nNO = Disappear")
            action_type = "appear" if appear else "disappear"
            duration = simpledialog.askfloat("Duration", "How many seconds should the action take?", minvalue=0.1, maxvalue=10.0, initialvalue=2.0)
            if duration:
                self.add_trigger_action(action_type, duration=duration)
        else:  # Move
            duration = simpledialog.askfloat("Duration", "How many seconds should the movement take?", minvalue=0.1, maxvalue=10.0, initialvalue=2.0)
            if duration:
                messagebox.showinfo("Move Position", "Click on the map where the object should move to.")
                self.action_step = 2
                self.move_duration = duration
                # Set up ghost cursor object
                self.ghost_cursor_object = self.selected_object.copy()
                return
        
        self.reset_action_mode()
        root.destroy()
    
    def add_trigger_action(self, action_type, target_x=None, target_y=None, duration=2.0):
        """Add an action to the selected trigger"""
        if not self.selected_trigger or not self.selected_object:
            return
        
        action_data = {
            "action": action_type,
            "duration": duration
        }
        
        if target_x is not None and target_y is not None:
            action_data["target_x"] = target_x
            action_data["target_y"] = target_y
        
        # Add action to trigger
        if "actions" not in self.selected_trigger:
            self.selected_trigger["actions"] = {}
        
        self.selected_trigger["actions"][str(self.selected_object["id"])] = action_data
        
        # Store connection line between trigger and object
        self.connection_lines.append({
            "trigger": self.selected_trigger,
            "object": self.selected_object,
            "action": action_type
        })
        
        # For move actions, store ghost object
        if action_type == "move" and target_x is not None and target_y is not None:
            ghost_obj = self.selected_object.copy()
            ghost_obj["x"] = target_x
            ghost_obj["y"] = target_y
            ghost_obj["original"] = self.selected_object
            self.ghost_objects.append(ghost_obj)
        
        print(f"Action '{action_type}' added to trigger {self.selected_trigger['id']} for object {self.selected_object['id']}")
    
    def reset_action_mode(self):
        """Reset action mode state"""
        self.selected_trigger = None
        self.selected_object = None
        self.action_step = 0
        self.action_mode = False
        self.ghost_cursor_object = None
        print("Action mode reset. Press 8 to enter action mode again.")
    
    def exit_action_mode(self):
        """Exit action mode when switching to placement tools"""
        if self.action_mode:
            self.action_mode = False
            self.selected_trigger = None
            self.selected_object = None
            self.action_step = 0
            self.ghost_cursor_object = None
    
    def draw_grid(self):
        """Draw grid lines"""
        if not self.grid_visible:
            return
        
        # Vertical lines
        start_x = -(self.camera_x % GRID_SIZE)
        for x in range(start_x, SCREEN_WIDTH, GRID_SIZE):
            pygame.draw.line(screen, LIGHT_GRAY, (x, 0), (x, GAME_HEIGHT))
        
        # Horizontal lines
        start_y = -(self.camera_y % GRID_SIZE)
        for y in range(start_y, GAME_HEIGHT, GRID_SIZE):
            pygame.draw.line(screen, LIGHT_GRAY, (0, y), (SCREEN_WIDTH, y))
    
    def draw_ground_reference(self):
        """Draw a reference line showing where the ground would be"""
        ground_screen_y = GROUND_Y - self.camera_y
        if 0 <= ground_screen_y <= GAME_HEIGHT:
            pygame.draw.line(screen, GREEN, (0, ground_screen_y), (SCREEN_WIDTH, ground_screen_y), 2)
            
            # Draw ground label
            text = self.small_font.render("Ground Level", True, GREEN)
            screen.blit(text, (10, ground_screen_y - 20))
    
    def draw_objects(self):
        """Draw all level objects"""
        # Draw yellow blocks
        for block in self.yellow_blocks:
            screen_x, screen_y = self.world_to_screen(block["x"], block["y"])
            if -100 < screen_x < SCREEN_WIDTH + 100 and -100 < screen_y < GAME_HEIGHT + 100:
                rect = pygame.Rect(screen_x, screen_y, block["width"], block["height"])
                
                # Draw yellow block with rivets
                pygame.draw.rect(screen, YELLOW, rect)
                pygame.draw.rect(screen, DARK_YELLOW, rect, 2)
                
                # Add rivets
                rivet_size = 2
                for x in range(screen_x + rivet_size, screen_x + block["width"] - rivet_size, 15):
                    for y in range(screen_y + rivet_size, screen_y + block["height"] - rivet_size, 15):
                        if 0 <= x < SCREEN_WIDTH and 0 <= y < GAME_HEIGHT:
                            pygame.draw.circle(screen, DARK_YELLOW, (x, y), rivet_size)
                            pygame.draw.circle(screen, BLACK, (x, y), rivet_size, 1)
                
                # Draw object ID if it has one
                if "id" in block:
                    # Highlight if selected in action mode
                    id_color = (255, 0, 0) if block == self.selected_object else BLACK
                    id_text = self.small_font.render(f"B{block['id']}", True, id_color)
                    screen.blit(id_text, (screen_x + 2, screen_y + 2))
        
        # Draw spikes
        for spike in self.spikes:
            screen_x, screen_y = self.world_to_screen(spike["x"], spike["y"])
            if -100 < screen_x < SCREEN_WIDTH + 100 and -100 < screen_y < GAME_HEIGHT + 100:
                # Draw spike as red triangle
                points = [
                    (screen_x + GRID_SIZE//2, screen_y),  # Top point
                    (screen_x, screen_y + GRID_SIZE),      # Bottom left
                    (screen_x + GRID_SIZE, screen_y + GRID_SIZE)  # Bottom right
                ]
                pygame.draw.polygon(screen, RED, points)
                pygame.draw.polygon(screen, DARK_GRAY, points, 2)
                
                # Draw object ID
                if "id" in spike:
                    # Highlight if selected in action mode
                    id_color = (255, 255, 0) if spike == self.selected_object else WHITE
                    id_text = self.small_font.render(f"S{spike['id']}", True, id_color)
                    screen.blit(id_text, (screen_x + 2, screen_y + GRID_SIZE - 12))
        
        # Draw trigger boxes
        for trigger in self.trigger_boxes:
            screen_x, screen_y = self.world_to_screen(trigger["x"], trigger["y"])
            if -100 < screen_x < SCREEN_WIDTH + 100 and -100 < screen_y < GAME_HEIGHT + 100:
                rect = pygame.Rect(screen_x, screen_y, trigger["width"], trigger["height"])
                
                # Draw orange translucent box
                surface = pygame.Surface((trigger["width"], trigger["height"]), pygame.SRCALPHA)
                color = (255, 200, 0, 120) if trigger == self.selected_trigger else (255, 165, 0, 100)
                surface.fill(color)
                screen.blit(surface, (screen_x, screen_y))
                
                # Draw border
                border_color = (255, 255, 0) if trigger == self.selected_trigger else ORANGE
                pygame.draw.rect(screen, border_color, rect, 2)
                
                # Draw "TRIGGER" text in center
                trigger_text = self.font.render("TRIGGER", True, BLACK)
                text_rect = trigger_text.get_rect(center=(screen_x + trigger["width"]//2, screen_y + trigger["height"]//2))
                screen.blit(trigger_text, text_rect)
                
                # Draw object ID
                if "id" in trigger:
                    id_text = self.small_font.render(f"T{trigger['id']}", True, BLACK)
                    screen.blit(id_text, (screen_x + 2, screen_y + 2))
        
        # Draw pits
        for pit in self.pits:
            screen_x, _ = self.world_to_screen(pit["x"], GROUND_Y)
            screen_y = GROUND_Y - self.camera_y
            
            if -100 < screen_x < SCREEN_WIDTH + 100 and -50 < screen_y < GAME_HEIGHT + 50:
                rect = pygame.Rect(screen_x, screen_y, pit["width"], 40)
                pygame.draw.rect(screen, RED, rect)
                pygame.draw.rect(screen, DARK_GRAY, rect, 2)
                
                # Draw pit label
                label = self.small_font.render("PIT", True, WHITE)
                label_rect = label.get_rect(center=(screen_x + pit["width"]//2, screen_y + 20))
                screen.blit(label, label_rect)
        
        # Draw flag
        flag_screen_x, flag_screen_y = self.world_to_screen(self.flag_x, GROUND_Y - 80)
        if -50 < flag_screen_x < SCREEN_WIDTH + 50:
            # Draw flag pole
            pygame.draw.rect(screen, BROWN, (flag_screen_x + 18, flag_screen_y, 4, 80))
            
            # Draw flag
            flag_points = [
                (flag_screen_x + 22, flag_screen_y + 10),
                (flag_screen_x + 38, flag_screen_y + 10),
                (flag_screen_x + 38, flag_screen_y + 30),
                (flag_screen_x + 30, flag_screen_y + 25),
                (flag_screen_x + 22, flag_screen_y + 30)
            ]
            pygame.draw.polygon(screen, RED, flag_points)
        
        # Draw start point
        start_screen_x, start_screen_y = self.world_to_screen(self.start_x, GROUND_Y - 60)
        if -50 < start_screen_x < SCREEN_WIDTH + 50:
            # Draw player start indicator (green circle with "S")
            pygame.draw.circle(screen, GREEN, (start_screen_x + 20, start_screen_y + 30), 25)
            pygame.draw.circle(screen, DARK_GRAY, (start_screen_x + 20, start_screen_y + 30), 25, 2)
            
            # Draw "S" for start
            start_text = self.font.render("S", True, WHITE)
            start_rect = start_text.get_rect(center=(start_screen_x + 20, start_screen_y + 30))
            screen.blit(start_text, start_rect)
        
        # Draw connection lines between triggers and objects
        for connection in self.connection_lines:
            trigger = connection["trigger"]
            obj = connection["object"]
            
            trigger_center_x = trigger["x"] + trigger["width"] // 2 - self.camera_x
            trigger_center_y = trigger["y"] + trigger["height"] // 2 - self.camera_y
            obj_center_x = obj["x"] + obj["width"] // 2 - self.camera_x
            obj_center_y = obj["y"] + obj["height"] // 2 - self.camera_y
            
            # Draw brown connection line
            if (-50 < trigger_center_x < SCREEN_WIDTH + 50 and -50 < trigger_center_y < GAME_HEIGHT + 50 and
                -50 < obj_center_x < SCREEN_WIDTH + 50 and -50 < obj_center_y < GAME_HEIGHT + 50):
                pygame.draw.line(screen, BROWN, (trigger_center_x, trigger_center_y), (obj_center_x, obj_center_y), 2)
                
                # Draw small circle at connection points
                pygame.draw.circle(screen, BROWN, (int(trigger_center_x), int(trigger_center_y)), 3)
                pygame.draw.circle(screen, BROWN, (int(obj_center_x), int(obj_center_y)), 3)
        
        # Draw ghost objects for move actions
        for ghost in self.ghost_objects:
            screen_x, screen_y = self.world_to_screen(ghost["x"], ghost["y"])
            if -100 < screen_x < SCREEN_WIDTH + 100 and -100 < screen_y < GAME_HEIGHT + 100:
                # Draw translucent ghost object
                surface = pygame.Surface((ghost["width"], ghost["height"]), pygame.SRCALPHA)
                
                if "spike" in ghost and ghost.get("spike", False):
                    # Ghost spike
                    points = [
                        (GRID_SIZE//2, 0), (0, GRID_SIZE), (GRID_SIZE, GRID_SIZE)
                    ]
                    pygame.draw.polygon(surface, (255, 0, 0, 100), points)
                else:
                    # Ghost yellow block
                    pygame.draw.rect(surface, (255, 215, 0, 100), (0, 0, ghost["width"], ghost["height"]))
                
                screen.blit(surface, (screen_x, screen_y))
                
                # Draw arrow from original to ghost
                orig = ghost["original"]
                orig_center_x = orig["x"] + orig["width"] // 2 - self.camera_x
                orig_center_y = orig["y"] + orig["height"] // 2 - self.camera_y
                ghost_center_x = screen_x + ghost["width"] // 2
                ghost_center_y = screen_y + ghost["height"] // 2
                
                # Draw dark green arrow
                pygame.draw.line(screen, (0, 100, 0), (orig_center_x, orig_center_y), (ghost_center_x, ghost_center_y), 3)
                
                # Draw arrowhead
                import math
                angle = math.atan2(ghost_center_y - orig_center_y, ghost_center_x - orig_center_x)
                arrow_length = 10
                arrow_angle = 0.5
                
                arrow_x1 = ghost_center_x - arrow_length * math.cos(angle - arrow_angle)
                arrow_y1 = ghost_center_y - arrow_length * math.sin(angle - arrow_angle)
                arrow_x2 = ghost_center_x - arrow_length * math.cos(angle + arrow_angle)
                arrow_y2 = ghost_center_y - arrow_length * math.sin(angle + arrow_angle)
                
                pygame.draw.polygon(screen, (0, 100, 0), [
                    (ghost_center_x, ghost_center_y),
                    (arrow_x1, arrow_y1),
                    (arrow_x2, arrow_y2)
                ])
        
        # Draw ghost cursor object during move positioning
        if self.ghost_cursor_object and self.action_step == 2:
            snapped_x, snapped_y = self.snap_to_grid(self.mouse_world_pos[0], self.mouse_world_pos[1])
            screen_x, screen_y = self.world_to_screen(snapped_x, snapped_y)
            
            if -100 < screen_x < SCREEN_WIDTH + 100 and -100 < screen_y < GAME_HEIGHT + 100:
                # Draw translucent cursor object
                surface = pygame.Surface((self.ghost_cursor_object["width"], self.ghost_cursor_object["height"]), pygame.SRCALPHA)
                
                if "spike" in self.ghost_cursor_object and self.ghost_cursor_object.get("spike", False):
                    # Ghost spike at cursor
                    points = [
                        (GRID_SIZE//2, 0), (0, GRID_SIZE), (GRID_SIZE, GRID_SIZE)
                    ]
                    pygame.draw.polygon(surface, (255, 0, 0, 150), points)
                else:
                    # Ghost yellow block at cursor
                    pygame.draw.rect(surface, (255, 215, 0, 150), (0, 0, self.ghost_cursor_object["width"], self.ghost_cursor_object["height"]))
                
                screen.blit(surface, (screen_x, screen_y))
    
    def draw_drag_preview(self):
        """Draw preview of object being dragged"""
        if self.dragging and self.drag_start and self.current_tool in ["yellow_block", "pit", "spike", "trigger_box"]:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            if mouse_y < GAME_HEIGHT:
                world_x, world_y = self.screen_to_world(mouse_x, mouse_y)
                end_pos = self.snap_to_grid(world_x, world_y)
                
                x1, y1 = self.drag_start
                x2, y2 = end_pos
                
                left = min(x1, x2)
                right = max(x1, x2)
                top = min(y1, y2)
                bottom = max(y1, y2)
                
                width = right - left + GRID_SIZE
                height = bottom - top + GRID_SIZE
                
                screen_x, screen_y = self.world_to_screen(left, top)
                
                if self.current_tool == "yellow_block":
                    rect = pygame.Rect(screen_x, screen_y, width, height)
                    pygame.draw.rect(screen, YELLOW, rect, 3)
                elif self.current_tool == "pit":
                    pit_screen_y = GROUND_Y - self.camera_y
                    rect = pygame.Rect(screen_x, pit_screen_y, width, 40)
                    pygame.draw.rect(screen, RED, rect, 3)
                elif self.current_tool == "spike":
                    # Show spike preview grid
                    for x in range(left, right + GRID_SIZE, GRID_SIZE):
                        for y in range(top, bottom + GRID_SIZE, GRID_SIZE):
                            preview_screen_x, preview_screen_y = self.world_to_screen(x, y)
                            points = [
                                (preview_screen_x + GRID_SIZE//2, preview_screen_y),
                                (preview_screen_x, preview_screen_y + GRID_SIZE),
                                (preview_screen_x + GRID_SIZE, preview_screen_y + GRID_SIZE)
                            ]
                            pygame.draw.polygon(screen, RED, points, 3)
                elif self.current_tool == "trigger_box":
                    rect = pygame.Rect(screen_x, screen_y, width, height)
                    pygame.draw.rect(screen, (255, 0, 255), rect, 3)
    
    def draw_ui(self):
        """Draw user interface"""
        ui_rect = pygame.Rect(0, GAME_HEIGHT, SCREEN_WIDTH, UI_HEIGHT)
        pygame.draw.rect(screen, DARK_GRAY, ui_rect)
        pygame.draw.line(screen, WHITE, (0, GAME_HEIGHT), (SCREEN_WIDTH, GAME_HEIGHT), 2)
        
        y_offset = GAME_HEIGHT + 10
        
        # Tool selection
        tools = [
            ("1: Yellow Block", "yellow_block", YELLOW),
            ("2: Pit", "pit", RED),
            ("3: Flag", "flag", BLUE),
            ("4: Start Point", "start", GREEN),
            ("5: Spike", "spike", RED),
            ("6: Trigger Box", "trigger_box", ORANGE),
            ("7: Erase", "erase", WHITE),
            ("8: Action Mode", "action", (255, 0, 255) if self.action_mode else GRAY)
        ]
        
        x_offset = 10
        for i, (name, tool, color) in enumerate(tools):
            # Check if this tool is active
            if tool == "action":
                is_active = self.action_mode
            else:
                is_active = (self.current_tool == tool) and not self.action_mode
            
            text_color = color if is_active else GRAY
            text = self.font.render(name, True, text_color)
            screen.blit(text, (x_offset, y_offset))
            
            # Draw colored indicator
            indicator_rect = pygame.Rect(x_offset - 5, y_offset, 3, 20)
            pygame.draw.rect(screen, color if is_active else GRAY, indicator_rect)
            
            x_offset += 150
        
        # Controls
        controls = [
            "WASD/Arrows: Move Camera",
            "G: Toggle Grid",
            "Enter: Save Level (with name)",
            "L: Load Level (with name)",
            "N: New Level",
            "T: Test Level"
        ]
        
        y_offset += 30
        x_offset = 10
        for i, control in enumerate(controls):
            if i == 3:  # New line after 3 items
                y_offset += 20
                x_offset = 10
            text = self.small_font.render(control, True, WHITE)
            screen.blit(text, (x_offset, y_offset))
            x_offset += 200
        

        
        # Level info
        info_text = f"Level: {self.level_name} | Blocks: {len(self.yellow_blocks)} | Pits: {len(self.pits)} | Spikes: {len(self.spikes)} | Triggers: {len(self.trigger_boxes)}"
        info = self.small_font.render(info_text, True, WHITE)
        screen.blit(info, (10, GAME_HEIGHT + 75))
    
    def draw_sky_background(self):
        """Draw gradient sky background"""
        for y in range(GAME_HEIGHT):
            ratio = y / GAME_HEIGHT
            r = int(SKY_BLUE_TOP[0] * (1 - ratio) + SKY_BLUE_BOTTOM[0] * ratio)
            g = int(SKY_BLUE_TOP[1] * (1 - ratio) + SKY_BLUE_BOTTOM[1] * ratio)
            b = int(SKY_BLUE_TOP[2] * (1 - ratio) + SKY_BLUE_BOTTOM[2] * ratio)
            pygame.draw.line(screen, (r, g, b), (0, y), (SCREEN_WIDTH, y))
    
    def validate_level(self):
        """Check if level has required elements"""
        if not hasattr(self, 'flag_x') or self.flag_x == 2000:  # Check if flag is still at default position
            return False, "Level must have an end flag! Use tool 3 to place a flag."
        return True, ""
    
    def prompt_save_level(self):
        """Prompt user for level name and save"""
        # Validate level first
        is_valid, error_msg = self.validate_level()
        if not is_valid:
            try:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()
                messagebox.showwarning("Invalid Level", error_msg)
                root.destroy()
                return
            except ImportError:
                print(f"Cannot save: {error_msg}")
                return
        
        print("Enter level name (or press Enter for current name):")
        print(f"Current name: {self.level_name}")
        
        # Simple input method - you could enhance this with a GUI text box
        try:
            import tkinter as tk
            from tkinter import simpledialog
            
            root = tk.Tk()
            root.withdraw()  # Hide the main window
            
            new_name = simpledialog.askstring("Save Level", 
                                            f"Enter level name:", 
                                            initialvalue=self.level_name)
            root.destroy()
            
            if new_name:
                self.level_name = new_name.replace(" ", "_").lower()
                self.save_level()
            else:
                print("Save cancelled")
                
        except ImportError:
            # Fallback if tkinter not available
            print("Using current name for save")
            self.save_level()
    
    def prompt_load_level(self):
        """Prompt user for level name and load"""
        try:
            import tkinter as tk
            from tkinter import simpledialog
            
            root = tk.Tk()
            root.withdraw()
            
            # List available levels from maps directory
            available_levels = []
            if os.path.exists(self.maps_dir):
                for file in os.listdir(self.maps_dir):
                    if file.endswith(".json"):
                        level_name = file.replace(".json", "")
                        available_levels.append(level_name)
            
            level_list = ", ".join(available_levels) if available_levels else "No levels found"
            
            load_name = simpledialog.askstring("Load Level", 
                                             f"Enter level name to load:\nAvailable: {level_list}")
            root.destroy()
            
            if load_name:
                self.level_name = load_name.replace(" ", "_").lower()
                self.load_level()
            else:
                print("Load cancelled")
                
        except ImportError:
            print("Using current name for load")
            self.load_level()

    def save_level(self):
        """Save current level to JSON file"""
        # Convert yellow blocks to proper format
        yellow_blocks = []
        for block in self.yellow_blocks:
            yellow_blocks.append({
                "x": block["x"],
                "y": block["y"],
                "width": block["width"],
                "height": block["height"],
                "id": block.get("id", 0)
            })
        
        # Convert spikes to proper format
        spikes = []
        for spike in self.spikes:
            spikes.append({
                "x": spike["x"],
                "y": spike["y"],
                "width": spike["width"],
                "height": spike["height"],
                "id": spike.get("id", 0)
            })
        
        # Convert trigger boxes to proper format
        trigger_boxes = []
        for trigger in self.trigger_boxes:
            trigger_boxes.append({
                "x": trigger["x"],
                "y": trigger["y"],
                "width": trigger["width"],
                "height": trigger["height"],
                "id": trigger.get("id", 0),
                "actions": trigger.get("actions", {})
            })
        
        level_data = {
            "name": f"{self.level_name.replace('_', ' ').title()}",
            "start_position": {
                "x": self.start_x,
                "y": GROUND_Y - 100
            },
            "yellow_blocks": yellow_blocks,
            "pits": self.pits,
            "spikes": spikes,
            "trigger_boxes": trigger_boxes,
            "flag": {
                "x": self.flag_x
            }
        }
        
        filename = os.path.join(self.maps_dir, f"{self.level_name}.json")
        try:
            with open(filename, 'w') as f:
                json.dump(level_data, f, indent=2)
            print(f"Level saved as {filename}")
        except Exception as e:
            print(f"Error saving level: {e}")
    
    def load_level(self):
        """Load level from JSON file"""
        filename = os.path.join(self.maps_dir, f"{self.level_name}.json")
        try:
            with open(filename, 'r') as f:
                level_data = json.load(f)
            
            # Clear current level
            self.yellow_blocks = []
            self.pits = []
            self.spikes = []
            self.trigger_boxes = []
            
            # Load yellow blocks
            for block_data in level_data.get("yellow_blocks", []):
                self.yellow_blocks.append({
                    "x": block_data["x"],
                    "y": block_data["y"],
                    "width": block_data["width"],
                    "height": block_data.get("height", 40),  # Default height
                    "id": block_data.get("id", 0)
                })
            
            # Load spikes
            for spike_data in level_data.get("spikes", []):
                self.spikes.append({
                    "x": spike_data["x"],
                    "y": spike_data["y"],
                    "width": spike_data["width"],
                    "height": spike_data["height"],
                    "id": spike_data.get("id", 0)
                })
            
            # Load trigger boxes
            for trigger_data in level_data.get("trigger_boxes", []):
                self.trigger_boxes.append({
                    "x": trigger_data["x"],
                    "y": trigger_data["y"],
                    "width": trigger_data["width"],
                    "height": trigger_data["height"],
                    "id": trigger_data.get("id", 0),
                    "actions": trigger_data.get("actions", {})
                })
            
            # Load pits
            self.pits = level_data.get("pits", [])
            
            # Load flag
            flag_data = level_data.get("flag", {"x": 2000})
            self.flag_x = flag_data["x"]
            
            # Load start position
            start_data = level_data.get("start_position", {"x": 100})
            self.start_x = start_data["x"]
            
            # Update next object ID to avoid conflicts
            max_id = 0
            for obj in self.yellow_blocks + self.spikes + self.trigger_boxes:
                if "id" in obj and obj["id"] > max_id:
                    max_id = obj["id"]
            self.next_object_id = max_id + 1
            
            print(f"Level loaded from {filename}")
            
        except FileNotFoundError:
            print(f"Level file {filename} not found")
        except Exception as e:
            print(f"Error loading level: {e}")
    
    def new_level(self):
        """Create a new empty level"""
        self.yellow_blocks = []
        self.pits = []
        self.spikes = []
        self.trigger_boxes = []
        self.flag_x = 2000
        self.start_x = 100
        self.camera_x = 0
        self.camera_y = 0
        self.next_object_id = 1
        self.selected_trigger = None
        self.action_mode = False
        print("New level created")
    
    def test_level(self):
        """Test the current level in the main game"""
        # Validate level first
        is_valid, error_msg = self.validate_level()
        if not is_valid:
            try:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()
                messagebox.showwarning("Invalid Level", error_msg)
                root.destroy()
                return
            except ImportError:
                print(f"Cannot test: {error_msg}")
                return
        
        # Save current level as a temporary test level
        original_name = self.level_name
        self.level_name = "test_level"
        self.save_level()
        self.level_name = original_name
        
        # Launch the main game with the test level
        import subprocess
        try:
            subprocess.Popen([sys.executable, "dani_jatek.py"])
            print("Launched game for testing. Load 'test_level' to test your level.")
        except FileNotFoundError:
            print("dani_jatek.py not found!")
    
    def run(self):
        """Main editor loop"""
        running = True
        
        while running:
            events = pygame.event.get()
            running = self.handle_input(events)
            
            # Draw everything
            self.draw_sky_background()
            self.draw_grid()
            self.draw_ground_reference()
            self.draw_objects()
            self.draw_drag_preview()
            self.draw_action_instructions()  # Draw instructions at top
            self.draw_ui()
            
            pygame.display.flip()
            clock.tick(FPS)
        
        pygame.quit()
    
    def draw_action_instructions(self):
        """Draw action mode instructions at top center"""
        if self.action_mode:
            if self.action_step == 0:
                instruction = "ACTION MODE: Click on a TRIGGER BOX to select it"
                color = (255, 255, 0)
            elif self.action_step == 1:
                instruction = f"Trigger {self.selected_trigger['id']} selected. Click on an OBJECT to link"
                color = (0, 255, 255)
            elif self.action_step == 2:
                instruction = "Click where the object should MOVE TO"
                color = (255, 0, 255)
            else:
                return
            
            instruction_text = self.font.render(instruction, True, color)
            text_rect = instruction_text.get_rect(center=(SCREEN_WIDTH//2, 30))
            
            # Draw background for better visibility
            bg_rect = pygame.Rect(text_rect.x - 10, text_rect.y - 5, text_rect.width + 20, text_rect.height + 10)
            pygame.draw.rect(screen, (0, 0, 0, 180), bg_rect)
            pygame.draw.rect(screen, color, bg_rect, 2)
            
            screen.blit(instruction_text, text_rect)

if __name__ == "__main__":
    editor = LevelEditor()
    editor.run()