import customtkinter as ctk
import numpy as np
import sounddevice as sd
import threading
import pystray
from PIL import Image, ImageDraw
from engine import CHAR_LIST, S

# --- ЦВЕТОВАЯ ПАЛИТРА WINDOWS 11 ---
COL_BG = "#101010"        
COL_CARD = "#1e1e1e"      
COL_TEXT = "#FFFFFF"      
COL_SUBTEXT = "#A0A0A0"   
COL_ACCENT = "#0078D4"    
COL_START = "#212121"     
COL_START_HOVER = "#2d2d2d" 
COL_STOP = "#4A1D1D"      
COL_STOP_HOVER = "#612525" 
COL_STATUS_OK = "#00D415" 

class AvatarUI(ctk.CTk):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine  
        
        self.selected_char = CHAR_LIST[0]
        first_char_name = self.selected_char['name']

        self.title("WarCraft3 Camera") 
        self.geometry("400x540") 
        self.resizable(False, False) 
        
        ctk.set_appearance_mode("dark")
        self.configure(fg_color=COL_BG) 

        # --- ЗАХВАТ ЗВУКА ---
        self.current_volume = 0.0
        try:
            self.audio_stream = sd.InputStream(callback=self.audio_callback, channels=1, samplerate=44100)
            self.audio_stream.start()
        except Exception as e:
            print(f"Не удалось запустить микрофон: {e}")
            self.audio_stream = None

        # --- ЦЕНТРАЛЬНАЯ КАРТОЧКА ---
        self.main_frame = ctk.CTkFrame(self, fg_color=COL_CARD, corner_radius=20, border_width=1, border_color="#2d2d2d")
        self.main_frame.pack(pady=20, padx=20, fill="both", expand=True)

        # --- БЛОК МИКРОФОНА ---
        self.mic_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.mic_frame.pack(pady=(20, 10), padx=25, fill="x")

        self.label_mic_title = ctk.CTkLabel(self.mic_frame, text="ВХОДНОЙ МИКРОФОН:", font=("Segoe UI Variable Semibold", 12), text_color=COL_SUBTEXT, anchor="w")
        self.label_mic_title.pack(pady=0, anchor="w")

        full_mic_name = self.get_full_mic_name()
        self.label_mic = ctk.CTkLabel(self.mic_frame, text=full_mic_name, font=("Segoe UI Variable", 16, "bold"), text_color=COL_TEXT, anchor="w", justify="left", wraplength=300)
        self.label_mic.pack(pady=(2, 5), anchor="w")

        # --- ВИЗУАЛИЗАТОР ЗВУКА ---
        self.viz_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent", height=40)
        self.viz_frame.pack(pady=(0, 10), padx=25, fill="x")
        self.viz_frame.pack_propagate(False)

        self.viz_bars_frame = ctk.CTkFrame(self.viz_frame, fg_color="transparent")
        self.viz_bars_frame.pack(side="left", fill="both", expand=True)

        self.bars = []
        for i in range(7): 
            bar = ctk.CTkFrame(self.viz_bars_frame, fg_color=COL_SUBTEXT, width=15, height=5, corner_radius=3)
            bar.pack(side="left", padx=3, anchor="s") 
            self.bars.append(bar)

        self.update_visualization()

        self.separator = ctk.CTkFrame(self.main_frame, height=1, fg_color="#2d2d2d")
        self.separator.pack(fill="x", padx=25, pady=5)

        # --- БЛОК ВЫБОРА ГЕРОЯ ---
        self.char_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.char_frame.pack(pady=15, padx=25, fill="x")

        self.label_char_title = ctk.CTkLabel(self.char_frame, text="👥 ВЫБЕРИТЕ ГЕРОЯ:", font=("Segoe UI Variable", 18, "bold"), text_color=COL_SUBTEXT, anchor="w")
        self.label_char_title.pack(pady=0, anchor="w")

        self.char_var = ctk.StringVar(value=first_char_name) 
        
        self.menu_border_frame = ctk.CTkFrame(self.char_frame, fg_color=COL_CARD, border_width=2, border_color="#3399FF", corner_radius=12) 
        self.menu_border_frame.pack(pady=(10, 15), fill="x")

        self.char_menu = ctk.CTkOptionMenu(self.menu_border_frame, 
                                          values=[c['name'] for c in CHAR_LIST], 
                                          variable=self.char_var, 
                                          command=self.on_char_select,
                                          fg_color="#0060A8",          
                                          button_color="#0060A8",       # Единый цвет для монолитности
                                          button_hover_color="#004A85", 
                                          text_color=COL_TEXT, 
                                          dropdown_fg_color=COL_CARD,
                                          dropdown_hover_color=COL_START_HOVER,
                                          dropdown_text_color=COL_TEXT,
                                          font=("Segoe UI Variable", 21, "bold"), 
                                          dropdown_font=("Segoe UI Variable", 19, "bold"), 
                                          corner_radius=10, 
                                          height=46) 
        self.char_menu.pack(padx=4, pady=4, fill="x")

        # --- ФУТЕР ---
        self.footer_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.footer_frame.pack(side="bottom", fill="x", pady=(10, 25))

        self.btn_action = ctk.CTkButton(self.footer_frame, text="▶️ ЗАПУСТИТЬ ТРАНСЛЯЦИЮ", command=self.on_btn_click, fg_color=COL_START, hover_color=COL_START_HOVER, text_color=COL_TEXT, font=("Segoe UI Variable Semibold", 15, "bold"), corner_radius=8, height=45, border_width=1, border_color="#333333")
        self.btn_action.pack(pady=(10, 20), padx=25, fill="x")

        self.status_label = ctk.CTkLabel(self.footer_frame, text=f"🟢 Герой готов: {first_char_name}", font=("Segoe UI Variable", 12), text_color=COL_TEXT)
        self.status_label.pack(pady=0)

        # ПЕРЕХВАТЫВАЕМ НАЖАТИЕ НА КРЕСТИК И ЗАПУСКАЕМ ТРЕЙ
        self.protocol("WM_DELETE_WINDOW", self.hide_window)
        self.setup_tray_icon() # <-- Трей создается сразу при старте!

    # --- ЛОГИКА СИСТЕМНОГО ТРЕЯ ---

    def create_tray_icon_image(self):
        """ Создает базовую иконку для трея (синий квадратик). """
        image = Image.new('RGB', (64, 64), color=COL_BG)
        dc = ImageDraw.Draw(image)
        dc.rectangle((16, 16, 48, 48), fill=COL_ACCENT)
        return image

    def setup_tray_icon(self):
        """ Создает иконку в трее и крутит ее в фоновом потоке всю жизнь программы """
        image = self.create_tray_icon_image()
        
        # Меню по правому клику (default=True — реакция на двойной клик)
        menu = pystray.Menu(
            pystray.MenuItem('Развернуть', self.show_window, default=True),
            pystray.MenuItem('Выход', self.quit_window)
        )
        
        self.tray_icon = pystray.Icon("WC3Camera", image, "WarCraft3 Camera", menu)
        
        # Запускаем трей в фоновом потоке, иначе интерфейс Tkinter зависнет
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def hide_window(self):
        """ Теперь просто прячет окно. Иконка в трее уже есть и продолжает работать """
        self.withdraw() 

    def show_window(self, icon, item):
        """ Восстанавливает окно из трея, НЕ убивая саму иконку """
        self.after(0, self.deiconify) 

    def quit_window(self, icon, item):
        """ Полностью закрывает программу из трея """
        icon.stop() # Убиваем иконку
        self.after(0, self.on_closing) # Закрываем приложение

    # --- ОСТАЛЬНАЯ ЛОГИКА ---

    def get_full_mic_name(self):
        try:
            all_devices = sd.query_devices()
            default_input = sd.query_devices(kind='input')
            raw_name = default_input['name']
            best_name = raw_name
            clean_raw = raw_name.replace("Микрофон (", "").replace("Microphone (", "").replace(")", "")
            search_part = clean_raw[:12] 
            
            for d in all_devices:
                if search_part in d['name'] and len(d['name']) > len(best_name):
                    best_name = d['name']
            
            for word in ["Микрофон", "Microphone", "(", ")", "Windows WASAPI", "MME", "DirectSound"]:
                best_name = best_name.replace(word, "")
            
            mic_name = " ".join(best_name.strip().split())
            return mic_name if mic_name else raw_name
        except Exception:
            try: return self.engine.get_mic_name()
            except: return "Микрофон не найден!"

    def audio_callback(self, indata, frames, time, status):
        self.current_volume = np.linalg.norm(indata) * 15

    def on_char_select(self, name):
        self.selected_char = next(c for c in CHAR_LIST if c['name'] == name)
        self.status_label.configure(text=f"🟢 Герой готов: {name}", text_color=COL_TEXT)

    def on_btn_click(self):
        if not self.engine.is_running:
            self.engine.start_stream(self.selected_char)
            self.btn_action.configure(text="⏹️ ОСТАНОВИТЬ", fg_color=COL_STOP, hover_color=COL_STOP_HOVER, border_color="#6c2929")
            self.status_label.configure(text="🟢 Статус: ТРАНСЛЯЦИЯ АКТИВНА", text_color=COL_STATUS_OK)
            self.char_menu.configure(state="disabled")
            for bar in self.bars: bar.configure(fg_color=COL_STATUS_OK)
        else:
            self.engine.stop_stream()
            self.btn_action.configure(text="▶️ ЗАПУСТИТЬ ТРАНСЛЯЦИЮ", fg_color=COL_START, hover_color=COL_START_HOVER, border_color="#333333")
            self.status_label.configure(text=f"🟢 Герой готов: {self.selected_char['name']}", text_color=COL_TEXT)
            self.char_menu.configure(state="normal")
            for bar in self.bars: bar.configure(fg_color=COL_SUBTEXT)

    def update_visualization(self):
        if self.current_volume > 1.5: 
            for bar in self.bars:
                base_h = int(self.current_volume * np.random.uniform(0.7, 1.3))
                bar.configure(height=max(5, min(base_h, 35)))
        else:
            for bar in self.bars:
                bar.configure(height=5)
        self.after(50, self.update_visualization)

    def on_closing(self):
        if self.audio_stream:
            self.audio_stream.stop()
            self.audio_stream.close()
        self.engine.shutdown()
        self.destroy()