import tkinter as tk
from tkinter import messagebox
import paho.mqtt.client as mqtt
import json
import time
import collections 
import csv

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
plt.style.use('ggplot') 

# --- Configuration ---
MQTT_BROKER = "127.0.0.1" 
MQTT_PORT = 1883
DATA_TOPIC = "conveyor/data"     
CONTROL_TOPIC = "conveyor/control" 
CONFIG_TOPIC_TEMP = "conveyor/config/temp_threshold" 
CONFIG_TOPIC_VIB = "conveyor/config/vib_threshold" 
CLIENT_ID = f'digital_twin_gui_{time.time()}' 
TEMP_THRESHOLD = 30.0 
VIB_THRESHOLD = 120.0 

# --- Thread-Safe Update Helper (FIX for 'main thread is not in main loop') ---
# --- Thread-Safe Update Helper (FINAL FIX for stability) ---
# --- Thread-Safe Update Helper (FIXED SYNTAX & FINAL STABILITY WRAPPER) ---
def _process_mqtt_update(app, temp, vib, item, message, color):
    """Safely updates GUI and data history on the main Tkinter thread."""
    try:
        # 1. Update data history (Phase 4)
        app.temp_history.append(temp)
        app.vib_history.append(vib)
        app.time_history.append(time.time() % 1000)
        
        # 2. Update Basic Labels (Phase 3)
        app.current_temp_var.set(f"{temp:.1f} °C")
        app.current_vib_var.set(f"{vib:.1f} Units")
        
        item_text = "📦 ITEM DETECTED" if item else "Clear"
        app.item_detected_var.set(item_text)
        
        # --- PHASE 6: Calculate and Display Health Score ---
        health_score, health_color = app.calculate_health_score(temp, vib)
        app.health_score_var.set(f"{health_score:.1f}%")
        app.health_score_label.config(fg=health_color) 
        
        # --- PHASE 6: Dynamic Status Messages (Based on Health Score) ---
        if health_score < 30:
            status_message = "🛑 CRITICAL: Immediate Inspection Required!"
            status_color = "red"
        elif health_score < 70:
            status_message = "⚠️ WARNING: Performance Degradation Detected."
            status_color = "orange"
        else:
            status_message = "Normal Operation (Health: Excellent)"
            status_color = "green"
        
        app.status_message_var.set(status_message)
        app.status_message_label.config(fg=status_color)
        
        # Note: The 'message' and 'color' arguments passed in from on_message 
        # are now overwritten by the Phase 6 calculated status/color.
        # --- PHASE 7: Item Tracking Logic (Rising Edge) ---
        if item and not app.item_detected_previous:
            app.items_processed_count += 1
            app.items_processed_var.set(str(app.items_processed_count))
            log_event = "Item Processed"
        elif item:
            log_event = "Item Present"
        else:
            log_event = "Data Update"
            
        app.item_detected_previous = item
        
        # 3. Update Status Variables (Health Score, Status Message, etc.)
        # ... (Keep Phase 6 logic: health_score, status_message, status_color) ...

        # --- PHASE 7: Data Logging Logic ---
        app._log_data_to_csv(temp, vib, health_score, status_message, item, log_event)
            
        # ... (Keep final exception block) ...
        pass   
    except Exception as e:
        # Final stability wrapper to prevent background thread crashes.
        # This catches errors that occur when widgets are still initializing.
        pass



def on_connect(client, userdata, flags, rc, properties):
    """Callback function when the client connects to the MQTT broker."""
    if rc == 0:
        print(f"✅ MQTT Client Connected successfully to {MQTT_BROKER}")
        client.subscribe(DATA_TOPIC)
        print(f"✅ Subscribed to topic: {DATA_TOPIC}")
    else:
        print(f"❌ Connection failed with result code {rc}")

