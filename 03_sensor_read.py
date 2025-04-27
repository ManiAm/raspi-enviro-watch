#!/usr/bin/env python3

# Author: Mani Amoozadeh
# Email: mani.amoozadeh2@gmail.com

import sys
import string
import asyncio
from bluepy import btle
from bleak import BleakClient

mac_address = "A4:C1:38:AA:EA:0D"

def try_decode(value: bytes):
    """
        Try to decode bytes to a UTF-8 string if possible.
        If the decoded string is mostly printable characters, return it.
        Otherwise, return the raw bytes in hex form.
    """

    try:
        decoded = value.decode('utf-8').rstrip('\x00')
        if all(c in string.printable for c in decoded):
            return decoded
        else:
            return value.hex()
    except UnicodeDecodeError:
        return value.hex()


if __name__ == "__main__":

    try:
        peripheral = btle.Peripheral(mac_address)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(0)

    try:

        read_props = []
        for service in peripheral.getServices():
            for char in service.getCharacteristics():
                props = char.propertiesToString()
                if "READ" in props:
                    read_props.append(str(char.uuid))

    finally:
        peripheral.disconnect()

    async def read_characteristics(address):

        async with BleakClient(address, timeout=20) as client:

            if not client.is_connected:
                print("Failed to connect!")
                return

            print(f"Connected to {address}\n")

            for uuid in read_props:

                try:
                    value = await client.read_gatt_char(uuid)
                except Exception as e:
                    print(f"({uuid}): {e}")
                    continue

                output = try_decode(value)
                print(f"({uuid}): {output}")

    asyncio.run(read_characteristics(mac_address))
