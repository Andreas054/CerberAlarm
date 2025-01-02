import serial
import time

# Configure the serial connection
arduino_port = '/dev/ttyUSB0'  # Replace with your device path if different
baud_rate = 9600  # Match the Arduino's Serial.begin rate
timeout = 1  # Optional timeout in seconds

# Initialize serial connection
ser = serial.Serial(arduino_port, baud_rate, timeout=timeout)

def send_command(command):
    """
    Sends a command to the Arduino.
    """
    if ser.is_open:
        print(f"Sending: {command}")
        ser.write((command + '\n').encode())  # Append newline to match Arduino's input handling
        time.sleep(0.1)  # Give Arduino time to process command

def read_response():
    """
    Reads and prints the response from Arduino.
    """
    if ser.is_open and ser.in_waiting > 0:
        response = ser.readline().decode().strip()

#        print(response, response[-1], response[-1] == "1")
#        if response[-1] == "1":
#            print(response)

        print(f"Received: {response}")
        return response
    return None

def main():
    try:
        while True:
            time.sleep(0.05)  # Adjust this delay if needed
            response = read_response()
#            if response:
#                print(response)

    except KeyboardInterrupt:
        print("\nExiting program.")

    finally:
        if ser.is_open:
            ser.close()
            print("Serial connection closed.")

if __name__ == "__main__":
    main()