def on_message(client, userdata, msg):
    """Callback function when a message is received from the subscribed topic."""
    
    app = userdata['app'] 
    payload = msg.payload.decode()
    
    try:
        data = json.loads(payload)
        
        temp = data.get("temp", 0.0)
        vib = data.get("vib", 0.0)
        item = data.get("item", False)
        
        # Determine status message and color
        if temp > TEMP_THRESHOLD or vib > VIB_THRESHOLD:
            message = "⚠️ WARNING: Check Machine"
            color = "red"
        else:
            message = "Normal Operation"
            color = "green"
            
        # CRITICAL FIX: Schedule the GUI update function on the main thread
        app.master.after(0, 
            lambda: _process_mqtt_update(app, temp, vib, item, message, color)
        )
        
    except json.JSONDecodeError:
        print(f"⚠️ Error parsing JSON payload: {payload}")
    except Exception as e:
        print(f"An unexpected error occurred in on_message: {e}") 

# --- GUI Application Class ---

class DigitalTwinApp:
    def __init__(self, master):
        self.master = master
        master.title("Conveyor Belt Digital Twin (Phase 5: Control)")
        master.geometry("1000x700") 
        master.resizable(False, False) 

        # --- Phase 4/5 Variables ---
        self.max_data_points = 100
        self.time_history = collections.deque(maxlen=self.max_data_points)
        self.temp_history = collections.deque(maxlen=self.max_data_points)
        self.vib_history = collections.deque(maxlen=self.max_data_points)
        
        self.is_running = True 
        self.item_position = -50  
        self.item_id = None       
        self.belt_id = []         
        self.belt_offset = 0      
        self.animation_delay_ms = 50 

        # --- Phase 3: Define tk.StringVar Instances Inside the Class ---
        self.current_temp_var = tk.StringVar(value="-- °C")
        self.current_vib_var = tk.StringVar(value="-- Units")
        self.item_detected_var = tk.StringVar(value="Waiting...")
        self.health_score_var = tk.StringVar(value="N/A")
        self.status_message_var = tk.StringVar(value="System Initializing...")
        self.conveyor_speed_var = tk.StringVar(value="100") 
        
        self.temp_threshold_var = tk.StringVar(value=f"{TEMP_THRESHOLD:.1f}")
        self.vib_threshold_var = tk.StringVar(value=f"{VIB_THRESHOLD:.1f}")

        # --- Phase 1: MQTT Initialization ---
        self.client = mqtt.Client(
            client_id=CLIENT_ID, 
            userdata={'app': self},
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2 
        )
        self.client.on_connect = on_connect
        self.client.on_message = on_message
        
        try:
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start() 
        except Exception as e:
            messagebox.showerror("MQTT Connection Error", f"Could not connect to broker: {e}")
            self.master.destroy()
            return
            
        # --- UI Setup and Animation Start ---
        self._setup_main_layout(master)
        self._animate_conveyor()
        self._update_graphs() 
        
        master.protocol("WM_DELETE_WINDOW", self.on_closing)

    # --- PHASE 5: Control Methods (Functionality remains the same) ---
    def toggle_run_pause(self):
        """5.1 'Run/Pause' Toggle: Publishes RUN or PAUSE command."""
        command = "PAUSE" if self.is_running else "RUN"
        
        try:
            self.client.publish(CONTROL_TOPIC, command)
            print(f"➡️ Published Control: {command}")
        except Exception as e:
            print(f"❌ Error publishing control command: {e}")

    def send_speed_command(self, *args):
        """5.2 Conveyor Speed Slider/Input: Publishes new speed via MQTT."""
        try:
            speed_val = int(self.conveyor_speed_var.get())
            if 0 <= speed_val <= 255:
                payload = json.dumps({"cmd": "speed", "value": speed_val})
                self.client.publish(CONTROL_TOPIC, payload)
                print(f"➡️ Published Speed: {speed_val}")
            else:
                messagebox.showerror("Invalid Input", "Speed must be between 0 and 255.")
        except ValueError:
             messagebox.showerror("Invalid Input", "Speed must be an integer.")
        except Exception as e:
            print(f"❌ Error publishing speed command: {e}")

    # No need for this function right now as it's not fully implemented to handle
    # external status yet, and the simpler logic avoids the initial crash.
    # def update_run_pause_button(self, status): 
    #     """Updates the button's text and color based on the actual status (from on_message)."""
    #     self.is_running = (status == "RUN")
        
    #     if self.is_running:
    #         self.run_pause_button.config(text="▶️ RUNNING", bg="#AADDAA", fg="black")
    #     else:
    #         self.run_pause_button.config(text="⏸️ PAUSED", bg="#EEAAAA", fg="black")

    def publish_threshold(self, threshold_type):
        """5.3 Threshold Configuration: Publishes new threshold values."""
        try:
            if threshold_type == 'temp':
                new_threshold = float(self.temp_threshold_var.get())
                topic = CONFIG_TOPIC_TEMP
                global TEMP_THRESHOLD
                TEMP_THRESHOLD = new_threshold
            else: # 'vib'
                new_threshold = float(self.vib_threshold_var.get())
                topic = CONFIG_TOPIC_VIB
                global VIB_THRESHOLD
                VIB_THRESHOLD = new_threshold
                
            payload = json.dumps({"value": new_threshold})
            self.client.publish(topic, payload)
            print(f"➡️ Published {threshold_type.upper()} Threshold: {new_threshold}")

        except ValueError:
            messagebox.showerror("Invalid Input", f"{threshold_type.capitalize()} threshold must be a number.")
        except Exception as e:
            print(f"❌ Error publishing threshold: {e}")


    # --- UI Setup Methods (The FIX is here!) ---

    def _setup_main_layout(self, master):
        """Creates the main two-panel grid layout."""
        master.columnconfigure(0, weight=1) 
        master.columnconfigure(1, weight=1) 
        master.rowconfigure(0, weight=1)    
        
        self.left_frame = tk.Frame(master, padx=10, pady=10, bg="#F0F0F0")
        self.left_frame.grid(row=0, column=0, sticky="nsew")
        self.left_frame.columnconfigure(0, weight=1)
        
        self.right_frame = tk.Frame(master, padx=10, pady=10, bg="#E0E0E0")
        self.right_frame.grid(row=0, column=1, sticky="nsew")
        self.right_frame.columnconfigure(0, weight=1)

        self._setup_health_status(self.left_frame)
        self._setup_animation_area(self.left_frame)
        self._setup_graphs(self.left_frame) 
        self._setup_controls_area(self.right_frame)
        self._setup_item_tracking(self.right_frame)

    def _setup_health_status(self, parent_frame):
        """Creates the static layout for the Machine Health Status section."""
        
        health_frame = tk.LabelFrame(parent_frame, text="Machine Health Status", padx=10, pady=10)
        health_frame.grid(row=0, column=0, sticky="ew", pady=5)
        health_frame.columnconfigure((0, 1), weight=1) 

        tk.Label(health_frame, text="Current Temperature:", anchor="w").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        tk.Label(health_frame, text="Current Vibration:", anchor="w").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        tk.Label(health_frame, text="Overall Health Score:", anchor="w", font=("Arial", 10, "bold")).grid(row=2, column=0, padx=5, pady=5, sticky="w")
        tk.Label(health_frame, text="Status Messages:", anchor="w", font=("Arial", 10, "bold")).grid(row=3, column=0, padx=5, pady=5, sticky="w")

        tk.Label(health_frame, textvariable=self.current_temp_var, fg="blue", font=("Arial", 10, "bold")).grid(row=0, column=1, padx=5, pady=2, sticky="e")
        tk.Label(health_frame, textvariable=self.current_vib_var, fg="blue", font=("Arial", 10, "bold")).grid(row=1, column=1, padx=5, pady=2, sticky="e")
        tk.Label(health_frame, textvariable=self.health_score_var, fg="green", font=("Arial", 12, "bold")).grid(row=2, column=1, padx=5, pady=5, sticky="e")
        
        # *** FIX APPLIED HERE: The Label is created and saved to self.status_message_label ***
        self.status_message_label = tk.Label(health_frame, textvariable=self.status_message_var, fg="black", font=("Arial", 10, "italic"))
        self.status_message_label.grid(row=4, column=0, columnspan=2, padx=5, pady=5)


    def _setup_animation_area(self, parent_frame):
        """Creates the static layout for the Conveyor Animation section."""
        
        animation_frame = tk.LabelFrame(parent_frame, text="Conveyor Animation Area", padx=10, pady=5)
        animation_frame.grid(row=1, column=0, sticky="ew", pady=5)
        
        self.conveyor_canvas = tk.Canvas(animation_frame, width=450, height=150, bg="#CCCCCC") 
        self.conveyor_canvas.pack(padx=5, pady=5, fill="both", expand=True)
        

    def _setup_graphs(self, parent_frame):
        """4.2 Real-time Graphs: Creates Matplotlib figures and embeds them in the GUI."""
        
        graph_frame = tk.LabelFrame(parent_frame, text="Real-time Sensor Graphs", padx=5, pady=5)
        graph_frame.grid(row=2, column=0, sticky="ew", pady=5)
        graph_frame.columnconfigure((0, 1), weight=1)

        self.fig_temp, self.ax_temp = plt.subplots(figsize=(4, 2.5), dpi=90)
        self.ax_temp.set_title("Temperature (°C)", fontsize=8)
        self.ax_temp.set_xticks([]) 
        self.ax_temp.set_ylim(20, 40) 
        self.canvas_temp = FigureCanvasTkAgg(self.fig_temp, master=graph_frame)
        self.canvas_widget_temp = self.canvas_temp.get_tk_widget()
        self.canvas_widget_temp.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self.fig_vib, self.ax_vib = plt.subplots(figsize=(4, 2.5), dpi=90)
        self.ax_vib.set_title("Vibration (Units)", fontsize=8)
        self.ax_vib.set_xticks([])
        self.ax_vib.set_ylim(80, 150)
        self.canvas_vib = FigureCanvasTkAgg(self.fig_vib, master=graph_frame)
        self.canvas_widget_vib = self.canvas_vib.get_tk_widget()
        self.canvas_widget_vib.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

        plt.tight_layout() 
        plt.close('all') 


    def _setup_controls_area(self, parent_frame):
        """Creates the static layout for the Controls & Settings section."""
        
        control_frame = tk.LabelFrame(parent_frame, text="Controls & Configuration", padx=10, pady=10)
        control_frame.grid(row=0, column=0, sticky="ew", pady=5)
        control_frame.columnconfigure((0, 1), weight=1) 

        # 5.1 Run/Pause Toggle (Functional)
        self.run_pause_button = tk.Button(control_frame, text="▶️ RUNNING", command=self.toggle_run_pause, bg="#AADDAA", fg="black")
        self.run_pause_button.grid(row=0, column=0, columnspan=2, pady=10, sticky="ew")

        # 5.2 Conveyor Speed (Functional)
        tk.Label(control_frame, text="Conveyor Speed (0-255):", anchor="w").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        speed_entry = tk.Entry(control_frame, textvariable=self.conveyor_speed_var, width=10)
        speed_entry.grid(row=1, column=1, padx=5, pady=5, sticky="e")
        speed_entry.bind('<Return>', self.send_speed_command)
        
        tk.Button(control_frame, text="Set Speed", command=self.send_speed_command, width=10).grid(row=2, column=1, padx=5, pady=5, sticky="e")
        
        # 5.3 Threshold Configuration (Functional)
        tk.Label(control_frame, text="Temp Threshold (°C):", anchor="w").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        temp_entry = tk.Entry(control_frame, textvariable=self.temp_threshold_var, width=10)
        temp_entry.grid(row=3, column=1, padx=5, pady=5, sticky="e")
        temp_entry.bind('<Return>', lambda e: self.publish_threshold('temp'))
        
        tk.Label(control_frame, text="Vib Threshold (Units):", anchor="w").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        vib_entry = tk.Entry(control_frame, textvariable=self.vib_threshold_var, width=10)
        vib_entry.grid(row=4, column=1, padx=5, pady=5, sticky="e")
        vib_entry.bind('<Return>', lambda e: self.publish_threshold('vib'))


    def _setup_item_tracking(self, parent_frame):
        """Creates the static layout for the Item Tracking section."""
        
        tracking_frame = tk.LabelFrame(parent_frame, text="Item Tracking & Logging", padx=10, pady=10)
        tracking_frame.grid(row=1, column=0, sticky="ew", pady=5)
        tracking_frame.columnconfigure((0, 1), weight=1)

        tk.Label(tracking_frame, text="Item Detected Status:", anchor="w").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        tk.Label(tracking_frame, text="Items Processed Today:", anchor="w").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        
        # Dynamic Placeholders
        tk.Label(tracking_frame, textvariable=self.item_detected_var, fg="orange", font=("Arial", 10, "bold")).grid(row=0, column=1, padx=5, pady=5, sticky="e")
        
        # 7.1 Item Tracking Display - Connect to the live counter variable
        tk.Label(tracking_frame, textvariable=self.items_processed_var, fg="black", font=("Arial", 12, "bold")).grid(row=1, column=1, padx=5, pady=5, sticky="e")
        
        # ... (Keep the rest of the method) ...


    def _animate_conveyor(self):
        """4.1 Conveyor Animation: Updates the canvas to simulate movement."""
        
        canvas = self.conveyor_canvas
        canvas.update_idletasks() 
        width = canvas.winfo_width() if canvas.winfo_width() > 1 else 450
        height = canvas.winfo_height() if canvas.winfo_height() > 1 else 150
        belt_y = height / 2

        canvas.delete("all")

        # Draw the main belt surface
        canvas.create_rectangle(0, belt_y - 20, width, belt_y + 20, fill="#333333", outline="")
        
        # Animate the inner lines (dashes)
        self.belt_offset = (self.belt_offset + 5) % 40 
        for i in range(-10, int(width / 40) + 1):
            x = i * 40 + self.belt_offset
            canvas.create_line(x, belt_y - 20, x + 20, belt_y + 20, fill="#555555", width=2)
            
        # 2. Animate the item
        if self.item_detected_var.get() == "📦 ITEM DETECTED":
            self.item_position = (self.item_position + 5) 
            if self.item_position > width + 50:
                self.item_position = -50 
            
            item_size = 15
            canvas.create_rectangle(
                self.item_position - item_size, belt_y - item_size, 
                self.item_position + item_size, belt_y + item_size, 
                fill="#CC0000", outline="black", width=2
            )
        else:
            self.item_position = -50 

        self.master.after(self.animation_delay_ms, self._animate_conveyor)

    
    def _update_graphs(self):
        """4.2 Real-time Graphs: Clears, plots, and updates the Matplotlib canvases."""
        
        if not self.temp_history:
            self.master.after(1000, self._update_graphs)
            return

        self.ax_temp.clear()
        self.ax_temp.plot(self.time_history, self.temp_history, color='tab:red')
        self.ax_temp.set_title("Temperature (°C)", fontsize=10)
        self.ax_temp.set_xticks([])
        min_t = min(self.temp_history) if self.temp_history else 20
        max_t = max(self.temp_history) if self.temp_history else 40
        self.ax_temp.set_ylim(min_t - 2, max_t + 2) 
        self.canvas_temp.draw_idle()

        self.ax_vib.clear()
        self.ax_vib.plot(self.time_history, self.vib_history, color='tab:blue')
        self.ax_vib.set_title("Vibration (Units)", fontsize=10)
        self.ax_vib.set_xticks([])
        min_v = min(self.vib_history) if self.vib_history else 80
        max_v = max(self.vib_history) if self.vib_history else 150
        self.ax_vib.set_ylim(min_v - 5, max_v + 5)
        self.canvas_vib.draw_idle()
        
        self.master.after(500, self._update_graphs)

    def on_closing(self):
        """Cleanly stop the MQTT client before closing the application."""
        print("🛑 Disconnecting MQTT client...")
        self.client.loop_stop()
        self.client.disconnect()
        self.master.destroy()
