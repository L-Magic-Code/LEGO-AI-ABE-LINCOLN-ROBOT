import time
import threading
import random
from datetime import datetime

datetime_dict = {
    1: "Monday",
    2 : "Tuesday",
    3 : "Wednesday",
    4:  "Thursday",
    5  : "Friday",
    6 : "Saturday",
    7 : "Sunday"

}

def pass_functions(abe, vision):
    global Abe
    global Vision
    Abe = abe
    Vision = vision

def _cool_print(text, print_time, delay):
    r"""
    Prints 'text' from left to right over 'print_time'.

    Not designed for \r or \n.
    """
    time.sleep(delay)
    if text == '':
        print("")
        return
    
    sleep_time = print_time / len(text)
    for letter in text:
        print(letter, end='')
        time.sleep(sleep_time)
    print()

def cool_print(text : str, print_time : int=1, thread : bool=False, delay : float=0):
    r"""
    Prints 'text' from left to right over 'print_time'.
    If thread is True, it will start it as a thread, otherwise it will block.

    Not designed for \r or \n.
    """
    if thread:
        threading.Thread(target=_cool_print, args=[text, print_time, delay]).start()
    else:
        _cool_print(text=text, print_time=print_time, delay=delay)

def print_red(text):
    print("\033[0;31m" + str(text) + "\033[0m")

def get_date_and_time():
    """
    Returns:
      year, month, day, date, and time as str.
    """
    print("[extra_functions] Called get_date_and_time() function!")
    return str(f"Today is {datetime.now()}. It is a {datetime_dict[datetime.isoweekday(datetime.now())]}.")



def rock_paper_scissors() -> str:
    """
    Plays a game of rock paper scissors with the user. Returns the result as a string.
    """
    print("[extra_functions] Starting a game of rock paper scissors!")
    choice = random.choice(["rock", "paper", "scissors"])
    Vision.camera_tracking_mode = 'right hand'
    Abe.say("Ready? Rock, paper, scissors, shoot!")
    while True:
        users_hand = Vision.Hand
        if users_hand is None:
            continue
        users_choice = Vision.hand_tracking.fingersUp(users_hand)
        if users_choice in [[0,1,1,1,1], [1,0,0,0,0], [1,1,1,0,0]]:
            if users_choice == [0,1,1,1,1]:
                users_choice = 'paper'
            elif users_choice == [1,0,0,0,0]:
                users_choice = 'rock'
            elif users_choice == [1, 1, 1, 0, 0]:
                users_choice = 'scissors'
            break
    print(f"[extra_functions] User chose {users_choice}, Abe chose {choice}.")

    Abe.move_hand_rps(choice, 'right')
    Vision.camera_tracking_mode = 'face'


    if (users_choice, choice) in [('paper', 'paper'), ('rock', 'rock'), ('scissors', 'scissors')]:
        ret = f'The round is over. Both of you chose {choice}, which means that you tied.'
    elif (users_choice, choice) in [('rock', 'paper'), ('paper', 'scissors'), ('scissors', 'rock')]:
        ret = f'The round is over. You chose {choice}, and the user chose {users_choice}, which means that you won.'
    elif (users_choice, choice) in [('paper', 'rock'), ('scissors', 'paper'), ('rock', 'scissors')]:
        ret = f'The round is over. You chose {choice}, and the user chose {users_choice}, which means that you lost.'
    return ret

if __name__ == '__main__':
    print_red(get_date_and_time())
