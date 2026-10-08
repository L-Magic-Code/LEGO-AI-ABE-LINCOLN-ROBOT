import time
import ev3_dc as ev3
import os
import subprocess
import uuid
import edge_tts
import asyncio
import random
import json
import threading
import nxt.locator
import nxt.motor
import tempfile
import pathlib
import math
import pygame

class Abe:
    """
    Connects to both ev3s, and sets up motors and sensors, if use_mindstorms in the ev3_config is True.
    """
    def __init__(self, use_mindstorms=True, debug_level=1):
        BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
        self.pathlib_config_file = BASE_DIR / "External_Files" / "Config" / "ev3_config.json"
        with open(self.pathlib_config_file, "r", encoding="utf-8") as ev3_config_file:
            self.config =  json.load(ev3_config_file)
        self.debug_level = debug_level 
        if self.debug_level > 1:
            print("[ev3_functions] [Info_debug] Starting...")

        self.use_mindstorms = use_mindstorms
        self.clapping_sound_file = BASE_DIR / "External_Files" / "clapping.mp3"
        self.pathlib_gettysburg_address_file = BASE_DIR / pathlib.Path(self.config["gettysburg_address_file_path"])
        with open(self.pathlib_config_file, "r", encoding="utf-8") as ev3_config_file:
            self.config =  json.load(ev3_config_file)
        if self.use_mindstorms:
#           -- Connect to EV3 head hub --
            try:
                self.ev3_head_hub = ev3.Jukebox(protocol=ev3.USB, host=self.config["EV3_HEAD_HUB_ADDRESS"])
                print("[ev3_functions] Connected to head hub!")
            except ev3.exceptions.NoEV3:
                raise Exception("Abe's head hub isn't connected or powered on!")

#           -- Connect to EV3 arms hub --
            try:
                self.ev3_arms_hub = ev3.Jukebox(protocol=ev3.USB, host=self.config["EV3_ARMS_HUB_ADDRESS"])
                print("[ev3_functions] Connected to ev3 arm hub!")
            except ev3.exceptions.NoEV3:
                raise Exception("Abe's ev3 arm hub isn't connected or powered on!")

#           -- Conect to NXT arms hub --
            try:
                self.nxt_arms_hub = nxt.locator.find()
                print("[ev3_functions] Connected to nxt arm and chest hub!")
            except Exception:
                raise Exception("Abe's nxt hub isn't connected or powered on!")
            self.debug_level = debug_level
            if self.debug_level > 0:
                print(f"[ev3_functions] [Info_debug] Head hub battery percentage: {self.ev3_head_hub.battery.percentage}")
                print(f"[ev3_functions] [Info_debug] EV3 arms hub battery percentage: {self.ev3_arms_hub.battery.percentage}")
                print(f"[ev3_functions] [Info_debug] NXT arms hub battery voltage: {self.nxt_arms_hub.get_battery_level()}")

#           -- Connect to motors from the head hub --
            self.eyebrows = ev3.Motor(port=getattr(ev3, self.config["EYEBROWS_PORT"]), ev3_obj=self.ev3_head_hub)
            self.mouth_corners = ev3.Motor(port=getattr(ev3, self.config["MOUTH_CORNERS_PORT"]), ev3_obj=self.ev3_head_hub)
            self.eyes = ev3.Motor(port=getattr(ev3, self.config["EYES_PORT"]), ev3_obj=self.ev3_head_hub)
            self.mouth = ev3.Motor(port=getattr(ev3, self.config["MOUTH_PORT"]), ev3_obj=self.ev3_head_hub)


            
