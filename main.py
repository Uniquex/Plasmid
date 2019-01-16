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





def getServerValues(now):

    print('Getting utilization values')

    x = psutil.virtual_memory()

    # print(x.percent)

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


def getNetworkValues(now):
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


def insertUtilizationValues():
    client = InfluxDBClient('192.168.31.103', 8086, 'root', 'root')
    dbName = "RPI"

    try:
        client.create_database(dbName)
    except ConnectionError:
        print("no connection to DB")
        exit(-1)

    jsons = []
    client.switch_database(dbName)
    now = datetime.utcnow()

    jsons.append(getServerValues(now))
    jsons.append(getNetworkValues(now))

    for js in jsons:
        client.write_points(js)

    writeProcessValues(client, now)
    writeServerDetails(client, now)


def writeProcessValues(client, now):
    plist = psutil.pids()
    print('Writing to DB')
    for x in plist:
        # TODO catch psutil._exceptions.NoSuchProcess
        try:
            proc = psutil.Process(x)
            pname = proc.name()
            pmem = float("{0:.2f}".format(proc.memory_percent()))
            pcpu = proc.cpu_times().system

            json_body = [
                {
                    "measurement": "process_list",
                    "tags": {
                        "host": socket.gethostname(),
                        'pName': pname
                    },
                    "time": now.isoformat(),
                    "fields": {
                        'procId': x,
                        'pMemory': pmem,
                        'pCPU': pcpu

                    }
                }
            ]

            # print("Write points: {0}".format(json_body))
            client.write_points(json_body)

        except psutil.NoSuchProcess:
            print('Process not found')

def writeServerDetails(client, now):

    query = "SELECT * FROM RPI.autogen.server WHERE host =\'" + socket.gethostname() + "\' order by desc limit 1"
    result = client.query(query)

    if len(result) == 0:
        obj_Disk = psutil.disk_usage('/')

        json_body = [
            {
                "measurement": "server",
                "tags": {
                    "host": socket.gethostname(),
                    "region": "uk"
                },
                "time": now.isoformat(),
                "fields": {
                    "CPU_Cores": psutil.cpu_count(),
                    'CPU_Freq': psutil.cpu_freq(percpu=False).max,
                    "Memory": psutil.virtual_memory().total / (1024.0 ** 3),
                    "Disk_total": float("{0:.2f}".format(obj_Disk.total / (1024.0 ** 3))),
                    "Disk_free": float("{0:.2f}".format(obj_Disk.free / (1024.0 ** 3))),
                    "Disk_used": float("{0:.2f}".format(obj_Disk.used / (1024.0 ** 3))),
                    "Disk_percent": obj_Disk.percent
                }
            }
        ]

        client.write_points(json_body)
        print('wrote server details to db')
    else:
        print("server values already exist")

if __name__ == '__main__':

    while True:
        insertUtilizationValues()
        time.sleep(60)

pass
