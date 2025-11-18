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

# Game camera constants (from the actual game)
GAME_SCREEN_WIDTH = 800
GAME_SCREEN_HEIGHT = 600

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
        self.temp_move_position = None  # Temporary storage for move position before applying
        self.ghost_objects = []  # Store ghost positions for move actions
        self.connection_lines = []  # Store trigger-object connections
        self.ghost_cursor_object = None  # Object being positioned for move action
        self.mouse_world_pos = (0, 0)  # Current mouse position in world coordinates
        self.dragging = False
        self.drag_start = None
        self.level_name = "new_level"
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)
        
        # Undo/Redo functionality
        self.undo_history = []
        self.redo_history = []
        self.max_undo_history = 50  # Limit to prevent memory issues
        
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
                elif event.key == pygame.K_z and (keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]):
                    self.undo_last_action()
                elif event.key == pygame.K_y and (keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]):
                    self.redo_last_action()
                elif event.key == pygame.K_RETURN:
                    self.prompt_save_level()
                elif event.key == pygame.K_l:
                    self.prompt_load_level()
                elif event.key == pygame.K_n:
                    self.new_level()
                elif event.key == pygame.K_t:
                    self.test_level()
                elif event.key == pygame.K_e:
                    self.toggle_trigger_at_mouse()
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    if mouse_y < GAME_HEIGHT:  # Only in game area, not UI
                        world_x, world_y = self.screen_to_world(mouse_x, mouse_y)
                        
                        if self.action_mode:
                            if self.action_step == 2:  # Setting move position
                                snapped_x, snapped_y = self.snap_to_grid(world_x, world_y)
                                # Store temporary move position and reopen dialog
                                self.temp_move_position = (snapped_x, snapped_y)
                                self.ghost_cursor_object = None
                                self.action_step = 1  # Reset to object selection step
                                self.show_object_action_dialog()
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
        
        # Save state before making changes
        if self.current_tool in ["flag", "start", "spike", "erase"]:
            self.save_state_to_undo()
        
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
        
        # Save state before making changes
        self.save_state_to_undo()
        
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
                "actions": {},
                "enabled": True
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
            
            # Check other triggers (for enable/disable actions)
            for trigger in self.trigger_boxes:
                if (trigger["x"] <= world_x < trigger["x"] + trigger["width"] and
                    trigger["y"] <= world_y < trigger["y"] + trigger["height"]):
                    # Don't allow self-targeting
                    if trigger != self.selected_trigger:
                        trigger_copy = trigger.copy()
                        trigger_copy["type"] = "trigger"  # Mark as trigger for action selection
                        self.selected_object = trigger_copy
                        self.show_action_dialog()
                        return
            
            print("Click on an object (yellow block, spike, or another trigger) to link it to the trigger.")
    
    def show_action_dialog(self):
        """Show dialog to select action type with checkboxes"""
        # Check if target object is a trigger
        target_is_trigger = self.selected_object.get("type") == "trigger"
        
        if target_is_trigger:
            self.show_trigger_action_dialog()
        else:
            self.show_object_action_dialog()
    
    def get_existing_action(self):
        """Get existing action between selected trigger and object"""
        if not self.selected_trigger or not self.selected_object:
            return None
        
        actions = self.selected_trigger.get("actions", {})
        return actions.get(str(self.selected_object["id"]), None)
    
    def get_existing_action(self):
        """Get existing action between selected trigger and object"""
        if not self.selected_trigger or not self.selected_object:
            return None
        
        actions = self.selected_trigger.get("actions", {})
        return actions.get(str(self.selected_object["id"]), None)
    
    def get_existing_trigger_action(self):
        """Get existing action between selected trigger and target trigger"""
        if not self.selected_trigger or not self.selected_object:
            return None
        
        trigger_actions = self.selected_trigger.get("trigger_actions", {})
        return trigger_actions.get(str(self.selected_object["id"]), None)
    
    def get_all_existing_actions(self):
        """Get all existing actions between selected trigger and object"""
        if not self.selected_trigger or not self.selected_object:
            return []
        
        actions = self.selected_trigger.get("actions", {})
        obj_actions = actions.get(str(self.selected_object["id"]), [])
        
        # Handle both single action (old format) and multiple actions (new format)
        if isinstance(obj_actions, dict):
            return [obj_actions]  # Convert single action to list
        elif isinstance(obj_actions, list):
            return obj_actions
        else:
            return []
    
    def get_all_existing_actions(self):
        """Get all existing actions between selected trigger and object"""
        if not self.selected_trigger or not self.selected_object:
            return []
        
        actions = self.selected_trigger.get("actions", {})
        obj_actions = actions.get(str(self.selected_object["id"]), [])
        
        # Handle both single action (old format) and multiple actions (new format)
        if isinstance(obj_actions, dict):
            return [obj_actions]  # Convert single action to list
        elif isinstance(obj_actions, list):
            return obj_actions
        else:
            return []
    
    def show_trigger_action_dialog(self):
        """Show dialog for trigger-to-trigger actions"""
        root = tk.Tk()
        root.title("Trigger Action Setup")
        root.geometry("400x200")
        
        # Center the window
        root.eval('tk::PlaceWindow . center')
        
        # Variables for checkboxes
        enable_var = tk.BooleanVar()
        disable_var = tk.BooleanVar()
        
        # Check existing action and pre-select checkbox
        existing_action = self.get_existing_trigger_action()
        if existing_action:
            if existing_action["action"] == "enable":
                enable_var.set(True)
            elif existing_action["action"] == "disable":
                disable_var.set(True)
        
        # Title label
        title_label = tk.Label(root, text=f"Trigger {self.selected_trigger['id']} → Trigger {self.selected_object['id']}", 
                              font=('Arial', 12, 'bold'))
        title_label.pack(pady=10)
        
        # Checkbox frame
        checkbox_frame = tk.Frame(root)
        checkbox_frame.pack(pady=10)
        
        def on_enable_change():
            if enable_var.get():
                disable_var.set(False)
        
        def on_disable_change():
            if disable_var.get():
                enable_var.set(False)
        
        # Enable checkbox
        enable_cb = tk.Checkbutton(checkbox_frame, text="Enable Target Trigger", 
                                  variable=enable_var, command=on_enable_change)
        enable_cb.pack(anchor='w', pady=5)
        
        # Disable checkbox
        disable_cb = tk.Checkbutton(checkbox_frame, text="Disable Target Trigger", 
                                   variable=disable_var, command=on_disable_change)
        disable_cb.pack(anchor='w', pady=5)
        
        # Buttons frame
        button_frame = tk.Frame(root)
        button_frame.pack(pady=20)
        
        def apply_action():
            if enable_var.get():
                self.add_trigger_action("enable", duration=0.0)
                root.destroy()
                self.reset_action_mode()
            elif disable_var.get():
                self.add_trigger_action("disable", duration=0.0)
                root.destroy()
                self.reset_action_mode()
            else:
                messagebox.showwarning("No Action Selected", "Please select an action (Enable or Disable)")
        
        def cancel_action():
            root.destroy()
            self.reset_action_mode()
        
        apply_btn = tk.Button(button_frame, text="Apply", command=apply_action, bg='lightgreen')
        apply_btn.pack(side='left', padx=10)
        
        cancel_btn = tk.Button(button_frame, text="Cancel", command=cancel_action, bg='lightcoral')
        cancel_btn.pack(side='left', padx=10)
        
        root.mainloop()
    
    def show_object_action_dialog(self):
        """Show dialog for trigger-to-object actions"""
        root = tk.Tk()
        root.title("Object Action Setup")
        root.geometry("450x300")
        
        # Center the window
        root.eval('tk::PlaceWindow . center')
        
        # Variables for checkboxes and entries
        appear_var = tk.BooleanVar()
        disappear_var = tk.BooleanVar()
        move_var = tk.BooleanVar()
        
        # Delay variables for each action
        appear_delay_var = tk.StringVar(value="0.0")
        disappear_delay_var = tk.StringVar(value="0.0")
        move_delay_var = tk.StringVar(value="0.0")
        
        # Delay variables for each action
        appear_delay_var = tk.StringVar(value="0.0")
        disappear_delay_var = tk.StringVar(value="0.0")
        move_delay_var = tk.StringVar(value="0.0")
        
        # Check existing actions and pre-select checkboxes
        existing_actions = self.get_all_existing_actions()
        for action_data in existing_actions:
            if action_data["action"] == "appear":
                appear_var.set(True)
                if "delay" in action_data:
                    appear_delay_var.set(str(action_data["delay"]))
            elif action_data["action"] == "disappear":
                disappear_var.set(True)
                if "delay" in action_data:
                    disappear_delay_var.set(str(action_data["delay"]))
            elif action_data["action"] == "move":
                move_var.set(True)
                if "duration" in action_data:
                    self.move_duration = action_data["duration"]
                if "delay" in action_data:
                    move_delay_var.set(str(action_data["delay"]))
        
        # Also check for temporary move position (dialog reopening case)
        if self.temp_move_position:
            move_var.set(True)
        
        # Title label
        title_label = tk.Label(root, text=f"Trigger {self.selected_trigger['id']} → Object {self.selected_object['id']}", 
                              font=('Arial', 12, 'bold'))
        title_label.pack(pady=10)
        
        # Checkbox frame
        checkbox_frame = tk.Frame(root)
        checkbox_frame.pack(pady=10)
        
        def on_appear_change():
            if appear_var.get():
                disappear_var.set(False)
        
        def on_disappear_change():
            if disappear_var.get():
                appear_var.set(False)
        
        # Appear section
        appear_frame = tk.Frame(checkbox_frame)
        appear_frame.pack(anchor='w', pady=5, fill='x')
        
        appear_cb = tk.Checkbutton(appear_frame, text="Appear", 
                                  variable=appear_var, command=on_appear_change)
        appear_cb.pack(side='left')
        
        appear_delay_label = tk.Label(appear_frame, text="Delay (sec):")
        appear_delay_label.pack(side='left', padx=(20, 5))
        
        appear_delay_entry = tk.Entry(appear_frame, textvariable=appear_delay_var, width=8)
        appear_delay_entry.pack(side='left', padx=5)
        
        # Disappear section  
        disappear_frame = tk.Frame(checkbox_frame)
        disappear_frame.pack(anchor='w', pady=5, fill='x')
        
        disappear_cb = tk.Checkbutton(disappear_frame, text="Disappear", 
                                     variable=disappear_var, command=on_disappear_change)
        disappear_cb.pack(side='left')
        
        disappear_delay_label = tk.Label(disappear_frame, text="Delay (sec):")
        disappear_delay_label.pack(side='left', padx=(20, 5))
        
        disappear_delay_entry = tk.Entry(disappear_frame, textvariable=disappear_delay_var, width=8)
        disappear_delay_entry.pack(side='left', padx=5)
        
        # Move section
        move_frame = tk.Frame(checkbox_frame)
        move_frame.pack(anchor='w', pady=5, fill='x')
        
        move_cb = tk.Checkbutton(move_frame, text="Move", variable=move_var)
        move_cb.pack(side='left')
        
        # Delay entry for move
        move_delay_label = tk.Label(move_frame, text="Delay (sec):")
        move_delay_label.pack(side='left', padx=(20, 5))
        
        move_delay_entry = tk.Entry(move_frame, textvariable=move_delay_var, width=8)
        move_delay_entry.pack(side='left', padx=5)
        
        # Time entry for move
        time_label = tk.Label(move_frame, text="Duration (sec):")
        time_label.pack(side='left', padx=(20, 5))
        
        # Use existing duration or default
        default_time = str(self.move_duration)
        time_var = tk.StringVar(value=default_time)
        time_entry = tk.Entry(move_frame, textvariable=time_var, width=8)
        time_entry.pack(side='left', padx=5)
        
        # Show move position status
        move_status_label = tk.Label(move_frame, text="")
        move_status_label.pack(side='left', padx=10)
        
        if self.temp_move_position:
            move_status_label.config(text=f"Position: ({self.temp_move_position[0]}, {self.temp_move_position[1]})", fg='green')
        else:
            # Check for existing move action position
            for action_data in existing_actions:
                if action_data["action"] == "move" and "target_x" in action_data and "target_y" in action_data:
                    move_status_label.config(text=f"Position: ({action_data['target_x']}, {action_data['target_y']})", fg='blue')
                    break
        
        # Place button for move
        def start_place_mode():
            try:
                duration = float(time_var.get())
                if duration <= 0:
                    raise ValueError("Duration must be positive")
                
                self.move_duration = duration
                self.action_step = 2
                self.ghost_cursor_object = self.selected_object.copy()
                root.destroy()
                messagebox.showinfo("Move Position", "Click on the map where the object should move to.")
            except ValueError:
                messagebox.showerror("Invalid Time", "Please enter a valid positive number for time.")
        
        place_btn = tk.Button(move_frame, text="Place", command=start_place_mode, bg='lightblue')
        place_btn.pack(side='left', padx=10)
        
        # Buttons frame
        button_frame = tk.Frame(root)
        button_frame.pack(pady=20)
        
        def apply_action():
            # Save state before making changes
            self.save_state_to_undo()
            
            # Get current actions to modify
            if "actions" not in self.selected_trigger:
                self.selected_trigger["actions"] = {}
            
            obj_id = str(self.selected_object["id"])
            
            # Initialize actions list if needed
            if obj_id not in self.selected_trigger["actions"]:
                self.selected_trigger["actions"][obj_id] = []
            elif isinstance(self.selected_trigger["actions"][obj_id], dict):
                # Convert old single action format to list
                old_action = self.selected_trigger["actions"][obj_id]
                self.selected_trigger["actions"][obj_id] = [old_action]
            
            current_actions = self.selected_trigger["actions"][obj_id]
            
            # Remove existing actions of the same types we're managing
            current_actions[:] = [action for action in current_actions 
                                if action["action"] not in ["appear", "disappear", "move"]]
            
            # Clean up visual indicators for removed actions
            self.cleanup_visual_indicators_for_object()
            
            # Add new actions based on checkbox states
            actions_added = False
            
            if appear_var.get():
                try:
                    delay = float(appear_delay_var.get())
                    if delay < 0:
                        raise ValueError("Delay must be non-negative")
                    
                    action_data = {
                        "action": "appear",
                        "duration": 2.0,
                        "delay": delay
                    }
                    current_actions.append(action_data)
                    self.add_visual_indicator("appear")
                    actions_added = True
                except ValueError:
                    messagebox.showerror("Invalid Delay", "Please enter a valid non-negative number for appear delay.")
                    return
            
            if disappear_var.get():
                try:
                    delay = float(disappear_delay_var.get())
                    if delay < 0:
                        raise ValueError("Delay must be non-negative")
                    
                    action_data = {
                        "action": "disappear",
                        "duration": 2.0,
                        "delay": delay
                    }
                    current_actions.append(action_data)
                    self.add_visual_indicator("disappear")
                    actions_added = True
                except ValueError:
                    messagebox.showerror("Invalid Delay", "Please enter a valid non-negative number for disappear delay.")
                    return
            
            if move_var.get():
                if self.temp_move_position:
                    try:
                        duration = float(time_var.get())
                        delay = float(move_delay_var.get())
                        if duration <= 0:
                            raise ValueError("Duration must be positive")
                        if delay < 0:
                            raise ValueError("Delay must be non-negative")
                        
                        action_data = {
                            "action": "move",
                            "duration": duration,
                            "delay": delay,
                            "target_x": self.temp_move_position[0],
                            "target_y": self.temp_move_position[1]
                        }
                        current_actions.append(action_data)
                        self.add_visual_indicator("move", self.temp_move_position[0], self.temp_move_position[1])
                        actions_added = True
                    except ValueError as e:
                        messagebox.showerror("Invalid Input", f"Please enter valid numbers: {str(e)}")
                        return
                else:
                    messagebox.showinfo("Move Action", "Click the 'Place' button to set move destination first.")
                    return
            
            # Clean up empty actions
            if not current_actions:
                del self.selected_trigger["actions"][obj_id]
                if not self.selected_trigger["actions"]:
                    del self.selected_trigger["actions"]
            
            action_count = len(current_actions) if current_actions else 0
            print(f"Updated actions for trigger {self.selected_trigger['id']} -> object {self.selected_object['id']}: {action_count} actions")
            
            self.temp_move_position = None  # Clear temp position
            root.destroy()
            self.reset_action_mode()
        
        def cancel_action():
            self.temp_move_position = None  # Clear temp position
            root.destroy()
            self.reset_action_mode()
        
        apply_btn = tk.Button(button_frame, text="Apply", command=apply_action, bg='lightgreen')
        apply_btn.pack(side='left', padx=10)
        
        cancel_btn = tk.Button(button_frame, text="Cancel", command=cancel_action, bg='lightcoral')
        cancel_btn.pack(side='left', padx=10)
        
        root.mainloop()
    
    def add_visual_indicator(self, action_type, target_x=None, target_y=None):
        """Add visual indicators for an action"""
        if not self.selected_trigger or not self.selected_object:
            return
        
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
    
    def cleanup_visual_indicators_for_object(self):
        """Clean up visual indicators for the currently selected trigger-object pair"""
        if not self.selected_trigger or not self.selected_object:
            return
        
        # Remove connection lines for this trigger-object pair
        self.connection_lines = [conn for conn in self.connection_lines 
                               if not (conn["trigger"] == self.selected_trigger and 
                                     conn["object"] == self.selected_object)]
        
        # Remove ghost objects for this object
        self.ghost_objects = [ghost for ghost in self.ghost_objects 
                            if not ("original" in ghost and 
                                  ghost["original"] == self.selected_object)]
    
    def add_trigger_action(self, action_type, target_x=None, target_y=None, duration=2.0, delay=0.0):
        """Legacy method for compatibility - now redirects to new system"""
        print(f"Legacy add_trigger_action called for {action_type} - use new dialog system instead")
    
    def reset_action_mode(self):
        """Reset action mode state"""
        self.selected_trigger = None
        self.selected_object = None
        self.action_step = 0
        self.action_mode = False
        self.ghost_cursor_object = None
        self.temp_move_position = None
        print("Action mode reset. Press 8 to enter action mode again.")
    
    def exit_action_mode(self):
        """Exit action mode when switching to placement tools"""
        if self.action_mode:
            self.action_mode = False
            self.selected_trigger = None
            self.selected_object = None
            self.temp_move_position = None
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
    
    def draw_camera_view_indicators(self):
        """Draw horizontal lines showing game camera view area (top and bottom boundaries)"""
        # Calculate camera view boundaries in world coordinates
        # Camera Y position follows the player with some offset
        camera_center_world_y = self.camera_y
        
        # Camera view area in world coordinates (vertical)
        camera_top = camera_center_world_y
        camera_bottom = camera_center_world_y + GAME_SCREEN_HEIGHT
        
        # Convert to screen coordinates
        camera_top_screen = camera_top - self.camera_y
        camera_bottom_screen = camera_bottom - self.camera_y
        
        # Draw horizontal lines to indicate camera boundaries
        if 0 <= camera_top_screen <= GAME_HEIGHT:
            pygame.draw.line(screen, (255, 100, 100), (0, camera_top_screen), (SCREEN_WIDTH, camera_top_screen), 3)
            # Label for top boundary
            text = self.small_font.render("Camera Top", True, (255, 100, 100))
            screen.blit(text, (10, camera_top_screen + 5))
            
        if 0 <= camera_bottom_screen <= GAME_HEIGHT:
            pygame.draw.line(screen, (255, 100, 100), (0, camera_bottom_screen), (SCREEN_WIDTH, camera_bottom_screen), 3)
            # Label for bottom boundary
            text = self.small_font.render("Camera Bottom", True, (255, 100, 100))
            screen.blit(text, (10, camera_bottom_screen - 20))
            
        # Draw camera center line (horizontal)
        camera_center_screen_y = camera_center_world_y + (GAME_SCREEN_HEIGHT // 2) - self.camera_y
        if 0 <= camera_center_screen_y <= GAME_HEIGHT:
            pygame.draw.line(screen, (255, 150, 150), (0, camera_center_screen_y), (SCREEN_WIDTH, camera_center_screen_y), 1)
            text = self.small_font.render("Camera Center", True, (255, 150, 150))
            screen.blit(text, (SCREEN_WIDTH - 100, camera_center_screen_y - 15))
    
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
                
                # Determine colors based on enabled state
                enabled = trigger.get("enabled", True)
                is_selected = trigger == self.selected_trigger
                
                if enabled:
                    # Orange colors for enabled triggers
                    fill_color = (255, 200, 0, 120) if is_selected else (255, 165, 0, 100)
                    border_color = (255, 255, 0) if is_selected else ORANGE
                    text_color = BLACK
                else:
                    # Gray colors for disabled triggers
                    fill_color = (128, 128, 128, 120) if is_selected else (100, 100, 100, 100)
                    border_color = (200, 200, 200) if is_selected else (128, 128, 128)
                    text_color = (64, 64, 64)
                
                # Draw translucent box
                surface = pygame.Surface((trigger["width"], trigger["height"]), pygame.SRCALPHA)
                surface.fill(fill_color)
                screen.blit(surface, (screen_x, screen_y))
                
                # Draw border
                pygame.draw.rect(screen, border_color, rect, 2)
                
                # Draw "TRIGGER" text in center with status
                status_suffix = " (OFF)" if not enabled else ""
                trigger_text = self.font.render(f"TRIGGER{status_suffix}", True, text_color)
                text_rect = trigger_text.get_rect(center=(screen_x + trigger["width"]//2, screen_y + trigger["height"]//2))
                screen.blit(trigger_text, text_rect)
                
                # Draw object ID
                if "id" in trigger:
                    id_text = self.small_font.render(f"T{trigger['id']}", True, text_color)
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
            "Ctrl+Z: Undo",
            "Enter: Save Level (with name)",
            "L: Load Level (with name)",
            "N: New Level",
            "T: Test Level",
            "E: Toggle Trigger Enable/Disable"
        ]
        
        y_offset += 30
        x_offset = 10
        for i, control in enumerate(controls):
            if i == 4:  # New line after 4 items
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
                "actions": trigger.get("actions", {}),
                "enabled": trigger.get("enabled", True)
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
        # Save current state before loading
        self.save_state_to_undo()
        
        filename = os.path.join(self.maps_dir, f"{self.level_name}.json")
        try:
            with open(filename, 'r') as f:
                level_data = json.load(f)
            
            # Clear current level
            self.yellow_blocks = []
            self.pits = []
            self.spikes = []
            self.trigger_boxes = []
            
            # Clear visual indicators
            self.connection_lines = []
            self.ghost_objects = []
            
            # Clear visual indicators
            self.connection_lines = []
            self.ghost_objects = []
            
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
                    "actions": trigger_data.get("actions", {}),
                    "enabled": trigger_data.get("enabled", True)
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
            
            # Rebuild visual indicators after loading
            self.rebuild_visual_indicators()
            
            print(f"Level loaded from {filename}")
            
        except FileNotFoundError:
            print(f"Level file {filename} not found")
        except Exception as e:
            print(f"Error loading level: {e}")
    
    def new_level(self):
        """Create a new empty level"""
        # Save current state before clearing
        self.save_state_to_undo()
        
        self.yellow_blocks = []
        self.pits = []
        self.spikes = []
        self.trigger_boxes = []
        
        # Clear visual indicators
        self.connection_lines = []
        self.ghost_objects = []
        
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
    
    def toggle_trigger_at_mouse(self):
        """Toggle enabled state of trigger at mouse position"""
        mouse_x, mouse_y = pygame.mouse.get_pos()
        if mouse_y < GAME_HEIGHT:  # Only in game area
            world_x, world_y = self.screen_to_world(mouse_x, mouse_y)
            
            # Find trigger at mouse position
            for trigger in self.trigger_boxes:
                if (trigger["x"] <= world_x < trigger["x"] + trigger["width"] and
                    trigger["y"] <= world_y < trigger["y"] + trigger["height"]):
                    
                    # Save state before making changes
                    self.save_state_to_undo()
                    
                    # Toggle enabled state
                    current_state = trigger.get("enabled", True)
                    trigger["enabled"] = not current_state
                    
                    status = "enabled" if trigger["enabled"] else "disabled"
                    print(f"Trigger {trigger['id']} is now {status}")
                    return
            
            print("No trigger found at mouse position. Hover over a trigger and press 'E' to toggle it.")
    
    def rebuild_visual_indicators(self):
        """Rebuild connection lines and ghost objects from loaded level data"""
        # Clear existing indicators
        self.connection_lines = []
        self.ghost_objects = []
        
        print("Rebuilding visual indicators...")
        
        # Rebuild connection lines and ghost objects from trigger actions
        for trigger in self.trigger_boxes:
            trigger_actions = trigger.get("actions", {})
            
            for target_id_str, action_data in trigger_actions.items():
                action_type = action_data.get("action", "appear")
                
                # Find target object by ID
                target_object = None
                
                # Check all object types for the target ID
                for obj_list, obj_type in [(self.yellow_blocks, "yellow_block"), 
                                         (self.spikes, "spike"),
                                         (self.trigger_boxes, "trigger")]:
                    for obj in obj_list:
                        if str(obj.get("id")) == str(target_id_str):
                            target_object = obj.copy()
                            target_object["type"] = obj_type
                            break
                    if target_object:
                        break
                
                if target_object:
                    # Create connection line
                    self.connection_lines.append({
                        "trigger": trigger,
                        "object": target_object,
                        "action": action_type
                    })
                    
                    # Create ghost object for move actions
                    if action_type == "move":
                        target_x = action_data.get("target_x")
                        target_y = action_data.get("target_y")
                        if target_x is not None and target_y is not None:
                            ghost_obj = target_object.copy()
                            ghost_obj["x"] = target_x
                            ghost_obj["y"] = target_y
                            ghost_obj["original"] = target_object
                            self.ghost_objects.append(ghost_obj)
                    
                    print(f"Rebuilt: Trigger {trigger['id']} -> {action_type} -> Object {target_id_str}")
                else:
                    print(f"Warning: Target object {target_id_str} not found for trigger {trigger['id']}")
        
        print(f"Rebuilt {len(self.connection_lines)} connections and {len(self.ghost_objects)} ghost objects")
    
    def save_state_to_undo(self):
        """Save current state to undo history"""
        state = {
            'yellow_blocks': [block.copy() for block in self.yellow_blocks],
            'pits': [pit.copy() for pit in self.pits],
            'spikes': [spike.copy() for spike in self.spikes],
            'trigger_boxes': [trigger.copy() for trigger in self.trigger_boxes],
            'flag_x': self.flag_x,
            'start_x': self.start_x,
            'next_object_id': self.next_object_id,
            'connection_lines': [conn.copy() for conn in self.connection_lines],
            'ghost_objects': [ghost.copy() for ghost in self.ghost_objects]
        }
        
        self.undo_history.append(state)
        
        # Clear redo history when new action is performed
        self.redo_history.clear()
        
        # Limit undo history size
        if len(self.undo_history) > self.max_undo_history:
            self.undo_history.pop(0)
    
    def undo_last_action(self):
        """Undo the last action"""
        if not self.undo_history:
            print("Nothing to undo")
            return
        
        # Save current state to redo history before undoing
        current_state = {
            'yellow_blocks': [block.copy() for block in self.yellow_blocks],
            'pits': [pit.copy() for pit in self.pits],
            'spikes': [spike.copy() for spike in self.spikes],
            'trigger_boxes': [trigger.copy() for trigger in self.trigger_boxes],
            'flag_x': self.flag_x,
            'start_x': self.start_x,
            'next_object_id': self.next_object_id,
            'connection_lines': [line.copy() for line in self.connection_lines],
            'ghost_objects': [ghost.copy() for ghost in self.ghost_objects]
        }
        self.redo_history.append(current_state)
        
        # Limit redo history size
        if len(self.redo_history) > self.max_undo_history:
            self.redo_history.pop(0)
        
        # Restore the last saved state
        last_state = self.undo_history.pop()
        
        self.yellow_blocks = last_state['yellow_blocks']
        self.pits = last_state['pits']
        self.spikes = last_state['spikes']
        self.trigger_boxes = last_state['trigger_boxes']
        self.flag_x = last_state['flag_x']
        self.start_x = last_state['start_x']
        self.next_object_id = last_state['next_object_id']
        self.connection_lines = last_state['connection_lines']
        self.ghost_objects = last_state['ghost_objects']
        
        print("Undid last action")
    
    def redo_last_action(self):
        """Redo the last undone action"""
        if not self.redo_history:
            print("Nothing to redo")
            return
        
        # Save current state to undo history before redoing
        current_state = {
            'yellow_blocks': [block.copy() for block in self.yellow_blocks],
            'pits': [pit.copy() for pit in self.pits],
            'spikes': [spike.copy() for spike in self.spikes],
            'trigger_boxes': [trigger.copy() for trigger in self.trigger_boxes],
            'flag_x': self.flag_x,
            'start_x': self.start_x,
            'next_object_id': self.next_object_id,
            'connection_lines': [line.copy() for line in self.connection_lines],
            'ghost_objects': [ghost.copy() for ghost in self.ghost_objects]
        }
        self.undo_history.append(current_state)
        
        # Limit undo history size
        if len(self.undo_history) > self.max_undo_history:
            self.undo_history.pop(0)
        
        # Restore the redo state
        redo_state = self.redo_history.pop()
        
        self.yellow_blocks = redo_state['yellow_blocks']
        self.pits = redo_state['pits']
        self.spikes = redo_state['spikes']
        self.trigger_boxes = redo_state['trigger_boxes']
        self.flag_x = redo_state['flag_x']
        self.start_x = redo_state['start_x']
        self.next_object_id = redo_state['next_object_id']
        self.connection_lines = redo_state['connection_lines']
        self.ghost_objects = redo_state['ghost_objects']
        
        print("Redid last action")
    
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
            self.draw_camera_view_indicators()
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