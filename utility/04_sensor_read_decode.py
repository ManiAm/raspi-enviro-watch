#!/usr/bin/env python3

# Author: Mani Amoozadeh
# Email: mani.amoozadeh2@gmail.com

import struct
import asyncio
from bleak import BleakClient
from datetime import datetime

mac_address = "A4:C1:38:AA:EA:0D"

UUID_UNITS   = "EBE0CCBE-7A0A-4B0C-8A1A-6FF2997DA3A6"
UUID_DATA    = "EBE0CCC1-7A0A-4B0C-8A1A-6FF2997DA3A6"
UUID_BATTERY = "EBE0CCC4-7A0A-4B0C-8A1A-6FF2997DA3A6"
UUID_TIME    = "EBE0CCB7-7A0A-4B0C-8A1A-6FF2997DA3A6"

UNITS = {
    b'\x00': '°C',
    b'\x01': '°F'
}

if __name__ == "__main__":

    async def read_characteristics(address):

        try:

            print(f"Connecting to BLE device at {mac_address}")

            async with BleakClient(address, timeout=20) as client:

                if not client.is_connected:
                    print("Failed to connect!")
                    return

                print(f"Connected to {address}\n")

                ###############################

                try:
                    value = await client.read_gatt_char(UUID_UNITS)
                except Exception as e:
                    print(f"({UUID_UNITS}): {e}")

                unit = UNITS[bytes(value)]

                ###############################

                try:
                    value = await client.read_gatt_char(UUID_DATA)
                except Exception as e:
                    print(f"({UUID_DATA}): {e}")

                temperature, humidity, voltage = struct.unpack_from('<hBh', value)
                temperature /= 100
                voltage /= 1000

                # Estimate the battery percentage remaining
                # 3.1 or above --> 100%
                # 2.1 --> 0 %
                battery_percent = min(int(round((voltage - 2.1),2) * 100), 100)

                print(f"temperature: {temperature} {unit}, humidity: {humidity} %, voltage: {voltage} V, estimated_battery: {battery_percent} %")

                ###############################

                try:
                    value = await client.read_gatt_char(UUID_BATTERY)
                except Exception as e:
                    print(f"({UUID_BATTERY}): {e}")

                battery = ord(value) # shows a wrong value

                print(f"battery: {battery} %")

                ###############################

                try:
                    value = await client.read_gatt_char(UUID_TIME)
                except Exception as e:
                    print(f"({UUID_TIME}): {e}")

                if len(value) == 5:
                    ts, tz_offset = struct.unpack('Ib', value)
                else:
                    ts = struct.unpack('I', value)[0]
                    tz_offset = 0

                _ = datetime.fromtimestamp(ts), tz_offset

                print(f"time: {datetime.fromtimestamp(ts)}")

        except Exception as e:

            print(f"Error: cannot connect. {e}")

    asyncio.run(read_characteristics(mac_address))
