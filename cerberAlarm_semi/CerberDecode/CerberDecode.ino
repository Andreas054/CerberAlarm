// (C) Kirils Solovjovs

#define pin_clock 8 // yellow
#define pin_data 12 // green
#define pin_data_transistor 10 // green out according to DSC?

#define MASTER 1
#define SLAVE 0

int clock_previous = 0;
unsigned long int timer = 0;

int bit_cnt[2] = {0, 0};
int byte_cnt[2] = {0, 0};
int hex_nibble_cnt[2] = {0, 0};

byte incoming[2][64];
char incoming_hex[2][200]; // 64x3

char hexmap[0x10] = {
  '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
  'A', 'B', 'C', 'D', 'E', 'F'
};

bool sending = false; // Flag to indicate sending mode
byte sendBuffer[64];  // Buffer for data to send
int sendBufferLength = 0;
int sendBufferIndex = 0;

void storeBit(byte source, byte bitvalue) {
  incoming[source][byte_cnt[source]] <<= 1;
  incoming[source][byte_cnt[source]] += bitvalue;

  if (++bit_cnt[source] % 4 == 0) // Two nibbles stored
    incoming_hex[source][hex_nibble_cnt[source]++] = hexmap[incoming[source][byte_cnt[source]] & 0xf];

  if (bit_cnt[source] == 8)
    incoming_hex[source][hex_nibble_cnt[source]++] = ' ';

  if (bit_cnt[source] == 8) {
    byte_cnt[source]++;
    if (byte_cnt[source] >= 64) // Crude overflow protection
      byte_cnt[source] = 0;

    bit_cnt[source] = 0;
  }
}

void sendByte(byte data) {
  for (int i = 7; i >= 0; i--) {
    // Wait for clock to go low
    while (digitalRead(pin_clock) != LOW);

    // Set the data line via transistor
    digitalWrite(pin_data_transistor, (data & (1 << i)) ? LOW : HIGH);

    // Wait for clock to go high
    while (digitalRead(pin_clock) != HIGH);
  }
}

void sendData() {
  if (sendBufferIndex < sendBufferLength) {
    sendByte(sendBuffer[sendBufferIndex]);
    sendBufferIndex++;
  } else {
    // Reset sending state
    sending = false;
    sendBufferIndex = 0;
    sendBufferLength = 0;
  }
}

void setup() { 
  pinMode(pin_clock, INPUT);
  pinMode(pin_data, INPUT);
  pinMode(pin_data_transistor, OUTPUT);
  digitalWrite(pin_data_transistor, LOW);
  Serial.begin(115200);
}

void loop() {
  if (sending) {
    sendData();
    return;
  }

  byte clock_current = digitalRead(pin_clock);

  if (clock_current != clock_previous) { // New bit being sent on data line
    delayMicroseconds(50); // Add tolerance
    timer = micros();

    if (clock_previous == HIGH)
      storeBit(MASTER, digitalRead(pin_data) & 1);
    else
      storeBit(SLAVE, 1 - digitalRead(pin_data) & 1);

    clock_previous = clock_current;

  } else if (abs(micros() - timer) > 2000 && byte_cnt[MASTER]) { // No clock change for some time and there is data collected

    // Do pre-processing here if needed

    for (int i = SLAVE; i <= MASTER; i++) { // ;)
      incoming_hex[i][hex_nibble_cnt[i]++] = '\0';
      if (i == SLAVE) {
        Serial.print("SLAVE: ");
        Serial.println(incoming_hex[i]);
      } else {
        Serial.print("MASTR: ");
        Serial.println(incoming_hex[i]);
      }

      bit_cnt[i] = byte_cnt[i] = hex_nibble_cnt[i] = 0; // Reset counters between frames
    }
  }

  // Example: Send data when "SEND " is received
  if (Serial.available() > 0) {
    String input = Serial.readString();
    if (input.startsWith("SEND ")) {
      String hexData = input.substring(5); // Get the hex data to send
      sendBufferLength = 0;

      for (int i = 0; i < hexData.length(); i += 2) {
        if (i + 1 < hexData.length()) {
          byte value = (strtol(hexData.substring(i, i + 2).c_str(), NULL, 16) & 0xFF);
          sendBuffer[sendBufferLength++] = value;
        }
      }

      sending = true; // Start sending data
      sendBufferIndex = 0;
    }
  }
}
