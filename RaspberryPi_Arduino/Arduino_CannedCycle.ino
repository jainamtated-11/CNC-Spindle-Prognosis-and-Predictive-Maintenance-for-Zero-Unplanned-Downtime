#include <Wire.h>
#include <Adafruit_MCP4725.h>

Adafruit_MCP4725 dac;

unsigned long startMillis = 0;
int dacState = 0;
bool dacRunning = false;

const int spindlePin = 9; // PWM pin to control spindle (adjust if needed)

void setup() {
  Serial.begin(115200);
  dac.begin(0x60);  // MCP4725 I2C address
  delay(2000);      // Let serial stabilize

  Serial.println("System Ready");

  pinMode(6, INPUT);   // D6 - trigger input
  pinMode(5, OUTPUT);  // D5 - output mirror

  pinMode(1, INPUT);   // D1 - 100 Hz
  pinMode(2, INPUT);   // D2 - 200 Hz
  pinMode(3, INPUT);   // D3 - 300 Hz
  pinMode(4, INPUT);   // D4 - 400 Hz

  pinMode(spindlePin, OUTPUT); // PWM output pin
}

void loop() {
  bool d6High = digitalRead(6) == HIGH;
  digitalWrite(5, d6High ? HIGH : LOW);

  // Debug print every second
  static unsigned long lastDebug = 0;
  if (millis() - lastDebug >= 1000) {
    Serial.print("D6: ");
    Serial.print(d6High ? "HIGH" : "LOW");
    Serial.print(" | D5: ");
    Serial.println(digitalRead(5) == HIGH ? "HIGH" : "LOW");
    lastDebug = millis();
  }

  // Frequency selection logic when D6 is HIGH
  if (d6High) {
    if (digitalRead(1) == HIGH) {
      tone(spindlePin, 100);
      Serial.println("Spindle: 100 Hz");
    } else if (digitalRead(2) == HIGH) {
      tone(spindlePin, 200);
      Serial.println("Spindle: 200 Hz");
    } else if (digitalRead(3) == HIGH) {
      tone(spindlePin, 300);
      Serial.println("Spindle: 300 Hz");
    } else if (digitalRead(4) == HIGH) {
      tone(spindlePin, 400);
      Serial.println("Spindle: 400 Hz");
    } else {
      noTone(spindlePin); // No selection, turn off spindle
    }
  } else {
    noTone(spindlePin); // D6 is LOW, turn off spindle
  }

  // DAC logic
  if (d6High && !dacRunning) {
    startMillis = millis();
    dacState = 0;
    dacRunning = true;
    dac.setVoltage(4095, false);  // 5V
    Serial.println("DAC: 5V");
  }

  if (dacRunning) {
    unsigned long nowMillis = millis();
    if (dacState == 0 && nowMillis - startMillis >= 10000) {
      dac.setVoltage(2457, false);  // 3V
      Serial.println("DAC: 3V");
      dacState = 1;
    } else if (dacState == 1 && nowMillis - startMillis >= 20000) {
      dac.setVoltage(900, false);   // 1V
      Serial.println("DAC: 1V");
      dacState = 2;
    } else if (dacState == 2 && nowMillis - startMillis >= 30000) {
      dac.setVoltage(0, false);     // 0V
      Serial.println("DAC: 0V");
      dacState = 3; // Hold
    }
  }

  // Reset everything if D6 goes LOW
  if (!d6High && dacRunning) {
    dac.setVoltage(0, false);
    dacState = 0;
    startMillis = 0;
    dacRunning = false;
    Serial.println("DAC stopped, reset.");
  }
}
