from re import search

from google import genai
from google.genai import types #type: ignore
import json
from PIL import Image
import cv2
import pathlib


class AI:
    def __init__(self, functions: list= None, debug_level=1):
        """
        Sets up the genai client, api key, and chat.
        """
        self.debug_level = debug_level
        self.functions = list(functions) if functions is not None else []

        self.functions.append(self.get_image_description)
        self.functions.append(self.look_up_on_internet)

        if self.debug_level > 1:
            print("[gemini_functions] [Info] Starting...")
        

        self.BASE_DIR = pathlib.Path(__file__).resolve().parent.parent

        self.pathlib_config_file = self.BASE_DIR / "External_Files" / "Config" / "gemini_config.json"
        with open(self.pathlib_config_file, "r", encoding="utf-8") as config_file:
            self.config = json.load(config_file)

        self.client = genai.Client()

        raw_prompt_file = self.config["prompt_file_path"]
        file = self.BASE_DIR / pathlib.Path(raw_prompt_file)
        self.history_file = self.BASE_DIR / pathlib.Path(self.config["chat_history_file_path"])

        gemini_config = [*self.functions]

        self.chat = self.client.chats.create(
            model=self.config["gemini_model"],
            config=types.GenerateContentConfig(
                system_instruction=self.get_file_text(file),
                temperature=.5,
                tools=gemini_config
            )
            
        )

    
        self.possible_emotions = ["happy", "sad", "neutral", "surprised", "mad", "scared"]
        self.img = None

        if self.config["save_history"]:
            self.load_history()

        if self.debug_level > 0:
            print("[gemini_functions] [Info] set up the client and Abe's chat!")

    def get_image_description(self, prompt: str):
        """
        Gets a description of what the robot can see through it's eyes (camera).
        Args:
            prompt (str): What you are trying to find out about what you can see or the question you are trying to get imformation for.
        Returns:
            str: image description
        """
        if self.debug_level > 0:
            print(f"[gemini_functions] Called the image description function for {prompt}.")

        if self.img is None:
            return "Image desciption failed."
        description = self.client.models.generate_content(
            model=self.config["gemini_model"],
            contents=[self.img, prompt]
        )
        return description.text

    def look_up_on_internet(self, query: str):
        """
        Get's online, up to date, real time indormation.
        Args:
            query (str): the acctual text you would like to search, or the real-time or up to date info you need to access to complete a prompt.
        Returns:
            str: The result of your search, in a text form.
        """
        
        if self.debug_level > 0:
            print(f"[gemini_functions] Called the google search function for '{query}'.")


        result = self.client.models.generate_content(
            model=self.config["gemini_model"],
            contents=[query],
            config=types.GenerateContentConfig(
                system_instruction="Keep all responses under 30 words. Only output info and the facts. Do not make up any information. Do not use any special characters like asterisks or symbols.",
                max_output_tokens=500,
                thinking_config=types.ThinkingConfig(
                    thinking_budget=150
                ),
                tools=[
                    types.Tool(google_search=types.GoogleSearch())
                ]
            )
        )

        return str(result.text)

    def get_file_text(self, file) -> str:
        """
        Reads the "file" attribute and returns the file's text.
        """
        with open(file, "r", encoding="utf-8") as open_file:
            self.file_text = open_file.read()
        return self.file_text
    
    def load_history(self):
        """
        Sends all conversation history to the AI.
        """
        self.history = self.get_file_text(self.BASE_DIR / self.config["chat_history_file_path"])
        if  self.history != '':
            self.chat.send_message("Our conversation so far has been the following: \n" + self.history)
            if self.debug_level > 0:
                print("[gemini_functions] [Info] Loaded history!")
        else:
            print("[gemini_functions] Conversation history empty. Skipping history loading.")

    def send_ai_prompt(self):
        self.ai_prompt = self.get_file_text(self.config["prompt_file_path"])

        if self.ai_prompt == '':
            raise SyntaxError("No AI Prompt! Please add a prompt for Abe in the file ai_prompt.txt!")
        else:
            self.chat.send_message(self.ai_prompt)

    def add_to_conversation_history(self, text: str):
        with open(self.history_file, 'w') as h:
            h.write(self.history)

    def get_response(self, prompt: str=None, image=None) -> tuple[str, str, str]:
        """
        Returns a variables in this EXACT order: emotion, response
        
        Takes a str prompt that consists of the user's prompt.
        
        Also takes an optional image that WILL be sent to gemini.
        """

        if prompt == None or prompt == '':
            raise SyntaxError("Prompt was None, or empty!")

        self.prompt = str(prompt)
        
        if image is not None:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            self.img = Image.fromarray(image)

        self.response = self.chat.send_message(self.prompt)

        if self.config["save_history"]:
            self.history = self.get_file_text(self.config["chat_history_file_path"])
            self.history += f"User: {prompt} \nAbe: {self.response.text}\n\n"
            self.add_to_conversation_history(self.history)

        if self.response.text == None or self.response.text == '':
            return None, None

        split_text = self.response.text.split(None, 1)
        self.generated_emotion = split_text[0]
        self.text = split_text[1]
        if not self.generated_emotion.lower() in self.possible_emotions:
            self.generated_emotion = "neutral"
        return  self.generated_emotion, self.text

    def close(self):
        if self.config["save_history"]:
            if self.debug_level >= 1:
                print("[gemini_functions] [Info_Debug] Saving History...")
                self.add_to_conversation_history("\n[CODE] User turned you off.")
        if self.debug_level >= 1:
            print("[gemini_functions] Chat ended.")

    

if __name__ == '__main__':
    ai = AI(debug_level=2)
    while True:
        myinput = input("You: ")
        _, _, respo = ai.get_response(myinput)
        print(respo)
    