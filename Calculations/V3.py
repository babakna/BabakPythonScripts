import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import numpy as np
import threading
import time

class ETFOptimizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ETF Allocation Optimizer")
        self.root.geometry("800x800")
        self.root.resizable(True, True)
        
        self.stop_flag = threading.Event()
        self.calculation_thread = None
        
        # Use default styling to ensure button text is visible
        self.create_widgets()
        
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Total budget frame
        budget_frame = ttk.Frame(main_frame, padding="5")
        budget_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(budget_frame, text="Total Budget ($):", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        self.budget_entry = ttk.Entry(budget_frame, width=15)
        self.budget_entry.pack(side=tk.LEFT, padx=5)
        self.budget_entry.insert(0, "8000")
        
        # Input section frame
        input_frame = ttk.LabelFrame(main_frame, text="ETF Entries", padding="10")
        input_frame.pack(fill=tk.BOTH, pady=10)
        
        # Column headers
        header_frame = ttk.Frame(input_frame)
        header_frame.pack(fill=tk.X)
        
        headers = ["#", "Symbol", "Target ($)", "Price ($)", "Initial Shares Estimate"]
        widths = [3, 10, 12, 12, 20]
        
        for i, header in enumerate(headers):
            ttk.Label(header_frame, text=header, font=("Arial", 10, "bold"), width=widths[i]).grid(row=0, column=i, padx=5)
        
        # Input rows frame with scrolling capability
        self.rows_canvas = tk.Canvas(input_frame)
        scrollbar = ttk.Scrollbar(input_frame, orient="vertical", command=self.rows_canvas.yview)
        self.rows_frame = ttk.Frame(self.rows_canvas)
        
        self.rows_canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.rows_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.rows_canvas_window = self.rows_canvas.create_window((0, 0), window=self.rows_frame, anchor="nw")
        
        self.rows_canvas.bind('<Configure>', self.on_canvas_configure)
        self.rows_frame.bind('<Configure>', self.on_frame_configure)
        
        # Create entry rows
        self.symbol_entries = []
        self.target_entries = []
        self.price_entries = []
        self.initial_shares_entries = []
        
        for i in range(10):  # Create 10 rows
            ttk.Label(self.rows_frame, text=f"{i+1}", width=3).grid(row=i, column=0, padx=5, pady=2)
            
            symbol_entry = ttk.Entry(self.rows_frame, width=widths[1])
            symbol_entry.grid(row=i, column=1, padx=5, pady=2)
            self.symbol_entries.append(symbol_entry)
            
            target_entry = ttk.Entry(self.rows_frame, width=widths[2])
            target_entry.grid(row=i, column=2, padx=5, pady=2)
            self.target_entries.append(target_entry)
            
            price_entry = ttk.Entry(self.rows_frame, width=widths[3])
            price_entry.grid(row=i, column=3, padx=5, pady=2)
            self.price_entries.append(price_entry)
            
            initial_shares_entry = ttk.Entry(self.rows_frame, width=widths[4])
            initial_shares_entry.grid(row=i, column=4, padx=5, pady=2)
            self.initial_shares_entries.append(initial_shares_entry)
        
        # Add example data to first 5 rows
        example_data = [
            ("VGT", "1000", "625", ""),
            ("QQQM", "1000", "216", ""),
            ("SCHD", "1000", "28", ""),
            ("JEPI", "2500", "59", ""),
            ("JEPQ", "2500", "57", "")
        ]
        
        for i, (symbol, target, price, shares) in enumerate(example_data):
            self.symbol_entries[i].insert(0, symbol)
            self.target_entries[i].insert(0, target)
            self.price_entries[i].insert(0, price)
            self.initial_shares_entries[i].insert(0, shares)
        
        # Results display
        results_frame = ttk.LabelFrame(main_frame, text="Optimization Results", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.results_text = scrolledtext.ScrolledText(results_frame, wrap=tk.WORD, width=80, height=15)
        self.results_text.pack(fill=tk.BOTH, expand=True)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=5)
        
        # Buttons - Using tk.Button instead of ttk.Button for better visibility
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # Using standard tk.Button with explicit width for better visibility
        self.run_button = tk.Button(button_frame, text="Run Simulation", 
                                   command=self.start_simulation,
                                   width=15, height=2, 
                                   bg="#e1e1e1", fg="black")
        self.run_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = tk.Button(button_frame, text="Stop", 
                                    command=self.stop_simulation,
                                    width=15, height=2, 
                                    bg="#e1e1e1", fg="black",
                                    state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        self.clear_button = tk.Button(button_frame, text="Clear Entries", 
                                     command=self.clear_entries,
                                     width=15, height=2, 
                                     bg="#e1e1e1", fg="black")
        self.clear_button.pack(side=tk.LEFT, padx=5)
        
        self.exit_button = tk.Button(button_frame, text="Exit", 
                                    command=self.exit_application,
                                    width=15, height=2, 
                                    bg="#e1e1e1", fg="black")
        self.exit_button.pack(side=tk.RIGHT, padx=5)
    
    def on_canvas_configure(self, event):
        """Adjust the canvas window width when canvas is resized"""
        self.rows_canvas.itemconfig(self.rows_canvas_window, width=event.width)
    
    def on_frame_configure(self, event):
        """Update the scroll region when the rows frame changes size"""
        self.rows_canvas.configure(scrollregion=self.rows_canvas.bbox("all"))
    
    def validate_inputs(self):
        """Validate inputs and return ETF data if valid"""
        try:
            budget = float(self.budget_entry.get())
            if budget <= 0:
                raise ValueError("Budget must be a positive number")
        except ValueError as e:
            messagebox.showerror("Input Error", f"Invalid budget: {str(e)}")
            return None
        
        etfs = []
        targets = []
        prices = []
        initial_shares = []
        
        for i in range(10):
            symbol = self.symbol_entries[i].get().strip()
            if not symbol:
                continue  # Skip empty rows
            
            try:
                target = self.target_entries[i].get().strip()
                if not target:
                    messagebox.showerror("Input Error", f"Missing target value for ETF #{i+1}")
                    return None
                target = float(target)
                if target <= 0:
                    raise ValueError(f"Target for {symbol} must be positive")
                
                price = self.price_entries[i].get().strip()
                if not price:
                    messagebox.showerror("Input Error", f"Missing price value for ETF #{i+1}")
                    return None
                price = float(price)
                if price <= 0:
                    raise ValueError(f"Price for {symbol} must be positive")
                
                # Initial shares is optional
                init_shares_str = self.initial_shares_entries[i].get().strip()
                if init_shares_str:
                    init_shares = int(float(init_shares_str))
                    if init_shares < 0:
                        raise ValueError(f"Initial shares for {symbol} cannot be negative")
                else:
                    init_shares = None
                
                etfs.append(symbol)
                targets.append(target)
                prices.append(price)
                initial_shares.append(init_shares)
                
            except ValueError as e:
                messagebox.showerror("Input Error", f"Invalid value for ETF #{i+1} ({symbol}): {str(e)}")
                return None
        
        if not etfs:
            messagebox.showerror("Input Error", "At least one ETF must be defined")
            return None
        
        return {
            "budget": budget,
            "etfs": etfs,
            "targets": targets,
            "prices": prices,
            "initial_shares": initial_shares
        }
    
    def optimize_allocation(self, data):
        """Optimize ETF allocation based on input data"""
        self.status_var.set("Optimizing allocation...")
        self.root.update_idletasks()
        
        etfs = data["etfs"]
        targets = data["targets"]
        prices = data["prices"]
        total_budget = data["budget"]
        initial_shares_input = data["initial_shares"]
        
        # Check for stop request periodically
        if self.stop_flag.is_set():
            return "Optimization stopped by user."
        
        # Function to calculate allocation metrics
        def calculate_allocation_metrics(shares):
            actual_investments = [shares[i] * prices[i] for i in range(len(etfs))]
            total_invested = sum(actual_investments)
            remainder = total_budget - total_invested
            
            # Calculate target percentages and actual percentages
            target_percentages = [t/sum(targets)*100 for t in targets]
            actual_percentages = [a/total_invested*100 for a in actual_investments]
            
            # Calculate deviation from target percentages
            percentage_deviations = [abs(actual_percentages[i] - target_percentages[i]) for i in range(len(etfs))]
            total_deviation = sum(percentage_deviations)
            
            return actual_investments, total_invested, remainder, actual_percentages, total_deviation
        
        # Initial allocation - use provided initial shares or calculate
        initial_shares = []
        for i in range(len(etfs)):
            if initial_shares_input[i] is not None:
                initial_shares.append(initial_shares_input[i])
            else:
                initial_shares.append(int(targets[i] / prices[i]))
        
        # Calculate initial metrics
        initial_metrics = calculate_allocation_metrics(initial_shares)
        
        # Optimization approach: Add shares one by one to minimize remainder
        current_shares = initial_shares.copy()
        current_metrics = initial_metrics
        
        iteration = 0
        max_iterations = 1000  # Safety limit
        
        # Keep adding shares until we can't add more without exceeding budget
        while iteration < max_iterations:
            iteration += 1
            
            # Check for stop request
            if self.stop_flag.is_set():
                return "Optimization stopped by user."
            
            # Update status every few iterations
            if iteration % 10 == 0:
                self.status_var.set(f"Optimizing allocation... Iteration {iteration}")
                self.root.update_idletasks()
                time.sleep(0.01)  # Small delay to allow UI updates
            
            best_deviation = float('inf')
            best_idx = -1
            best_metrics = None
            
            # Try adding one share to each ETF and see which gives best result
            for i in range(len(etfs)):
                test_shares = current_shares.copy()
                test_shares[i] += 1
                test_metrics = calculate_allocation_metrics(test_shares)
                
                # Check if this allocation is within budget and improves deviation
                if test_metrics[2] >= 0 and test_metrics[4] < best_deviation:
                    best_deviation = test_metrics[4]
                    best_idx = i
                    best_metrics = test_metrics
            
            # If no improvement found, break
            if best_idx == -1:
                break
            
            # Update current shares and metrics
            current_shares[best_idx] += 1
            current_metrics = best_metrics
        
        # Generate results
        actual_investments = current_metrics[0]
        total_invested = current_metrics[1]
        remainder = current_metrics[2]
        actual_percentages = current_metrics[3]
        target_percentages = [t/sum(targets)*100 for t in targets]
        
        result = f"Optimization Results (Budget: ${total_budget:.2f})\n"
        result += f"\n{'ETF':<6} {'Target($)':<10} {'Price($)':<10} {'Shares':<8} {'Actual($)':<12} {'Target%':<10} {'Actual%':<10}\n"
        result += "-" * 70 + "\n"
        
        for i in range(len(etfs)):
            result += f"{etfs[i]:<6} ${targets[i]:<9.2f} ${prices[i]:<9.2f} {current_shares[i]:<8} ${actual_investments[i]:<11.2f} {target_percentages[i]:<9.2f}% {actual_percentages[i]:<9.2f}%\n"
        
        result += "-" * 70 + "\n"
        result += f"Total Invested: ${total_invested:.2f}\n"
        result += f"Remainder: ${remainder:.2f}\n"
        result += f"Total Percentage Deviation: {current_metrics[4]:.2f}%\n"
        
        return result
    
    def start_simulation(self):
        """Start the optimization process in a separate thread"""
        # Validate inputs first
        data = self.validate_inputs()
        if not data:
            return
        
        # Reset stop flag
        self.stop_flag.clear()
        
        # Clear results and update UI
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, "Optimization in progress...\n")
        self.run_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_var.set("Starting optimization...")
        
        # Start optimization in a separate thread
        self.calculation_thread = threading.Thread(target=self.run_optimization, args=(data,))
        self.calculation_thread.daemon = True
        self.calculation_thread.start()
    
    def run_optimization(self, data):
        """Run optimization in background thread"""
        try:
            result = self.optimize_allocation(data)
            
            # Update UI in the main thread
            self.root.after(0, self.update_results, result)
        except Exception as e:
            # Handle unexpected errors
            error_msg = f"Error during optimization: {str(e)}"
            self.root.after(0, self.update_results, error_msg)
    
    def update_results(self, result):
        """Update results in the UI (called from main thread)"""
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, result)
        self.run_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_var.set("Optimization complete")
    
    def stop_simulation(self):
        """Stop the running simulation"""
        self.stop_flag.set()
        self.status_var.set("Stopping optimization...")
        self.stop_button.config(state=tk.DISABLED)
    
    def clear_entries(self):
        """Clear all entry fields"""
        self.budget_entry.delete(0, tk.END)
        self.budget_entry.insert(0, "8000")
        
        for i in range(10):
            self.symbol_entries[i].delete(0, tk.END)
            self.target_entries[i].delete(0, tk.END)
            self.price_entries[i].delete(0, tk.END)
            self.initial_shares_entries[i].delete(0, tk.END)
        
        self.results_text.delete(1.0, tk.END)
        self.status_var.set("Entries cleared")
    
    def exit_application(self):
        """Exit the application gracefully"""
        if self.calculation_thread and self.calculation_thread.is_alive():
            # If calculation is running, ask for confirmation
            if messagebox.askyesno("Confirm Exit", "Calculation is still running. Are you sure you want to exit?"):
                self.stop_flag.set()
                self.root.destroy()
        else:
            self.root.destroy()

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = ETFOptimizerApp(root)
        root.protocol("WM_DELETE_WINDOW", app.exit_application)  # Handle window close
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Critical Error", f"An unexpected error occurred: {str(e)}")