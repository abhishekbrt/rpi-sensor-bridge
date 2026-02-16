import unittest

from bridge.serial_reader import parse_serial_line


class SerialReaderParsingTests(unittest.TestCase):
    def test_parse_serial_line_accepts_valid_json(self) -> None:
        line = '{"pir":1,"dht11_temp_c":28.5,"dht11_humidity":62.0,"lm393_raw":678,"lm393_lux":337.5}'

        parsed = parse_serial_line(line)

        self.assertEqual(
            parsed,
            {
                "pir": 1,
                "dht11_temp_c": 28.5,
                "dht11_humidity": 62.0,
                "lm393_raw": 678,
                "lm393_lux": 337.5,
            },
        )

    def test_parse_serial_line_rejects_invalid_json(self) -> None:
        with self.assertRaisesRegex(ValueError, "Invalid JSON"):
            parse_serial_line("this-is-not-json")

    def test_parse_serial_line_rejects_missing_keys(self) -> None:
        with self.assertRaisesRegex(ValueError, "Missing required key"):
            parse_serial_line('{"pir":1}')

    def test_parse_serial_line_rejects_non_numeric_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be numeric"):
            parse_serial_line(
                '{"pir":"motion","dht11_temp_c":28.5,"dht11_humidity":62.0,"lm393_raw":600,"lm393_lux":400.0}'
            )

    def test_parse_serial_line_rejects_non_binary_pir(self) -> None:
        with self.assertRaisesRegex(ValueError, "pir must be 0 or 1"):
            parse_serial_line(
                '{"pir":2,"dht11_temp_c":28.5,"dht11_humidity":62.0,"lm393_raw":600,"lm393_lux":400.0}'
            )

    def test_parse_serial_line_rejects_out_of_range_lm393_raw(self) -> None:
        with self.assertRaisesRegex(ValueError, "lm393_raw out of range"):
            parse_serial_line('{"pir":1,"dht11_temp_c":28.5,"dht11_humidity":62.0,"lm393_raw":1050,"lm393_lux":400.0}')

    def test_parse_serial_line_rejects_negative_lm393_lux(self) -> None:
        with self.assertRaisesRegex(ValueError, "lm393_lux out of range"):
            parse_serial_line('{"pir":1,"dht11_temp_c":28.5,"dht11_humidity":62.0,"lm393_raw":600,"lm393_lux":-1.0}')

    def test_parse_serial_line_rejects_out_of_range_dht11_temperature(self) -> None:
        with self.assertRaisesRegex(ValueError, "dht11_temp_c out of range"):
            parse_serial_line(
                '{"pir":1,"dht11_temp_c":55.0,"dht11_humidity":62.0,"lm393_raw":600,"lm393_lux":400.0}'
            )

    def test_parse_serial_line_rejects_out_of_range_dht11_humidity(self) -> None:
        with self.assertRaisesRegex(ValueError, "dht11_humidity out of range"):
            parse_serial_line(
                '{"pir":1,"dht11_temp_c":28.5,"dht11_humidity":95.0,"lm393_raw":600,"lm393_lux":400.0}'
            )


if __name__ == "__main__":
    unittest.main()