#           -- Connect to motors and sensors from the ev3 arms hub --
            self.left_arm = ev3.Motor(port=getattr(ev3, self.config["LEFT_ARM_PORT"]), ev3_obj=self.ev3_arms_hub)
            self.left_hand = ev3.Motor(port=getattr(ev3, self.config["LEFT_HAND_PORT"]), ev3_obj=self.ev3_arms_hub)
            self.right_arm = ev3.Motor(port=getattr(ev3, self.config["RIGHT_ARM_PORT"]), ev3_obj=self.ev3_arms_hub)
            self.right_hand = ev3.Motor(port=getattr(ev3, self.config["RIGHT_HAND_PORT"]), ev3_obj=self.ev3_arms_hub)

            self.left_fingers = ev3.Color(port=getattr(ev3, self.config["LEFT_FINGERS_PORT"]), ev3_obj=self.ev3_head_hub)
            self.right_fingers  = ev3.Color(port=getattr(ev3, self.config["RIGHT_FINGERS_PORT"]), ev3_obj=self.ev3_head_hub)
            self.key_sensor  = ev3.Touch(port=getattr(ev3, self.config["EV3_KEY_PORT"]), ev3_obj=self.ev3_head_hub)
                        


#           -- Connect to motors and sensors from the nxt hub --
            self.right_arm_rotate = self.nxt_arms_hub.get_motor(getattr(nxt.motor.Port, self.config["RIGHT_ARM_ROTATE_PORT"]))
            self.chest_motor = self.nxt_arms_hub.get_motor(getattr(nxt.motor.Port, self.config["CHEST_MOTOR_PORT"]))
            self.left_arm_rotate = self.nxt_arms_hub.get_motor(getattr(nxt.motor.Port, self.config["LEFT_ARM_ROTATE_PORT"]))


#           -- Set positions and speeds, and assign other variables --
            self.mouth.position = 0
            self.right_hand.position = 0
            self.left_hand.position = 0
            self.eyes.position = 0
            self.eyebrows.position = 0
            self.mouth_corners.speed = 25
            self.right_hand_empty = self.config["right_hand_empty"]
            self.left_hand_empty = self.config["left_hand_empty"]
            self.run_eyes = True
            self.reading = False
            self.move_scared = True

            print("[ev3_functions] All hubs, motors, and sensors connected!")
        else:
            self.current_emotion = 'neutral'
            print("[ev3_functions] Ignoring all ev3 functions!")

