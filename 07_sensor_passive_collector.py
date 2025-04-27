#!/usr/bin/env python3

# Author: Mani Amoozadeh
# Email: mani.amoozadeh2@gmail.com

import asyncio
from bleak import BleakScanner
from datetime import datetime

sensor_list = [
    {
        "name": "sensor1",
        "location": "bedroom",
        "mac_address": "A4:C1:38:AA:EA:0D"
    },
    {
        "name": "sensor2",
        "location": "outside",
        "mac_address": "A4:C1:38:AA:EA:1D"
    }
]

sensor_dict = {
    sensor["mac_address"]: sensor for sensor in sensor_list
}

TARGET_MACS = set(sensor_dict.keys())

# Environmental Sensing
UUID_ENV_SENSING = "0000181a-0000-1000-8000-00805f9b34fb"

_data_callbacks = []


def parse_custom_payload(data, advertisement_data):
    """
        Parses the custom advertisement payload according to the firmware spec.
    """

    if len(data) < 13:
        return None  # Payload too short to parse

    try:

        mac = ":".join(f"{b:02X}" for b in data[0:6])
        temp_raw = int.from_bytes(data[6:8], byteorder="big", signed=True)
        humidity = data[8]
        battery = data[9]
        voltage_raw = int.from_bytes(data[10:12], byteorder="big")
        frame_counter = data[12]

        temp = temp_raw / 10.0
        voltage = voltage_raw / 1000.0

        rssi = advertisement_data.rssi
        distance = estimate_distance(rssi)
        if distance:
            distance = round(distance, 2)

        entry = {
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Temperature": round(temp, 2),
            "Humidity (%)": humidity,
            "Battery Level (%)": battery,
            "Battery Voltage (V)": round(voltage, 3),
            "Frame Counter": frame_counter,
            "RSSI": rssi,
            "Distance (m)": distance
        }

        sensor_entry = sensor_dict.get(mac, {})
        entry.update(sensor_entry)

        return entry

    except Exception as e:
        print(f"Error parsing payload: {e}")
        return None


def estimate_distance(rssi, tx_power=-59):
    """
        Estimate distance based on RSSI.
        tx_power = expected RSSI at 1 meter (usually -59 dBm for BLE)
    """

    if rssi == 0:
        return None

    ratio = rssi / tx_power

    if ratio < 1.0:
        return pow(ratio, 10)
    else:
        return 0.89976 * pow(ratio, 7.7095) + 0.111


async def scan():
    """
        Start scanning for BLE advertisements.
        Parsed sensor data is passed to all registered callbacks.
    """

    def detection_callback(device, advertisement_data):

        if device.address.upper() not in TARGET_MACS:
            return  # Ignore other devices

        service_data = advertisement_data.service_data

        for uuid, payload in service_data.items():

            if not uuid.lower().startswith(UUID_ENV_SENSING[:8]):
                continue

            parsed = parse_custom_payload(payload, advertisement_data)
            if not parsed:
                continue

            # Notify all registered callbacks
            for callback in _data_callbacks:
                callback(parsed)

    print(f"Listening for passive data...")
    scanner = BleakScanner(detection_callback)
    await scanner.start()

    try:
        while True:
            await asyncio.sleep(5)
    except KeyboardInterrupt:
        await scanner.stop()
        print("\nStopped scanning.")


def register_callback(callback):
    """
        Register a callback to receive parsed sensor data.
        The callback should accept one argument (the parsed dictionary).
    """

    _data_callbacks.append(callback)


if __name__ == "__main__":

    def print_sensor_data(data):
        print(f"\n[+] Received Data:")
        for key, value in data.items():
            print(f"      {key}: {value}")

    register_callback(print_sensor_data)
    asyncio.run(scan())
