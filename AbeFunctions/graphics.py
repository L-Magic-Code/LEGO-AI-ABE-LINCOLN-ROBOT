import customtkinter as ctk
import time
import threading

class Graphics:
    def __init__(self, Vision, Mic, Abe=None):
        self.mic = Mic
        self.vision = Vision
        self.abe = Abe
        self.alerts = None

        ctk.set_appearance_mode("system")
        self.Window = ctk.CTk(className="Abe Control Center")
        self.Window.geometry("850x650")
        self.Window.title("Abe Control Center")
        self.Window.resizable(0, 0)


        self.status = "Starting..."
        self.mic_on = self.mic.is_on
        self.is_listening = False
        self.tracking_mode = self.vision.camera_tracking_mode

        self.status_text = ctk.CTkLabel(self.Window, text="STATUS:", font=("Arial", 30))
        self.status_text.place(x=370, y=3)

        self.alerts_text = ctk.CTkLabel(self.Window, text="Alerts:   ", font=("Nimbus Sans Narrow", 27))
        self.alerts_text.place(x=500, y=40)

        self.tracking_mode_text = ctk.CTkLabel(self.Window, text=f"Tracking mode:   {self.tracking_mode}", font=("Nimbus Sans Narrow", 27))
        self.tracking_mode_text.place(x=12, y=40)

        self.listening_text = ctk.CTkLabel(self.Window, text=f"Listening:    {self.is_listening}", font=("Nimbus Sans Narrow", 27))
        self.listening_text.place(x=12, y=80)

        self.mic_on_text = ctk.CTkLabel(self.Window, text=f"Mic on:   {self.mic_on}", font=("Nimbus Sans Narrow", 27))
        self.mic_on_text.place(x=12, y=120)


        self.control_text = ctk.CTkLabel(self.Window, text="CONTROL:", font=("Arial", 30))
        self.control_text.place(x=368, y=225)

        self.input_box_text = ""
        self.chat_box = ctk.CTkTextbox(self.Window, 400, 150, corner_radius=10, state='disabled')
        self.chat_box.place(x=260, y=275)

        self.input_box = ctk.CTkEntry(self.Window, 300, 45, corner_radius=10, state='normal')
        self.input_box.place(x=260, y=450)
        self.input_box.bind("<Return>", self._update_input)


    def Update_Loop(self):
        while True:
            self.mic_is_on = self.mic.is_on
            self.tracking_mode = self.vision.camera_tracking_mode

            self.alerts_text.configure(text=f"Alerts:     {self.alerts}")
            self.mic_on_text.configure(text=f"Mic On:    {self.mic_is_on}")
            self.tracking_mode_text.configure(text=f"Tracking mode:   {self.tracking_mode}")
            self.listening_text.configure(text=f"Listening:   {self.is_listening}")
            time.sleep(0.2)

    def _update_input(self, event=None):
        self.input_box_text = self.input_box.get()
        self.input_box.delete(0, 'end')

    def get_input(self):
        ret = self.input_box_text
        self.input_box_text = ''
        return ret

    def print_in_box(self, text):
        self.chat_box.configure(state="normal")
        self.chat_box.insert('end', text + '\n')
        self.chat_box.see("end")
        self.chat_box.configure(state="disabled")

    def main(self):
        threading.Thread(target=self.Update_Loop).start()
        self.Window.mainloop()