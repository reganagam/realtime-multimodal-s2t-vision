import cv2
import speech_recognition as sr
import threading
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import queue
import time
import textwrap
import audioop
from collections import deque

class FixedAudioCameraSpeech:
    def __init__(self):
        # Camera setup
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        # Speech recognition dengan setting audio yang diperbaiki
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # **PERBAIKAN: Setting audio yang lebih sensitif**
        self.recognizer.energy_threshold = 300  # DITURUNKAN DRASTIS dari 1000
        self.recognizer.dynamic_energy_threshold = False  # Non-aktifkan dynamic threshold
        self.recognizer.pause_threshold = 0.5   # Lebih pendek untuk response cepat
        self.recognizer.non_speaking_duration = 0.3  # Durasi non-speaking lebih pendek
        
        # Text management
        self.text_queue = queue.Queue()
        self.current_subtitle = "Silakan berbicara..."
        self.recent_texts = deque(maxlen=6)
        self.is_listening = True
        self.audio_level = 0  # Untuk menampilkan level audio
        
        # **PERBAIKAN: Kalibrasi dengan setting khusus**
        print("Kalibrasi mikrofon... (harap berbicara dengan volume normal)")
        with self.microphone as source:
            # Adjust dengan durasi lebih pendek dan threshold lebih rendah
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
        print(f"Kalibrasi selesai! Energy threshold: {self.recognizer.energy_threshold}")
        
        # Start speech thread
        self.speech_thread = threading.Thread(target=self.speech_worker)
        self.speech_thread.daemon = True
        self.speech_thread.start()
        
        # Font setup
        try:
            self.title_font = ImageFont.truetype("arial.ttf", 24)
            self.subtitle_font = ImageFont.truetype("arial.ttf", 32)
            self.side_font = ImageFont.truetype("arial.ttf", 18)
            self.small_font = ImageFont.truetype("arial.ttf", 14)
        except:
            self.title_font = ImageFont.load_default()
            self.subtitle_font = ImageFont.load_default()
            self.side_font = ImageFont.load_default()
            self.small_font = ImageFont.load_default()
    
    def speech_worker(self):
        """Background worker dengan audio processing yang diperbaiki"""
        while self.is_listening:
            try:
                with self.microphone as source:
                    # **PERBAIKAN: Timeout lebih pendek, phrase limit lebih panjang**
                    audio = self.recognizer.listen(
                        source, 
                        timeout=0.3,           # Timeout sangat pendek
                        phrase_time_limit=5    # Biarkan kalimat lebih panjang
                    )
                
                # **PERBAIKAN: Deteksi volume dengan threshold yang lebih rendah**
                audio_data = audio.get_raw_data()
                rms = audioop.rms(audio_data, 2) if audio_data else 0
                self.audio_level = min(rms / 50, 100)  # Normalisasi untuk display
                
                # **PERBAIKAN: Threshold volume jauh lebih rendah**
                if rms < 200:  # DITURUNKAN dari 500
                    self.text_queue.put(('INFO', 'Suara terdeteksi, memproses...'))
                    # Tapi tetap proses, jangan skip
                
                # Convert speech to text
                text = None
                languages = ['id-ID', 'en-US']
                
                for lang in languages:
                    try:
                        text = self.recognizer.recognize_google(audio, language=lang)
                        if text and len(text.strip()) > 1:
                            break
                    except sr.UnknownValueError:
                        continue
                    except sr.RequestError as e:
                        self.text_queue.put(('ERROR', f'Error koneksi: {e}'))
                        continue
                
                if text and len(text.strip()) > 1:
                    processed_text = text.strip().capitalize()
                    self.text_queue.put(('SUCCESS', processed_text))
                    print(f"✓ Terdeteksi: '{processed_text}' (Volume: {rms})")
                else:
                    self.text_queue.put(('INFO', 'Tidak dapat memahami audio'))
                
            except sr.WaitTimeoutError:
                # Reset audio level ketika timeout
                self.audio_level = 0
                continue
            except Exception as e:
                if "Audio data" not in str(e):
                    print(f"Speech error: {e}")
                continue
    
    def draw_audio_meter(self, draw, position, width=200, height=20):
        """Draw audio level meter"""
        x, y = position
        level = min(self.audio_level, 100)
        
        # Background
        draw.rectangle([x, y, x + width, y + height], fill=(50, 50, 50))
        
        # Level bar
        bar_width = int(width * level / 100)
        color = (0, 255, 0) if level > 30 else (255, 255, 0) if level > 10 else (255, 0, 0)
        draw.rectangle([x, y, x + bar_width, y + height], fill=color)
        
        # Border
        draw.rectangle([x, y, x + width, y + height], outline=(255, 255, 255), width=1)
        
        # Text
        meter_text = f"Volume: {int(level)}%"
        text_bbox = draw.textbbox((0, 0), meter_text, font=self.small_font)
        text_x = x + (width - (text_bbox[2] - text_bbox[0])) // 2
        text_y = y + (height - (text_bbox[3] - text_bbox[1])) // 2
        draw.text((text_x, text_y), meter_text, font=self.small_font, fill=(255, 255, 255))
    
    def draw_text_with_background(self, draw, text, position, font, text_color=(255, 255, 255), bg_color=(0, 0, 0, 180)):
        """Draw text dengan background"""
        if not text:
            return None
            
        try:
            bbox = draw.textbbox(position, text, font=font)
            
            padding = 12
            bg_coords = [
                bbox[0] - padding,
                bbox[1] - padding,
                bbox[2] + padding,
                bbox[3] + padding
            ]
            
            draw.rectangle(bg_coords, fill=bg_color)
            draw.text(position, text, font=font, fill=text_color)
            
            return bbox
        except Exception:
            return None
    
    def process_frame(self, frame):
        """Process frame dengan audio meter"""
        pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)
        
        img_width, img_height = pil_img.size
        
        # === MAIN SUBTITLE ===
        main_text = self.current_subtitle
        if main_text:
            self.draw_text_with_background(
                draw, main_text, 
                (img_width//2, img_height - 120), 
                self.subtitle_font,
                bg_color=(0, 100, 200, 220)
            )
        
        # === TITLE ===
        title_text = "KAMERA DENGAN SUBTITLE REAL-TIME"
        self.draw_text_with_background(
            draw, title_text,
            (img_width//2, 25),
            self.title_font,
            bg_color=(30, 30, 30, 200)
        )
        
        # === AUDIO LEVEL METER ===
        self.draw_audio_meter(draw, (img_width - 250, 80))
        
        # === SIDE PANEL ===
        side_x = img_width - 350
        side_y = 120
        
        # Side panel background
        draw.rectangle([side_x-10, side_y-10, img_width-10, img_height-150], 
                      fill=(0, 0, 0, 160))
        
        # Side panel title
        self.draw_text_with_background(
            draw, "KALIMAT TERBARU:",
            (side_x, side_y),
            self.side_font,
            bg_color=(80, 0, 0, 200)
        )
        
        # Recent texts
        for i, text in enumerate(list(self.recent_texts)[-5:]):
            if text:
                display_text = text[:35] + "..." if len(text) > 35 else text
                text_y = side_y + 35 + (i * 45)
                
                if text_y < img_height - 180:
                    self.draw_text_with_background(
                        draw, display_text,
                        (side_x, text_y),
                        self.side_font,
                        bg_color=(30, 30, 30, 200)
                    )
        
        # === STATUS & INSTRUKSI ===
        status = "● MENDENGARKAN" if self.is_listening else "■ BERHENTI"
        status_color = (50, 255, 50) if self.is_listening else (255, 50, 50)
        
        self.draw_text_with_background(
            draw, status,
            (20, img_height - 80),
            self.side_font,
            text_color=status_color,
            bg_color=(20, 20, 20, 200)
        )
        
        # Audio threshold info
        threshold_info = f"Threshold: {self.recognizer.energy_threshold}"
        draw.text((20, img_height - 110), threshold_info, font=self.small_font, fill=(200, 200, 200))
        
        # Instructions
        instructions = "Q:Keluar | C:Clear | P:Pause | +/-:Adjust Threshold"
        self.draw_text_with_background(
            draw, instructions,
            (20, img_height - 40),
            self.small_font,
            text_color=(200, 200, 100),
            bg_color=(20, 20, 20, 200)
        )
        
        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    
    def adjust_threshold(self, increase=True):
        """Adjust energy threshold secara real-time"""
        if increase:
            self.recognizer.energy_threshold += 100
        else:
            self.recognizer.energy_threshold = max(100, self.recognizer.energy_threshold - 100)
        
        print(f"Energy threshold diubah menjadi: {self.recognizer.energy_threshold}")
    
    def run(self):
        """Main application loop dengan kontrol threshold"""
        print("=== KAMERA SPEECH-TO-TEXT - AUDIO FIXED ===")
        print("MASALAH SEBELUMNYA: Suara terlalu pelan - SUDAH DIPERBAIKI")
        print("\nTips:")
        print("- Lihat meter volume di kanan atas")
        print("- Volume hijau = baik, kuning = rendah, merah = sangat rendah")
        print("- Gunakan +/- untuk adjust sensitivity jika perlu")
        print("\nCommands:")
        print("  Q - Keluar")
        print("  C - Clear teks") 
        print("  P - Pause/resume listening")
        print("  + - Increase threshold (kurang sensitif)")
        print("  - - Decrease threshold (lebih sensitif)")
        print("  R - Rekalibrasi mikrofon")
        print("=============================")
        
        last_text_time = time.time()
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            
            # Process new speech texts
            try:
                while True:
                    msg_type, text = self.text_queue.get_nowait()
                    
                    if msg_type == 'SUCCESS' and text:
                        self.current_subtitle = text
                        self.recent_texts.append(text)
                        last_text_time = time.time()
                    
                    elif msg_type == 'INFO':
                        if time.time() - last_text_time > 2:
                            self.current_subtitle = text
                            last_text_time = time.time()
                            
            except queue.Empty:
                pass
            
            # Auto-clear subtitle setelah 4 detik
            if time.time() - last_text_time > 4 and not self.current_subtitle.startswith("Silakan"):
                self.current_subtitle = "Silakan berbicara..."
            
            # Process frame
            processed_frame = self.process_frame(frame)
            
            # Display
            cv2.imshow('Kamera Subtitle - AUDIO FIXED', processed_frame)
            
            # Handle keys dengan kontrol threshold
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('c'):
                self.current_subtitle = "Silakan berbicara..."
                self.recent_texts.clear()
                print("Teks dibersihkan")
            elif key == ord('p'):
                self.is_listening = not self.is_listening
                status = "AKTIF" if self.is_listening else "PAUSE"
                print(f"Speech recognition: {status}")
            elif key == ord('r'):
                print("Rekalibrasi mikrofon...")
                with self.microphone as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
                print(f"Rekalibrasi selesai! Threshold: {self.recognizer.energy_threshold}")
            elif key == ord('+') or key == ord('='):
                self.adjust_threshold(increase=True)
            elif key == ord('-') or key == ord('_'):
                self.adjust_threshold(increase=False)
        
        # Cleanup
        self.is_listening = False
        time.sleep(0.5)
        self.cap.release()
        cv2.destroyAllWindows()
        print("Program selesai")

if __name__ == "__main__":
    try:
        app = FixedAudioCameraSpeech()
        app.run()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")