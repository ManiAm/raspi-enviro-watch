#!/usr/bin/env python3

# Author: Mani Amoozadeh
# Email: mani.amoozadeh2@gmail.com

import asyncio
import sensor_collector

def handle_sensor_data(data):
    print("Received new data:", data)

sensor_collector.register_callback(handle_sensor_data)

asyncio.run(sensor_collector.scan())