#       -- Assign manditory variables, even if use_mindstorms is False --
        self.current_emotion = 'neutral'
        self.VOICE_MODEL = self.config["voice"]
        self.available_emotions = ["happy", "sad", "mad", "neutral", "surprised-happy", "surprised-mad", "sarcastic"]
        pygame.mixer.init()

        
    def move_to_position_nxt(self, motor, degrees, speed, timeout=1):
        if self.use_mindstorms:
            self.current_motor_position = motor.get_tacho().rotation_count
            self.result = self.current_motor_position - degrees
            if self.result < 0:
                motor.turn(power=speed * -1,  tacho_units=abs(self.result), timeout=timeout)
            elif self.result > 0:
                motor.turn(power=speed, tacho_units=degrees, timeout=timeout)

    def move_to_neutral(self, thread=False, brake=True, move_eyebrows=True):
        if self.use_mindstorms:
            self.current_emotion = 'neutral'
            self.move_scared = False
            if move_eyebrows:
                self.run_eyes = True
                self.mouth.move_to(position=10)
                if self.eyebrows.position >= 5 or self.eyebrows.position <= -5: 
                    self.eyebrows.move_to(position=1, brake=True).start(thread=False)
                    time.sleep(.05)
            time.sleep(.4)
            self.mouth_corners.move_to(position=30, speed=75, brake=brake).start(thread=thread)

    def _scared_movement(self):
        if self.use_mindstorms:
            while self.move_scared:
                self.mouth_corners.move_by(degrees=2, speed=70).start(thread=False)
                self.mouth_corners.move_by(degrees=-2, speed=70).start(thread=False)
            self.mouth_corners.move_to(position=30, brake=True).start(thread=False)

    def move_to_emotion(self, emotion: str = 'happy'):
        if self.use_mindstorms:
            self.emotion = emotion.lower()
            self.current_emotion = self.emotion
            if self.eyebrows.position >= 5 or self.eyebrows.position <= -5: 
                self.eyebrows.move_to(position=1, brake=True).start(thread=False)
                time.sleep(.2)

            if self.emotion == 'happy':
                if self.eyebrows.position >= 20 or self.eyebrows.position <= 10: 
                    self.eyebrows.move_to(position=15, brake=True).start(thread=False)
                self.mouth_corners.move_to(position=10).start(thread=False)

            elif self.emotion == 'sad':
                if self.eyebrows.position >= 20 or self.eyebrows.position <= 10: 
                    self.eyebrows.move_to(position=15, brake=True).start(thread=False)
                self.mouth_corners.move_to(position=50).start(thread=False)

            elif self.emotion == 'mad':
                if self.eyebrows.position >= -20 or self.eyebrows.position <= -10: 
                    self.eyebrows.move_to(position=-15, brake=True).start(thread=False)
                self.mouth_corners.move_to(position=50).start(thread=False)  

            elif self.emotion == "surprised-happy":
                if self.eyebrows.position >= 20 or self.eyebrows.position <= 10: 
                    self.eyebrows.move_to(position=15, brake=True).start(thread=False)
                self.mouth_corners.move_to(position=30, speed=75, brake=True).start(thread=False)
                self.mouth.move_to(position=-15, speed=50, brake=True).start(thread=False)

            elif self.emotion == "surprised-mad":
                if self.eyebrows.position >= -20 or self.eyebrows.position <= -10: 
                    self.eyebrows.move_to(position=-15, brake=True).start(thread=False)
                self.mouth_corners.move_to(position=40, speed=75, brake=True).start(thread=False)
                self.mouth.move_to(position=-15, speed=50, brake=True).start(thread=False)

            elif self.emotion == "sarcastic":
                self.run_eyes = True
                self.move_eyes_to_position(position=45, speed=20)
                self.run_eyes = False
                self.move_to_emotion("happy")

            elif self.emotion == "scared":
                self.move_to_emotion("sad")
                time.sleep(.1)
                self.move_scared = True
                threading.Thread(target=self._scared_movement).start()
                time.sleep(.01)

            elif self.emotion == "neutral":
                if self.use_mindstorms:
                    self.move_to_neutral()

            else:
                print(f"[ev3_functions] Ignonoring unknown emotion: {self.emotion}!")

    def look_at_coord(self, x, y):
        self.center_x = x - .5
        self.center_y = (y - .5) * -1
        self.raw_degrees = math.degrees(math.atan2(self.center_y, self.center_x))
        self.degrees = (self.raw_degrees + 360) % 360
        self.degrees = round(self.degrees)
        if self.use_mindstorms:
            if abs((self.degrees - (self.eyes.position * 1.65 % 360) + 180) % 360 - 180) >= 25:
                if not self.eyes.busy:
                    self.move_eyes_to_position(position=self.degrees)

    def stop_all_motors(self):
        if self.use_mindstorms:
            ev3_motor_list = [self.eyes, self.eyebrows, self.mouth, self. mouth_corners, self.left_arm, self.right_arm, self.left_hand, self.right_hand]
            nxt_motor_list = [self.chest_motor, self.right_arm_rotate, self.left_arm_rotate]

            for motor in ev3_motor_list:
                motor.stop(brake=False)

            for motor in nxt_motor_list:
                motor.idle()

    def home_motors(self):
        if self.use_mindstorms:
            self.stop_all_motors()
#           -- Home eyebrows --
            if self.eyebrows.position >= 5 or self.eyebrows.position <= -5:
                self.eyebrows.move_to(position=1, brake=True).start(thread=False)

#          -- Home mouth jaw --
            self.mouth.start_move(direction=1)
            time.sleep(.8)
            self.mouth.stop(brake=True)
            self.mouth.position = 0
            self.mouth.move_to(-5, brake=True).start()

