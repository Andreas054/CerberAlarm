# CerberAlarm Primitive
 
## Telegram bot controlling Cerber alarm

```sh
python3 -m pip install pyserial telepot
```

Arduino UNO to which I connected:
- ### Input:
  - 5 zone inputs connected in series with each alarm zone input
  - 1 armed status input connected to the PGM of the alarm
  - ~~1 alarm state input connected to the alarm siren~~
- ### Output:
  - 12 wires going to the alarm keypad (1234567890*#)

The Arduino is connected to a Raspberry Pi through a USB cable.
