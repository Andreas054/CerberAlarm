const int nrInputZone = 6;
// const int listaInputZone[] = {22, 24, 26, 28, 30, 32, 34};
const int listaInputZone[] = {13, 14, 15, 16, 17, 19}; //, 1};

const int nrOutputTastatura = 12;
const char* keys[] = {"1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "*", "#"};
// const int listaOutputTastatura[] = {23, 25, 27, 29, 31, 33, 35, 37, 39, 41, 43, 45};
const int listaOutputTastatura[] = {18, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12};

unsigned long oneHourTime = 0;

void setup() {
  Serial.begin(9600);   // Start serial communication at 9600 baud

  for (int i = 0; i < nrInputZone; i++) {
    pinMode(listaInputZone[i], INPUT_PULLUP);
  }

  for (int i = 0; i < nrOutputTastatura; i++) {
    pinMode(listaOutputTastatura[i], OUTPUT);
    digitalWrite(listaOutputTastatura[i], LOW);
  }
}

void loop() {
  for (int i = 0; i < nrInputZone; i++) {
    int valueOfInputZone = digitalRead(listaInputZone[i]);

    if (valueOfInputZone != 0) {
      Serial.print("zone$");
      Serial.print(i + 1);
      Serial.print("$");
      Serial.println(valueOfInputZone);
      delay(250);
    }
  }

  if (millis() - oneHourTime >= 900 * 1000UL) {
    oneHourTime = millis();
    for (int i = 0; i < nrInputZone; i++) {
      int valueOfInputZone = digitalRead(listaInputZone[i]);
      Serial.print("zone$");
      Serial.print(i + 1);
      Serial.print("$");
      Serial.println(valueOfInputZone);
      delay(250);
    }
  }


  
  static String inputString = "";  // Stores the input string

  // Check if there is data available on the Serial Monitor
  while (Serial.available() > 0) {
    char receivedChar = Serial.read();  // Read the next character

    // Check for end of line (Enter key)
    if (receivedChar == '\n') {
      processMessage(inputString);  // Process the complete input string
      inputString = "";             // Clear the input buffer
    } else if (receivedChar != '\r') { // Exclude carriage return (if any)
      inputString += receivedChar;     // Append character to input buffer
    }
  }
}



void processMessage(String message) {
  // Split the message into parts based on the '$' delimiter
  int firstDelimiter = message.indexOf('$');

  if (firstDelimiter != -1) {
    String command = message.substring(0, firstDelimiter);         // Extract the command
    String keyToPressStr = message.substring(firstDelimiter + 1);

    // Check if the command is "disp"
    if (command == "keypad") {
      // int keyToPress = keyToPressStr.toInt(); // Convert key to integer

      for (int i = 0; i < nrOutputTastatura; i++) {
        if (keyToPressStr == keys[i]) {
          delay(100);
          digitalWrite(listaOutputTastatura[i], HIGH);
          delay(500);
          digitalWrite(listaOutputTastatura[i], LOW);
          break;
        }
      }


    } else {
    }
  } else {
  }
}
