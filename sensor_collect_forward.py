#!/usr/bin/env python3

# Author: Mani Amoozadeh
# Email: mani.amoozadeh2@gmail.com

import asyncio
import datetime
import socket
import getpass
import redis

import sensor_collector
from influxdb_access import InfluxDB_Access

redis_h = redis.Redis(host='localhost', port=6379, db=0)

def handle_sensor_data(data):

    if is_duplicate(data):
        return

    print(f"\n[+] Received new Data:")
    for key, value in data.items():
        print(f"      {key}: {value}")

    forward_influxdb(data)


def is_duplicate(data, ttl_seconds=2*60):
    """
        Checks if (MAC, Frame Counter) combo has already been seen using Redis.
    """

    mac_address = data.get("mac_address", None)
    frame_counter = data.get("frame_counter", None)

    if not mac_address or not frame_counter:
        print("Error: mac_address or frame_counter is missing!")
        return False  # still proceed

    key = f"dedup:{mac_address.upper()}:{frame_counter}"

    # NX = Only set the key if it does not already exist
    result = redis_h.set(key, 1, nx=True, ex=ttl_seconds)

    if result:
        return False  # Successfully set, it's a new entry

    return True  # Key already exists, it's a duplicate


def forward_influxdb(data):

    data_ts = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    sensor_name = data.pop("name", None)
    sensor_location = data.pop("location", None)
    sensor_mac = data.pop("mac_address", None)

    data_dict = {
        "measurement": "ble_sensor",
        "tags": {
            "hostname": socket.gethostname(),  # collector hostname
            "username": getpass.getuser(),     # collector username
            "sensor_name": sensor_name,
            "sensor_location": sensor_location,
            "sensor_mac": sensor_mac
        },
        "fields": data,
        "time": data_ts
    }

    status, output = InfluxDB_Access.write_points(data_dict)
    if not status:
        print(f"write_points failed: {output}")

sensor_collector.register_callback(handle_sensor_data)

asyncio.run(sensor_collector.scan())
