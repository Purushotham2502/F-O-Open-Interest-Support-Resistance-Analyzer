import tkinter as tk
from tkinter import messagebox
import subprocess

def run_option_chain_script():
    try:
        # Replace the path below with the full path to your script if needed
        subprocess.run(["python", "OI_Support&Resistance.py"], check=True)
        messagebox.showinfo("Success", "Script executed and Excel updated successfully.")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"Script execution failed.\n\n{e}")
    except Exception as e:
        messagebox.showerror("Error", f"Unexpected error:\n\n{e}")

root = tk.Tk()
root.title("Run Option Chain Script")
root.geometry("300x150")

run_button = tk.Button(root, text="Run Option Chain Script", command=run_option_chain_script, height=3, width=25)
run_button.pack(pady=40)

root.mainloop()
