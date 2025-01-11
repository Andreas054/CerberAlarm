import serial
import time
import threading
import telepot
import datetime
import traceback
from telepot.loop import MessageLoop

from config import LISTA_friendlyZoneNames, telepotBotToken, acceptedTelegramIds

CONFIG_entryDelay = 200

GLOBAL_editingMessage = False
GLOBAL_currentMessageId = None
GLOBAL_currentChatId = None
GLOBAL_pendingConfirmationArmDisarm = None
GLOBAL_pendingConfirmationBypass = None
GLOBAL_pendingConfirmationResetFum = None

TIME_threadStatusAlarm_startTime = None

bot = telepot.Bot(telepotBotToken)

# Configure the serial connection
arduino_port = '/dev/ttyACM0'
baud_rate = 115200
timeout = 1
ser = serial.Serial(arduino_port, baud_rate, timeout=timeout)

dictionarHexToWhichZones = {
    '7': [1],
    'B': [2],
    'D': [3],
    'E': [4],

    '3': [1, 2],
    '5': [1, 3],
    '6': [1, 4],

    '9': [2, 3],
    'A': [2, 4],

    'C': [3, 4],

    '1': [1, 2, 3],
    '2': [1, 2, 4],
    '4': [1, 3, 4],

    '8': [2, 3, 4],

    '0': [1, 2, 3, 4],

    'F': []
}

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
    while True:
        try:
            if ser.is_open and ser.in_waiting > 0:
                response = ser.readline().decode().strip()
                # print(f"Received: {response}")
                return response
        except Exception as e:
            print(e)
        
        time.sleep(0.1)

def getOpenZones(hexValue):
    """
    Returns a string with the zones that are open.
    """
    openZones = dictionarHexToWhichZones.get(hexValue, [])
    if not openZones:
        return "none"
    
    return ', '.join([LISTA_friendlyZoneNames[zone - 1] for zone in openZones])

# def printWithTimestamp(message):
#     """
#     Prints a message with a timestamp.
#     """
#     print(f"[{datetime.datetime.now().strftime('%T.%f')[:-3]}] {message}")


