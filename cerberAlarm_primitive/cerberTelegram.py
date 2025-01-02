import serial
import time
import threading
import telepot
import datetime
from telepot.loop import MessageLoop

from config import LISTA_friendlyZoneNames, LISTA_zone, telepotBotToken, acceptedTelegramIds, codAccess

CONFIG_entryDelay = 200

GLOBAL_editingMessage = False
GLOBAL_currentMessageId = None
GLOBAL_currentChatId = None
GLOBAL_pendingConfirmationArmDisarm = None

TIME_threadStatusAlarm_startTime = None

bot = telepot.Bot(telepotBotToken)

# Configure the serial connection
arduino_port = '/dev/ttyUSB0'
baud_rate = 9600
timeout = 1
ser = serial.Serial(arduino_port, baud_rate, timeout=timeout)

def serialSendCommand(command):
    """
    Sends a command to the Arduino.
    """
    if ser.is_open:
        # print(f"Sending: {command}")
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
        
        time.sleep(0.1)

def handle(msg):
    global GLOBAL_editingMessage, GLOBAL_currentMessageId, GLOBAL_currentChatId, GLOBAL_pendingConfirmationArmDisarm

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

    if command == '/help':
        bot.sendMessage(chat_id, "Commands:\n/status - Get alarm status\n/stop - Stop updating status\n/arm - Arm the alarm\n/disarm - Disarm the alarm\n/sequence <sequence> - Send a custom sequence")
    elif command == '/status':
        GLOBAL_editingMessage = False
        time.sleep(0.05)
        GLOBAL_currentMessageId = bot.sendMessage(chat_id, getAllZoneStatusAsString(), parse_mode='Markdown')['message_id']
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
        sendCodeArmDisarm(chat_id, GLOBAL_pendingConfirmationArmDisarm[1:])
        GLOBAL_pendingConfirmationArmDisarm = None
    elif command.startswith('/sequence'):
        sendCustomSequence(chat_id, command)

def startCountdownThenCheckIfArmed(timeToWait, chat_id):
    """
    Starts a countdown timer for N seconds, then check if the alarm is armed.
    """
    time.sleep(timeToWait)
    if getIsAlarmArmed():
        bot.sendMessage(chat_id, "Alarm is armed.")
    else:
        bot.sendMessage(chat_id, "Alarm is not armed.")

def getAllZoneStatusAsString():
    """
    Returns the status of all zones as a string in Markdown format.
    """
    messageStr = "```Zone_Status\n"
    for friendlyZoneName, zoneStatus in zip(LISTA_friendlyZoneNames[:-1], LISTA_zone[:-1]):
        messageStr += f"{friendlyZoneName.ljust(3 + len(max(LISTA_friendlyZoneNames, key=len)))} {'Open' if zoneStatus == 1 else ''}\n"
    messageStr += f"\n{LISTA_friendlyZoneNames[-1].ljust(3 + len(max(LISTA_friendlyZoneNames, key=len)))} {'Armed' if getIsAlarmArmed() else 'Disarmed'}\n"
    messageStr += f'==============================\n{datetime.datetime.now().strftime("%H:%M:%S")}\n'
    messageStr += "```Use /stop to stop updating status."
    return messageStr

def threadStatusAlarm():
    """
    Starts a thread to update the status of the alarm every second (edit the message).
    """
    global GLOBAL_editingMessage, GLOBAL_currentMessageId, GLOBAL_currentChatId, TIME_threadStatusAlarm_startTime

    TIME_threadStatusAlarm_startTime = time.time()

    while GLOBAL_editingMessage and time.time() - TIME_threadStatusAlarm_startTime < 300: # limit to 5 minutes
        try:
            bot.editMessageText((GLOBAL_currentChatId, GLOBAL_currentMessageId), getAllZoneStatusAsString(), parse_mode='Markdown')
        except Exception as e:
            print(e)
        time.sleep(1)

    if GLOBAL_editingMessage:
        bot.editMessageText((GLOBAL_currentChatId, GLOBAL_currentMessageId), "Stopped updating status automatically after 300 seconds.")
        GLOBAL_editingMessage, GLOBAL_currentMessageId, GLOBAL_currentChatId = False, None, None

def getIsAlarmArmed():
    """
    Returns True if the alarm is armed, False otherwise.
    """
    # inverted logic
    return LISTA_zone[5] == 0 # Zone 6

def sendCodeArmDisarm(chat_id, armOrDisarm):
    """
    Sends the code to the Arduino to arm/disarm or authorize.
    """
    isArmed = getIsAlarmArmed()
    if armOrDisarm == "arm" and isArmed:
        bot.sendMessage(chat_id, "Alarm is already armed.")
        return
    elif armOrDisarm == "disarm" and not isArmed:
        bot.sendMessage(chat_id, "Alarm is already disarmed.")
        return

    serialSendCommand("keypad$#")
    for char in codAccess:
        serialSendCommand(f"keypad${char}")
    
    if armOrDisarm == "arm":
        bot.sendMessage(chat_id, "Code sent. Waiting confirmation...")

        thread = threading.Thread(target=startCountdownThenCheckIfArmed, args=(CONFIG_entryDelay, chat_id))
        thread.start()
    else:
        time.sleep(0.5)
        if getIsAlarmArmed():
            bot.sendMessage(chat_id, "Alarm not disarmed.")
        else:
            bot.sendMessage(chat_id, "Alarm disarmed.")

def sendCustomSequence(chat_id, sequence):
    """
    Sends a custom sequence to the Arduino.
    """
    if len(sequence.split(' ')) < 2:
        bot.sendMessage(chat_id, "Usage: /sequence <sequence>")
        return
    
    sequence = sequence.split(' ')[1]

    if not all(char in "1234567890#*" for char in sequence):
        bot.sendMessage(chat_id, "Invalid sequence.\nAllowed characters: 0-9, #, *")
        return
    
    for char in sequence:
        serialSendCommand(f"keypad${char}")
        time.sleep(0.1)
    
    bot.sendMessage(chat_id, f"Sequence sent: {sequence}")

def main():
    try:
        MessageLoop(bot, handle).run_as_thread()
        print('I am listening ...')

        # Start a thread to read the serial port for responses
        response_thread = threading.Thread(target=serialReadResponse)
        # response_thread.daemon = True
        response_thread.start()

        while True:
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nExiting program.")

    finally:
        if ser.is_open:
            ser.close()
            print("Serial connection closed.")

if __name__ == "__main__":
    main()