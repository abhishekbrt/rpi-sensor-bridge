#include <Arduino.h>
#include <DHT.h>

/*
  Arduino -> Raspberry Pi serial payload (one JSON line per sample):
  {"pir":1,"dht11_temp_c":29.0,"dht11_humidity":61.0,"lm393_raw":678,"lm393_lux":337.5}

  Library needed:
  - DHT sensor library by Adafruit
*/

#define DHT_PIN 2
#define DHT_TYPE DHT11
#define PIR_PIN 3
#define LM393_ANALOG_PIN A0
#define SAMPLE_INTERVAL_MS 2000

DHT dht(DHT_PIN, DHT_TYPE);
unsigned long last_sample_ms = 0;

static int digital_to_binary(int value) {
  return value == HIGH ? 1 : 0;
}

static int clamp_int(int value, int min_value, int max_value) {
  if (value < min_value) return min_value;
  if (value > max_value) return max_value;
  return value;
}

static float lm393_raw_to_lux(int raw_value) {
  // LM393 modules expose a relative analog level. We map 0-1023 to an estimated 0-1000 lux range.
  const int clamped = clamp_int(raw_value, 0, 1023);
  return (static_cast<float>(clamped) / 1023.0f) * 1000.0f;
}

void setup() {
  Serial.begin(9600);
  pinMode(PIR_PIN, INPUT);
  pinMode(LM393_ANALOG_PIN, INPUT);
  dht.begin();
  delay(1000);
}

void loop() {
  const unsigned long now = millis();
  if (now - last_sample_ms < SAMPLE_INTERVAL_MS) {
    return;
  }
  last_sample_ms = now;

  float humidity = dht.readHumidity();
  float temp_c = dht.readTemperature();
  if (isnan(humidity) || isnan(temp_c)) {
    return;
  }

  // Clamp to the DHT11 range expected by the Raspberry Pi validator.
  if (temp_c < 0.0f) temp_c = 0.0f;
  if (temp_c > 50.0f) temp_c = 50.0f;
  if (humidity < 20.0f) humidity = 20.0f;
  if (humidity > 90.0f) humidity = 90.0f;

  const int pir = digital_to_binary(digitalRead(PIR_PIN));
  const int lm393_raw = clamp_int(analogRead(LM393_ANALOG_PIN), 0, 1023);
  const float lm393_lux = lm393_raw_to_lux(lm393_raw);

  Serial.print("{\"pir\":");
  Serial.print(pir);
  Serial.print(",\"dht11_temp_c\":");
  Serial.print(temp_c, 1);
  Serial.print(",\"dht11_humidity\":");
  Serial.print(humidity, 1);
  Serial.print(",\"lm393_raw\":");
  Serial.print(lm393_raw);
  Serial.print(",\"lm393_lux\":");
  Serial.print(lm393_lux, 1);
  Serial.println("}");
}
