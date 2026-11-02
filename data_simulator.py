import paho.mqtt.client as mqtt
import time
import random
import json

# Your computer's IP address. For local use, 127.0.0.1 (localhost) is perfect.
MQTT_BROKER_IP = "127.0.0.1" 
MQTT_PORT = 1883
MQTT_TOPIC = "conveyor/data"

# The callback for when the client connects to the broker
def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT broker with result code {rc}")

# Create a new MQTT client instance
client = mqtt.Client()
client.on_connect = on_connect

# Connect to the local MQTT broker
print(f"Connecting to MQTT broker at {MQTT_BROKER_IP}:{MQTT_PORT}")
client.connect(MQTT_BROKER_IP, MQTT_PORT, 60)

# Start the background loop to handle network traffic
client.loop_start()

try:
    # Loop forever to publish data
    while True:
        # Generate some random, but realistic, sensor data
        # Item detection (True or False)
        item_detected = random.choice([True, False])
        
        # Temperature data (e.g., 20.0 to 30.0 degrees)
        temp_value = round(random.uniform(20.0, 30.0), 2)
        
        # Vibration data (e.g., a number from 100 to 500)
        vib_value = random.randint(100, 500)
        
        # Create a dictionary to hold all the data
        sensor_data = {
            "item_detected": item_detected,
            "temperature": temp_value,
            "vibration": vib_value
        }
        
        # Convert the dictionary to a JSON string
        json_payload = json.dumps(sensor_data)
        
        # Publish the JSON string to the MQTT topic
        client.publish(MQTT_TOPIC, json_payload)
        
        print(f"Published: {json_payload}")
        
        # Wait for a second before publishing the next set of data
        time.sleep(1)

except KeyboardInterrupt:
    print("Stopping data simulator.")
    client.loop_stop()
    client.disconnect()