#!/usr/bin/env python3

# Author: Mani Amoozadeh
# Email: mani.amoozadeh2@gmail.com
# Description: Getting BLE services and characterisitics

from bluepy import btle

mac_address = "A4:C1:38:AA:EA:0D"

peripheral = btle.Peripheral(mac_address)

for service in peripheral.getServices():

    print(f"Service: {service.uuid}")

    try:
        for char in service.getCharacteristics():
            props = char.propertiesToString()
            print(f"  Characteristic: {char.uuid} (Handle: 0x{char.getHandle():04x}) - Properties: {props}")
    except Exception as e:
        print(f"Error: {e}")
