import serial
import time
import datetime
import threading

# Configure the serial connection
# arduino_port = '/dev/ttyUSB0'
arduino_port = 'COM10'
baud_rate = 115200
timeout = 1
ser = serial.Serial(arduino_port, baud_rate, timeout=timeout)

dictionarHexToWhichZones = {
    '7': 'Z1',
    'B': 'Z2',
    'D': 'Z3',
    'E': 'Z4',

    '3': 'Z1 & Z2',
    '5': 'Z1 & Z3',
    '6': 'Z1 & Z4',

    '9': 'Z2 & Z3',
    'A': 'Z2 & Z4',

    'C': 'Z3 & Z4',

    '1': 'Z1 & Z2 & Z3',
    '2': 'Z1 & Z2 & Z4',
    '4': 'Z1 & Z3 & Z4',

    '8': 'Z2 & Z3 & Z4',

    '0': 'Z1 & Z2 & Z3 & Z4',

    'F': 'none'
}


# # clear both files first
# open("logAlarm.txt", "w").close()
# open("logKeyboard.txt", "w").close()

def serialSendCommand(command):
    """
    Sends a command to the Arduino.
    """
    if ser.is_open:
        print(f"Sending: {command}")
        ser.write((command + '\n').encode())
        time.sleep(0.1)

def serialReadResponse():
    """
    Reads the serial port for a response from the Arduino and saves it to a global list variable.
    """
    global LISTA_zone

    while True:
        try:
            if ser.is_open and ser.in_waiting > 0:
                response = ser.readline().decode().strip()
                # print(f"Received: {response}")
                return response
        except Exception as e:
            print(e)
        
        time.sleep(0.1)

def printWithTimestamp(message):
    """
    Prints a message with a timestamp.
    """
    print(f"[{datetime.datetime.now().strftime('%T.%f')[:-3]}] {message}")


