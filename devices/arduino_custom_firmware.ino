/*
 * Project: Arduino R4 Minima Controller
 * Pins updated to include D13 as Digital Output 3
 */

const int PIN_DIG_OUT_1 = 2;
const int PIN_DIG_OUT_2 = 12;
const int PIN_DIG_OUT_3 = 13; // Built-in LED

const int PIN_DIG_IN_1  = 7;
const int PIN_DIG_IN_2  = 11;
const int PIN_PWM_IN    = 8;

const int PIN_ANA_OUT_1 = A0;  
const int PIN_ANA_OUT_2 = 3;   
const int PIN_ANA_OUT_3 = 6;   
const int PIN_ANA_OUT_4 = 9;   
const int PIN_PWM_OUT   = 10;  

const int PIN_ANA_IN_1  = A1;
const int PIN_ANA_IN_2  = A2;

String inputString = "";         
bool stringComplete = false;  

void setup() {
  Serial.begin(115200);
  inputString.reserve(50);

  analogWriteResolution(12); 
  analogReadResolution(12);  

  pinMode(PIN_DIG_OUT_1, OUTPUT);
  pinMode(PIN_DIG_OUT_2, OUTPUT);
  pinMode(PIN_DIG_OUT_3, OUTPUT); // D13 Setup
  
  pinMode(PIN_ANA_OUT_1, OUTPUT);
  pinMode(PIN_ANA_OUT_2, OUTPUT);
  pinMode(PIN_ANA_OUT_3, OUTPUT);
  pinMode(PIN_ANA_OUT_4, OUTPUT);
  pinMode(PIN_PWM_OUT, OUTPUT);

  pinMode(PIN_DIG_IN_1, INPUT_PULLUP);
  pinMode(PIN_DIG_IN_2, INPUT_PULLUP);
  pinMode(PIN_PWM_IN, INPUT);
}

void loop() {
  if (stringComplete) {
    parseCommand(inputString);
    inputString = "";
    stringComplete = false;
  }

  // Stream current data back to Python
  Serial.print("DATA:");
  Serial.print(digitalRead(PIN_DIG_IN_1)); Serial.print(",");
  Serial.print(digitalRead(PIN_DIG_IN_2)); Serial.print(",");
  Serial.print(analogRead(PIN_ANA_IN_1)); Serial.print(",");
  Serial.print(analogRead(PIN_ANA_IN_2)); Serial.print(",");
  Serial.println(pulseIn(PIN_PWM_IN, HIGH, 20000));

  delay(10); 
}

void parseCommand(String cmd) {
  int colonIndex = cmd.indexOf(':');
  if (colonIndex == -1) return;

  String key = cmd.substring(0, colonIndex);
  int val = cmd.substring(colonIndex + 1).toInt();

  if (key == "DO1")      digitalWrite(PIN_DIG_OUT_1, val > 0 ? HIGH : LOW);
  else if (key == "DO2") digitalWrite(PIN_DIG_OUT_2, val > 0 ? HIGH : LOW);
  else if (key == "DO3") digitalWrite(PIN_DIG_OUT_3, val > 0 ? HIGH : LOW); // New DO3
  else if (key == "AO1") analogWrite(PIN_ANA_OUT_1, val);
  else if (key == "AO2") analogWrite(PIN_ANA_OUT_2, val);
  else if (key == "AO3") analogWrite(PIN_ANA_OUT_3, val);
  else if (key == "AO4") analogWrite(PIN_ANA_OUT_4, val);
  else if (key == "PWMO") analogWrite(PIN_PWM_OUT, val);
}

void serialEvent() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    if (inChar == '\n') stringComplete = true;
    else inputString += inChar;
  }
}