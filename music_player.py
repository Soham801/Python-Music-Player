# Requires: pygame
# Run: python music_player.py

import tkinter as tk
from tkinter import filedialog, messagebox
import time
import re
import os

# don't import pygame.mixer at top-level to avoid interfering with Tk on some Windows setups
try:
    import pygame
except Exception as e:
    pygame = None

class MusicPlayer:
    def __init__(self, root):
        self.root = root
        root.title(" Music Player using Python")
        root.geometry("480x240")
        self.playing = False
        self.paused = False
        self.audio_path = None
        self.lrc = []
        self.start_time = 0.0
        self.pause_offset = 0.0
        self.pygame_initialized = False

        # UI
        self.label_song = tk.Label(root, text="No file loaded", wraplength=460)
        self.label_song.pack(pady=6)

        button_frame = tk.Frame(root)
        button_frame.pack(pady=6)
        tk.Button(button_frame, text="Load", command=self.load).grid(row=0, column=0, padx=6)
        self.btn_play = tk.Button(button_frame, text="Play", command=self.play_pause)
        self.btn_play.grid(row=0, column=1, padx=6)
        tk.Button(button_frame, text="Stop", command=self.stop).grid(row=0, column=2, padx=6)

        self.lyric_var = tk.StringVar()
        self.lyric_var.set("Lyrics will appear here when a .lrc file is loaded (same folder as audio or chosen).")
        self.label_lyric = tk.Label(root, textvariable=self.lyric_var, wraplength=460, font=("Helvetica", 12), justify="center")
        self.label_lyric.pack(pady=12, fill="x")

        # ensure pygame mixer is initialized lazily
        self.update_loop()

    def ensure_pygame(self):
        """Initialize pygame and mixer when needed."""
        if self.pygame_initialized:
            return True
        if pygame is None:
            messagebox.showerror("Missing dependency", "pygame is not installed. Run: pip install pygame")
            return False
        try:
            # initialize only the mixer module to avoid creating a pygame window
            pygame.mixer.init()
            self.pygame_initialized = True
            return True
        except Exception as e:
            messagebox.showerror("pygame init failed", f"Failed to initialize pygame.mixer:\n{e}")
            return False

    def load(self):
        # initialize pygame when trying to load a file
        if not self.ensure_pygame():
            return

        file = filedialog.askopenfilename(title="Choose audio file", filetypes=[("Audio","*.mp3 *.wav *.ogg"),("All","*.*")])
        if not file:
            return
        self.audio_path = file
        self.label_song.config(text=os.path.basename(file))
        try:
            pygame.mixer.music.load(file)
        except Exception as e:
            messagebox.showerror("Load error", f"Couldn't load audio:\n{e}")
            return

        base, _ = os.path.splitext(file)
        lrc_path = base + ".lrc"
        if os.path.exists(lrc_path):
            self.lrc = self.parse_lrc(lrc_path)
            messagebox.showinfo("Lyrics", f"Loaded lyrics from {os.path.basename(lrc_path)}")
        else:
            if messagebox.askyesno("Lyrics", "No .lrc found next to the audio. Load lyrics (.lrc) now?"):
                lrc_file = filedialog.askopenfilename(title="Choose .lrc file", filetypes=[("Lyrics",".lrc"),("All","*.*")])
                if lrc_file:
                    self.lrc = self.parse_lrc(lrc_file)

        self.playing = False
        self.paused = False
        self.btn_play.config(text="Play")
        self.pause_offset = 0.0

    def parse_lrc(self, path):
        pattern = re.compile(r'\[(\d+):(\d+)(?:\.(\d+))?\](.*)')
        entries = []
        with open(path, encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                for match in pattern.finditer(line):
                    mm = int(match.group(1))
                    ss = int(match.group(2))
                    ms = int(match.group(3) or 0)
                    text = match.group(4).strip()
                    t = mm*60 + ss + ms/1000.0
                    entries.append((t, text))
        entries.sort(key=lambda x: x[0])
        return entries

    def play_pause(self):
        if not self.audio_path:
            messagebox.showwarning("No file", "Load an audio file first.")
            return
        if not self.playing:
            try:
                pygame.mixer.music.play()
            except Exception as e:
                messagebox.showerror("Play error", f"Couldn't play audio:\n{e}")
                return
            self.start_time = time.time() - (self.pause_offset/1000.0)
            self.playing = True
            self.paused = False
            self.btn_play.config(text="Pause")
        else:
            if not self.paused:
                pygame.mixer.music.pause()
                self.paused = True
                self.pause_offset = pygame.mixer.music.get_pos()
                self.btn_play.config(text="Resume")
            else:
                pygame.mixer.music.unpause()
                self.start_time = time.time() - (self.pause_offset/1000.0)
                self.paused = False
                self.btn_play.config(text="Pause")

    def stop(self):
        if self.pygame_initialized:
            pygame.mixer.music.stop()
        self.playing = False
        self.paused = False
        self.pause_offset = 0.0
        self.btn_play.config(text="Play")
        self.lyric_var.set("Playback stopped.")

    def get_play_time(self):
        if not self.pygame_initialized:
            return 0.0
        pos = pygame.mixer.music.get_pos()
        if pos >= 0:
            return pos / 1000.0
        if self.playing and not self.paused:
            return time.time() - self.start_time
        if self.paused:
            return self.pause_offset / 1000.0
        return 0.0

    def update_loop(self):
        if self.playing or self.paused:
            t = self.get_play_time()
            text = ""
            for time_s, lyric in self.lrc:
                if time_s <= t + 0.1:
                    text = lyric
                else:
                    break
            if text:
                self.lyric_var.set(text)
        self.root.after(200, self.update_loop)


if __name__ == "__main__":
    root = tk.Tk()
    app = MusicPlayer(root)
    root.mainloop()
