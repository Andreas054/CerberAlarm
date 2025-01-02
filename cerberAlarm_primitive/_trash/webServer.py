from flask import Flask, render_template, request, jsonify, send_from_directory
import threading
import time
import serial

from config import LISTA_friendlyZoneNames, LISTA_zone

app = Flask(__name__)

# Configure the serial connection
arduino_port = '/dev/ttyUSB0'
baud_rate = 9600
timeout = 1

# Initialize serial connection
ser = serial.Serial(arduino_port, baud_rate, timeout=timeout)

GLOBAL_keepRunning = False
last_request_time = time.time()

def serialSendCommand(command):
    """
    Sends a command to the Arduino.
    """
    if ser.is_open:
        print(f"Sending: {command}")
        ser.write((command + '\n').encode())  # Append newline to match Arduino's input handling
        time.sleep(0.1)  # Give Arduino time to process command

def serialReadResponse():
    """
    Reads the serial port for a response from the Arduino and saves it to a global list variable.
    """
    global LISTA_zone, GLOBAL_keepRunning

    while True:
        if GLOBAL_keepRunning:
            try:
                if ser.is_open and ser.in_waiting > 0:
                    response = ser.readline().decode().strip()
                    # print(f"Received: {response}")

                    if response.startswith("zone"):
                        zone = response.split("$")[1]
                        status = response.split("$")[2]

                        if zone == "7": # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
                            continue

                        if status == "1":
                            LISTA_zone[int(zone) - 1] = 1
                        else:
                            LISTA_zone[int(zone) - 1] = 0
            except Exception as e:
                print(e)
        
        time.sleep(0.2)

def monitor_requests():
    """
    Monitors the time since the last request was made to the server for the /api/getZones endpoint.
    """
    global GLOBAL_keepRunning, last_request_time
    while True:
        if time.time() - last_request_time > 30:
            GLOBAL_keepRunning = False
        else:
            GLOBAL_keepRunning = True
        time.sleep(1)

def update_last_request_time(func):
    def wrapper(*args, **kwargs):
        global last_request_time
        last_request_time = time.time()
        return func(*args, **kwargs)
    return wrapper

@app.route('/api/getZones')
@update_last_request_time
def getZones():
    """
    Returns the current status of all zones.
    """
    global LISTA_friendlyZoneNames, LISTA_zone

    if not ser.is_open:
        print("Arduino is not connected")
        return jsonify({"error": "Arduino is not connected"})

    response = {i + 1:  {"status": LISTA_zone[i], "friendlyName": LISTA_friendlyZoneNames[i]} for i in range(len(LISTA_friendlyZoneNames))}
    return jsonify(response)

@app.route('/api/sendOneKey', methods=['POST'])
def sendOneKey():
    """
    Sends a command to the Arduino to simulate a key press.
    """
    key = request.json['key']
    serialSendCommand(f"keypad${key}")
    return jsonify({"message": f"Sent key {key} command"})

@app.route('/getPdf')
def getPdf():
    return send_from_directory('static', 'manual.pdf')

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    thread = threading.Thread(target=serialReadResponse)
    thread.start()

    monitor_thread = threading.Thread(target=monitor_requests)
    monitor_thread.start()

    app.run(debug=True, host='0.0.0.0')
