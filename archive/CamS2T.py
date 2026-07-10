import cv2
import speech_recognition as sr
import threading
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import queue
import time
import textwrap

class AdvancedCameraSpeech:
    def __init__(self):
        # Camera setup
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        # Speech recognition
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Text management
        self.text_queue = queue.Queue()
        self.current_subtitle = "Ayo bicara... Kalimat akan muncul di sini!"
        self.recent_texts = []  # Store recent texts
        self.is_listening = True
        
        # Calibrate microphone
        print("Kalibrasi mikrofon...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=2)
        
        # Start speech thread
        self.speech_thread = threading.Thread(target=self.speech_worker)
        self.speech_thread.daemon = True
        self.speech_thread.start()
        
        # Font setup
        try:
            self.title_font = ImageFont.truetype("arial.ttf", 28)
            self.subtitle_font = ImageFont.truetype("arial.ttf", 36)
            self.side_font = ImageFont.truetype("arial.ttf", 20)
        except:
            self.title_font = ImageFont.load_default()
            self.subtitle_font = ImageFont.load_default()
            self.side_font = ImageFont.load_default()
    
    def speech_worker(self):
        """Background worker untuk speech recognition"""
        while self.is_listening:
            try:
                with self.microphone as source:
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=8)
                
                try:
                    text = self.recognizer.recognize_google(audio, language='id-ID')
                    self.text_queue.put(('SUCCESS', text))
                except sr.UnknownValueError:
                    self.text_queue.put(('INFO', 'Tidak terdeteksi...'))
                except sr.RequestError as e:
                    self.text_queue.put(('ERROR', f'Service error: {e}'))
                    
            except sr.WaitTimeoutError:
                continue
            except Exception as e:
                print(f"Speech error: {e}")
    
    def draw_text_with_background(self, draw, text, position, font, text_color=(255, 255, 255), bg_color=(0, 0, 0, 160)):
        """Draw text with background"""
        bbox = draw.textbbox(position, text, font=font)
        
        # Expand background slightly
        padding = 15
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
    
    def process_frame(self, frame):
        """Process frame and add all text elements"""
        # Convert to PIL
        pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)
        
        img_width, img_height = pil_img.size
        
        # === MAIN SUBTITLE (Bottom Center) ===
        main_text = self.current_subtitle
        self.draw_text_with_background(
            draw, main_text, 
            (img_width//2, img_height - 100), 
            self.subtitle_font,
            bg_color=(0, 100, 200, 200)
        )
        
        # === TITLE (Top Center) ===
        title_text = "REAL-TIME SPEECH TO TEXT CAMERA"
        self.draw_text_with_background(
            draw, title_text,
            (img_width//2, 30),
            self.title_font,
            bg_color=(50, 50, 50, 200)
        )
        
        # === SIDE PANEL (Recent Texts) ===
        side_x = img_width - 400
        side_y = 100
        
        # Side panel background
        draw.rectangle([side_x-10, side_y-10, img_width-10, img_height-200], 
                      fill=(0, 0, 0, 180))
        
        # Side panel title
        self.draw_text_with_background(
            draw, "Teks Terbaru:",
            (side_x, side_y),
            self.side_font,
            bg_color=(100, 0, 0, 200)
        )
        
        # Recent texts
        for i, text in enumerate(self.recent_texts[-6:]):  # Show last 6 texts
            wrapped_text = textwrap.fill(text, width=30)
            text_y = side_y + 40 + (i * 60)
            
            if text_y < img_height - 250:  # Don't go too low
                self.draw_text_with_background(
                    draw, wrapped_text,
                    (side_x, text_y),
                    self.side_font,
                    bg_color=(40, 40, 40, 200)
                )
        
        # === STATUS BAR (Bottom Left) ===
        status = "● MENDENGARKAN" if self.is_listening else "■ BERHENTI"
        status_color = (0, 255, 0) if self.is_listening else (255, 0, 0)
        
        self.draw_text_with_background(
            draw, status,
            (20, img_height - 40),
            self.side_font,
            text_color=status_color,
            bg_color=(50, 50, 50, 200)
        )
        
        # Convert back to OpenCV
        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    
    def run(self):
        """Main application loop"""
        print("=== CAMERA SPEECH-TO-TEXT ===")
        print("Kamera aktif dengan speech recognition")
        print("Commands:")
        print("  'q' - Keluar")
        print("  'c' - Clear teks")
        print("  'p' - Pause/resume listening")
        print("=============================")
        
        last_update = time.time()
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            
            # Process new speech texts
            try:
                while True:
                    msg_type, text = self.text_queue.get_nowait()
                    
                    if msg_type == 'SUCCESS':
                        self.current_subtitle = text
                        self.recent_texts.append(text)
                        last_update = time.time()
                    
                    elif msg_type == 'INFO':
                        self.current_subtitle = text
                        last_update = time.time()
                        
            except queue.Empty:
                pass
            
            # Auto-clear subtitle after 4 seconds for INFO/ERROR messages
            if time.time() - last_update > 4 and self.current_subtitle != "Ayo bicara... Kalimat akan muncul di sini!":
                if not any(keyword in self.current_subtitle for keyword in ['SUKSES', 'Teks Terbaru']):
                    self.current_subtitle = "Ayo bicara... Kalimat akan muncul di sini!"
            
            # Process frame with all UI elements
            processed_frame = self.process_frame(frame)
            
            # Display
            cv2.imshow('Camera Speech-to-Text - Real Time Subtitle', processed_frame)
            
            # Handle keys
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('c'):
                self.current_subtitle = "Ayo bicara... Kalimat akan muncul di sini!"
                self.recent_texts.clear()
            elif key == ord('p'):
                self.is_listening = not self.is_listening
                print(f"Listening: {'ACTIVE' if self.is_listening else 'PAUSED'}")
        
        # Cleanup
        self.is_listening = False
        self.cap.release()
        cv2.destroyAllWindows()
        print("Program selesai")

if __name__ == "__main__":
    try:
        app = AdvancedCameraSpeech()
        app.run()
    except Exception as e:
        print(f"Error: {e}")
        input("Press Enter to exit...")