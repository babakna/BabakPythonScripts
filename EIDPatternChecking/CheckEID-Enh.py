import tkinter as tk
from tkinter import ttk
import re
import pyperclip

# To convert to executable
# pip install pyinstaller
# then run:   pyinstaller --onefile --windowed CheckEID-Enh.py
# When completed, the executable will be in the dist subfolder
#

class PatternCheckerGUI:
    PATTERN_DEFINITIONS = [
        {
            "name": "Samsung Pattern 1",
            "first_8_digits": "89043051",
            "digits_14_16": "000"
        },
        {
            "name": "Samsung Pattern 2",
            "first_8_digits": "89043051",
            "digits_14_16": "083"
        },
        {
            "name": "Samsung Pattern 3",
            "first_8_digits": "89033023",
            "digits_14_18": "01001"
        },
        {
            "name": "Samsung Pattern 4",
            "first_8_digits": "89033023",
            "digits_9_13": "42210",
            "digits_14_17": "0000"
        },
        {
            "name": "Pixel Pattern 1",
            "first_8_digits": "89033023",
            "digits_14_18": "90091"
        },
        {
            "name": "Motorola Pattern 1",
            "first_8_digits": "89033023",
            "digits_14_18": "90100"
        },
        {
            "name": "Motorola Pattern 2",
            "first_8_digits": "89033090",
            "digits_14_18": "90100"
        },
        {
            "name": "REVVL Pattern 1",
            "first_8_digits": "89034011",
            "digits_14_18": "90000"
        },
        {
            "name": "TCL Pattern 1",
            "first_8_digits": "89049032",
            "digits_13_18": "900913"
        }
    ]

    def __init__(self, root):
        self.root = root
        self.root.title("32-Digit EID Pattern Checker")
        self.root.geometry("900x700")

        main_frame = ttk.Frame(root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.root.style = ttk.Style()
        self.root.style.configure('Bold.TButton', font=('Arial', 12, 'bold'))

        self.input_var = tk.StringVar()
        self.input_var.trace('w', self.validate_input)

        ttk.Label(main_frame, text="Enter 32-digit EID number:",
             font=('Arial', 12)).grid(row=0, column=0, columnspan=4, sticky=tk.W, pady=(0, 5))

        self.input_field = ttk.Entry(main_frame, textvariable=self.input_var, width=50,
                               font=('Courier', 12))
        self.input_field.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 5))

        self.formatted_display = ttk.Label(main_frame, text="", font=('Courier', 10),
                                     wraplength=700)
        self.formatted_display.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 20))

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=4, pady=(0, 20))

        self.check_button = tk.Button(button_frame, text="Check Pattern",
                                 command=self.check_pattern, bg="green", fg="white",
                                 font=('Arial', 12, 'bold'), width=15)
        self.check_button.grid(row=0, column=0, padx=5)

        self.clear_button = ttk.Button(button_frame, text="Clear Input",
                                 command=self.clear_input,
                                 style='Bold.TButton', width=15)
        self.clear_button.grid(row=0, column=1, padx=5)

        self.copy_button = ttk.Button(button_frame, text="Copy Results",
                                command=self.copy_results,
                                style='Bold.TButton', width=15)
        self.copy_button.grid(row=0, column=2, padx=5)

        self.display_patterns_button = ttk.Button(button_frame, text="Display Patterns",
                                            command=self.show_patterns,
                                            style='Bold.TButton', width=15)
        self.display_patterns_button.grid(row=0, column=3, padx=5)

        self.exit_button = tk.Button(button_frame, text="Exit",
                                command=self.root.destroy, bg="red", fg="white",
                                font=('Arial', 12, 'bold'), width=15, justify='center')
        self.exit_button.grid(row=0, column=4, padx=5)

        self.result_frame = ttk.LabelFrame(main_frame, text="Results", padding="10")
        self.result_frame.grid(row=4, column=0, columnspan=4, sticky=(tk.W, tk.E))

        self.result_text = tk.Text(self.result_frame, height=12, width=70,
                             wrap=tk.WORD, font=('Arial', 11))
        self.result_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        self.result_text.config(state=tk.DISABLED)

        self.result_text.tag_configure("success", foreground="green", font=('Arial', 11, 'bold'))
        self.result_text.tag_configure("error", foreground="red", font=('Arial', 11, 'bold'))

        scrollbar = ttk.Scrollbar(self.result_frame, orient=tk.VERTICAL,
                            command=self.result_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.result_text.config(yscrollcommand=scrollbar.set)

        main_frame.columnconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        self.update_result("Enter a 32-digit EID number and click 'Check Pattern'")

    def validate_input(self, *args):
        input_text = self.input_var.get()
        cleaned_input = ''.join(filter(str.isdigit, input_text))

        if len(cleaned_input) > 32:
            cleaned_input = cleaned_input[:32]

        self.input_var.set(cleaned_input)
        self.update_formatted_display()

    def update_formatted_display(self):
        input_text = self.input_var.get()
        formatted_text = ' '.join([input_text[i:i+4] for i in range(0, len(input_text), 4)])
        self.formatted_display.config(text=formatted_text)

    def check_pattern(self):
        input_text = self.input_var.get()
        if len(input_text) != 32:
            self.update_result("Please enter a 32-digit EID number.")
            return

        results = []
        for pattern in self.PATTERN_DEFINITIONS:
            match = True
            if "first_8_digits" in pattern:
                if input_text[:8] != pattern["first_8_digits"]:
                    match = False
            if "digits_9_13" in pattern:
                if input_text[8:13] != pattern["digits_9_13"]:
                    match = False
            if "digits_14_16" in pattern:
                if input_text[13:16] != pattern["digits_14_16"]:
                    match = False
            if "digits_14_17" in pattern:
                if input_text[13:17] != pattern["digits_14_17"]:
                    match = False
            if "digits_14_18" in pattern:
                if input_text[13:18] != pattern["digits_14_18"]:
                    match = False
            if "digits_13_18" in pattern:
                if input_text[12:18] != pattern["digits_13_18"]:
                    match = False
            if match:
                results.append(f"Match found for {pattern['name']}")

        if results:
            self.update_result("\n".join(results))
        else:
            self.update_result("No matching patterns found.")

    def clear_input(self):
        self.input_var.set("")
        self.update_formatted_display()
        self.update_result("Input cleared. Enter a new 32-digit EID number.")

    def copy_results(self):
        results = self.result_text.get("1.0", tk.END).strip()
        pyperclip.copy(results)
        self.update_result("Results copied to clipboard.")

    def show_patterns(self):
        pattern_info = []
        for pattern in self.PATTERN_DEFINITIONS:
            info = f"Name: {pattern['name']}\n"
            if "first_8_digits" in pattern:
                info += f"First 8 digits: {pattern['first_8_digits']}\n"
            if "digits_9_13" in pattern:
                info += f"Digits 9-13: {pattern['digits_9_13']}\n"
            if "digits_14_16" in pattern:
                info += f"Digits 14-16: {pattern['digits_14_16']}\n"
            if "digits_14_17" in pattern:
                info += f"Digits 14-17: {pattern['digits_14_17']}\n"
            if "digits_14_18" in pattern:
                info += f"Digits 14-18: {pattern['digits_14_18']}\n"
            if "digits_13_18" in pattern:
                info += f"Digits 13-18: {pattern['digits_13_18']}\n"
            pattern_info.append(info)
        self.update_result("\n\n".join(pattern_info))

    def update_result(self, message):
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, message)
        
        if "Match found" in message:
            self.result_text.tag_add("success", "1.0", "end")
        elif message == "No matching patterns found.":
            self.result_text.tag_add("error", "1.0", "end")
        
        self.result_text.config(state=tk.DISABLED)

def main():
    root = tk.Tk()
    app = PatternCheckerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()