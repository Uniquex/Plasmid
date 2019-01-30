from pymongo import MongoClient
from bson.json_util import dumps

class MongoCon:
    def __init__(self):
        self.client = MongoClient("192.168.8.31", 27017)  # type: MongoClient
        self.db = self.client.plasmid
        self.colServ = self.db.servers


    def getServers(self):
        print(self.client.list_database_names())

    def getServer(self, name):
        client = MongoClient('192.168.31.103', 27017)
        db = client.plasmid
        collection = db.servers
        result = collection.find_one({'host': name})
        return dumps(result)
