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
    interactions: Dict[str, str]
    
    def contains_point(self, point_x: float, point_y: float) -> bool:
        """Check if the given point is within the object's bounds"""
        if self.object_type == "Living":
            # For triangles, use a simple radius check for simplicity
            radius = 15
            dx = point_x - self.x
            dy = point_y - self.y
            return (dx * dx + dy * dy) <= (radius * radius)
        else:
            # For circles, use radius check
            radius = 15
            dx = point_x - self.x
            dy = point_y - self.y
            return (dx * dx + dy * dy) <= (radius * radius)
    
    def draw(self, screen):
        if self.object_type == "Living":
            # Draw living objects as triangles
            radius = 15
            points = [
                (self.x, self.y - radius),
                (self.x - radius, self.y + radius),
                (self.x + radius, self.y + radius)
            ]
            pygame.draw.polygon(screen, self.color, points)
        else:
            # Draw non-living objects as circles
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), 15)
        
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
        
    def move_towards(self, target_obj: GameObject):
        self.target_x = target_obj.x
        self.target_y = target_obj.y
        
    def update(self):
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        distance = math.sqrt(dx * dx + dy * dy)
        
        if distance > self.speed:
            self.x += (dx / distance) * self.speed
            self.y += (dy / distance) * self.speed
            
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
        ttk.Button(self.interaction_controls, text="Send to AI", command=self.send_to_ai).pack(side=tk.LEFT)
        
        # AI Action History
        ttk.Label(self.main_container, text="AI Actions").pack()
        self.action_text = scrolledtext.ScrolledText(self.main_container, height=12, wrap=tk.WORD)
        self.action_text.pack(fill=tk.BOTH, expand=True, pady=5)
        self.action_text.config(state=tk.DISABLED)  # Make read-only
        
        self.update_lists()

    def generate_random_position(self):
        import random
        return random.randint(50, 750), random.randint(50, 550)

    def generate_object_color(self, object_type: str):
        if object_type == "Living":
            return (0, 255, 0)  # Green for living objects
        return (255, 165, 0)    # Orange for non-living objects

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
        dialog.geometry("400x500")  # Increased height
        
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
        
        # Main dialog buttons frame
        button_frame = ttk.Frame(container)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        def save_object():
            name = name_entry.get()
            obj_type = type_var.get()
            if name and obj_type:
                x, y = self.generate_random_position()
                color = self.generate_object_color(obj_type)
                
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
        
    def run_pygame(self):
        pygame.init()
        screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("World Simulation")
        clock = pygame.time.Clock()
        
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    self.root.quit()  # Stop tkinter mainloop
                    break
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left mouse button
                        mouse_x, mouse_y = event.pos
                        # Check if clicked on any object
                        for obj in self.game_objects:
                            if obj.contains_point(mouse_x, mouse_y):
                                self.dragged_object = obj
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
                        new_x = max(padding, min(800 - padding, new_x))
                        new_y = max(padding, min(600 - padding, new_y))
                        
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