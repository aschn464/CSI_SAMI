import requests
import speech_recognition as sr
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
TEXT_ONLY_MODE = False
story_summary = ""
full_story = ""
recent_turns = []
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
def save_game():
    text_to_speech("Would you like to save your game?")
    
    #quick check for text only mode
    if TEXT_ONLY_MODE:
        response = speech_to_text()
    else:
        response = speech_to_text(mic_index)

    while True:
        if response in {"yes", "y"}:
            save_data = {
                "inventory": inventory, 
                "full_story": full_story,
                "recent_turns": recent_turns,
                "story_summary": story_summary,
            }
            with open(SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump(save_data, f, indent=4)
                return

        elif response in {'n', 'no'}:
            return 
        else:
            print("Please enter 'yes' or 'no'!") 


########################################################################
# if save exists, load it
########################################################################
def load_game():
    global inventory, full_story, recent_turns, story_summary
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            inventory = data.get("inventory", {})
            full_story = data.get("full_story", "")
            recent_turns = data.get("recent_turns", [])
            story_summary = data.get("story_summary", "")
            return data.get("context", "")
    return None

    

########################################################################
# detects if a previous save file exists
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
        user_choice = input("Previous game file found. Would you like to continue? (y/n): ").strip().lower()
        if user_choice in {'y', 'yes'}:
            print("loading saved game... \n")
            return True
        elif user_choice in {'n', 'no'}:
            print ("Beginning new game... \n")
            return False
        else:
            print("Please enter 'yes' or 'no'!")
    

########################################################################
# Begin the game
########################################################################
def init_game():
    continue_game = False
    loaded = load_state()        #load game only returns true or Null... can remove loaded I think

    if loaded:
        continue_game = load_saved_game()

    if continue_game:
        global story_summary, recent_turns
        load_game()
        print(f"The game so far: {story_summary}\nMost Recent move: {recent_turns[2]}")
    else:
        text_to_speech("Welcome to The Inn, a Collaborative Storytelling Setting. Say begin to start game. Say quit to exit.")


########################################################################
# the "bread and butter" function. most the moment to moment gameplay happens here
########################################################################
def game_loop():
    global recent_turns, story_summary, full_story
    
    #get user input for text only game
    if TEXT_ONLY_MODE:
        query = speech_to_text().lower().strip()
    
    # get user input for speech to text
    else:
        query = speech_to_text(mic_index).lower().strip()
    
    # check for quit or save
    if query in {"quit", "exit"}:
        return 0
    
    elif query in {"save", "save game"}:
        save_game()
    
    if update_inventory(query):  # Skip LLM if inventory was handled
        return 1
    
    # start measuring time
    start_time = time.time()

    #build the prompt from summarized story and recent interactions
    prompt = construct_prompt(query)

    # call transmit prompt
    response = transmit_prompt(prompt)

    # stop measuring time
    elapsed_time = time.time() - start_time
    print(f"(Response time: {elapsed_time:.1f}s)")

    # call text to speech
    text_to_speech(response)

    #save the appropriate bits of information in the correct spaces. and summarize where appropriate
    latest_interaction = f"Player: {query}\nNarrator:{response}"
    recent_turns.append(latest_interaction)

    #keep the most_recent list to 3 interactions and summarize everything before that
    if len(recent_turns) > 3:
        oldest = recent_turns.pop(0)
        story_summary = summarize_story(oldest, story_summary)
    
    # add messages to full story
    full_story += f"Player: {query}\nNarrator:{response}"



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
def speech_to_text(mic_index=None):

    #if running as a text only game
    if TEXT_ONLY_MODE:
        return input("You: ")
    
    if mic_index == None:
        raise ValueError("mic_index must be defined for voice to text functionality.")

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
# function that builds the prompt to send to the LLM for it's DM response
########################################################################
def construct_prompt(query):
    prompt = f"summary of story so far:\n{story_summary}\n\n"
    prompt += f"recent interactions:\n" + "\n".join(recent_turns) + "\n"
    prompt += f"Player: {query}\nNarator: "
    return prompt


########################################################################
# function that summarizes older interactions to keep prompts short
########################################################################
def summarize_story(oldest, story_summary):
    prompt = (f"create a summary of the interactions below. Be sure to keep all important story beats and player interactions.", 
              " The summary should be coherent and anybody who reads it should be able to read it and remember what came before\n\n"
              f"current summary: {story_summary}\n\n"
              f"Newest interaction: {oldest}")
    return transmit_prompt(prompt)


########################################################################
# 
########################################################################
def transmit_prompt(prompt):
    inventory_context = format_inventory_for_prompt()
    content = f"{inventory_context}\n{prompt}"
    
    data = {
        "model": "llama_mud",
        "messages": [
            {
                "role": "user",
                "content": content,
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
    
    #if this is a text-only game, bypass all the text->speech
    if TEXT_ONLY_MODE:
        return

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

########################################################################
# 
########################################################################
def main():    
    
    #give the player the option to proceed in text-only mode
    mode_choice = input("would you like to play in text only mode (y/n): ").strip().lower()
    if mode_choice in {'y', 'yes'}:
        global TEXT_ONLY_MODE
        TEXT_ONLY_MODE = True

    #if you want to use the speech->text, then do this
    if TEXT_ONLY_MODE == False:
        global mic_index
        print("Available Microphones:")
        for i, name in enumerate(mic_names):
            print(f"{i}: {name}")
        mic_index = int(input("Enter the index of the microphone you want to use: "))
    
    init_game()
    
    while True:
        result = game_loop()
        if result == 0:
            break

if __name__ == "__main__":
  main()