def decodeSlave(hexValues):
    if len(hexValues) != 5:
        return None
    state = f"{''.join(hexValues)}\t"
    match hexValues:
        case ['D', 'D', x, 'F', 'F'] if x != 'F':                                                                           # DD*FF     Alarm tripped by entry delay zone
            state += f"Alarm tripped by entry delay zone while having {getOpenZones(x)} bypassed"
        case ['E', 'F', x, 'F', '3']:                                                                                       # EF*F3     Command to enter bypass mode (1 time), reminder battery disconnected?, zone open
            state += f"Command to enter bypass mode (1 time), {getOpenZones(x)} open, reminder battery disconnected?"
        case ['E', 'F', x, 'F', '7']:                                                                                       # EF*F7     Bypass Mode, which zone is bypassed, reminder battery disconnected?
            state += f"Bypass Mode, {getOpenZones(x)} bypassed, reminder battery disconnected?"
        case ['E', 'F', x, 'F', 'B']:                                                                                       # EF*FB     Command to enter bypass mode (1 time), zone open
            state += f"Command to enter bypass mode (1 time), {getOpenZones(x)} open"
        case ['E', 'F', x, 'F', 'F']:                                                                                       # EF*FF     Bypass Mode, which zone is bypassed
            state += f"Bypass Mode, {getOpenZones(x)} bypassed"
        case ['F', '8', '0', 'F', 'B']:                                                                                     # F80FB     Command 1 to arm away (1 time)
            state += f"Command 1 to arm away (1 time)"
        case ['F', '8', '0', 'F', 'F']:                                                                                     # F80FF     Command 2 to arm away (4 times)
            state += f"Command 2 to arm away (4 times)"
        case ['F', '8', x, 'F', 'F']:                                                                                       # F8*FF     Exit Delay, Zone open, Arming Away + (SYSTEM ON  or  battery out)
            state += f"Exit Delay, {getOpenZones(x)} open, Arming Away + (SYSTEM ON  or  battery out)"
        case ['F', '9', 'F', 'F', 'F']:                                                                                     # F9FFF     Exit Delay, Arming Away
            state += f"Exit Delay, Arming Away"
        case ['F', 'A', x, 'F', '7']:                                                                                       # FA*F7     Disarmed, which zone is open, reminder battery disconnected?
            state += f"Disarmed, {getOpenZones(x)} open, reminder battery disconnected?"
        case ['F', 'A', 'F', 'F', 'D']:                                                                                     # FAFFD     Disarmed after alarm, no zones open
            state += f"Disarmed after alarm, no open zones"
        case ['F', 'A', x, 'F', 'F']:                                                                                       # FA*FF     SYSTEM LED ON - Disarmed, zone open and bypass active
            state += f"Disarmed, {getOpenZones(x)} open and bypass active OR battery out"
        case ['F', 'B', 'F', 'F', 'D']:                                                                                     # FBFFD     Command to disarm alternative? (1 time)
            state += f"Command to disarm alternative? (1 time)"
        case ['F', 'B', 'F', 'F', 'E']:                                                                                     # FBFFE     Incorrect keycode on keypad
            state += f"Incorrect keycode on keypad"
        case ['F', 'B', 'F', 'F', 'F']:                                                                                     # FBFFF     Disarmed, no zones open
            state += f"Disarmed, no open zones"
        case ['F', 'C', x, 'F', 'F'] if x != 'F':                                                                           # FC*FF     Exit delay, zone open and battery disconnected?
            state += f"Exit delay, {getOpenZones(x)} open and battery disconnected?"
        case ['F', 'D', 'F', 'F', '7']:                                                                                     # FDFF7     Armed away, reminder battery disconnected?
            state += f"Armed away, reminder battery disconnected?"
        case ['F', 'D', x, 'F', 'F'] if x != 'F':                                                                           # FD*FF     Alarm tripped or Zone Open while exit delay is ON
            state += f"Alarm tripped or {getOpenZones(x)} open while exit delay is ON"
        case ['F', 'D', 'F', 'F', 'E']:                                                                                     # FDFFE     Entry delay OR incorrect input on keypad?
            state += f"Entry delay OR incorrect input on keypad?"
        case ['F', 'D', 'F', 'F', 'F']:                                                                                     # FDFFF     Armed away
            state += f"Armed away"
        case ['F', 'E', x, 'F', '3'] if x != 'F':                                                                           # FE*F3     SYSTEM ON - Entry chime, zone open
            state += f"Entry chime, {getOpenZones(x)} open SYSTEM"
        case ['F', 'E', x, 'F', '4'] if x != 'F':                                                                           # FE*F4     Trying to arm with open zone, battery disconnected?
            state += f"Trying to arm with open zone, {getOpenZones(x)} open, battery disconnected?"
        case ['F', 'E', x, 'F', '5'] if x != 'F':                                                                           # FE*F5     Command to disarm, zone open, reminder battery disconnected? (1 time)
            state += f"Command to disarm, {getOpenZones(x)} open, reminder battery disconnected? (1 time)"
        case ['F', 'E', x, 'F', '6'] if x != 'F':                                                                           # FE*F6     Incorrect code on keypad, zone open, reminder battery disconnected?
            state += f"Incorrect code on keypad, {getOpenZones(x)} open, reminder battery disconnected?"
        case ['F', 'E', x, 'F', '7'] if x != 'F':                                                                           # FE*F7     Disarmed, zone open + reminder battery disconnected?
            state += f"Disarmed, {getOpenZones(x)} open + reminder battery disconnected?"
        case ['F', 'E', x, 'F', 'B'] if x != 'F':                                                                           # FE*FB     SYSTEM ON - Entry chime, zone open
            state += f"Entry chime, {getOpenZones(x)} open SYSTEM"
        case ['F', 'E', x, 'F', 'C'] if x != 'F':                                                                           # FE*FC     Trying to arm with open zone, battery disconnected?
            state += f"Trying to arm with open zone, {getOpenZones(x)} open, battery disconnected?"
        case ['F', 'E', x, 'F', 'D'] if x != 'F':                                                                           # FE*FD     Command to disarm, zone open, after entry delay? + reminder battery disconnected? (1 time)
            state += f"Command to disarm, {getOpenZones(x)} open, after entry delay? + reminder battery disconnected? (1 time)"
        case ['F', 'E', x, 'F', 'E'] if x != 'F':                                                                           # FE*FE     Incorrect code on keypad, zone open, SYSTEM
            state += f"Incorrect code on keypad, {getOpenZones(x)} open, SYSTEM"
        case ['F', 'E', x, 'F', 'F'] if x != 'F':                                                                           # FE*FF     SYSTEM ON - Disarmed, zone open    (or bypass) or battery
            state += f"Disarmed, {getOpenZones(x)} open OR battery out? SYSTEM"
        case ['F', 'F', x, 'F', '7'] if x != 'F':                                                                           # FF*F7     Battery disconnected, zone open (1 time)
            state += f"Battery disconnected, {getOpenZones(x)} open (1 time)"
        case ['F', 'F', x, 'F', 'B'] if x != 'F':                                                                           # FF*FB     Entry chime
            state += f"Entry chime, {getOpenZones(x)} open"
        case ['F', 'F', x, 'F', 'C'] if x != 'F':                                                                           # FF*FC     Trying to arm with open zone
            state += f"Trying to arm with open zone, {getOpenZones(x)} open"
        case ['F', 'F', x, 'F', 'D']:                                                                                       # FF*FD     I DONT KNOW, WHEN DISARMING AND A ZONE IS OPEN
            state += f"Disarmed, {getOpenZones(x)} open, I DONT KNOW"
        case ['F', 'F', x, 'F', 'E'] if x != 'F':                                                                           # FF*FE     Incorrect code on keypad
            state += f"Incorrect code on keypad, {getOpenZones(x)} open"
        case ['F', 'F', x, 'F', 'F'] if x != 'F':                                                                           # FF*FF     Disarmed, zone open
            state += f"Disarmed, {getOpenZones(x)} open"
        case ['F', 'F', 'F', 'F', '7']:                                                                                     # FFFF7     * pressed, reminder battery disconnected?
            state += f"* pressed, reminder battery disconnected?"
        case ['F', 'F', 'F', 'F', 'F']:                                                                                     # FFFFF     * pressed
            state += f"* pressed, waiting for code on keypad"
        case _:
            state += f"NOT-YET-DOCUMENTED-----------------------------------"
    
    return state

