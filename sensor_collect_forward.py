#!/usr/bin/env python3

# Author: Mani Amoozadeh
# Email: mani.amoozadeh2@gmail.com

import asyncio
import datetime
import socket
import getpass
import sensor_collector
from influxdb_access import InfluxDB_Access

def handle_sensor_data(data):

    print("Received new data:", data)

    data_ts = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    sensor_name = data.pop("name", None)
    sensor_location = data.pop("location", None)
    sensor_mac = data.pop("mac_address", None)

    data_dict = {
        "measurement": "ble_sensor",
        "tags": {
            "hostname": socket.gethostname(),  # collector hostname
            "username": getpass.getuser(),  # collector username
            "sensor_name": sensor_name,
            "sensor_location": sensor_location,
            "sensor_mac": sensor_mac
        },
        "fields": data,
        "time": data_ts
    }

    status, output = InfluxDB_Access.write_points(data_dict)
    if not status:
        print(f"telemetry reporting failed: {output}")


sensor_collector.register_callback(handle_sensor_data)

asyncio.run(sensor_collector.scan())
