#!/usr/bin/env python

from __future__ import print_function
from influxdb import InfluxDBClient
from requests.exceptions import ConnectionError
import psutil
import socket
import datetime


def getCPUvalues():

    pass



if __name__ == '__main__':
    client = InfluxDBClient('192.168.31.103', 8086, 'root', 'root')
    dbName = "RPI"

    try:
        client.create_database(dbName)
    except ConnectionError:
        print("no connection to DB")
        exit(-1)

    client.switch_database(dbName)

    json = getCPUvalues()

    print("Write points: {0}".format(json))
    client.write_points(json)

    query = "SELECT * FROM " + dbName + ".autogen.cpu_load_short"
    result = client.query(query)
    print(query)
    print("Result: {0}".format(result))