#       -- Home mouth corners --
            self.mouth_corners.start_move(direction=-1)
            time.sleep(1)
            self.mouth_corners.stop(brake=True)
            self.mouth_corners.position = 0
            self.move_to_neutral(move_eyebrows=False)
            
#           -- Home rotate motor for left arm --
            try:
                self.left_arm_rotate.turn(power=15, tacho_units=180)
            except Exception:
                pass
            self.left_arm_rotate.brake()
            self.left_arm_rotate.reset_position(relative=False)

#           -- Home rotate motor for right arm --
            try:
                self.right_arm_rotate.turn(power=15, tacho_units=180)
            except Exception:
                pass
            self.right_arm.stop(brake=False)
            self.left_arm.stop(brake=False)
            self.right_arm.position = 0
            self.left_arm.position = 0

            self.right_arm_rotate.brake()
            self.right_arm_rotate.reset_position(relative=False)
            try:
                self.rotate_arm('right', 2)
            except:
                pass

            try:
                self.rotate_arm('left', 2)
            except:
                pass

            self.left_arm.stop(brake=False)
            self.right_arm.stop(brake=False)
            time.sleep(2)
            self.left_arm.move_by(-10, speed=65)
            self.right_arm.move_by(-10, speed=65)
            self.left_arm.stop(brake=True)
            self.right_arm.stop(brake=True)
                        

            if self.debug_level > 1:
                print("[ev3_functions] [debug] Homed arms!")

    def wait_for_key_insert(self):
        """
        Wait for the key to be inserted.
        """
        if self.use_mindstorms:
            while not self.key_sensor.touched:
                time.sleep(0.1)
            
    def say(self, text:str, degrees_add:int=0, intensity_add:int=0, emotion=None):
        """
        Say 'text' using edge_tts.

        If use_mindstorms is True, it will also move the jaw.
        'degrees_add' will add that many degrees to the mouth opening and closing.
        'intensity_add' will add to the speed of the mouth opening and closing.

        The voice pitch, rate, and volume will very slightly based on 'emotion'.
        If 'emotion' is None or not defines, it will use his current emotion.
        """


        tmp_directory = tempfile.gettempdir()
        audio_file = f"{uuid.uuid4}.mp3"
        file = os.path.join(tmp_directory, audio_file)
        self.voice_settings = {}

        if emotion == None:
            emotion = self.current_emotion

        if emotion.lower() == "scared":
            self.voice_settings = {"rate" : "+10%", "pitch" : "-5Hz", "volume" : "-8%"}

        elif emotion.lower() == "surprised-happy":
            self.voice_settings = {"rate" : "+10%", "pitch" : "+5Hz", "volume" : "+10%"}

        elif emotion.lower() == "surprised-mad":
            self.voice_settings = {"rate" : "-10%", "pitch" : "-5Hz", "volume" : "+10%"}

        elif emotion.lower() == "happy":
            self.voice_settings = {"rate" : "+4%", "pitch" : "+2Hz"}

        elif emotion.lower() == "sad":
            self.voice_settings = {"rate" : "-10%", "pitch" : "-8Hz", "volume" : "-20%"}

        elif emotion.lower() == "sarcastic":
            self.voice_settings = {"rate" : "-15%", "pitch" : "-8Hz", "volume" : "+10%"}

        async def _generate():
            self.communicate = edge_tts.Communicate(text, self.VOICE_MODEL, **self.voice_settings)
            await self.communicate.save(file)
        asyncio.run(_generate())
        self.is_speaking = True
        threading.Thread(target=self.move_mouth_up_and_down, args=[degrees_add, intensity_add]).start()
        subprocess.run([
            "ffplay",
            "-nodisp",
            "-autoexit",
            file
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.is_speaking = False
        os.remove(file)
        self.move_scared = False

    def move_mouth_up_and_down(self, degrees_add: int=0, intensity_add: int=0):
        """
        Moves Abes mouth up and down randomly.
        
        Degrees_add argument should be how many more degrees open then usual the mouth should go. By defaut, it is set to 0. It can be 0 to 10,
        Intensity_add argument should be how much faster then usual the mouth should go. By defaut, it is set to 0. It can be 0 to 10,
        """
        if self.use_mindstorms:
            degrees_add = int(degrees_add)
            if degrees_add > 100:
                self.degrees_add = 100
            elif degrees_add < 0:
                self.degrees_add = 0
            else:
                self.degrees_add = degrees_add

            self.open_mouth(25 + self.degrees_add, speed=25)

            intensity_add = int(intensity_add)
            if intensity_add > 10:
                self.intensity_add = 10
            elif intensity_add < 0:
                self.intensity_add = 0
            else:
                self.intensity_add = intensity_add
            

            while self.is_speaking:
                self.random_degree = random.randrange(5, 17) + self.degrees_add
                self.intensity = random.randrange(5, 17) + self.intensity_add
                self.close_mouth(self.random_degree, speed=self.intensity, brake=True)
                time.sleep(.07)
                self.open_mouth(self.random_degree, speed=self.intensity, brake=True)
                time.sleep(.07)
            self.close_mouth(25 + self.degrees_add, speed=25, brake=True)

    def open_mouth(self, degrees=25, speed=50, brake=True):
        """Opens Abe's jaw."""
        if self.use_mindstorms:
            degrees = degrees * -1
            self.move_for_degrees(self.mouth, degrees, speed=speed, brake=brake)

    def close_mouth(self, degrees=10, speed=50, brake=False):
        """Closes Abe's jaw."""
        if self.use_mindstorms:
            self.move_for_degrees(self.mouth, degrees, speed=speed, brake=brake)

    def move_to_position(self, motor, position, speed=50, brake=False):
        "Moves a motor to a specific position."
        if self.use_mindstorms:
            if not motor.busy:
                motor.start_move_to(position, speed=speed, brake=brake)
                while motor.busy:
                    time.sleep(.01)

    def move_for_degrees(self, motor, degrees, speed=50, brake=False):
        """Moves a motor for a specific amount of degrees."""
        if self.use_mindstorms:
            if not motor.busy:
                motor.start_move_by(degrees, speed=speed, brake=brake)
                while motor.busy:
                    time.sleep(.01)

    def open_hand(self, hand, speed: int = 75):
        """Opens one of Abe's hands."""
        if self.use_mindstorms:
            if hand.position != 180:
                if not hand.busy:
                    hand.move_to(180, speed=speed, brake=True).start(thread=False)

    def close_hand(self, hand, speed: int = 75):
        """Closes one of Abe's hands."""
        if self.use_mindstorms:
            if hand.position != 0:
                if not hand.busy:
                    hand.move_to(0, speed=speed, brake=True).start(thread=False)

    def change_config(self, key, property):
        """
        Allows you to easily change a value or add a key in the ev3_config.
        """
        with open(self.pathlib_config_file, "r", encoding="utf-8") as config_file:
            self.config_str = config_file.read()

        self.config = json.loads(self.config_str)
        self.config[key] = property

        with open(self.pathlib_config_file, "w", encoding="utf-8") as file:
            json.dump(self.config, file, indent=4)

    def grab(self):
        if self.use_mindstorms:
            if self.right_hand_empty:
                self.open_hand(self.right_hand)
                while self.right_fingers.reflected < self.config["reflected_light_threshold"]:
                    time.sleep(.1)
                self.close_hand(self.right_hand)
                self.right_hand_empty = False
                self.change_config("right_hand_empty", False)
                return True
            elif self.left_hand_empty:
                self.open_hand(self.left_hand)
                while self.left_fingers.reflected < self.config["reflected_light_threshold"]:
                    time.sleep(.1)
                self.close_hand(self.left_hand)
                self.left_hand_empty = False
                self.change_config("left_hand_empty", False)
                return True
            else:
                return False
        else:
            return True

    def wait_until_touched(self, sensor, max_wait=0):
        if self.use_mindstorms:
            if max_wait < 0:
                raise Exception("The 'max_wait' parameter can't be negative!")
            elif max_wait != 0:
                for _ in range(max_wait * 100):
                    time.sleep(.01)
                    if sensor.is_touched:
                        break
            else:
                while True:
                    time.sleep(.01)
                    if self.is_touched:
                        break

    def eyes_read(self):
        if self.use_mindstorms:
            while self.reading:
                self.move_eyes_to_position(135, speed=1)
                self.move_eyes_to_position(45, speed=40)

    def deliver_gettysburg_address(self):
        """
        Delivers the entire Gettysbrg adress.
        """
        with open(self.pathlib_gettysburg_address_file, "r", encoding="utf-8") as open_file:
            gettysburg_address = open_file.read()

        if self.use_mindstorms:
            self.right_hand.stop()

        self.say("Alright, I shall now deliver the gettysburg address.")
        if self.use_mindstorms:
            if not self.left_fingers.ambient <= self.config["reflected_light_threshold"] and not self.right_fingers.ambient <= self.config["reflected_light_threshold"] and self.left_hand_empty and self.right_hand_empty and self.config["hold_gettysburg_speech"]:
                self.say("Can you please give me my speech?")
                time.sleep(.5)
                self.open_hand(self.left_hand)
                self.open_hand(self.right_hand)
                while not self.left_fingers.touched:
                    time.sleep(.01)
                if self.left_fingers.touched:
                    self.close_hand(self.left_hand)
                while not self.right_fingers.touched:
                    time.sleep(.01)
                if self.right_fingers.touched:
                    self.close_hand(self.right_hand)
                self.say("Thank you.")
        try:
            time.sleep(1)
            self.reading = True
            if self.use_mindstorms:
                threading.Thread(target=self.eyes_read).start()
            self.say(gettysburg_address)
            self.reading = False
            self.say("Thank you!")
        finally:
            if self.use_mindstorms:
                self.right_hand.stop()

    def move_eyes_to_position(self, position, speed=30):
        if self.use_mindstorms:
            if self.run_eyes:
                self.position = position / 1.65
                if not self.eyes.busy:
                    self.eyes.move_to(position=round(self.position), speed=speed).start(thread=False)

    def open_chest(self):
        """
        Opens up the robot's chest. 
        Returns:
            str
        """
        if self.use_mindstorms:
            try:
                self.chest_motor.turn(power=5, tacho_units=125)
            except Exception:
                pass
            return "Your chest is now open."
        else:
            return "Your chest has not opened because you are not connected to your body. This is not an error, it is just an alert."

    def close_chest(self):
        """
        Closes the robot's chest. 
        Returns:
            str
        """
        if self.use_mindstorms:
            try:
                self.chest_motor.turn(power=-5, tacho_units=125)
            except Exception:
                pass
            return "Your chest is now closed"
        else:
            return "Your chest has not closed because you are not connected to your body. This is not an error, it is just an alert."

    def rotate_arm(self, arm, position=2, handel_error=False, timeout=1):
        """
        Rotates abe's arm, which may be either 'left' or 'right'.
        position can be an int from 1-5
        """
        if self.use_mindstorms:
            if not position in [0, 1, 2, 3, 4, 5]:
                position = 3
            if arm == 'left':
                try:
                    self.move_to_position_nxt(self.left_arm_rotate, position * 18, speed=50, timeout=timeout)
                except Exception:
                    pass
            elif arm == 'right':
                try:
                    self.move_to_position_nxt(self.right_arm_rotate, position * 18 , speed=50, timeout=timeout)
                except Exception:
                      pass  
            else:
                if self.debug_level > 1:
                    print(f"[ev3_functions] [debug] [rotate_arm()] Unknown arm: {arm}")

    def move_arm(self, arm : str='left', position : int=2):
        """
        Arm  may be 'left' or 'right'.
        Position may be an int for 0 to 3, with 3 being the highest, and 0 the lowest.
        """
        if self.use_mindstorms:
            if not position in [0, 1, 2, 3]:
                position = 2
            if arm == 'left':
                self.left_arm.move_to(position * -200, speed=75, brake=True).start(thread=False)
            elif arm == 'right':
                self.right_arm.move_to(position * -200, speed=75, brake=True).start(thread=False)
            else:
                if self.debug_level > 1:
                    print(f"[ev3_functions] [debug] [move_arm()] Unknown arm: {arm}")

    def _clapping(self):
        if self.use_mindstorms:
            self.move_arm('right', 1)
            self.move_arm('left', 1)
            while self.is_clapping:
                self.left_hand.start_move(speed=100)
                self.right_hand.start_move(speed=100)
            self.left_hand.stop(brake=True)
            self.right_hand.stop(brake=True)
            self.open_hand(self.right_hand)
            self.open_hand(self.left_hand)

            self.move_arm('right', 0)
            self.move_arm('left', 0)

    def clap(self):
        """
        Plays a clapping sound effect and moves your arms acordingly.
        There are no arguments and the function will not return anything.
        """

        clapping = pygame.mixer.Sound(self.clapping_sound_file).play()

        if self.use_mindstorms:
            self.is_clapping = True
            threading.Thread(target=self._clapping).start()
        while clapping.get_busy():
            time.sleep(1)
        self.is_clapping = False
            
    def move_hand_rps(self, rps, hand):
        if self.use_mindstorms:
            self.move_arm(hand, 2)
            if hand == 'left':
                if rps == 'rock':
                    self.rotate_arm("left", 3, True)
                    self.close_hand(self.left_hand)
                elif rps == 'paper':
                    self.rotate_arm("left", 1, True)
                    self.open_hand(self.left_hand)
                elif rps == 'scissors':
                    self.rotate_arm("left", 3, True)
                    self.open_hand(self.left_hand)
            elif hand == 'right':
                if rps == 'rock':
                    self.rotate_arm("right", 3, True)
                    self.close_hand(self.right_hand)
                elif rps == 'paper':
                    self.rotate_arm("right", 1, True)
                    self.open_hand(self.right_hand)
                elif rps == 'scissors':
                    self.rotate_arm("right", 3, True)
                    self.open_hand(self.right_hand)
            time.sleep(2)
            self.move_arm(hand, 0)

    def wave(self):
        if self.use_mindstorms:
            if self.right_hand_empty:
                arm_string_to_move = 'right'
                hand_object_to_move = self.right_hand
            elif self.left_hand_empty:
                arm_string_to_move = 'left'
                hand_object_to_move = self.left_hand
            else:
                return "You cannot wave because both hands are full."
            
            self.move_arm(arm_string_to_move, position=3)
            self.rotate_arm(arm_string_to_move, 0)
            time.sleep(2)
            self.rotate_arm(arm_string_to_move, 0)
            hand_object_to_move.start_move(speed=50)
            
            time.sleep(1.5)

            hand_object_to_move.stop(brake=True)
            self.rotate_arm(arm_string_to_move, 3)
            self.close_hand(hand_object_to_move)
            self.move_arm(arm_string_to_move, 0)

            return "You waved"
        else:
            return "You cannot wave because your body is not connected."




if __name__ == "__main__":
    abe = Abe(use_mindstorms=True, debug_level=2)


    print("===== HOMING MOTORS =====")
    abe.home_motors()
    time.sleep(1)

    abe.wave()

    print("===== MOVING TO EMOTION 'happy' =====")
#    abe.move_to_emotion('happy')
    time.sleep(2)
#    abe.deliver_gettysburg_address()

#    abe.move_to_neutral()

#    abe.say("Thanks for watching! Make sure to like and subscribe, and share this video if you thought it was intresting!")
    time.sleep(2)
