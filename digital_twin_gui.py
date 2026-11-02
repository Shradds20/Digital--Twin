import tkinter as tk
import paho.mqtt.client as mqtt
import json

# Your computer's IP address. This must match the IP in the simulator script.
MQTT_BROKER_IP = "127.0.0.1" 
MQTT_PORT = 1883
MQTT_TOPIC = "conveyor/data"

# The callback for when the client connects to the broker
def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT broker with result code {rc}")
    # Subscribe to the data topic
    client.subscribe(MQTT_TOPIC)

# The callback for when a PUBLISH message is received from the broker
def on_message(client, userdata, msg):
    try:
        # Decode the message from bytes to a string
        json_payload = msg.payload.decode()
        # Parse the JSON string into a Python dictionary
        sensor_data = json.loads(json_payload)

        # Update the labels in the GUI with the new data
        temperature_var.set(f"Temperature: {sensor_data['temperature']} °C")
        vibration_var.set(f"Vibration: {sensor_data['vibration']} units")
        item_var.set(f"Item Detected: {'Yes' if sensor_data['item_detected'] else 'No'}")
        
    except Exception as e:
        print(f"Error processing message: {e}")

# Create the main application window
root = tk.Tk()
root.title("Digital Twin Conveyor System")
root.geometry("400x200")

# Create a frame for the sensor data
data_frame = tk.Frame(root, padx=10, pady=10)
data_frame.pack()

# Create variables to hold the text for the labels
temperature_var = tk.StringVar(value="Temperature: -- °C")
vibration_var = tk.StringVar(value="Vibration: -- units")
item_var = tk.StringVar(value="Item Detected: --")

# Create labels to display the sensor data
temp_label = tk.Label(data_frame, textvariable=temperature_var, font=("Arial", 14))
temp_label.pack(pady=5, anchor="w")

vib_label = tk.Label(data_frame, textvariable=vibration_var, font=("Arial", 14))
vib_label.pack(pady=5, anchor="w")

item_label = tk.Label(data_frame, textvariable=item_var, font=("Arial", 14))
item_label.pack(pady=5, anchor="w")

# Create a new MQTT client instance for the GUI
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# Connect to the local MQTT broker
client.connect(MQTT_BROKER_IP, MQTT_PORT, 60)

# Start the background loop to handle network traffic
client.loop_start()

# Start the GUI's main loop
root.mainloop()