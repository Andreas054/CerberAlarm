# CerberAlarm Semi primitive

## Sending commands
Sending data over the bus wires. (**not working correctly**)
```
SEND${5-digit-hex}

i.e.
SEND$FFFB7
```

Bypass zones
```
BYPASS${zone}

zone = 1-4

i.e.
BYPASS$5

Response ack:
G00*00
where * is the {zone} which was bypassed
```

Unbypass zones
```
UNBYPASS${zone}

zone = 1-4

i.e.
UNBYPASS$5

Response ack:
H00*01
where * is the {zone} which was bypassed
```

List all zones if bypassed or not
```
LISTBYPASS$

Response:
L****0
where * is either 1 or 0 for each zones 1-4

i.e. zones 2 and 4 are bypassed
L01010
```

Arm/Disarm with Zone 5 which is defined as Key
```
KEY$

Response ack:
I00000
```

Reset smoke sensors (turn relay [NC] powering them on and off)
```
RESETFUM$

No response ack...
```
 
## Telegram bot controlling Cerber alarm

```sh
python3 -m pip install pyserial telepot
```

Arduino UNO to which I connected yellow (clock), green (data) and ground wires from the alarm.

[Arduino code source](https://github.com/0ki/paradox)

[Wiring to also write to alarm system](https://github.com/Dilbert66/esphome-dsckeybus?tab=readme-ov-file#non-isolated-simple-version)