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

class OptimizedCameraSpeech:
    def __init__(self):
        # Camera setup
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        # Speech recognition dengan optimasi
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Optimasi parameter recognizer
        self.recognizer.energy_threshold = 1000  # Lebih tinggi untuk mengurangi false positive
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8   # Lebih pendek
        
        # Text management
        self.text_queue = queue.Queue()
        self.current_subtitle = "Silakan berbicara dengan jelas..."
        self.recent_texts = deque(maxlen=8)  # Batasi history
        self.is_listening = True
        self.last_audio_time = 0
        
        # Kalibrasi mikrofon lebih agresif
        print("Kalibrasi mikrofon... (harap diam)")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1.5)
        print("Kalibrasi selesai!")
        
        # Start speech thread
        self.speech_thread = threading.Thread(target=self.speech_worker)
        self.speech_thread.daemon = True
        self.speech_thread.start()
        
        # Font setup
        try:
            self.title_font = ImageFont.truetype("arial.ttf", 24)
            self.subtitle_font = ImageFont.truetype("arial.ttf", 32)
            self.side_font = ImageFont.truetype("arial.ttf", 18)
        except:
            # Fallback fonts
            self.title_font = ImageFont.load_default()
            self.subtitle_font = ImageFont.load_default()
            self.side_font = ImageFont.load_default()
    
    def speech_worker(self):
        """Background worker yang dioptimalkan untuk speech recognition"""
        silence_timeout = 0
        consecutive_silence = 0
        
        while self.is_listening:
            try:
                with self.microphone as source:
                    # Listen dengan parameter yang dioptimalkan
                    audio = self.recognizer.listen(
                        source, 
                        timeout=0.5,           # Timeout lebih pendek
                        phrase_time_limit=3    # Batas waktu ucapan lebih pendek
                    )
                
                # Deteksi volume audio untuk filter noise
                audio_data = audio.get_raw_data()
                rms = audioop.rms(audio_data, 2)  # Root mean square untuk volume
                
                # Filter audio terlalu pelan
                if rms < 500:  # Threshold volume minimum
                    consecutive_silence += 1
                    if consecutive_silence > 2:
                        self.text_queue.put(('INFO', 'Suara terlalu pelan...'))
                    continue
                
                consecutive_silence = 0
                self.last_audio_time = time.time()
                
                # Convert speech to text - coba multiple languages
                text = None
                languages = ['id-ID', 'en-US']  # Coba Indonesia dulu, lalu English
                
                for lang in languages:
                    try:
                        text = self.recognizer.recognize_google(audio, language=lang)
                        if text and len(text.strip()) > 1:  # Minimal 2 karakter
                            break
                    except sr.UnknownValueError:
                        continue
                    except sr.RequestError:
                        continue
                
                if text and len(text.strip()) > 1:
                    # Post-processing: kapitalisasi awal kalimat
                    processed_text = text.strip().capitalize()
                    self.text_queue.put(('SUCCESS', processed_text))
                    print(f"✓ Terdeteksi: {processed_text}")
                
            except sr.WaitTimeoutError:
                # Timeout adalah kondisi normal
                continue
            except Exception as e:
                if "Audio data" not in str(e):  # Jangan tampilkan error audio data
                    print(f"Speech error: {e}")
                continue
    
    def draw_text_with_background(self, draw, text, position, font, text_color=(255, 255, 255), bg_color=(0, 0, 0, 180)):
        """Draw text dengan background yang dioptimalkan"""
        if not text:
            return None
            
        try:
            bbox = draw.textbbox(position, text, font=font)
            
            # Expand background
            padding = 12
            bg_coords = [
                bbox[0] - padding,
                bbox[1] - padding,
                bbox[2] + padding,
                bbox[3] + padding
            ]
            
            # Draw background
            draw.rectangle(bg_coords, fill=bg_color)
            
            # Draw text
            draw.text(position, text, font=font, fill=text_color)
            
            return bbox
        except Exception:
            return None
    
    def process_frame(self, frame):
        """Process frame dengan optimasi performa"""
        # Convert to PIL
        pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)
        
        img_width, img_height = pil_img.size
        
        # === MAIN SUBTITLE (Bottom Center) ===
        main_text = self.current_subtitle
        if main_text:
            self.draw_text_with_background(
                draw, main_text, 
                (img_width//2, img_height - 120), 
                self.subtitle_font,
                bg_color=(0, 80, 160, 220)  # Warna lebih gelap untuk kontras
            )
        
        # === TITLE (Top Center) ===
        title_text = "KAMERA REAL-TIME DENGAN SUBTITLE OTOMATIS"
        self.draw_text_with_background(
            draw, title_text,
            (img_width//2, 25),
            self.title_font,
            bg_color=(30, 30, 30, 200)
        )
        
        # === SIDE PANEL (Recent Texts) ===
        side_x = img_width - 350  # Lebih sempit
        side_y = 80
        
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
        
        # Recent texts - maksimal 5
        for i, text in enumerate(list(self.recent_texts)[-5:]):
            if text:
                # Potong teks jika terlalu panjang
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
        
        # Instructions
        instructions = "Q:Keluar | C:Clear | P:Pause | R:Recalibrate"
        self.draw_text_with_background(
            draw, instructions,
            (20, img_height - 40),
            self.side_font,
            text_color=(200, 200, 100),
            bg_color=(20, 20, 20, 200)
        )
        
        # Convert back to OpenCV
        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    
    def run(self):
        """Main application loop yang dioptimalkan"""
        print("=== KAMERA SPEECH-TO-TEXT OPTIMIZED ===")
        print("Tips untuk hasil terbaik:")
        print("1. Gunakan mikrofon eksternal jika memungkinkan")
        print("2. Berbicara dengan jelas dan tidak terlalu cepat")
        print("3. Pastikan lingkungan cukup tenang")
        print("4. Jarak ke mikrofon 20-50 cm")
        print("\nCommands:")
        print("  Q - Keluar")
        print("  C - Clear teks")
        print("  P - Pause/resume listening") 
        print("  R - Rekalibrasi mikrofon")
        print("=============================")
        
        last_text_time = time.time()
        frame_count = 0
        start_time = time.time()
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("Error: Tidak bisa mengakses kamera")
                break
            
            frame_count += 1
            
            # Process new speech texts - lebih agresif
            try:
                while True:
                    msg_type, text = self.text_queue.get_nowait()
                    
                    if msg_type == 'SUCCESS' and text:
                        self.current_subtitle = text
                        self.recent_texts.append(text)
                        last_text_time = time.time()
                    
                    elif msg_type == 'INFO':
                        # Hanya update jika sudah lama tidak ada update
                        if time.time() - last_text_time > 3:
                            self.current_subtitle = text
                            last_text_time = time.time()
                            
            except queue.Empty:
                pass
            
            # Auto-clear subtitle setelah 3 detik
            if time.time() - last_text_time > 3 and self.current_subtitle != "Silakan berbicara dengan jelas...":
                self.current_subtitle = "Silakan berbicara dengan jelas..."
            
            # Calculate FPS (setiap 30 frame)
            if frame_count % 30 == 0:
                fps = frame_count / (time.time() - start_time)
                print(f"FPS: {fps:.1f} | Status: {'Listening' if self.is_listening else 'Paused'}")
            
            # Process frame
            processed_frame = self.process_frame(frame)
            
            # Display
            cv2.imshow('Kamera dengan Subtitle Real-time - OPTIMIZED', processed_frame)
            
            # Handle keys dengan response lebih cepat
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('c'):
                self.current_subtitle = "Silakan berbicara dengan jelas..."
                self.recent_texts.clear()
                print("Teks dibersihkan")
            elif key == ord('p'):
                self.is_listening = not self.is_listening
                status = "AKTIF" if self.is_listening else "PAUSE"
                print(f"Speech recognition: {status}")
            elif key == ord('r'):
                print("Rekalibrasi mikrofon... (harap diam)")
                with self.microphone as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
                print("Rekalibrasi selesai!")
        
        # Cleanup
        self.is_listening = False
        time.sleep(0.5)  # Beri waktu untuk thread berhenti
        self.cap.release()
        cv2.destroyAllWindows()
        print("Program selesai")

if __name__ == "__main__":
    try:
        app = OptimizedCameraSpeech()
        app.run()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")