def decodeMaster(hexValues):
    if ''.join(hexValues) in ['FFFBF', 'FF7BF', 'FFBBF', 'FFFDF', 'FF3BF']:
        # return
        # printWithTimestamp(f"{''.join(hexValues)}     - usual")
        print(f"{''.join(hexValues)}", end="\t\t")
    else:
        # printWithTimestamp(f"{''.join(hexValues)}")
        print(f"{''.join(hexValues)}", end="\t\t")


def threadStatusAlarm():
    global GLOBAL_editingMessage, GLOBAL_currentMessageId, GLOBAL_currentChatId, TIME_threadStatusAlarm_startTime

    TIME_threadStatusAlarm_startTime = time.time()

    counterIgnoreFirst = 0

    lastState = None
    while GLOBAL_editingMessage and time.time() - TIME_threadStatusAlarm_startTime < 300: # limit to 5 minutes
        currentStateSlave = None
        response = serialReadResponse()

        if counterIgnoreFirst < 3:
            counterIgnoreFirst += 1
            time.sleep(0.1)
            continue

        if response:
            hexValues = []
            if response.startswith("SLAVE: "):
                response = response[len("SLAVE: "):].replace(" ", "")
                for hex in response:
                    hexValues.append(hex)

                currentStateSlave = decodeSlave(hexValues)

            # elif response.startswith("MASTR: "):
            #     response = response[len("MASTR: "):].replace(" ", "")
            #     for hex in response:
            #         hexValues.append(hex)

            #     decodeMaster(hexValues)


            if currentStateSlave is None:
                continue

            if currentStateSlave != lastState:
                # printWithTimestamp(currentStateSlave)
                hexValuesStr = currentStateSlave.split('\t')[0]
                statusStr = currentStateSlave.split('\t')[1]

                # messageStr = f"```\n{currentStateSlave}\n"
                # messageStr += f'==============================\n{datetime.datetime.now().strftime("%H:%M:%S")}\n'
                # messageStr += "```Use /stop to stop updating status."

                messageStr = f"```{hexValuesStr}\n"
                messageStr += f'{statusStr}\n'
                messageStr += f'==============================\n{datetime.datetime.now().strftime("%H:%M:%S")}\n'
                messageStr += "```Use /stop to stop updating status."

                print(messageStr)

                try:
                    bot.editMessageText((GLOBAL_currentChatId, GLOBAL_currentMessageId), messageStr, parse_mode='Markdown')
                except Exception as e:
                    traceback.print_exc()
                    print(e)
                lastState = currentStateSlave
                time.sleep(0.5)


