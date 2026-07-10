import speech_recognition as sr
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import queue
import time
import sys

class SimpleSpeechToText:
    def __init__(self, root):
        self.root = root
        self.root.title("Speech to Text Real-Time")
        self.root.geometry("700x500")
        
        # Initialize variables
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.is_listening = False
        self.audio_queue = queue.Queue()
        
        self.setup_gui()
        self.setup_microphone()
        
        # Start queue processor
        self.root.after(100, self.process_queue)

    def setup_gui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Speech to Text Converter", 
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=10)
        
        # Status
        self.status_var = tk.StringVar(value="Status: Ready")
        status_label = ttk.Label(main_frame, textvariable=self.status_var)
        status_label.pack(pady=5)
        
        # Text area
        self.text_area = scrolledtext.ScrolledText(
            main_frame, 
            wrap=tk.WORD, 
            width=80, 
            height=15,
            font=("Arial", 10)
        )
        self.text_area.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)
        
        self.start_btn = ttk.Button(
            button_frame, 
            text="Start Listening", 
            command=self.start_listening
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(
            button_frame, 
            text="Stop Listening", 
            command=self.stop_listening,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame, 
            text="Clear Text", 
            command=self.clear_text
        ).pack(side=tk.LEFT, padx=5)

    def setup_microphone(self):
        try:
            self.microphone = sr.Microphone()
            self.status_var.set("Status: Microphone ready")
        except Exception as e:
            self.status_var.set(f"Status: Microphone error - {str(e)}")
            messagebox.showerror("Error", f"Cannot access microphone: {e}")

    def start_listening(self):
        if self.microphone is None:
            messagebox.showerror("Error", "Microphone not available")
            return
            
        self.is_listening = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_var.set("Status: Listening... Speak now!")
        
        # Start in separate thread
        thread = threading.Thread(target=self.listen_continuous)
        thread.daemon = True
        thread.start()

    def stop_listening(self):
        self.is_listening = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_var.set("Status: Stopped")

    def listen_continuous(self):
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                
            while self.is_listening:
                try:
                    with self.microphone as source:
                        audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=8)
                    
                    # Try to recognize speech
                    try:
                        text = self.recognizer.recognize_google(audio, language='id-ID')
                        self.audio_queue.put(f"SUCCESS:{text}")
                    except sr.UnknownValueError:
                        self.audio_queue.put("ERROR:Cannot understand audio")
                    except sr.RequestError as e:
                        self.audio_queue.put(f"ERROR:API unavailable - {e}")
                        
                except sr.WaitTimeoutError:
                    continue
                except Exception as e:
                    self.audio_queue.put(f"ERROR:{str(e)}")
                    
        except Exception as e:
            self.audio_queue.put(f"ERROR:Microphone error - {str(e)}")

    def process_queue(self):
        try:
            while True:
                message = self.audio_queue.get_nowait()
                
                if message.startswith("SUCCESS:"):
                    text = message[8:]  # Remove "SUCCESS:" prefix
                    timestamp = time.strftime("%H:%M:%S")
                    self.text_area.insert(tk.END, f"[{timestamp}] {text}\n")
                    self.text_area.see(tk.END)
                    self.status_var.set("Status: Text recognized")
                    
                elif message.startswith("ERROR:"):
                    error_msg = message[6:]  # Remove "ERROR:" prefix
                    self.text_area.insert(tk.END, f"[Error] {error_msg}\n")
                    self.text_area.see(tk.END)
                    self.status_var.set("Status: Error occurred")
                    
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)

    def clear_text(self):
        self.text_area.delete(1.0, tk.END)

def main():
    try:
        root = tk.Tk()
        app = SimpleSpeechToText(root)
        root.mainloop()
    except Exception as e:
        print(f"Error: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()