#!/usr/bin/env python

from __future__ import print_function
from influxdb import InfluxDBClient
from requests.exceptions import ConnectionError
import psutil
import socket
from datetime import datetime
import platform
import os
import json as jsson
import time



class SomeObject(object):
    pass


def disksinfo():
    values = []
    disk_partitions = psutil.disk_partitions(all=False)
    for partition in disk_partitions:
        usage = psutil.disk_usage(partition.mountpoint)
        device = {'device': partition.device,
                  'mountpoint': partition.mountpoint,
                  'fstype': partition.fstype,
                  'opts': partition.opts,
                  'total': usage.total,
                  'used': usage.used,
                  'free': usage.free,
                  'percent': usage.percent
                  }
        values.append(device)

    return values


def getCPUDetails():
    cpus = psutil.cpu_freq(percpu=True)

    values = []

    for cpu in cpus:
        core = {'device': cpu.current,
                'max': cpu.max,
                'min': cpu.min
                }
        values.append(core)

    return jsson.dumps(values)


def getSystemValues():
    now = datetime.utcnow()

    net = psutil.net_io_counters()

    x = psutil.cpu_freq(percpu=False)

    # TODO get adaptor dynamically
    json_body = [
        {
            "measurement": "system_details",
            "tags": {
                "host": socket.gethostname()
            },
            "time": now.isoformat(),
            "fields": {
                "OS": os.name,
                "System": platform.system(),
                "Release": platform.release(),
                "CPU_Cores": psutil.cpu_count(),
                "CPU_Frequency": psutil.cpu_freq(percpu=False).max,
                "RAM": psutil.virtual_memory().available,
                "Disk_Count": int(psutil.disk_partitions().__len__())
            }
        }
    ]

    return json_body


def getServerValues():
    now = datetime.utcnow()

    print(now.utcnow())

    x = psutil.virtual_memory()

    #print(x.percent)

    json_body = [
        {
            "measurement": "server_load_short",
            "tags": {
                "host": socket.gethostname(),
                "region": "uk"
            },
            "time": now.isoformat(),
            "fields": {
                "CPU_Usage": psutil.cpu_percent(),
                "RAM_Usage": psutil.virtual_memory().percent,
                "RAM_Available": psutil.virtual_memory().available,
                "RAM_Used": psutil.virtual_memory().used,
            }
        }
    ]

    return json_body


def getNetworkValues():
    now = datetime.utcnow()

    net = psutil.net_io_counters()

    # TODO get adaptor dynamically
    json_body = [
        {
            "measurement": "network_load_short",
            "tags": {
                "host": socket.gethostname(),
                "adaptor": "eth0"
            },
            "time": now.isoformat(),
            "fields": {
                "Bytes_Received": net.bytes_recv,
                "Bytes_Sent": net.bytes_sent,
                "ErrorIn": net.errin,
                "ErrorOut": net.errout,
                "PackagesReceived": net.packets_recv,
                "PackagesSent": net.packets_sent
            }
        }
    ]

    return json_body

def insertUtilizationValues() :
    client = InfluxDBClient('192.168.31.103', 8086, 'root', 'root')
    dbName = "RPI"

    try:
        client.create_database(dbName)
    except ConnectionError:
        print("no connection to DB")
        exit(-1)

    client.switch_database(dbName)

    json = getServerValues()

    print("Write points: {0}".format(json))
    client.write_points(json)

    # query = "SELECT * FROM " + dbName + ".autogen.cpu_load_short"
    # result = client.query(query)
    # print("Result: {0}".format(result))

    json = getNetworkValues()
    print("Write points: {0}".format(json))
    client.write_points(json)

    # json = getSystemValues()
    # print("Write points: {0}".format(json))
    # client.write_points(json)




if __name__ == '__main__':
    while True:
        insertUtilizationValues()
        time.sleep(10)
pass