def decodeSlave(hexValues):
    match hexValues:
        case ['D', 'D', x, 'F', 'F'] if x != 'F':                                                                           # DD*FF     Alarm tripped by entry delay zone
            printWithTimestamp(f"{''.join(hexValues)}\tAlarm tripped by entry delay zone while having {dictionarHexToWhichZones[x]} bypassed")
        case ['E', 'F', x, 'F', '3']:                                                                                       # EF*F3     Command to enter bypass mode (1 time), reminder battery disconnected?, zone open
            printWithTimestamp(f"{''.join(hexValues)}\tCommand to enter bypass mode (1 time), {dictionarHexToWhichZones[x]} open, reminder battery disconnected?")
        case ['E', 'F', x, 'F', '7']:                                                                                       # EF*F7     Bypass Mode, which zone is bypassed, reminder battery disconnected?
            printWithTimestamp(f"{''.join(hexValues)}\tBypass Mode, {dictionarHexToWhichZones[x]} bypassed, reminder battery disconnected?")
        case ['E', 'F', x, 'F', 'B']:                                                                                       # EF*FB     Command to enter bypass mode (1 time), zone open
            printWithTimestamp(f"{''.join(hexValues)}\tCommand to enter bypass mode (1 time), {dictionarHexToWhichZones[x]} open")
        case ['E', 'F', x, 'F', 'F']:                                                                                       # EF*FF     Bypass Mode, which zone is bypassed
            printWithTimestamp(f"{''.join(hexValues)}\tBypass Mode, {dictionarHexToWhichZones[x]} bypassed")
        case ['F', '8', '0', 'F', 'B']:                                                                                     # F80FB     Command 1 to arm away (1 time)
            printWithTimestamp(f"{''.join(hexValues)}\tCommand 1 to arm away (1 time)")
        case ['F', '8', '0', 'F', 'F']:                                                                                     # F80FF     Command 2 to arm away (4 times)
            printWithTimestamp(f"{''.join(hexValues)}\tCommand 2 to arm away (4 times)")
        case ['F', '8', x, 'F', 'F'] if x != 'F':                                                                           # F8*FF     Exit Delay, Zone open, Arming Away + (SYSTEM ON  or  battery out)
            printWithTimestamp(f"{''.join(hexValues)}\tExit Delay, {dictionarHexToWhichZones[x]} open, Arming Away + (SYSTEM ON  or  battery out)")
        case ['F', '9', 'F', 'F', 'F']:                                                                                     # F9FFF     Exit Delay, Arming Away
            printWithTimestamp(f"{''.join(hexValues)}\tExit Delay, Arming Away")
        # case ['F', 'A', 'F', 'F', '7']:                                                                                     # FAFF7     Disarmed, + reminder battery disconnected?
        #     printWithTimestamp(f"{''.join(hexValues)}\tDisarmed, reminder battery disconnected?")
        case ['F', 'A', x, 'F', '7']:                                                                                       # FA*F7     Disarmed, which zone is open, reminder battery disconnected?
            printWithTimestamp(f"{''.join(hexValues)}\tDisarmed, {dictionarHexToWhichZones[x]} open, reminder battery disconnected?")
        case ['F', 'A', 'F', 'F', 'D']:                                                                                     # FAFFD     Disarmed after alarm, no zones open
            printWithTimestamp(f"{''.join(hexValues)}\tDisarmed after alarm, no open zones")
        # case ['F', 'A', 'F', 'F', 'F']:                                                                                     # FAFFF     SYSTEM ON - Disarmed   or   bypass something?   MAYBE ALSO BATTERY OUT?
            # printWithTimestamp(f"{''.join(hexValues)}\tDisarmed - after Alarm?   or   bypass something? + battery out??")
        case ['F', 'A', x, 'F', 'F']:                                                                                       # FA*FF     SYSTEM LED ON - Disarmed, zone open and bypass active
            printWithTimestamp(f"{''.join(hexValues)}\tDisarmed, {dictionarHexToWhichZones[x]} open and bypass active")
        case ['F', 'B', 'F', 'F', 'D']:                                                                                     # FBFFD     Command to disarm alternative? (1 time)
            printWithTimestamp(f"{''.join(hexValues)}\tCommand to disarm alternative? (1 time)")
        case ['F', 'B', 'F', 'F', 'E']:                                                                                     # FBFFE     Incorrect keycode on keypad
            printWithTimestamp(f"{''.join(hexValues)}\tIncorrect keycode on keypad")
        case ['F', 'B', 'F', 'F', 'F']:                                                                                     # FBFFF     Disarmed, no zones open
            printWithTimestamp(f"{''.join(hexValues)}\tDisarmed, no open zones")
        case ['F', 'C', x, 'F', 'F'] if x != 'F':                                                                           # FC*FF     Exit delay, zone open and battery disconnected?
            printWithTimestamp(f"{''.join(hexValues)}\tExit delay, {dictionarHexToWhichZones[x]} open and battery disconnected?")
        case ['F', 'D', 'F', 'F', '7']:                                                                                     # FDFF7     Armed away, reminder battery disconnected?
            printWithTimestamp(f"{''.join(hexValues)}\tArmed away, reminder battery disconnected?")
        case ['F', 'D', x, 'F', 'F'] if x != 'F':                                                                           # FD*FF     Alarm tripped or Zone Open while exit delay is ON
            printWithTimestamp(f"{''.join(hexValues)}\tAlarm tripped or {dictionarHexToWhichZones[x]} open while exit delay is ON")
        case ['F', 'D', 'F', 'F', 'E']:                                                                                     # FDFFE     Entry delay OR incorrect input on keypad?
            printWithTimestamp(f"{''.join(hexValues)}\tEntry delay OR incorrect input on keypad?")
        case ['F', 'D', 'F', 'F', 'F']:                                                                                     # FDFFF     Armed away
            printWithTimestamp(f"{''.join(hexValues)}\tArmed away")
        case ['F', 'E', x, 'F', '3'] if x != 'F':                                                                           # FE*F3     SYSTEM ON - Entry chime, zone open
            printWithTimestamp(f"{''.join(hexValues)}\tEntry chime, {dictionarHexToWhichZones[x]} open SYSTEM")
        case ['F', 'E', x, 'F', '4'] if x != 'F':                                                                           # FE*F4     Trying to arm with open zone, battery disconnected?
            printWithTimestamp(f"{''.join(hexValues)}\tTrying to arm with open zone, {dictionarHexToWhichZones[x]} open, battery disconnected?")
        case ['F', 'E', x, 'F', '5'] if x != 'F':                                                                           # FE*F5     Command to disarm, zone open, reminder battery disconnected? (1 time)
            printWithTimestamp(f"{''.join(hexValues)}\tCommand to disarm, {dictionarHexToWhichZones[x]} open, reminder battery disconnected? (1 time)")
        case ['F', 'E', x, 'F', '6'] if x != 'F':                                                                           # FE*F6     Incorrect code on keypad, zone open, reminder battery disconnected?
            printWithTimestamp(f"{''.join(hexValues)}\tIncorrect code on keypad, {dictionarHexToWhichZones[x]} open, reminder battery disconnected?")
        case ['F', 'E', x, 'F', '7'] if x != 'F':                                                                           # FE*F7     Disarmed, zone open + reminder battery disconnected?
            printWithTimestamp(f"{''.join(hexValues)}\tDisarmed, {dictionarHexToWhichZones[x]} open + reminder battery disconnected?")
        case ['F', 'E', x, 'F', 'B'] if x != 'F':                                                                           # FE*FB     SYSTEM ON - Entry chime, zone open
            printWithTimestamp(f"{''.join(hexValues)}\tEntry chime, {dictionarHexToWhichZones[x]} open SYSTEM")
        case ['F', 'E', x, 'F', 'C'] if x != 'F':                                                                           # FE*FC     Trying to arm with open zone, battery disconnected?
            printWithTimestamp(f"{''.join(hexValues)}\tTrying to arm with open zone, {dictionarHexToWhichZones[x]} open, battery disconnected?")
        case ['F', 'E', x, 'F', 'D'] if x != 'F':                                                                           # FE*FD     Command to disarm, zone open, after entry delay? + reminder battery disconnected? (1 time)
            printWithTimestamp(f"{''.join(hexValues)}\tCommand to disarm, {dictionarHexToWhichZones[x]} open, after entry delay? + reminder battery disconnected? (1 time)")
        case ['F', 'E', x, 'F', 'E'] if x != 'F':                                                                           # FE*FE     Incorrect code on keypad, zone open, SYSTEM
            printWithTimestamp(f"{''.join(hexValues)}\tIncorrect code on keypad, {dictionarHexToWhichZones[x]} open, SYSTEM")
        case ['F', 'E', x, 'F', 'F'] if x != 'F':                                                                           # FE*FF     SYSTEM ON - Disarmed, zone open    (or bypass) or battery
            printWithTimestamp(f"{''.join(hexValues)}\tDisarmed, {dictionarHexToWhichZones[x]} open OR battery out? SYSTEM")
        case ['F', 'F', x, 'F', '7'] if x != 'F':                                                                           # FF*F7     Battery disconnected, zone open (1 time)
            printWithTimestamp(f"{''.join(hexValues)}\tBattery disconnected, {dictionarHexToWhichZones[x]} open (1 time)")
        case ['F', 'F', x, 'F', 'B'] if x != 'F':                                                                           # FF*FB     Entry chime
            printWithTimestamp(f"{''.join(hexValues)}\tEntry chime, {dictionarHexToWhichZones[x]} open")
        case ['F', 'F', x, 'F', 'C'] if x != 'F':                                                                           # FF*FC     Trying to arm with open zone
            printWithTimestamp(f"{''.join(hexValues)}\tTrying to arm with open zone, {dictionarHexToWhichZones[x]} open")
        case ['F', 'F', x, 'F', 'D']:                                                                                       # FF*FD     I DONT KNOW, WHEN DISARMING AND A ZONE IS OPEN
            printWithTimestamp(f"{''.join(hexValues)}\tDisarmed, {dictionarHexToWhichZones[x]} open, I DONT KNOW")
        case ['F', 'F', x, 'F', 'E'] if x != 'F':                                                                           # FF*FE     Incorrect code on keypad
            printWithTimestamp(f"{''.join(hexValues)}\tIncorrect code on keypad, {dictionarHexToWhichZones[x]} open")
        case ['F', 'F', x, 'F', 'F'] if x != 'F':                                                                           # FF*FF     Disarmed, zone open
            printWithTimestamp(f"{''.join(hexValues)}\tDisarmed, {dictionarHexToWhichZones[x]} open")
        case ['F', 'F', 'F', 'F', '7']:                                                                                     # FFFF7     * pressed, reminder battery disconnected?
            printWithTimestamp(f"{''.join(hexValues)}\t* pressed, reminder battery disconnected?")
        case ['F', 'F', 'F', 'F', 'F']:                                                                                     # FFFFF     * pressed
            printWithTimestamp(f"{''.join(hexValues)}\t* pressed, waiting for code on keypad")
        case _:
            printWithTimestamp(f"{''.join(hexValues)}\t------------------------------------")

