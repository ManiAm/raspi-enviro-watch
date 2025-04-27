#!/usr/bin/env python3

# Author: Mani Amoozadeh
# Email: mani.amoozadeh2@gmail.com

import os
import sys
import textwrap
import logging
from tabulate import tabulate
from dotenv import load_dotenv

from influxdb_client import InfluxDBClient as InfluxDBClient_url
from influxdb_client import BucketRetentionRules
from influxdb_client.client.write_api import SYNCHRONOUS

import utility

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

load_dotenv()

class InfluxDB_Access():

    def __init__(self,
                 timeout=10_000,
                 url=None,
                 org=None):

        self.client = None
        self.log_influx_db_dir = os.getcwd()
        self.legacy = False
        self.boilerplate_cols = [
            'result',
            'table',
            '_start',
            '_stop',
            '_measurement'
        ]

        token = os.getenv('INFLUXDB_TOKEN', None)
        if not token:
            log.error("InfluxDB_Access: cannot read 'INFLUXDB_TOKEN' env variable")
            sys.exit(2)

        self.client = InfluxDBClient_url(url=url, token=token, org=org, timeout=timeout)


    def get_database_names(self, skip_internal=True):

        try:
            bucket_api = self.client.buckets_api()
            # we might hit this:
            # https://github.com/influxdata/influxdb/issues/18971
            buckets = bucket_api.find_buckets(limit=100)
        except Exception as E:
            return False, str(E)

        names = [x.name for x in buckets.buckets]

        if skip_internal:
            for name in names[:]:
                if name.startswith("_"):
                    names.remove(name)

        names.sort()
        return True, names

    #############

    def dump_tables(self, database=None):

        if not database:
            status, output = self.get_database_names()
            if not status:
                log.error(output)
                sys.exit(2)
            database_list = output
        else:
            database_list = [database]

        for database_name in database_list:
            self.__dump_tables(database_name)


    def __dump_tables(self, bucket_name):

        query_api = self.client.query_api()

        try:

            # https://docs.influxdata.com/influxdb/v2.7/query-data/flux/explore-schema/#list-measurements
            query = f"""
                import "influxdata/influxdb/schema"
                schema.measurements(bucket: "{bucket_name}")
            """

            tables = query_api.query(query=query)

        except Exception as E:
            return False, str(E)

        measurements = []
        for table in tables:
            for record in table.records:
                measurements.append(record.row[2])

        rows = []

        for measurement in sorted(measurements):

            # https://docs.influxdata.com/influxdb/v2.7/query-data/flux/explore-schema/#list-tag-keys-in-a-measurement
            query = f"""
                import "influxdata/influxdb/schema"

                schema.measurementTagKeys(
                  bucket: "{bucket_name}",
                  measurement: "{measurement}"
                )
            """

            tables = query_api.query(query=query)

            tags = []
            for table in tables:
                for record in table.records:
                    tags.append(record.row[2])

            # https://docs.influxdata.com/influxdb/v2.7/query-data/flux/explore-schema/#list-fields-in-a-measurement
            query = f"""
                import "influxdata/influxdb/schema"

                schema.measurementFieldKeys(
                  bucket: "{bucket_name}",
                  measurement: "{measurement}"
                )
            """

            tables = query_api.query(query=query)

            fields = []
            for table in tables:
                for record in table.records:
                    fields.append(record.row[2])

            rows.append([measurement, ', '.join(tags), ', '.join(fields)])

        log.info("\nBucket: %s\n", bucket_name)

        headers = ['Measurement', 'Tag Keys', 'Field Keys']
        log.info(tabulate(rows, headers=headers, tablefmt="grid"))

    #############

    def write_data(self, data_list, database_name):

        if not data_list:
            return False, "write_data: data_list is empty"

        if not isinstance(data_list, list):
            data_list = [data_list]

        # NOTE: If the time field is missing in a data point, InfluxDB will automatically
        # assign a timestamp to the data point based on the server's current time
        # when the data point is written

        # NOTE: duplicate data points:
        # For points that have the same measurement name, tag set, and timestamp,
        # InfluxDB creates a union of the old and new field sets.
        # For any matching field keys, InfluxDB uses the field value of the new point.
        # check example in here:
        #   https://docs.influxdata.com/influxdb/v2.7/write-data/best-practices/duplicate-points/#duplicate-data-points

        for data in data_list[:]:

            # if measurement exists, but has empty value
            measurement = data.get("measurement", None)
            if measurement is None or not measurement:
                data_list.remove(data)
                log.warning("write_data: measurement is missing from data")
                continue

            tags = data.get("tags", None)
            if tags is not None: # if 'tags' exists
                if not tags: # ... but has empty value
                    data_list.remove(data)
                    log.warning("write_data: empty 'tags' is present in data")
                    continue

            # Fields are a required piece of InfluxDB's data structure.
            # You cannot have data in InfluxDB without fields.
            fields = data.get("fields", None)
            if fields is None:
                data_list.remove(data)
                log.warning("write_data: no 'fields' is present in data")
                continue

        if not data_list:
            log.warning("write_data: data to write is empty")
            return True, None

        return self.__write_data(data_list, database_name)


    def __write_data(self, data_list, bucket_name):

        status, output = self.get_database_names()
        if not status:
            return False, output

        database_list = output

        try:
            # Create a new bucket (if not exists)
            if bucket_name not in database_list:

                buckets_api = self.client.buckets_api()

                months = 1
                days = months * 30
                hours = days * 24
                minutes = hours * 60
                seconds = minutes * 60

                retention_rules = BucketRetentionRules(type="expire", every_seconds=seconds)

                buckets_api.create_bucket(bucket_name=bucket_name,
                                          retention_rules=retention_rules)

        except Exception as E:
            return False, f"cannot create bucket {bucket_name}: {E}"

        # the write API waits for the server to confirm that the data was written successfully before
        # returning control back to the caller. This means that the write operation is synchronous
        # i.e., the write API is blocked until the write operation is completed.

        try:
            write_api = self.client.write_api(write_options=SYNCHRONOUS)
            write_api.write(bucket=bucket_name, record=data_list)
        except Exception as E:
            return False, f"cannot write to bucket {bucket_name}: {E}"

        return True, None

    #############

    def read_data(self, query, omit_boilerplate_col=True):

        query = textwrap.dedent(query)
        query = query.strip()

        return self.__read_data(query, omit_boilerplate_col)


    def __read_data(self, query, omit_boilerplate_col):

        try:
            query_api = self.client.query_api()
            tables = query_api.query(query)
        except Exception as E:
            return False, f"query failed: {E}"

        data_dict = {}

        # going over each table
        for table_num, table in enumerate(tables):

            # going over records in each table
            for record_num, record in enumerate(table.records):

                entry = {}

                for key, val in record.values.items():

                    if omit_boilerplate_col and key in self.boilerplate_cols:
                        continue

                    entry[key] = val

                if entry:
                    utility.add_key(data_dict, [table_num, record_num], entry)

        return True, data_dict

    #############

    def remove_measurement(self, measurement_name):

        status, output = self.get_database_names()
        if not status:
            return False, output

        bucket_names = output

        delete_api = self.client.delete_api()

        for bucket_name in bucket_names:

            try:

                delete_api.delete('1970-01-01T00:00:00Z',
                                  '2025-04-27T00:00:00Z',
                                  f'_measurement="{measurement_name}"',
                                  bucket=bucket_name)
            except Exception as E:
                return False, str(E)

        return True, None


    @staticmethod
    def write_points(data_list, url="http://zeus.home", port=8086, database_name="home_sensors", timeout=None):

        url_port = f"{url}:{port}"

        try:
            influx_obj = InfluxDB_Access(url=url_port, org="home", timeout=timeout)
            return influx_obj.write_data(data_list, database_name)
        except (Exception, SystemExit) as E:
            return False, f"write_points failed: {E}"


    @staticmethod
    def read_points(query, url="http://zeus.home", port=8086, timeout=None):

        url_port = f"{url}:{port}"

        try:
            influx_obj = InfluxDB_Access(url=url_port, org="home", timeout=timeout)
            return influx_obj.read_data(query)
        except (Exception, SystemExit) as E:
            return False, f"read_points failed: {E}"
