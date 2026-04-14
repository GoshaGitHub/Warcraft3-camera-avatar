import os
import sys
import subprocess
import ctypes
import threading
import json
import time
import numpy as np
import sounddevice as sd
import pyvirtualcam
from PIL import Image, ImageSequence

def get_base_path():
    return os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))

def load_config():
    config_path = os.path.join(get_base_path(), 'config.json')
    if not os.path.exists(config_path):
        print(f"❌ Config {config_path} not found!")
        sys.exit()
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

CONFIG = load_config()
S = CONFIG['settings']
CHAR_LIST = CONFIG['characters']
DLL_NAME = S['dll_name']

class AvatarEngine:
    def __init__(self):
        self.is_running = False
        self.is_speaking = False
        self.last_speak_time = 0.0
        self.camera_thread = None
        self.dll_path = os.path.join(get_base_path(), DLL_NAME)
        
        self._register_camera()

    def _register_camera(self):
        subprocess.run(['regsvr32', '/s', self.dll_path], check=False)
        
        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)
        def console_handler(ctrl_type):
            if ctrl_type == 2:
                self.shutdown()
            return False
        ctypes.windll.kernel32.SetConsoleCtrlHandler(console_handler, True)

    def get_mic_name(self):
        try:
            dev = sd.query_devices(kind='input')
            name = dev['name']
            for word in ["Microphone", "Mic", "(", ")", "WASAPI", "MME"]:
                name = name.replace(word, "")
            return name.strip()
        except: 
            return "Microphone not found"

    def _audio_callback(self, indata, frames, time_info, status):
        volume = np.sqrt(np.mean(indata**2))
        if volume > S['volume_threshold']:
            self.is_speaking = True
            self.last_speak_time = time.time()

    def _load_frames(self, filename):
        path = os.path.join(get_base_path(), 'gifs', filename)
        gif = Image.open(path)
        return [np.array(f.convert('RGB').resize((S['width'], S['height']))) for f in ImageSequence.Iterator(gif)]

    def start_stream(self, char_info):
        self.is_running = True
        self.camera_thread = threading.Thread(target=self._stream_logic, args=(char_info,), daemon=True)
        self.camera_thread.start()

    def stop_stream(self):
        self.is_running = False
        if self.camera_thread:
            self.camera_thread.join(timeout=1.0)

    def _stream_logic(self, char_info):
        frames_idle = self._load_frames(char_info["idle"])
        frames_speak = self._load_frames(char_info["speak"])
        
        with sd.InputStream(callback=self._audio_callback, channels=1):
            with pyvirtualcam.Camera(width=S['width'], height=S['height'], fps=S['fps']) as cam:
                start_time = time.time()
                while self.is_running:
                    current_time = time.time()
                    if self.is_speaking and (current_time - self.last_speak_time > S['silence_delay']):
                        self.is_speaking = False
                    
                    idx = int((current_time - start_time) * S['gif_speed'])
                    frames = frames_speak if self.is_speaking else frames_idle
                    cam.send(frames[idx % len(frames)])
                    cam.sleep_until_next_frame()

    def shutdown(self):
        self.stop_stream()
        subprocess.run(['regsvr32', '/s', '/u', self.dll_path], check=False)