def main():
    from AbeFunctions import ev3_functions
    from AbeFunctions import vision_functons
    from AbeFunctions import gemini_functions
    from AbeFunctions import mic_functions
    from AbeFunctions import extra_functions
    from AbeFunctions import graphics
    import time
    import json
    import pathlib
    import sys
    import threading

    BASE_DIR = pathlib.Path(__file__).resolve().parent

    with open(BASE_DIR / "External_Files" / "Config" / "mic_config.json", "r",  encoding="utf-8") as opened_file:
        config = json.load(opened_file)

    with open(BASE_DIR / "External_Files" / "Config" / "ev3_config.json", "r",  encoding="utf-8") as opened_file:
        ev3_config = json.load(opened_file)

    USE_MINDSTORMS = ev3_config["use_mindstorms"]
    USE_MIC = config["use_mic"]

    abe = ev3_functions.Abe(USE_MINDSTORMS)
    vision = vision_functons.Vision(abe, USE_MINDSTORMS, debug_level=2)
    vision.start_camera_windows_loop(thread=True)
    extra_functions.pass_functions(abe, vision)
    gemini = gemini_functions.AI([
        extra_functions.rock_paper_scissors, 
        extra_functions.get_date_and_time, 
        abe.clap,
        vision.look_at_hand,
        vision.look_at_face,
        abe.open_chest,
        abe.close_chest,
        abe.deliver_gettysburg_address,
        abe.wave])
    
    
    mic = mic_functions.Mic(USE_MIC, debug_level=2)
    window = graphics.Graphics(vision, mic, abe)

    if USE_MINDSTORMS:
        print("[main] Waiting for key to be inserted...")
        abe.wait_for_key_insert()
    print("[main] Starting...")
    if USE_MIC:
        mic.start_listening()
    abe.home_motors()

    time.sleep(1)
    def _main_loop():
        while True:
            window.is_listening = False
            if USE_MIC:
                print("[main] Say \"Hey Abraham Lincoln\" to start talking to Abe!")
                mic.wait_for_trigger_word(config["listen-trigger-words"])
                print("[main] Abe is listening!")
                window.is_listening = True
            timer = time.time()
            while True:
                if time.time() - timer >= config["listening-timeout"] and USE_MIC:
                    print("[main] Stopped listening!")
                    break 
                if USE_MIC:
                    prompt = mic.get_speech()
                else:
                    time.sleep(.2)
                    prompt = window.get_input()

                if prompt.lower() in ['shutdown', 'shut down']:
                    gemini.close()
                    vision.close()
                    sys.exit()
            
                if len(prompt.split()) < 3 and USE_MIC or prompt == '':
                    continue
                if USE_MIC:
                    mic.listen = False
                if USE_MIC:
                    print(f"[main] You: {prompt}")
                window.print_in_box(f"You: {prompt}")

                image = vision.get_gemini_img()
                emotion,  response = gemini.get_response(prompt, image)
                if emotion is None or response is None:
                    continue
                print(f"[main] Abe: {response}")
                abe.move_to_emotion(emotion)
                window.print_in_box("Abe: " + response)
                abe.say(response)
                abe.move_to_neutral()
                timer = time.time()
                if USE_MIC:
                    mic.listen = True 
    try:
        threading.Thread(target=_main_loop).start()
    except KeyboardInterrupt:
        pass
    window.main()
    gemini.close()
    vision.close()
    sys.exit()

if __name__ == '__main__':
    main()