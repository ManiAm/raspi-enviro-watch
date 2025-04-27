#!/usr/bin/env python3

# Author: Mani Amoozadeh
# Email: mani.amoozadeh2@gmail.com

import asyncio
from bleak import BleakClient

mac_address = "A4:C1:38:AA:EA:0D"

UUID_UNITS   = "EBE0CCBE-7A0A-4B0C-8A1A-6FF2997DA3A6"

UNITS = {
    b'\x00': '°C',
    b'\x01': '°F'
}

async def write_characteristics(address, desired_unit=None):

    try:
        print(f"Connecting to BLE device at {mac_address}")

        async with BleakClient(address, timeout=20) as client:

            if not client.is_connected:
                print("Failed to connect!")
                return

            print(f"Connected to {address}\n")

            if desired_unit:
                await set_unit(client, desired_unit)

            try:
                value = await client.read_gatt_char(UUID_UNITS)
                unit = UNITS[bytes(value)]
            except Exception as e:
                print(f"({UUID_UNITS}): {e}")
                unit = "unknown"

            print(f"Unit is {unit}.")

    except Exception as e:
        print(f"Error: cannot connect. {e}")


async def set_unit(client, unit):
    """
        Write unit (°C or °F) to the device.
    """

    if unit.upper() == "C":
        value = b'\x00'
    elif unit.upper() == "F":
        value = b'\x01'
    else:
        print("Invalid unit. Use 'C' or 'F'.")
        return

    try:
        print(f"Setting unit to {unit.upper()}...")
        await client.write_gatt_char(UUID_UNITS, value, response=True)
        print(f"Unit set to {unit.upper()}.\n")
    except Exception as e:
        print(f"Failed to set unit: {e}")


if __name__ == "__main__":

    asyncio.run(write_characteristics(mac_address, desired_unit="F"))
