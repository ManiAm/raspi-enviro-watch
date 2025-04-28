#!/usr/bin/env python3

# Author: Mani Amoozadeh
# Email: mani.amoozadeh2@gmail.com
# Description: Scan for BLE devices

import asyncio
from bleak import BleakScanner
from tabulate import tabulate
from mac_vendor_lookup import MacLookup
from mac_vendor_lookup import AsyncMacLookup

mac_lookup = AsyncMacLookup()
mac_cache = {}        # cache for MAC -> Company
pending_macs = set()  # macs waiting for lookup


async def get_company_from_mac(mac):

    if mac in mac_cache:
        return mac_cache[mac]

    try:
        company = await mac_lookup.lookup(mac)
    except Exception:
        company = "Unknown"

    mac_cache[mac] = company

    return company


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


def blue_text(text):

    if text:
        return f"\033[94m{text}\033[0m"
    return text


async def main(update_interval=2, filter_unknown=False):

    seen = {}

    def detection_callback(device, advertisement_data):

        mac = device.address
        name = device.name or "(unknown)"

        rssi = advertisement_data.rssi
        distance = estimate_distance(rssi)
        distance = round(distance, 2) if distance is not None else None

        platform_data = advertisement_data.platform_data
        details = platform_data[1]

        entry = {
            "MAC": mac,
            "Company": mac_cache.get(mac, "Looking up..."),
            "Device Name": name,
            "RSSI (dBm)": rssi,
            "Distance (m)": distance,
            "AddressType": details.get("AddressType", None),

            "Paired": blue_text(details.get("Paired", None)),
            "Bonded": blue_text(details.get("Bonded", None)),
            "Trusted": blue_text(details.get("Trusted", None)),
            "Blocked": blue_text(details.get("Blocked", None)),
            "LegacyPairing": blue_text(details.get("LegacyPairing", None)),
            "Connected": blue_text(details.get("Connected", None))
        }

        seen[mac] = entry
        pending_macs.add(mac)


    async def handle_pending_macs():

        while True:

            for mac in list(pending_macs):
                company = await get_company_from_mac(mac)
                seen[mac]["Company"] = company
                pending_macs.remove(mac)
            await asyncio.sleep(0.5)

    scanner = BleakScanner(detection_callback=detection_callback)

    print("Scanning for BLE devices... Press Ctrl+C to stop.\n")
    await scanner.start()

    lookup_task = asyncio.create_task(handle_pending_macs())

    try:

        while True:

            await asyncio.sleep(update_interval)
            print("\033c", end="")  # Clear screen

            print("Discovered Devices:\n")

            devices_list = list(seen.values())

            if filter_unknown:
                devices_list = [
                    d for d in devices_list
                    if d["Device Name"] != "(unknown)" and d["Device Name"].replace("-", ":") != d["MAC"]
                ]

            if devices_list:
                sort_column = "RSSI (dBm)"
                devices_list = sorted(devices_list, key=lambda d: d.get(sort_column, ""), reverse=True)
                print(tabulate(devices_list, headers="keys", tablefmt="pretty"))
            else:
                print("No devices found yet.")

            print("\n(Scanning... Press Ctrl+C to stop.)")

    except asyncio.CancelledError:
        print("\nScan stopped.")

    except KeyboardInterrupt:
        await scanner.stop()
        lookup_task.cancel()
        print("\nScan stopped.")


if __name__ == "__main__":

    #mac = MacLookup()
    #mac.update_vendors()

    asyncio.run(main(filter_unknown=True))
