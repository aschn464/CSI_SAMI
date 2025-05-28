import requests
import speech_recognition as sr
# from ollama import Client
# from ollama import generate
import os
import time
from gtts import gTTS
import pygame
from tempfile import NamedTemporaryFile 
import json

language = "en"
mic_names = sr.Microphone.list_microphone_names()
url = "http://localhost:11434/api/chat"
SAVE_FILE = 'game_so_far.txt'
story_context = ""
full_story = ""
inventory = {}

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
        save_data = {
            "context": context,
            "inventory": inventory
        }
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(save_data, f)


########################################################################
# if save exists, load it
########################################################################
def load_game():
    global inventory
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            inventory = data.get("inventory", {})
            return data.get("context", "")
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
        user_choice = input("Previous game file found. Would you like to continue? (y/n) \n").strip().lower()
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
    global full_story

    story_context = ""
    full_story = ""
    
    print("Available Microphones:")
    for i, name in enumerate(mic_names):
        print(f"{i}: {name}")
    mic_index = int(input("Enter the index of the microphone you want to use: "))
    
    init_game()
    
    while True:
        result = game_loop()
        if result == 0:
            break
    

########################################################################
# Begin the game
########################################################################
def init_game():
    global story_context
    
    
    loaded = load_game()
    if loaded: 
        story_context = loaded
    else: 
        story_context = ""

    text_to_speech("Welcome to The Inn, a Collaborative Storytelling Setting. Say begin to start game. Say quit to exit.")



########################################################################
# 
########################################################################
def game_loop():
    global story_context
    
    # get user input
    query = speech_to_text(mic_index).lower().strip()
    
    # check for quit or save
    if query in {"quit", "exit", "save", "save game"}:
        save_game(story_context)
        return 0
    
    if update_inventory(query):  # Skip LLM if inventory was handled
        return 1
    
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
# update inventory
########################################################################
def update_inventory(query):
    if query.lower() in {"inventory", "check inventory", "show inventory"}:
        if not inventory:
            text_to_speech("Your inventory is empty.")
        else:
            inv_list = ', '.join(f"{item} (x{count})" if isinstance(inventory, dict) else item for item, count in inventory.items() if isinstance(inventory, dict))
            text_to_speech(f"You have: {inv_list}")
        return True
    
    elif query.lower().startswith("take ") or query.lower().startswith("pick up "):
        item = query.split(" ", 1)[1].strip()
        inventory[item] = inventory.get(item, 0) + 1
        text_to_speech(f"You have picked up a {item}.")
        return True

    elif query.lower().startswith("use "):
        item = query.split(" ", 1)[1].strip()
        if item in inventory and inventory[item] > 0:
            inventory[item] -= 1
            if inventory[item] == 0:
                del inventory[item]
            text_to_speech(f"You use the {item}.")
        else:
            text_to_speech(f"You don't have a {item} to use.")
        return True
    
    elif query.startswith("drop ") or query.startswith("remove "):
        item = query.split(" ", 1)[1].strip()
        if item in inventory:
            inventory[item] -= 1
            if inventory[item] <= 0:
                del inventory[item]
            text_to_speech(f"You dropped the {item}.")
        else:
            text_to_speech(f"You don't have a {item}.")
        return True
    
    return False




########################################################################
# format inventory
########################################################################
def format_inventory_for_prompt():
    if not inventory:
        return "The player's inventory is empty."
    else:
        return "The player has the following items: " + ", ".join(
            f"{item} (x{count})" for item, count in inventory.items()
        )



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
    inventory_context = format_inventory_for_prompt()
    full_story = f"{inventory_context}\n{story_context}\nPlayer: {prompt}\nNarrator:"
    
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
    print(response)
    
    ttsobj = gTTS(text=response, lang=language, slow=False)
    with NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
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