def bypassOrUnbypassZone(zone, bypassOrUnbypass):
    """
    Bypasses or unbypasses a zone.
    """
    tmpTimeStart = time.time()

    if ser.is_open:
        if bypassOrUnbypass == "bypass":
            serialSendCommand(f"BYPASS${zone}")
        elif bypassOrUnbypass == "unbypass":
            serialSendCommand(f"UNBYPASS${zone}")

        while time.time() - tmpTimeStart < 7:
            response = serialReadResponse()
            if response:
                if response.startswith("G") or response.startswith("H"):
                    messageStr = f"Zone {zone} has been {bypassOrUnbypass}ed."
                    return messageStr
            time.sleep(0.1)
    return f"Error {bypassOrUnbypass}ing zone {zone}.\nUse /listbypass to see the current bypassed zones."

        

def listBypassedZones():
    """
    Lists the bypassed zones.
    """
    tmpTimeStart = time.time()

    if ser.is_open:
        serialSendCommand("LISTBYPASS$")
        while time.time() - tmpTimeStart < 7:
            response = serialReadResponse()
            if response:
                if response.startswith("L"):
                    bypassedZones = response[1:]
                    messageStr = "Bypassed zones:\n"
                    for i, zone in enumerate(bypassedZones):
                        if zone == '1':
                            messageStr += f"{i + 1}. {LISTA_friendlyZoneNames[i]}\n"
                    return messageStr
            time.sleep(0.1)
    return "Error listing bypassed zones."

def armDisarmAlarm(armOrDisarm): # not checking for response                  I00000
    """
    Arms or disarms the alarm.
    """

    if ser.is_open:
        if armOrDisarm == "arm":
            serialSendCommand("KEY$")
        elif armOrDisarm == "disarm":
            serialSendCommand("KEY$")

    return True

