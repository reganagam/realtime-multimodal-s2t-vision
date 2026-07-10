import speech_recognition as sr
import pyaudio
import time

def test_microphone_quality():
    print("Testing Kualitas Mikrofon...")
    
    r = sr.Recognizer()
    
    # Test semua mikrofon
    mics = sr.Microphone.list_microphone_names()
    print(f"\nDitemukan {len(mics)} mikrofon:")
    
    for i, name in enumerate(mics):
        print(f"{i}: {name}")
    
    # Test mikrofon default
    print("\nTesting mikrofon default...")
    try:
        with sr.Microphone() as source:
            print("Mengatur noise ambient... (diam selama 2 detik)")
            r.adjust_for_ambient_noise(source, duration=2)
            print(f"Energy threshold: {r.energy_threshold}")
            
            print("Berbicara sekarang... (uji: 'halo testing satu dua tiga')")
            audio = r.listen(source, timeout=5, phrase_time_limit=3)
            
            try:
                text = r.recognize_google(audio, language='id-ID')
                print(f"✓ Terdeteksi: {text}")
                print("✓ Mikrofon berfungsi dengan baik!")
            except sr.UnknownValueError:
                print("✗ Tidak bisa memahami audio")
            except sr.RequestError as e:
                print(f"✗ Error service: {e}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_microphone_quality()
    input("\nPress Enter to exit...")