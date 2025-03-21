import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, TypedDict, Optional
from AIControl import transmitAndPost
import asyncio
import json

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

class WorldGUI:
    def __init__(self):
        self.objects: List[Object] = []
        self.interactions: List[Dict[str, str]] = []
        
        self.root = tk.Tk()
        self.root.title("World Simulation GUI")
        self.root.geometry("1000x800")
        
        # Create main container frame
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create top frame for objects and interactions
        self.top_frame = ttk.Frame(self.main_container)
        self.top_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create main frames in top frame
        self.left_frame = ttk.Frame(self.top_frame)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.right_frame = ttk.Frame(self.top_frame)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Objects List
        ttk.Label(self.left_frame, text="Objects").pack()
        self.objects_listbox = tk.Listbox(self.left_frame, height=10)
        self.objects_listbox.pack(fill=tk.BOTH, expand=True)
        
        # Object Controls
        self.object_controls = ttk.Frame(self.left_frame)
        self.object_controls.pack(fill=tk.X, pady=5)
        ttk.Button(self.object_controls, text="Add Object", command=self.show_add_object_dialog).pack(side=tk.LEFT)
        ttk.Button(self.object_controls, text="Remove Object", command=self.remove_object).pack(side=tk.LEFT)
        
        # Interactions List
        ttk.Label(self.right_frame, text="Interactions").pack()
        self.interactions_listbox = tk.Listbox(self.right_frame, height=10)
        self.interactions_listbox.pack(fill=tk.BOTH, expand=True)
        
        # Interaction Controls
        self.interaction_controls = ttk.Frame(self.right_frame)
        self.interaction_controls.pack(fill=tk.X, pady=5)
        ttk.Button(self.interaction_controls, text="Add Interaction", command=self.show_add_interaction_dialog).pack(side=tk.LEFT)
        ttk.Button(self.interaction_controls, text="Send to AI", command=self.send_to_ai).pack(side=tk.LEFT)
        
        # Create bottom frame for AI output
        self.bottom_frame = ttk.Frame(self.main_container)
        self.bottom_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # AI Output
        ttk.Label(self.bottom_frame, text="AI Output").pack()
        self.output_text = tk.Text(self.bottom_frame, wrap=tk.WORD, height=10)
        self.output_text.pack(fill=tk.BOTH, expand=True)
        
        # Add scrollbar to output text
        output_scrollbar = ttk.Scrollbar(self.bottom_frame, orient="vertical", command=self.output_text.yview)
        output_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.output_text.configure(yscrollcommand=output_scrollbar.set)
        
        self.update_lists()

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
        dialog.geometry("400x300")
        
        ttk.Label(dialog, text="Name:").pack(pady=5)
        name_entry = ttk.Entry(dialog)
        name_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Type:").pack(pady=5)
        type_var = tk.StringVar(value="Living")
        type_frame = ttk.Frame(dialog)
        type_frame.pack(pady=5)
        ttk.Radiobutton(type_frame, text="Living", variable=type_var, value="Living").pack(side=tk.LEFT)
        ttk.Radiobutton(type_frame, text="NonLiving", variable=type_var, value="NonLiving").pack(side=tk.LEFT)
        
        # Interactions
        ttk.Label(dialog, text="Interactions:").pack(pady=5)
        interactions_frame = ttk.Frame(dialog)
        interactions_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        interactions: Dict[str, str] = {}
        interactions_listbox = tk.Listbox(interactions_frame, height=5)
        interactions_listbox.pack(fill=tk.BOTH, expand=True)
        
        def add_interaction():
            interaction_dialog = tk.Toplevel(dialog)
            interaction_dialog.title("Add Interaction")
            
            ttk.Label(interaction_dialog, text="Name:").pack(pady=5)
            int_name_entry = ttk.Entry(interaction_dialog)
            int_name_entry.pack(pady=5)
            
            ttk.Label(interaction_dialog, text="Description:").pack(pady=5)
            int_desc_entry = ttk.Entry(interaction_dialog)
            int_desc_entry.pack(pady=5)
            
            def save_interaction():
                name = int_name_entry.get()
                desc = int_desc_entry.get()
                if name and desc:
                    interactions[name] = desc
                    interactions_listbox.delete(0, tk.END)
                    for k, v in interactions.items():
                        interactions_listbox.insert(tk.END, f"{k}: {v}")
                interaction_dialog.destroy()
            
            ttk.Button(interaction_dialog, text="Save", command=save_interaction).pack(pady=5)
        
        ttk.Button(interactions_frame, text="Add Interaction", command=add_interaction).pack(pady=5)
        
        def save_object():
            name = name_entry.get()
            obj_type = type_var.get()
            if name and obj_type:
                new_object: Object = {
                    "name": name,
                    "object_type": obj_type,
                    "interactions": interactions
                }
                self.objects.append(new_object)
                self.update_lists()
                dialog.destroy()
        
        ttk.Button(dialog, text="Save", command=save_object).pack(pady=10)

    def remove_object(self):
        selection = self.objects_listbox.curselection()
        if selection:
            index = selection[0]
            self.objects.pop(index)
            self.update_lists()

    def show_add_interaction_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Interaction")
        dialog.geometry("400x200")
        
        ttk.Label(dialog, text="From Object:").pack(pady=5)
        from_entry = ttk.Entry(dialog)
        from_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Type:").pack(pady=5)
        type_entry = ttk.Entry(dialog)
        type_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Description:").pack(pady=5)
        desc_entry = ttk.Entry(dialog)
        desc_entry.pack(pady=5)
        
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
        
        ttk.Button(dialog, text="Save", command=save_interaction).pack(pady=10)

    async def _send_to_ai(self):
        data = {
            "objects": self.objects,
            "interactionsWithYou": self.interactions
        }
        result = await transmitAndPost(data)
        return result

    def send_to_ai(self):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(self._send_to_ai())
        
        # Clear previous output and enable text widget for updating
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        
        # Insert new AI response
        self.output_text.insert(tk.END, f"The AI Moves toward {result['focusObject']}\n\n")
        for interaction in result['interactions']:
            if interaction['extraData']:
                self.output_text.insert(tk.END, f"The AI chooses to use '{interaction['type']}' toward {interaction['with_']} and says {interaction['extraData']}\n")
            else:
                self.output_text.insert(tk.END, f"The AI chooses to {interaction['type']} with {interaction['with_']}\n")
        
        # Disable text widget to prevent user editing
        self.output_text.config(state=tk.DISABLED)
        
        # Clear interactions after processing
        self.interactions = []
        self.update_lists()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = WorldGUI()
    app.run() 