def handle(msg):
    global GLOBAL_editingMessage, GLOBAL_currentMessageId, GLOBAL_currentChatId, GLOBAL_pendingConfirmationArmDisarm, GLOBAL_pendingConfirmationBypass, GLOBAL_pendingConfirmationResetFum

    chat_id = msg['chat']['id']
    command = msg['text']

    if str(chat_id) not in acceptedTelegramIds:
        return
    
    GLOBAL_currentChatId = chat_id

    # Cancel confirmation if NOT 'yes'
    if GLOBAL_pendingConfirmationArmDisarm and command.lower() != 'yes':
        GLOBAL_pendingConfirmationArmDisarm = None
        bot.sendMessage(chat_id, "Confirmation cancelled.")
        return

    # Cancel confirmation if NOT between 1 and 4
    if GLOBAL_pendingConfirmationBypass and not command.isdigit():
        GLOBAL_pendingConfirmationBypass = None
        bot.sendMessage(chat_id, "Confirmation cancelled. Zone must be a number between 1 and 4.")
        return
    if GLOBAL_pendingConfirmationBypass and int(command) not in range(1, 5):
        GLOBAL_pendingConfirmationBypass = None
        bot.sendMessage(chat_id, "Confirmation cancelled. Zone must be between 1 and 4.")
        return
    
    # Cancel confirmation if NOT 'yes' for resetfum
    if GLOBAL_pendingConfirmationResetFum and command.lower() != 'yes':
        GLOBAL_pendingConfirmationResetFum = None
        bot.sendMessage(chat_id, "Confirmation cancelled.")
        return

    if command == '/help':
        bot.sendMessage(chat_id, "Commands:\n/status\n/stop\n/arm\n/disarm\n/bypass\n/unbypass\n/listbypass\n/resetfum")
    elif command == '/status':
        GLOBAL_editingMessage = False
        time.sleep(0.05)

        GLOBAL_currentMessageId = bot.sendMessage(chat_id, "Loading...", parse_mode='Markdown')['message_id']
        GLOBAL_editingMessage = True

        threading.Thread(target=threadStatusAlarm).start()
    elif command == '/stop':
        GLOBAL_editingMessage = False
        
        try:
            bot.editMessageText((chat_id, GLOBAL_currentMessageId), "Stopped updating status.")
        except Exception as e:
            print(e)

    elif command == '/arm' or command == '/disarm':
        GLOBAL_pendingConfirmationArmDisarm = command
        bot.sendMessage(chat_id, f"Are you sure you want to {command[1:]} the alarm? Reply with 'yes' to confirm.")
    elif command.lower() == 'yes' and GLOBAL_pendingConfirmationArmDisarm:
        armDisarmAlarm(GLOBAL_pendingConfirmationArmDisarm[1:])
        GLOBAL_pendingConfirmationArmDisarm = None

        # start status
        GLOBAL_editingMessage = False
        time.sleep(0.05)

        GLOBAL_currentMessageId = bot.sendMessage(chat_id, "Loading...", parse_mode='Markdown')['message_id']
        GLOBAL_editingMessage = True

        threading.Thread(target=threadStatusAlarm).start()

    elif command == '/bypass' or command == '/unbypass':
        GLOBAL_pendingConfirmationBypass = command
        bot.sendMessage(chat_id, f"Which zone do you want to {command[1:]}? Reply with a number between 1 and 4.")
    elif command.isdigit() and int(command) in range(1, 5) and GLOBAL_pendingConfirmationBypass:
        zone = int(command)
        bypassOrUnbypassZone(zone, GLOBAL_pendingConfirmationBypass[1:])
        bot.sendMessage(chat_id, f"Zone {zone} has been {GLOBAL_pendingConfirmationBypass[1:]}ed.")
        GLOBAL_pendingConfirmationBypass = None

    elif command == '/listbypass':
        bot.sendMessage(chat_id, listBypassedZones())

    elif command == '/resetfum':
        GLOBAL_pendingConfirmationResetFum = True
        bot.sendMessage(chat_id, "Are you sure you want to reset the FUM? Reply with 'yes' to confirm.")
    elif command.lower() == 'yes' and GLOBAL_pendingConfirmationResetFum:
        serialSendCommand("RESETFUM$")
        bot.sendMessage(chat_id, "FUM has been reset.")
        GLOBAL_pendingConfirmationResetFum = None


def main():
    try:
        MessageLoop(bot, handle).run_as_thread()
        print('I am listening ...')

        time.sleep(0.1)
        # serialSendCommand("KEY$")

        while True:
            time.sleep(0.1)
            # response = serialReadResponse()
            
            
            # if response:
            #     hexValues = []
            #     if response.startswith("SLAVE: "):
            #         response = response[len("SLAVE: "):].replace(" ", "")
            #         for hex in response:
            #             hexValues.append(hex)

            #         decodeSlave(hexValues)

                # elif response.startswith("MASTR: "):
                #     response = response[len("MASTR: "):].replace(" ", "")
                #     for hex in response:
                #         hexValues.append(hex)

                #     decodeMaster(hexValues)
            


    except KeyboardInterrupt:
        print("\nExiting program.")

    finally:
        if ser.is_open:
            ser.close()
            print("Serial connection closed.")


if __name__ == "__main__":
    main()