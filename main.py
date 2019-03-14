#!/usr/bin/env python

from __future__ import print_function

import traceback

from influxdb import InfluxDBClient
from requests.exceptions import ConnectionError
import psutil
import socket
from datetime import datetime
import platform
import os
import json as jsson
import time
import pymongo
from threading import Thread


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
    client2 = InfluxDBClient('192.168.31.103', 8086, 'root', 'root')
    dbName = "RPI"
    dbName2 = "RPI_Process"

    now = datetime.utcnow()

    try:
        client.create_database(dbName)
    except ConnectionError:
        print("no connection to DB")
        # exit(-1)

    try:
        client2.create_database(dbName2)
        client2.switch_database(dbName2)
        writeProcessValues(client2, now)
    except ConnectionError:
        print("no connection to DB")

    jsons = []
    client.switch_database(dbName)

    jsons.append(getServerValues(now))
    jsons.append(getNetworkValues(now))

    for js in jsons:
        client.write_points(js)

    writeServerDetails(client, now)


def writeProcessValues(client, now):
    plist = psutil.pids()
    print('Writing to DB')

    for x in plist:
        try:
            proc = psutil.Process(x)
            pname = proc.name()
            pmem = float("{0:.2f}".format(proc.memory_percent()))
            pcpu = proc.cpu_percent()

            json_body = [
                {
                    "measurement": "process_list",
                    "tags": {
                        "host": socket.gethostname(),
                        'pName': pname,
                    },
                    "time": now.isoformat(),
                    "fields": {
                        'procId': x,
                        'pMemory': pmem,
                        'pCPU': pcpu

                    }
                }
            ]

            client.write_points(retention_policy="rp1", points=json_body)

        except psutil.NoSuchProcess:
            print('Process not found')
        except InfluxDBClient.exceptions.InfluxDBClientError:
            print('InfluxDB error')


def writeServerDetails(client, now):
    query = "SELECT * FROM RPI.autogen.server WHERE host =\'" + socket.gethostname() + "\' order by desc limit 1"
    result = client.query(query)

    if len(result) == 0:
        json_body = [
            {
                "measurement": "server",
                "tags": {
                    "host": socket.gethostname(),
                    "region": "uk"
                },
                "time": now.isoformat()
            }
        ]

        client.write_points(json_body)
        print('wrote server details to db')
    else:
        print("server values already exist")

    pass


def getServerDetailsJson():
    network = psutil.net_if_addrs()
    interface = []
    json = jsson.dumps(network)
    for attr, value in network.items():
        interface.append({attr: value})

    disks = psutil.disk_partitions()
    disks_formatted = []

    for disk in disks:
        disks_formatted.append({"name": disk[1], "fstype": disk.fstype})

    sensors = []
    for x in psutil.sensors_temperatures():
        sensors.append(psutil.sensors_temperatures(fahrenheit=False)[x][0][1])
    avgtemp = 0
    for s in sensors:
        avgtemp += s

    avgtemp = avgtemp/sensors.__len__()

    obj_Disk = psutil.disk_usage('/')
    json_body = {"host": socket.gethostname(),
                 "timestamp": time.time(),
                 "system": {
                     "system": platform.system(),
                     "release": platform.release(),
                     "machine": platform.machine(),
                     "version": platform.version()
                 },
                 "cpu": {
                     "cpu_cores": psutil.cpu_count(),
                     'cpu_freq': psutil.cpu_freq(percpu=False).max,
                     'cpu_load': psutil.cpu_percent(),
                     'cpu_temp': avgtemp
                 },
                 "memory": {
                     "memory_size": float("{0:.2f}".format(psutil.virtual_memory().total / (1024.0 ** 3))),
                     "memory_load": psutil.virtual_memory()[2]
                 },
                 "disk": {
                     "disk_total": float("{0:.2f}".format(obj_Disk.total / (1024.0 ** 3))),
                     "disk_free": float("{0:.2f}".format(obj_Disk.free / (1024.0 ** 3))),
                     "disk_used": float("{0:.2f}".format(obj_Disk.used / (1024.0 ** 3))),
                     "disk_percent": obj_Disk.percent
                 },
                 "network": network}

    return json_body


def writeServerDetailsToMongoDB():
    try:
        client = pymongo.MongoClient('192.168.31.103', 27017)
        db = client.plasmid
        collection = db.servers

        doc = collection.find({'host': socket.gethostname()})

        if doc.count() == 0:

            collection.insert(getServerDetailsJson())

        elif doc.count() > 0:
            collection.update({'_id': doc[0]['_id']}, {"$set": getServerDetailsJson()})

        else:
            print('could not write server details to db')

    except Exception:
        print(traceback.format_exc())
        print("No connection to MongoDB")


def influxLooper(cycle):
    while True:
        insertUtilizationValues()
        time.sleep(cycle)


def mongoLooper(cycle):
    while True:
        writeServerDetailsToMongoDB()
        time.sleep(cycle)


if __name__ == '__main__':

    threads = [
        Thread(target=mongoLooper(600)),
        Thread(target=influxLooper(60))
    ]
    for i in threads:
        i.start()
