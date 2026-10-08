import cv2
import json
import time
import threading
import pathlib
if __name__ == '__main__':
    from extra_functions import print_red
else:
    from .extra_functions import print_red
import numpy
import cvzone.FaceDetectionModule
import cvzone.HandTrackingModule
import sys

class Camera:
    black_img = numpy.zeros((720, 1280, 3), numpy.uint8)
    def __init__(self, camera_type, port=None, debug_level=1, force=False):
        """
        Returns Camera object. 
        'type' may be camera.pi_camera, or Camera
        """

        self.type = camera_type.lower()

        self.debug_level = debug_level

        self.stable = True

        self.latest_frame = numpy.zeros((720, 1280, 3), numpy.uint8)

        self.black_frame = numpy.zeros((720, 1280, 3), numpy.uint8)

        self.run = True

        cv2.putText(self.black_frame, "CAMERA NOT CONNECTED", (360, 360), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.rectangle(self.black_frame, (325, 280), (925, 400), (255, 255, 2550), 2,  cv2.LINE_AA)

        self.force = force

        if self.type == "raspberry_pi_camera":
            try:
                import picamera2
            except Exception:
                print_red("[vision_functions] [ERROR] PiCamera2 not installed! Ignoring Raspiberry Pi camera!")
                self.stable = False
                return
            self.cam = picamera2.Picamera2()
            self.cam.start()
            if self.debug_level > 0:
                print("[vision_functions] [Debug] Testing camera connection...")
            try:
                self.get_frame()
            except TimeoutError:
                print_red("[vision_functions] [ERROR] Failed to connect to desk camera. Ignoring all desk camera calls")
                self.stable = False
            if self.stable:
                print("[vision_functions] [DEBUG] Connection to regular camera successfull!")


        elif self.type == "regular_camera":
            if type(port) not in [str, int]:
                raise Exception(f"camera_type must be str or int, not {type(self.type)}!")
            self.cam = cv2.VideoCapture(port)

            if self.debug_level > 0:
                print("[vision_functions] [Debug] Testing camera connection...")


            if not self.cam.isOpened():
                print_red("[vision_functions] [ERROR] Failed to connect to front camera. Ignoring all front camera calls")
                self.stable = False

            if self.stable:
                ret, _ = self.cam.read()
                if not ret:
                    print_red("[vision_functions] [ERROR] Failed to connect to front camera. Ignoring all front camera calls")
                    self.stable = False                
                else:
                    if self.debug_level > 0:
                        print("[vision_functions] [DEBUG] Connection to raspberry pi camera successfull!")

        elif self.type == "placeholder_camera":
            pass
        
        else:
            print_red(f"Unknown camera type: {self.type}.")
            self.stable = False
        
    def get_frame(self):
        if self.type == "raspberry_pi_camera":
            if self.stable:
                try:
                    self.latest_frame = self.cam.capture_array(wait=1)
                    self.latest_frame = cv2.cvtColor(self.latest_frame, cv2.COLOR_RGB2BGR)
                    return self.latest_frame
                except:
                    if self.force:
                        return self.black_frame
                    else:
                        return None
            else:
                if self.force:
                    return self.black_frame
                else:
                    return None
                
        elif self.type == "regular_camera":
            if self.stable:
                ret, frame = self.cam.read()
                if not ret:
                   raise ConnectionError("Failed to grab a frame. This might be because the camera is not connected.")
                return frame
            else:
                if self.force:
                    return cv2.flip(self.black_frame, 1)
                else:
                    return None
                
        elif self.type == "placeholder_camera":
            if self.force:
                return self.black_frame
            else:
                return None

    def _loop(self):
        while self.run:
            self.latest_frame = self.get_frame()
            time.sleep(.01)

    def start_capture_loop(self):
        threading.Thread(target=self._loop).start()

    def close(self):
        if self.type == 'raspberry_pi_camera':
            self.cam.close()
        elif self.type == 'regular_camera':
            self.cam.release()
                

class Vision:
    def __init__(self, abe : object = None, use_mindstorms=None, debug_level=1):
        """
        Abe's main vision class.
        Accepts 'Abe' class from ev3_functions.py.
        """
        BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
        self.pathlib_config_file = BASE_DIR / "External_Files" / "Config" / "vision_config.json"
        with open(self.pathlib_config_file, "r", encoding="utf-8") as opened_file:
            self.config = json.load(opened_file)

        self.capture_frame = self.config["auto_camera_start"]

        self.vision_trigger_words = self.config["vision_trigger_words"]

        self.abe = abe

        self.debug_level = debug_level

        self.Hand = None

        self.use_front_camera = self.config["use_front_camera"]
        self.use_desk_camera = self.config["use_desk_camera"]


        if self.use_front_camera:
            self.front_camera = Camera(self.config["front_camera_type"], self.config["front_camera_port"], self.debug_level, self.config["force_front_camera"])
            self.front_camera.start_capture_loop()
        else:
            self.front_camera = Camera("placeholder_camera", self.config["force_front_camera"])
            if self.debug_level > 0:
                print("[vision_functions] [Info] Ignoring all front camera functions!")

        if self.use_desk_camera:
            self.desk_camera = Camera(self.config["desk_camera_type"], self.config["desk_camera_port"], self.debug_level, self.config["force_desk_camera"])
            self.desk_camera.start_capture_loop()
        else:
            self.desk_camera = Camera("placeholder_camera", self.config["force_desk_camera"])
            if self.debug_level == 1:
                print("[vision_functions] [Info] Ignoring all desk camera functions!")


        self.hand_tracking = cvzone.HandTrackingModule.HandDetector(maxHands=2, detectionCon=.75)
        self.face_tracking = cvzone.FaceDetectionModule.FaceDetector(minDetectionCon=.75)

        self.camera_tracking_mode = self.config["default_tracking_mode"]
        self.run_camera_loop = True
        self.capture_frame = True
        self.move_eyes = True
        self.use_mindstorms = use_mindstorms
        self.include_desk_feed = self.config["show_desk_feed"]
        self.include_front_feed = self.config["show_front_feed"]

    def get_float_coords(self, frame, x, y):
        """
        Arguments: frame, and x and y pixel coordinates
        Returns: 
            Tuple:
                x and y converted to a float from 0.0 to 1.0
        """
        height, width, _ = frame.shape
        x = x / width
        y = y / height
        return (x, y)


    def _camera_windows_loop(self):
        """
        Abe's main camera loop.
        
        It will capture frames as long as the capture_frame attribute is True.

        Eye tracking depends on the camera_tracking_mode attribute, that may either be "face" or "hand" 
        """

        while self.run_camera_loop:
            if self.use_front_camera:
                self.tracking = False
                if self.capture_frame == True:
                    self.frame = self.front_camera.latest_frame
                    self.frame = cv2.flip(self.frame, 1)
                else:
                    time.sleep(.01)
                    continue
                if self.frame is None:
                    time.sleep(.01)
                    continue


                if self.camera_tracking_mode.lower() == 'face':
                    _, self.results = self.face_tracking.findFaces(self.frame, draw=False)
                    if self.results:
                        self.tracking = True
                        self.label = 'Face'
                        self.result = self.results[0]
                        self.bbox = self.result["bbox"]   


                elif self.camera_tracking_mode.lower() in ['hands', 'left hand', 'right hand']:
                    self.results, _ = self.hand_tracking.findHands(self.frame, draw=False)
                    if self.results:

                        if self.camera_tracking_mode == 'hands':
                            self.tracking = True
                            self.label = 'Hand'
                            self.result = self.results[0]
                            self.bbox = self.result["bbox"]            
    
                        else:
                            if self.camera_tracking_mode == 'left hand':
                                search = 'Left'
                                self.label = 'Left Hand'
                            elif self.camera_tracking_mode == 'right hand':
                                search = 'Right'
                                self.label = 'Right Hand'
                            for hand in self.results:
                                if hand['type'] == search:
                                    self.Hand = hand
                                    self.tracking = True
                                    self.bbox = hand["bbox"]            
                                    break



            
            if self.include_front_feed:
                if self.tracking:
                    self.center_x = self.bbox[0] + self.bbox[2] / 2
                    self.center_y = self.bbox[1] + self.bbox[3] / 2
                    self.center_x, self.center_y = self.get_float_coords(self.frame, self.center_x, self.center_y)

                    self.abe.look_at_coord(self.center_x, self.center_y)
                    x, y, width, height = self.bbox
                    cv2.rectangle(self.frame, (x, y), (x + width, y + height), (0, 255, 0), 2, cv2.LINE_AA)
                    cv2.putText(self.frame, self.label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, .8, (0, 255, 0), 5, cv2.LINE_AA, False)

                cv2.imshow("Front Camera", self.frame)
                
                
            if self.use_desk_camera:
                self.desk_frame = self.desk_camera.get_frame()
                if self.desk_frame is not None:
                    cv2.imshow("Desk Camera", self.desk_frame)
            cv2.waitKey(1)

    def start_camera_windows_loop(self, thread : bool=True):
        """
        Starts tracking faces or hands, and opens preview windows.
        Uses threading if 'thread' argument is True.
        """
        if thread == False:
            self._camera_windows_loop()
        else:
            threading.Thread(target=self._camera_windows_loop).start()



    def get_gemini_img(self):
        """
        Returns: a frame to send to gemini based on config prefrences
        """
        if self.config["gemini_camera"] == 'front':
            return self.front_camera.get_frame()
        elif self.config["gemini_camera"] == 'desk':
            return self.desk_camera.get_frame()
        else:
            if self.debug_level > 0:
                print_red(f"[vision_functions] [ERROR] 'gemini_camera' in config must be either 'front' or 'desk', not {self.config['gemini_camera' ]}!")
            return Camera.black_img
    def look_at_face(self):
        """
        Starts tracking the user's face if it detects one.
        his function doesn't return anything, and doesn't take any args.
        """
        if self.debug_level > 0:
            print(f"[vision_functions] Called the face tracking function.")
        
        self.camera_tracking_mode = 'face'

    def look_at_hand(self, hand:str):
        """Starts look at user's hand if it detects one.
        Args:
            hand: The hand you want to track. This may be one of the following: 'left_hand', 'right_hand', or 'either_one'
        """
        if self.debug_level > 0:
            print(f"[vision_functions] Called the hand tracking function for {hand}.")
        
        if hand == 'either_one':
            self.camera_tracking_mode = 'hands'
        elif hand == 'left_hand':
            self.camera_tracking_mode = 'left hand'
        elif hand == 'right_hand':
            self.camera_tracking_mode = 'right hand'
        else:
            if self.debug_level > 0:
                (f"[vision_functions] [ERROR] Uknown hand: {hand}!")
                
        
    def close(self):
        self.run_camera_loop =  False
        time.sleep(.5)
        self.desk_camera.run = False
        self.front_camera.run = False
        self.desk_camera.close()
        self.front_camera.close()
        cv2.destroyAllWindows()
        sys.exit()

        
if __name__ == "__main__":
    vision = Vision(debug_level=2)
    vision.start_camera_windows_loop()
    while True:
        time.sleep(1)