# --- PHASE 6: New Health Logic Method ---
    def calculate_health_score(self, temp, vib):
        """
        6.1 Overall Health Score: Calculates a combined score (0-100%).
        Score decreases as Temperature and Vibration move away from nominal values.
        """
        # Define nominal values (e.g., typical healthy values)
        NOMINAL_TEMP = 25.0
        NOMINAL_VIB = 100.0
        
        # Define maximum tolerable deviations (where health score hits 0)
        MAX_TEMP_DEV = 15.0  # 25C + 15C = 40C is 0% health
        MAX_VIB_DEV = 50.0   # 100 units + 50 units = 150 units is 0% health
        
        # Weights (Vibration often indicates mechanical health more than temp)
        WEIGHT_TEMP = 0.3
        WEIGHT_VIB = 0.7

        # 1. Calculate Deviation (0-1) for Temperature
        temp_dev = abs(temp - NOMINAL_TEMP) / MAX_TEMP_DEV
        temp_dev = min(temp_dev, 1.0) # Cap deviation at 1.0 (0% health)
        
        # 2. Calculate Deviation (0-1) for Vibration
        vib_dev = abs(vib - NOMINAL_VIB) / MAX_VIB_DEV
        vib_dev = min(vib_dev, 1.0) 
        
        # 3. Calculate Overall Health Loss
        health_loss = (temp_dev * WEIGHT_TEMP) + (vib_dev * WEIGHT_VIB)
        
        # 4. Convert loss to score (100 - loss%)
        score = 100.0 - (health_loss * 100.0)
        
        # Determine color
        if score > 85:
            color = "green"
        elif score > 50:
            color = "orange"
        else:
            color = "red"
            
        return score, color

    # --- UI Setup Methods (Modified for Phase 6) ---

    def _setup_health_status(self, parent_frame):
        """Creates the static layout for the Machine Health Status section."""
        
        health_frame = tk.LabelFrame(parent_frame, text="Machine Health Status", padx=10, pady=10)
        health_frame.grid(row=0, column=0, sticky="ew", pady=5)
        health_frame.columnconfigure((0, 1), weight=1) 

        # ... (Keep static labels) ...

        # Dynamic Placeholders (Updated with self.variables)
        tk.Label(health_frame, textvariable=self.current_temp_var, fg="blue", font=("Arial", 10, "bold")).grid(row=0, column=1, padx=5, pady=2, sticky="e")
        tk.Label(health_frame, textvariable=self.current_vib_var, fg="blue", font=("Arial", 10, "bold")).grid(row=1, column=1, padx=5, pady=2, sticky="e")
        
        # *** PHASE 6 FIX: Save the Health Score Label for color updates ***
        self.health_score_label = tk.Label(health_frame, textvariable=self.health_score_var, fg="green", font=("Arial", 12, "bold"))
        self.health_score_label.grid(row=2, column=1, padx=5, pady=5, sticky="e")
        
        # Status Message Label (saved for color updates)
        self.status_message_label = tk.Label(health_frame, textvariable=self.status_message_var, fg="black", font=("Arial", 10, "italic"))
        self.status_message_label.grid(row=4, column=0, columnspan=2, padx=5, pady=5)

    # ... (Keep all other methods: _setup_main_layout, _setup_graphs, _animate_conveyor, etc.) ...
        # --- Phase 7: Tracking & Logging Variables ---
        self.items_processed_count = 0
        self.items_processed_var = tk.StringVar(value="0") # Variable linked to the display label
        self.item_detected_previous = False # State flag to detect rising edge (item appearing)
        
        # 7.2 CSV Logging Setup
        self.log_file_name = "conveyor_log.csv"
        self._initialize_csv_log()
        
        # ... (rest of __init__ keeps all existing code) ...
        
    def _initialize_csv_log(self):
        """Creates the CSV file with headers if it doesn't exist."""
        try:
            with open(self.log_file_name, mode='w', newline='') as file:
                writer = csv.writer(file)
                # Headers for the CSV file
                writer.writerow([
                    "Timestamp", "Temperature_C", "Vibration_Units", "Health_Score_pct",
                    "Status_Message", "Item_Detected", "Conveyor_Speed", "Event_Type"
                ])
            print(f"✅ Initialized CSV log: {self.log_file_name}")
        except Exception as e:
            print(f"❌ Error initializing CSV log: {e}")
    
    def _log_data_to_csv(self, temp, vib, health_score, status_message, item_detected, event_type):
    
        try:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            data_row = [
                timestamp,
                temp,
                vib,
                health_score,
                status_message,
                "True" if item_detected else "False",
                self.conveyor_speed_var.get(),
                event_type
            ]
            
            # FIX APPLIED HERE: Added encoding='utf-8'
            with open(self.log_file_name, mode='a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(data_row)
                
        except Exception as e:
            # This should not crash the main thread, so we print to console
            print(f"❌ Critical Logging Error: {e}")
        
# --- Main Execution ---
if __name__ == "__main__":
    root = tk.Tk()
    app = DigitalTwinApp(root)
    root.mainloop()
    print("Application closed.")