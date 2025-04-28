#!/usr/bin/env python3

# Author: Mani Amoozadeh
# Email: mani.amoozadeh2@gmail.com

import struct
import asyncio
from bleak import BleakClient
from datetime import datetime

# BLE device MAC address
mac_address = "A4:C1:38:AA:EA:0D"

# UUID for temperature/humidity/voltage data
UUID_DATA = "EBE0CCC1-7A0A-4B0C-8A1A-6FF2997DA3A6"

def notification_handler(sender, data):

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    temperature, humidity, voltage = struct.unpack_from('<hBh', data)
    temperature /= 100
    voltage /= 1000
    battery_percent = min(int(round((voltage - 2.1),2) * 100), 100)

    print(
        f"{now} Sender: {sender.uuid}  "
        f"Temperature: {temperature:6.2f} °C "
        f"Humidity: {humidity:3d} % "
        f"Voltage: {voltage:5.2f} V "
        f"Estimated Battery: {battery_percent:3d} %"
    )


async def main():

    try:

        async with BleakClient(mac_address, timeout=20) as client:

            # Subscribe to notifications
            await client.start_notify(UUID_DATA, notification_handler)

            print("Subscribed to notifications. Listening...")

            # Keep the program running to receive notifications
            await asyncio.sleep(60)

            # Stop notifications
            await client.stop_notify(UUID_DATA)

    except Exception as e:

        print(f"Error: cannot connect. {e}")


if __name__ == "__main__":

    asyncio.run(main())
