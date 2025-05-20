import requests
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
url = "http://localhost:11434/api/chat"
SAVE_FILE = 'game_so_far.txt'

########################################################################
# load model
########################################################################
def init_model():
    requests.post(url,
        json={
            "model": "llama_mud",
            "prompt": "load"
        }
                  )
    


########################################################################
# save game to text file
########################################################################
def save_game(context):
    text_to_speech("Would you like to save your game?")
    response = speech_to_text(mic_index)

    if response in {"yes"}:
        with open(SAVE_FILE, "w", encoding = "utf-8") as f:
            f.write(context)
        return
    
    else:
        return


########################################################################
# if save exists, load it
########################################################################
def load_game():
    saved = load_state()
    if saved and load_saved_game():
        return saved
    else:
        return None
    

########################################################################
# read previous save
########################################################################
def load_state():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return None

########################################################################
# prompt user to choose new or saved game
########################################################################
def load_saved_game():
    while True:
        user_choice = input("Previous game file found. Would you like to continue? (y/n) \n").strip().lower
        if user_choice in {'y', 'yes'}:
            print("loading saved game... \n")
            return True
        elif user_choice in {'n', 'no'}:
            print ("Beginning new game... \n")
            return False
        else:
            print("Please enter 'yes' or 'no'!")



########################################################################
# 
########################################################################
def main():    
    global story_context
    global mic_index
    
    print("Available Microphones:")
    for i, name in enumerate(mic_names):
        print(f"{i}: {name}")
    mic_index = int(input("Enter the index of the microphone you want to use: "))
    
    init_game()
    
    while game_loop:
        game_loop()
    

########################################################################
# Begin the game
########################################################################
def init_game():
    loaded = load_game
    if loaded: story_context = loaded

    text_to_speech("Welcome to The Inn, a Collaborative Storytelling Setting. Say begin to start game. Say quit to exit.")



########################################################################
# 
########################################################################
def game_loop():
    # get user input
    query = speech_to_text(mic_index)
    
    # check for quit or save
    if query in {"quit", "exit", "save", "save game"}:
        save_game()
        return 0

    # start measuring time
    start_time = time.time()

    # call transmit prompt
    response = transmit_prompt(query, story_context)

    # stop measuring time
    elapsed_time = time.time() - start_time
    print(f"(Response time: {elapsed_time:.1f}s)")

    # call text to speech
    text_to_speech(response)

    # add messages to full story
    story_context += f"Player: {query}\nNarrator:{response}"



########################################################################
# 
########################################################################
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
                    return query
                    #transmit_prompt(query)
                except sr.UnknownValueError:
                    print("Could not understand audio.")
                except sr.RequestError as e:
                    print(f"API error: {e}")
    except KeyboardInterrupt:
        print("Stopped by user.")
    

########################################################################
# 
########################################################################
def transmit_prompt(prompt, story_context):
    full_story = f"{story_context}\nPlayer: {prompt}\nNarrator:"

    data = {
        "model": "llama_mud",
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
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()["message"]["content"]
    except Exception as e:
        print("Error during LLAMA call:", e)
        return "[Error]"
  
  
  
 




########################################################################
# 
########################################################################
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

