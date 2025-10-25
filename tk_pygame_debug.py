# tk_pygame_debug.py — debug for Tkinter + pygame window issue
import sys, time
print("Python:", sys.executable)
print("Starting imports...")

try:
    import tkinter as tk
    from tkinter import messagebox
    print("Tkinter imported OK")
except Exception as e:
    print("Tkinter import FAILED:", repr(e))
    raise

try:
    import pygame
    print("pygame imported OK:", pygame.version.ver)
except Exception as e:
    print("pygame import FAILED:", repr(e))
    raise

# Simple Tk test
root = tk.Tk()
root.title("DEBUG: Tkinter Window")
root.geometry("320x140")

lbl = tk.Label(root, text="If you see this, Tkinter works.\nClose window to exit.", pady=10)
lbl.pack()

def on_show_msg():
    try:
        messagebox.showinfo("DEBUG", "Messagebox works — GUI is visible.")
    except Exception as e:
        print("messagebox FAILED:", repr(e))

btn = tk.Button(root, text="Show messagebox", command=on_show_msg)
btn.pack(pady=8)

print("Entering mainloop (Tk window should open)...")
root.update()          # try to force update
time.sleep(0.5)
root.deiconify()       # ensure window is not hidden
root.lift()            # bring to front
root.attributes('-topmost', True)
root.after(100, lambda: root.attributes('-topmost', False))
root.mainloop()
print("Exited mainloop")
