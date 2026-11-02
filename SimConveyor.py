import paho.mqtt.client as mqtt
import json
import time
import random

# --- Configuration ---
MQTT_BROKER = "127.0.0.1" 
MQTT_PORT = 1883
DATA_TOPIC = "conveyor/data"     
CONTROL_TOPIC = "conveyor/control" 
CONFIG_TOPIC_TEMP = "conveyor/config/temp_threshold" # NEW
CONFIG_TOPIC_VIB = "conveyor/config/vib_threshold"   # NEW

# --- Simulator State ---
SIM_SPEED = 100       
SIM_IS_RUNNING = True 
BASE_TEMP = 25.0      
BASE_VIB = 100.0      
TEMP_LIMIT = 30.0    # Simulator's internal threshold (updated by GUI)
VIB_LIMIT = 120.0    # Simulator's internal threshold (updated by GUI)

# --- MQTT Callbacks ---
def on_connect(client, userdata, flags, rc, properties):
    """Callback function when the client connects to the MQTT broker."""
    if rc == 0:
        print(f"✅ SIMULATOR Connected successfully to {MQTT_BROKER}")
        # Subscribe to all control topics
        client.subscribe([(CONTROL_TOPIC, 0), (CONFIG_TOPIC_TEMP, 0), (CONFIG_TOPIC_VIB, 0)])
        print(f"✅ Subscribed to control topics.")
    else:
        print(f"❌ SIMULATOR Connection failed with result code {rc}")

def on_control_message(client, userdata, msg):
    """Callback function for receiving control and config commands from the GUI."""
    global SIM_SPEED, SIM_IS_RUNNING, TEMP_LIMIT, VIB_LIMIT
    
    payload = msg.payload.decode()
    topic = msg.topic
    print(f"[{time.strftime('%H:%M:%S')}] ⚙️ Received on {topic}: {payload}")
    
    try:
        # 1. Handle Threshold Configuration
        if topic == CONFIG_TOPIC_TEMP:
            TEMP_LIMIT = float(json.loads(payload).get("value"))
            print(f"    ➡️ Internal Temp Limit set to: {TEMP_LIMIT}")
            return
        if topic == CONFIG_TOPIC_VIB:
            VIB_LIMIT = float(json.loads(payload).get("value"))
            print(f"    ➡️ Internal Vib Limit set to: {VIB_LIMIT}")
            return

        # 2. Handle Control Commands (RUN/PAUSE or Speed)
        
        # Check for simple string commands (RUN/PAUSE)
        if payload == "PAUSE":
            SIM_IS_RUNNING = False
            print("    ➡️ Simulated PAUSE.")
            return
        elif payload == "RUN":
            SIM_IS_RUNNING = True
            print("    ➡️ Simulated RUN.")
            return

        # Check for JSON commands (e.g., speed change)
        command = json.loads(payload)
        cmd = command.get("cmd")
        value = command.get("value")
        
        if cmd == "speed" and isinstance(value, (int, float)):
            SIM_SPEED = max(0, min(255, int(value))) 
            print(f"    ➡️ Simulated Speed set to: {SIM_SPEED}")
            
    except Exception as e:
        print(f"⚠️ SIMULATOR Error processing message on {topic}: {e}")

# --- Data Generation Function ---

def generate_sensor_data():
    """Generates a dictionary of simulated sensor data."""
    global TEMP_LIMIT, VIB_LIMIT # Ensure we use the latest user-set limits

    # Noise magnitude slightly influenced by speed
    noise_factor = SIM_SPEED / 255.0 * 0.5 + 0.5 # Range 0.5 to 1.0
    
    # Base readings (influenced by noise/speed)
    temp = BASE_TEMP + random.uniform(-1.0 * noise_factor, 1.0 * noise_factor) 
    vib = BASE_VIB + random.uniform(-5.0 * noise_factor, 5.0 * noise_factor) 
    
    # Randomly simulate item detection (e.g., 5% chance per cycle)
    item_detected = random.random() < 0.05
    
    status = "Running" if SIM_IS_RUNNING else "Paused"
    
    # --- PHASE 6 ANOMALY LOGIC (Modified to cross user-set limits) ---
    # We increase the chance slightly to make testing easier
    if random.random() < 0.05: 
        # Generate a spike: take the current limit and add a small deviation
        # This guarantees the anomaly will trigger a WARNING/CRITICAL state in the GUI
        temp = TEMP_LIMIT + random.uniform(2.0, 5.0) 
        vib = VIB_LIMIT + random.uniform(10.0, 25.0)
        print("🚨 SIMULATOR ANOMALY GENERATED (Crossing Thresholds)!")

    # Clamp the values in case they went below 0 (just for safety)
    temp = max(0.0, temp)
    vib = max(0.0, vib)

    data = {
        "temp": round(temp, 2),
        "vib": round(vib, 2),
        "item": item_detected,
        "speed": SIM_SPEED,
        "status": status
    }
    return data

# --- Main Execution ---

if __name__ == "__main__":
    print("--- Digital Twin Data Simulator Starting ---")
    
    client = mqtt.Client(
        client_id="conveyor_simulator",
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
    )
    client.on_connect = on_connect
    client.on_message = on_control_message 
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start() 
    except Exception as e:
        print(f"❌ SIMULATOR Failed to connect to MQTT broker: {e}")
        exit()

    try:
        while True:
            # Check SIM_IS_RUNNING status
            if SIM_IS_RUNNING:
                sensor_data = generate_sensor_data()
                payload = json.dumps(sensor_data)
                
                client.publish(DATA_TOPIC, payload)
                
                # Delay based on simulated speed (faster speed = less delay)
                delay = 1.0 - (SIM_SPEED / 255 * 0.9) 
                time.sleep(delay)
            else:
                # If paused, still send a message occasionally to show status
                if random.random() < 0.2:
                    sensor_data = {"temp": BASE_TEMP, "vib": BASE_VIB, "item": False, "speed": 0, "status": "Paused"}
                    client.publish(DATA_TOPIC, json.dumps(sensor_data))
                time.sleep(1.0)
                
    except KeyboardInterrupt:
        print("\n--- Simulator Stopped by User ---")
    finally:
        client.loop_stop()
        client.disconnect()
        print("SIMULATOR Disconnected.")