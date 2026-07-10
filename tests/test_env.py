import sys

def test_environment():
    print("Testing Environment Setup...")
    print(f"Python version: {sys.version}")
    
    # Test basic imports
    try:
        import tkinter
        print("✅ Tkinter: OK")
    except ImportError:
        print("❌ Tkinter: FAILED")
        
    try:
        import speech_recognition
        print("✅ SpeechRecognition: OK")
    except ImportError:
        print("❌ SpeechRecognition: FAILED")
        
    try:
        import pyaudio
        print("✅ PyAudio: OK")
    except ImportError:
        print("❌ PyAudio: FAILED")
    
    # Test microphone
    try:
        import speech_recognition as sr
        with sr.Microphone() as mic:
            print("✅ Microphone: OK")
    except Exception as e:
        print(f"❌ Microphone: {e}")

if __name__ == "__main__":
    test_environment()
    input("\nPress Enter to exit...")