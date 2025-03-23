import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from typing import Dict, List, TypedDict, Optional
from AIControl import transmitAndPost
import asyncio
import pygame
import threading
import math
import time
from dataclasses import dataclass
from queue import Queue

class Object(TypedDict):
    name: str
    object_type: str
    interactions: Dict[str, str]

class AIInteractionResponse(TypedDict):
    with_: str
    type: str
    extraData: Optional[str]

class AIResponse(TypedDict):
    focusObject: str
    movementDirectionObject: str
    interactions: List[AIInteractionResponse]

@dataclass
class GameObject:
    name: str
    object_type: str
    x: float
    y: float
    color: tuple
    shape: str  # 'circle', 'triangle', 'square', 'pentagon'
    interactions: Dict[str, str]
    
    def contains_point(self, point_x: float, point_y: float) -> bool:
        """Check if the given point is within the object's bounds"""
        radius = 15
        dx = point_x - self.x
        dy = point_y - self.y
        return (dx * dx + dy * dy) <= (radius * radius)
    
    def draw(self, screen):
        radius = 15
        if self.shape == "triangle":
            points = [
                (self.x, self.y - radius),
                (self.x - radius, self.y + radius),
                (self.x + radius, self.y + radius)
            ]
            pygame.draw.polygon(screen, self.color, points)
        elif self.shape == "square":
            rect = pygame.Rect(self.x - radius, self.y - radius, radius * 2, radius * 2)
            pygame.draw.rect(screen, self.color, rect)
        elif self.shape == "pentagon":
            points = []
            for i in range(5):
                angle = math.radians(i * 72 - 90)
                points.append((
                    self.x + radius * math.cos(angle),
                    self.y + radius * math.sin(angle)
                ))
            pygame.draw.polygon(screen, self.color, points)
        else:  # Default to circle
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), radius)
        
        # Draw name above object
        font = pygame.font.Font(None, 24)
        text = font.render(self.name, True, (255, 255, 255))
        screen.blit(text, (self.x - text.get_width() // 2, self.y - 30))

class AIAgent:
    def __init__(self):
        self.x = 400
        self.y = 300
        self.target_x = 400
        self.target_y = 300
        self.speed = 2
        self.current_text = ""
        self.text_timer = 0
        self.stopping_distance = 50  # Distance at which AI stops from target
        
    def move_towards(self, target_obj: GameObject):
        self.target_x = target_obj.x
        self.target_y = target_obj.y
        
    def update(self):
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        distance = math.sqrt(dx * dx + dy * dy)
        
        # Only move if we're further than the stopping distance
        if distance > self.stopping_distance:
            # Calculate movement while maintaining speed
            move_distance = min(self.speed, distance - self.stopping_distance)
            self.x += (dx / distance) * move_distance
            self.y += (dy / distance) * move_distance
            
        if self.text_timer > 0:
            self.text_timer -= 1
            
    def say(self, text: str):
        self.current_text = text
        self.text_timer = 180  # Show text for 3 seconds (60 fps * 3)
        
    def draw(self, screen):
        # Draw AI as a blue pentagon
        points = []
        radius = 20
        for i in range(5):
            angle = math.radians(i * 72 - 90)
            points.append((
                self.x + radius * math.cos(angle),
                self.y + radius * math.sin(angle)
            ))
        pygame.draw.polygon(screen, (0, 128, 255), points)
        
        # Draw speech bubble if text is active
        if self.text_timer > 0:
            font = pygame.font.Font(None, 24)
            text = font.render(self.current_text, True, (255, 255, 255))
            pygame.draw.rect(screen, (0, 0, 0), 
                           (self.x - text.get_width()//2 - 5, 
                            self.y - 60, 
                            text.get_width() + 10, 
                            30))
            screen.blit(text, (self.x - text.get_width()//2, self.y - 55))

class WorldGUI:
    def __init__(self):
        self.objects: List[Object] = []
        self.game_objects: List[GameObject] = []
        self.interactions: List[Dict[str, str]] = []
        self.ai_agent = AIAgent()
        
        # Add running flag for clean shutdown
        self.running = True
        
        # Add dragging state
        self.dragged_object = None
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        
        # Add double click tracking
        self.last_click_time = 0
        self.last_clicked_object = None
        
        # Initialize Pygame in a separate thread
        self.pygame_queue = Queue()
        self.pygame_thread = threading.Thread(target=self.run_pygame)
        self.pygame_thread.daemon = True
        self.pygame_thread.start()
        
        # Initialize Tkinter
        self.root = tk.Tk()
        self.root.title("World Simulation GUI")
        self.root.geometry("400x800")  # Made window taller to accommodate new text area
        
        # Add window close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Create main container frame
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Objects List
        ttk.Label(self.main_container, text="Objects").pack()
        self.objects_listbox = tk.Listbox(self.main_container, height=8)  # Reduced height
        self.objects_listbox.pack(fill=tk.BOTH, expand=True)
        
        # Object Controls
        self.object_controls = ttk.Frame(self.main_container)
        self.object_controls.pack(fill=tk.X, pady=5)
        ttk.Button(self.object_controls, text="Add Object", command=self.show_add_object_dialog).pack(side=tk.LEFT)
        ttk.Button(self.object_controls, text="Remove Object", command=self.remove_object).pack(side=tk.LEFT)
        
        # Interactions List
        ttk.Label(self.main_container, text="Interactions").pack()
        self.interactions_listbox = tk.Listbox(self.main_container, height=8)  # Reduced height
        self.interactions_listbox.pack(fill=tk.BOTH, expand=True)
        
        # Interaction Controls
        self.interaction_controls = ttk.Frame(self.main_container)
        self.interaction_controls.pack(fill=tk.X, pady=5)
        ttk.Button(self.interaction_controls, text="Add Interaction", command=self.show_add_interaction_dialog).pack(side=tk.LEFT)
        ttk.Button(self.interaction_controls, text="Remove Interaction", command=self.remove_interaction).pack(side=tk.LEFT)
        ttk.Button(self.interaction_controls, text="Send to AI", command=self.send_to_ai).pack(side=tk.LEFT)
        
        # AI Action History
        ttk.Label(self.main_container, text="AI Actions").pack()
        self.action_text = scrolledtext.ScrolledText(self.main_container, height=12, wrap=tk.WORD)
        self.action_text.pack(fill=tk.BOTH, expand=True, pady=5)
        self.action_text.config(state=tk.DISABLED)  # Make read-only
        
        # Close button frame
        close_frame = ttk.Frame(self.main_container)
        close_frame.pack(fill=tk.X, pady=10)
        ttk.Button(close_frame, text="Close Program", command=self.close_program, style="Accent.TButton").pack(anchor=tk.CENTER)
        
        # Create custom style for the close button
        style = ttk.Style()
        style.configure("Accent.TButton", 
                       padding=10,
                       font=("TkDefaultFont", 10, "bold"))
        
        # Define available shapes and colors
        self.available_shapes = ["circle", "triangle", "square", "pentagon"]
        self.available_colors = [
            ("Red", (255, 0, 0)),
            ("Green", (0, 255, 0)),
            ("Blue", (0, 0, 255)),
            ("Yellow", (255, 255, 0)),
            ("Orange", (255, 165, 0)),
            ("Purple", (128, 0, 128)),
            ("Pink", (255, 192, 203)),
            ("Cyan", (0, 255, 255))
        ]
        
        self.update_lists()

    def generate_random_position(self):
        """Generate a random position within the current window bounds"""
        import random
        # Get current window size
        window_size = pygame.display.get_surface().get_size()
        return random.randint(50, window_size[0] - 50), random.randint(50, window_size[1] - 50)

    def update_lists(self):
        # Update objects listbox
        self.objects_listbox.delete(0, tk.END)
        for obj in self.objects:
            self.objects_listbox.insert(tk.END, f"{obj['name']} ({obj['object_type']})")
        
        # Update interactions listbox
        self.interactions_listbox.delete(0, tk.END)
        for interaction in self.interactions:
            self.interactions_listbox.insert(tk.END, f"{interaction['from']} - {interaction['type']}")

    def show_add_object_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add New Object")
        dialog.geometry("400x600")  # Increased height for new controls
        
        # Make dialog modal
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Main container with padding
        container = ttk.Frame(dialog, padding="10")
        container.pack(fill=tk.BOTH, expand=True)
        
        # Name section
        name_frame = ttk.LabelFrame(container, text="Object Name", padding="5")
        name_frame.pack(fill=tk.X, pady=(0, 10))
        name_entry = ttk.Entry(name_frame)
        name_entry.pack(fill=tk.X, padx=5, pady=5)
        
        # Type section
        type_frame = ttk.LabelFrame(container, text="Object Type", padding="5")
        type_frame.pack(fill=tk.X, pady=(0, 10))
        type_var = tk.StringVar(value="Living")
        ttk.Radiobutton(type_frame, text="Living", variable=type_var, value="Living").pack(side=tk.LEFT, padx=20, pady=5)
        ttk.Radiobutton(type_frame, text="NonLiving", variable=type_var, value="NonLiving").pack(side=tk.LEFT, padx=20, pady=5)
        
        # Shape section
        shape_frame = ttk.LabelFrame(container, text="Shape", padding="5")
        shape_frame.pack(fill=tk.X, pady=(0, 10))
        shape_var = tk.StringVar(value="circle")
        for shape in self.available_shapes:
            ttk.Radiobutton(shape_frame, text=shape.capitalize(), 
                          variable=shape_var, value=shape).pack(side=tk.LEFT, padx=10)
        
        # Color section
        color_frame = ttk.LabelFrame(container, text="Color", padding="5")
        color_frame.pack(fill=tk.X, pady=(0, 10))
        color_var = tk.StringVar(value="Green")
        for color_name, _ in self.available_colors:
            ttk.Radiobutton(color_frame, text=color_name, 
                          variable=color_var, value=color_name).pack(side=tk.LEFT, padx=5)
        
        # Interactions section
        interactions_frame = ttk.LabelFrame(container, text="Interactions", padding="5")
        interactions_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        interactions: Dict[str, str] = {}
        interactions_listbox = tk.Listbox(interactions_frame, height=8)
        interactions_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbar for interactions listbox
        scrollbar = ttk.Scrollbar(interactions_frame, orient="vertical", command=interactions_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        interactions_listbox.configure(yscrollcommand=scrollbar.set)
        
        def add_interaction():
            interaction_dialog = tk.Toplevel(dialog)
            interaction_dialog.title("Add Interaction")
            interaction_dialog.geometry("350x250")  # Adjusted size
            interaction_dialog.transient(dialog)
            interaction_dialog.grab_set()
            
            # Container with padding
            int_container = ttk.Frame(interaction_dialog, padding="10")
            int_container.pack(fill=tk.BOTH, expand=True)
            
            # Name field
            name_frame = ttk.LabelFrame(int_container, text="Interaction Name", padding="5")
            name_frame.pack(fill=tk.X, pady=(0, 10))
            int_name_entry = ttk.Entry(name_frame)
            int_name_entry.pack(fill=tk.X, padx=5, pady=5)
            
            # Description field
            desc_frame = ttk.LabelFrame(int_container, text="Description", padding="5")
            desc_frame.pack(fill=tk.X, pady=(0, 10))
            int_desc_entry = ttk.Entry(desc_frame)
            int_desc_entry.pack(fill=tk.X, padx=5, pady=5)
            
            # Buttons frame
            button_frame = ttk.Frame(int_container)
            button_frame.pack(fill=tk.X, pady=(10, 0))
            
            def save_interaction():
                name = int_name_entry.get()
                desc = int_desc_entry.get()
                if name and desc:
                    interactions[name] = desc
                    interactions_listbox.delete(0, tk.END)
                    for k, v in interactions.items():
                        interactions_listbox.insert(tk.END, f"{k}: {v}")
                interaction_dialog.destroy()
            
            def cancel_interaction():
                interaction_dialog.destroy()
            
            ttk.Button(button_frame, text="Save", command=save_interaction).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Cancel", command=cancel_interaction).pack(side=tk.LEFT, padx=5)
        
        # Interaction buttons frame
        int_button_frame = ttk.Frame(interactions_frame)
        int_button_frame.pack(fill=tk.X, pady=5)
        ttk.Button(int_button_frame, text="Add Interaction", command=add_interaction).pack(side=tk.LEFT, padx=5)
        ttk.Button(int_button_frame, text="Remove Interaction", command=lambda: remove_object_interaction()).pack(side=tk.LEFT, padx=5)
        
        def remove_object_interaction():
            selection = interactions_listbox.curselection()
            if selection:
                index = selection[0]
                selected_item = interactions_listbox.get(index)
                interaction_name = selected_item.split(":")[0].strip()
                if interaction_name in interactions:
                    del interactions[interaction_name]
                    interactions_listbox.delete(0, tk.END)
                    for k, v in interactions.items():
                        interactions_listbox.insert(tk.END, f"{k}: {v}")
        
        # Main dialog buttons frame
        button_frame = ttk.Frame(container)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        def save_object():
            name = name_entry.get()
            obj_type = type_var.get()
            if name and obj_type:
                x, y = self.generate_random_position()
                # Get color tuple from selected color name
                color = next(color_tuple for name, color_tuple in self.available_colors 
                           if name == color_var.get())
                
                new_object: Object = {
                    "name": name,
                    "object_type": obj_type,
                    "interactions": interactions
                }
                
                game_object = GameObject(
                    name=name,
                    object_type=obj_type,
                    x=x,
                    y=y,
                    color=color,
                    shape=shape_var.get(),
                    interactions=interactions
                )
                
                self.objects.append(new_object)
                self.game_objects.append(game_object)
                self.update_lists()
                dialog.destroy()
        
        def cancel_object():
            dialog.destroy()
        
        ttk.Button(button_frame, text="Save", command=save_object).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=cancel_object).pack(side=tk.LEFT, padx=5)

    def remove_object(self):
        selection = self.objects_listbox.curselection()
        if selection:
            index = selection[0]
            self.objects.pop(index)
            self.game_objects.pop(index)
            self.update_lists()

    def show_add_interaction_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Interaction")
        dialog.geometry("400x300")  # Increased height
        
        # Make dialog modal
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Main container with padding
        container = ttk.Frame(dialog, padding="10")
        container.pack(fill=tk.BOTH, expand=True)
        
        # From Object field
        from_frame = ttk.LabelFrame(container, text="From Object", padding="5")
        from_frame.pack(fill=tk.X, pady=(0, 10))
        from_entry = ttk.Entry(from_frame)
        from_entry.pack(fill=tk.X, padx=5, pady=5)
        
        # Type field
        type_frame = ttk.LabelFrame(container, text="Interaction Type", padding="5")
        type_frame.pack(fill=tk.X, pady=(0, 10))
        type_entry = ttk.Entry(type_frame)
        type_entry.pack(fill=tk.X, padx=5, pady=5)
        
        # Description field
        desc_frame = ttk.LabelFrame(container, text="Description", padding="5")
        desc_frame.pack(fill=tk.X, pady=(0, 10))
        desc_entry = ttk.Entry(desc_frame)
        desc_entry.pack(fill=tk.X, padx=5, pady=5)
        
        # Buttons frame
        button_frame = ttk.Frame(container)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        def save_interaction():
            from_obj = from_entry.get()
            int_type = type_entry.get()
            desc = desc_entry.get()
            if from_obj and int_type and desc:
                interaction = {
                    "from": from_obj,
                    "type": int_type,
                    "description": desc
                }
                self.interactions.append(interaction)
                self.update_lists()
                dialog.destroy()
        
        def cancel_interaction():
            dialog.destroy()
        
        ttk.Button(button_frame, text="Save", command=save_interaction).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=cancel_interaction).pack(side=tk.LEFT, padx=5)

    def remove_interaction(self):
        """Remove the selected interaction from the interactions list"""
        selection = self.interactions_listbox.curselection()
        if selection:
            index = selection[0]
            self.interactions.pop(index)
            self.update_lists()

    async def _send_to_ai(self):
        data = {
            "objects": self.objects,
            "interactionsWithYou": self.interactions
        }
        result = await transmitAndPost(data)
        return result

    def add_ai_action(self, text: str):
        """Add an AI action to the history with timestamp"""
        self.action_text.config(state=tk.NORMAL)
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        self.action_text.insert(tk.END, f"[{timestamp}] {text}\n")
        self.action_text.see(tk.END)  # Scroll to bottom
        self.action_text.config(state=tk.DISABLED)

    def send_to_ai(self):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(self._send_to_ai())
        
        # Find target object and move AI towards it
        target_obj = next((obj for obj in self.game_objects if obj.name == result['focusObject']), None)
        if target_obj:
            self.pygame_queue.put(('move_ai', target_obj))
            self.add_ai_action(f"Moving toward {result['focusObject']}")
        
        # Process interactions
        for interaction in result['interactions']:
            target_obj = next((obj for obj in self.game_objects if obj.name == interaction['with_']), None)
            if target_obj:
                if interaction['extraData']:
                    self.pygame_queue.put(('ai_speak', interaction['extraData']))
                    self.add_ai_action(f"Speaking to {interaction['with_']}: {interaction['extraData']}")
                self.pygame_queue.put(('move_ai', target_obj))
                self.add_ai_action(f"Using '{interaction['type']}' with {interaction['with_']}")
                time.sleep(1)  # Add delay between interactions
        
        # Clear interactions after processing
        self.interactions = []
        self.update_lists()

    def on_closing(self):
        """Handle window closing event"""
        self.running = False  # Signal pygame thread to stop
        self.root.quit()  # Stop tkinter mainloop
        self.root.destroy()  # Destroy the window
        pygame.quit()  # Quit pygame
        
    def show_edit_object_dialog(self, game_object: GameObject, object_index: int):
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Object")
        dialog.geometry("400x600")  # Increased height for new controls
        
        # Make dialog modal
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Main container with padding
        container = ttk.Frame(dialog, padding="10")
        container.pack(fill=tk.BOTH, expand=True)
        
        # Name section
        name_frame = ttk.LabelFrame(container, text="Object Name", padding="5")
        name_frame.pack(fill=tk.X, pady=(0, 10))
        name_entry = ttk.Entry(name_frame)
        name_entry.insert(0, game_object.name)  # Pre-fill name
        name_entry.pack(fill=tk.X, padx=5, pady=5)
        
        # Type section
        type_frame = ttk.LabelFrame(container, text="Object Type", padding="5")
        type_frame.pack(fill=tk.X, pady=(0, 10))
        type_var = tk.StringVar(value=game_object.object_type)  # Pre-fill type
        ttk.Radiobutton(type_frame, text="Living", variable=type_var, value="Living").pack(side=tk.LEFT, padx=20, pady=5)
        ttk.Radiobutton(type_frame, text="NonLiving", variable=type_var, value="NonLiving").pack(side=tk.LEFT, padx=20, pady=5)
        
        # Shape section
        shape_frame = ttk.LabelFrame(container, text="Shape", padding="5")
        shape_frame.pack(fill=tk.X, pady=(0, 10))
        shape_var = tk.StringVar(value=game_object.shape)  # Pre-fill shape
        for shape in self.available_shapes:
            ttk.Radiobutton(shape_frame, text=shape.capitalize(), 
                          variable=shape_var, value=shape).pack(side=tk.LEFT, padx=10)
        
        # Color section
        color_frame = ttk.LabelFrame(container, text="Color", padding="5")
        color_frame.pack(fill=tk.X, pady=(0, 10))
        # Find the color name from the tuple
        current_color_name = next(name for name, color_tuple in self.available_colors 
                                if color_tuple == game_object.color)
        color_var = tk.StringVar(value=current_color_name)
        for color_name, _ in self.available_colors:
            ttk.Radiobutton(color_frame, text=color_name, 
                          variable=color_var, value=color_name).pack(side=tk.LEFT, padx=5)
        
        # Interactions section
        interactions_frame = ttk.LabelFrame(container, text="Interactions", padding="5")
        interactions_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        interactions: Dict[str, str] = game_object.interactions.copy()  # Copy existing interactions
        interactions_listbox = tk.Listbox(interactions_frame, height=8)
        interactions_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Pre-fill interactions listbox
        for k, v in interactions.items():
            interactions_listbox.insert(tk.END, f"{k}: {v}")
        
        # Scrollbar for interactions listbox
        scrollbar = ttk.Scrollbar(interactions_frame, orient="vertical", command=interactions_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        interactions_listbox.configure(yscrollcommand=scrollbar.set)
        
        def add_interaction():
            interaction_dialog = tk.Toplevel(dialog)
            interaction_dialog.title("Add Interaction")
            interaction_dialog.geometry("350x250")
            interaction_dialog.transient(dialog)
            interaction_dialog.grab_set()
            
            # Container with padding
            int_container = ttk.Frame(interaction_dialog, padding="10")
            int_container.pack(fill=tk.BOTH, expand=True)
            
            # Name field
            name_frame = ttk.LabelFrame(int_container, text="Interaction Name", padding="5")
            name_frame.pack(fill=tk.X, pady=(0, 10))
            int_name_entry = ttk.Entry(name_frame)
            int_name_entry.pack(fill=tk.X, padx=5, pady=5)
            
            # Description field
            desc_frame = ttk.LabelFrame(int_container, text="Description", padding="5")
            desc_frame.pack(fill=tk.X, pady=(0, 10))
            int_desc_entry = ttk.Entry(desc_frame)
            int_desc_entry.pack(fill=tk.X, padx=5, pady=5)
            
            # Buttons frame
            button_frame = ttk.Frame(int_container)
            button_frame.pack(fill=tk.X, pady=(10, 0))
            
            def save_interaction():
                name = int_name_entry.get()
                desc = int_desc_entry.get()
                if name and desc:
                    interactions[name] = desc
                    interactions_listbox.delete(0, tk.END)
                    for k, v in interactions.items():
                        interactions_listbox.insert(tk.END, f"{k}: {v}")
                interaction_dialog.destroy()
            
            def cancel_interaction():
                interaction_dialog.destroy()
            
            ttk.Button(button_frame, text="Save", command=save_interaction).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Cancel", command=cancel_interaction).pack(side=tk.LEFT, padx=5)
        
        # Interaction buttons frame
        int_button_frame = ttk.Frame(interactions_frame)
        int_button_frame.pack(fill=tk.X, pady=5)
        ttk.Button(int_button_frame, text="Add Interaction", command=add_interaction).pack(side=tk.LEFT, padx=5)
        ttk.Button(int_button_frame, text="Remove Interaction", command=lambda: remove_object_interaction()).pack(side=tk.LEFT, padx=5)
        
        def remove_object_interaction():
            selection = interactions_listbox.curselection()
            if selection:
                index = selection[0]
                selected_item = interactions_listbox.get(index)
                interaction_name = selected_item.split(":")[0].strip()
                if interaction_name in interactions:
                    del interactions[interaction_name]
                    interactions_listbox.delete(0, tk.END)
                    for k, v in interactions.items():
                        interactions_listbox.insert(tk.END, f"{k}: {v}")
        
        # Main dialog buttons frame
        button_frame = ttk.Frame(container)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        def save_object():
            name = name_entry.get()
            obj_type = type_var.get()
            if name and obj_type:
                # Get color tuple from selected color name
                color = next(color_tuple for name, color_tuple in self.available_colors 
                           if name == color_var.get())
                
                # Update the existing objects
                self.objects[object_index].update({
                    "name": name,
                    "object_type": obj_type,
                    "interactions": interactions
                })
                
                # Update game object
                game_object.name = name
                game_object.object_type = obj_type
                game_object.interactions = interactions
                game_object.color = color
                game_object.shape = shape_var.get()
                
                self.update_lists()
                dialog.destroy()
        
        def cancel_object():
            dialog.destroy()
        
        ttk.Button(button_frame, text="Save", command=save_object).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=cancel_object).pack(side=tk.LEFT, padx=5)

    def close_program(self):
        """Gracefully close the program with confirmation"""
        if messagebox.askokcancel("Close Program", "Are you sure you want to close the program?"):
            self.on_closing()

    def run_pygame(self):
        pygame.init()
        screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
        pygame.display.set_caption("World Simulation")
        clock = pygame.time.Clock()
        
        # Track window size
        window_width = 800
        window_height = 600
        
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    self.root.quit()
                    break
                elif event.type == pygame.VIDEORESIZE:
                    # Handle window resize
                    old_width = window_width
                    old_height = window_height
                    window_width = event.w
                    window_height = event.h
                    screen = pygame.display.set_mode((window_width, window_height), pygame.RESIZABLE)
                    
                    # Scale object positions to maintain relative positions
                    scale_x = window_width / old_width
                    scale_y = window_height / old_height
                    for obj in self.game_objects:
                        obj.x *= scale_x
                        obj.y *= scale_y
                    
                    # Scale AI position
                    self.ai_agent.x *= scale_x
                    self.ai_agent.y *= scale_y
                    self.ai_agent.target_x *= scale_x
                    self.ai_agent.target_y *= scale_y
                    
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left mouse button
                        current_time = time.time()
                        mouse_x, mouse_y = event.pos
                        
                        # Check for double click
                        if (current_time - self.last_click_time) < 0.4:  # 400ms for double click
                            # Check if clicked on the same object
                            for i, obj in enumerate(self.game_objects):
                                if obj == self.last_clicked_object and obj.contains_point(mouse_x, mouse_y):
                                    # Open edit dialog
                                    self.show_edit_object_dialog(obj, i)
                                    break
                        
                        # Update last click info
                        self.last_click_time = current_time
                        
                        # Check for dragging
                        for obj in self.game_objects:
                            if obj.contains_point(mouse_x, mouse_y):
                                self.dragged_object = obj
                                self.last_clicked_object = obj
                                self.drag_offset_x = obj.x - mouse_x
                                self.drag_offset_y = obj.y - mouse_y
                                break
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:  # Left mouse button
                        self.dragged_object = None
                elif event.type == pygame.MOUSEMOTION:
                    if self.dragged_object is not None:
                        # Update object position, keeping it within screen bounds
                        mouse_x, mouse_y = event.pos
                        new_x = mouse_x + self.drag_offset_x
                        new_y = mouse_y + self.drag_offset_y
                        
                        # Constrain to screen bounds with padding
                        padding = 30  # Enough to keep object and name visible
                        new_x = max(padding, min(window_width - padding, new_x))
                        new_y = max(padding, min(window_height - padding, new_y))
                        
                        self.dragged_object.x = new_x
                        self.dragged_object.y = new_y
            
            if not self.running:
                break
                
            # Process any commands from the tkinter thread
            while not self.pygame_queue.empty():
                cmd, data = self.pygame_queue.get()
                if cmd == 'move_ai':
                    self.ai_agent.move_towards(data)
                elif cmd == 'ai_speak':
                    self.ai_agent.say(data)
            
            # Update
            self.ai_agent.update()
            
            # Draw
            screen.fill((32, 32, 32))  # Dark gray background
            
            # Draw all game objects
            for obj in self.game_objects:
                obj.draw(screen)
            
            # Draw AI agent
            self.ai_agent.draw(screen)
            
            pygame.display.flip()
            clock.tick(60)
        
        pygame.quit()

    def run(self):
        try:
            self.root.mainloop()
        finally:
            self.running = False  # Ensure pygame thread stops
            pygame.quit()  # Ensure pygame is properly shut down

if __name__ == "__main__":
    app = WorldGUI()
    app.run() 