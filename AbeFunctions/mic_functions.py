import vosk
import json
import sounddevice
import time
import pathlib

class Mic:
    def __init__(self, use_mic, debug_level=1):
        """
        Returns Mic.
        Debug level can be 0, 1, or 2.
        """
        self.is_on = use_mic

        self.debug_level = debug_level
        if self.debug_level > 1:
            print("[mic_functions] [Info_debug] Starting...")


        BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
        self.pathlib_config_file = BASE_DIR / "External_Files" / "Config" / "mic_config.json"
        with open(self.pathlib_config_file, "r") as config_file:
            self.config = json.load(config_file)

        _path_to_vosk_model_basic_folder = pathlib.Path(BASE_DIR / "External_Files" / "vosk-model")
        _path_to_vosk_model_basic_folder = next(path for path in _path_to_vosk_model_basic_folder.iterdir() if path.is_dir())
        
        print(_path_to_vosk_model_basic_folder)

        self.VOSK_MODEL_PATH = _path_to_vosk_model_basic_folder

        

        self.model = vosk.Model(str(self.VOSK_MODEL_PATH))
        self.recognizer = vosk.KaldiRecognizer(self.model, 16000)

        if self.debug_level > 1:
            print(f"Succesfully loaded model from: {self.VOSK_MODEL_PATH}")

        self.what_was_last_said = ''
        self.what_was_just_said = ''
        self._isListening = False
        self.listen = True

        if self.debug_level > 0:
            print("[mic_functions] [Debug] Succesfully set up vosk speech recognizer!")

    def start_listening(self):
        self.mic = sounddevice.RawInputStream(
            samplerate=16000,
            blocksize=8000,
            dtype='int16',
            channels=1,
            callback=self._callback)
        self.mic.start()
        self._isListening = True
        self.is_on = True
        
    def _callback(self, indata, frames, time, status):
        if self.listen:
            if self.recognizer.AcceptWaveform(bytes(indata)):
                self.result = self.recognizer.Result()
                self.dict_result = json.loads(self.result)
                self.what_was_just_said = self.dict_result['text']

    def get_speech(self) -> str:
        if self.what_was_last_said != self.what_was_just_said:
            self.what_was_last_said = self.what_was_just_said
            return self.what_was_just_said
        else:
            self.what_was_last_said = self.what_was_just_said
            return ''

    def wait_for_trigger_word(self, trigList : list):
        """
        Blocks until any item in trigList is recognized.
        """
        if not self._isListening:
            raise Exception("Called wait_for_trigger_word, but not listening!")
    
        while True:
            self.text = self.get_speech().lower()
            if self.text == '':
                continue
           
            if self.debug_level > 1:
                print(f"Heard: {self.text}")
                time.sleep(.5)

            for trigger in trigList:
                if trigger in self.text:
                    return trigger

    def pause_listening(self):
        self.is_on = False
        self.mic.stop()

    def close(self):
        self.mic.stop()
        self._isListening = False
        self.is_on = False
        
if __name__ == '__main__':
    mic = Mic(True)
    mic.start_listening()
    print("OKAY!")
    word = mic.wait_for_trigger_word(["robot", "happy", "abraham"])
    print(f"Listening! triggered by: {word}")
    try:
        while True:
            text = mic.get_speech()
            if text != '':
                print("You said:")
                print(text)
    finally:
        mic.close()