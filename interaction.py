import speech_recognition as sr
from ollama import Client
from ollama import generate
import os
import time
from gtts import gTTS
import pygame
from tempfile import TemporaryFile

language = "en"
mic_names = sr.Microphone.list_microphone_names()


def main():
    print("Available Microphones:")
    for i, name in enumerate(mic_names):
        print(f"{i}: {name}")
    mic_index = int(input("Enter the index of the microphone you want to use: "))
    while True:
        speech_to_text(mic_index)



def speech_to_text(mic_index):
    r = sr.Recognizer()
    try:
        with sr.Microphone(device_index=mic_index) as source:
            r.adjust_for_ambient_noise(source)
            while True:
                print("Listening...")
                audio = r.listen(source)
                try:
                    query = r.recognize_google(audio)
                    print(query)
                    transmit_prompt(query)
                except sr.UnknownValueError:
                    print("Could not understand audio.")
                except sr.RequestError as e:
                    print(f"API error: {e}")
    except KeyboardInterrupt:
        print("Stopped by user.")
    


def transmit_prompt(prompt):
  #full_story = 


  data = {    
        "model": "llama3.2:latest",
        "messages": [
            {
                "role": "user",
                "content": full_story,

            }
        ],
        "stream": False,
    }
  
    headers = {
        "Content-Type": "application/json"
    }
    try:
        response = generate(model='llama_mud', prompt=prompt)
        response.raise_for_status()
        return response.json()["message"]["content"]
    except Exception as e:
        print("Error during LLaMA call:", e)
        return "[Error]"
  
  
  
  
#   print("Sending prompt to model...")
#   request = generate(model='llama_mud', prompt=prompt)
#   response = request['response']
#   print(response)
#   text_to_speech(response)





def text_to_speech(response):
    ttsobj = gTTS(text=response, lang=language, slow=False)
    with TemporaryFile(delete=False, suffix=".mp3") as temp_file:
        ttsobj.save(temp_file.name)
        filename = temp_file.name

    pygame.mixer.init()
    pygame.mixer.music.load(filename)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(0.5)

    pygame.mixer.quit()
    os.remove(filename)


if __name__ == "__main__":
  main()

