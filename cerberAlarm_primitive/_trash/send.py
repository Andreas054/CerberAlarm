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
        print(f"Received: {response}")
        return response
    return None

def main():
    try:
        while True:
            # Example: send a command and receive response
            user_input = input("Enter a command (e.g., keypad$1): ")
            if user_input.lower() == "exit":
                print("Exiting...")
                break
            
            send_command(user_input)
            time.sleep(0.1)  # Optional delay before reading response

    except KeyboardInterrupt:
        print("\nExiting program.")

    finally:
        if ser.is_open:
            ser.close()
            print("Serial connection closed.")

if __name__ == "__main__":
    main()