def decodeMaster(hexValues):
    if ''.join(hexValues) in ['FFFBF', 'FF7BF', 'FFBBF', 'FFFDF', 'FF3BF']:
        # return
        printWithTimestamp(f"{''.join(hexValues)}     - usual")
    else:
        printWithTimestamp(f"{''.join(hexValues)}")
    # fileWriteAlarm.write(f"{datetime.datetime.now().strftime('%T.%f')[:-3]}\t{''.join(hexValues)}\n")

def threadKeyboardInput():
    while True:
        userInput = input()
        # with open("logKeyboard.txt", "a") as file:
        #     file.write(f"{datetime.datetime.now().strftime('%T.%f')[:-3]}\t{userInput}\n")

# fileWriteAlarm = open("logAlarm.txt", "a")
def main():
    # thread = threading.Thread(target=threadKeyboardInput)
    # thread.start()

    try:
        time.sleep(0.1)

        while True:
            response = serialReadResponse()
            
            
            if response:
                hexValues = []
                if response.startswith("SLAVE: "):
                    response = response[len("SLAVE: "):].replace(" ", "")
                    for hex in response:
                        hexValues.append(hex)

                    decodeSlave(hexValues)

                # elif response.startswith("MASTR: "):
                #     response = response[len("MASTR: "):].replace(" ", "")
                #     for hex in response:
                #         hexValues.append(hex)

                #     decodeMaster(hexValues)
            


    except KeyboardInterrupt:
        print("\nExiting program.")

        # fileWriteAlarm.close()

    finally:
        if ser.is_open:
            ser.close()
            print("Serial connection closed.")

        # fileWriteAlarm.close()

if __name__ == "__main__":
    main()