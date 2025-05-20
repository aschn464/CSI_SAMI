import requests
import json
import time

url = "http://localhost:11434/api/chat"

story_context = """
    you are the narrator for a fantasy, text-based adventure game. The game setting is an
    inn in a fantasy setting. The characters are able to interact with the world 
    and inspect objects and people.  

    Use rich but concise descriptions. Focus only on what the player sees, hears, or directly interacts with.

    Do NOT repeat previous descriptions or add unrelated lore. Avoid filler words or overly poetic language.

    do NOT repeat previous descriptions.

    Every response should either reveal something new, describe a change, or offer a clear next action.

    The story so far:
"""

def llama3(prompt, story_context):
    
    full_story = f"{story_context}\nPlayer: {prompt}\nNarrator:"

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
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()["message"]["content"]
    except Exception as e:
        print("Error during LLaMA call:", e)
        return "[Error]"
    # response = requests.post(url, headers=headers, json=data)
    # return response.json()["message"]["content"]

def main():
    global story_context
    print("welcome to The Inn, a storytelling setting")
    print("what would you like to do? (type quit or exit to leave)")    
    while True:
        user_input = input("You: ")
    
        if user_input.lower() in {"quit", "exit"}:
            print("Goodbye player")
            break
        
        start_time = time.time()

        narration = llama3(user_input, story_context)

        elapsed_time = time.time() - start_time
        print(f"\nNarrator: {narration}\n")
        print(f"(narrator took {elapsed_time:.1f}s to respond)")

        story_context += f"Player: {user_input}\nNarrator:{narration}"

if __name__ == "__main__":
    main()