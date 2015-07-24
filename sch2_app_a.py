#!/usr/bin/env python
# sch2_app_a.py
# Copyright (C) ContinuumBridge Limited, 2014-2015 - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Peter Claydon
#

# Default values:
config = {
    "temperature": "True",
    "temp_min_change": 0.1,
    "irtemperature": "False",
    "irtemp_min_change": 0.5,
    "humidity": "True",
    "humidity_min_change": 0.2,
    "buttons": "False",
    "accel": "False",
    "accel_min_change": 0.02,
    "accel_polling_interval": 3.0,
    "gyro": "False",
    "gyro_min_change": 0.5,
    "gyro_polling_interval": 3.0,
    "magnet": "False",
    "magnet_min_change": 1.5,
    "magnet_polling_interval": 3.0,
    "binary": "True",
    "luminance": "True",
    "luminance_min_change": 2.0,
    "power": "True",
    "power_min_change": 1.0,
    "battery": "True",
    "battery_min_change": 1.0,
    "connected": "True",
    "slow_polling_interval": 600.0,
    "night_wandering": "False",
    "night_start": "00:30",
    "night_end": "07:00",
    "night_sensors": [],
    "night_ignore_time": 600,
    "entry-exit": "False",
    "entry-exits": [],
    "hot_drinks": {"name": "Not Set",
                   "enable": "False",
                   "sensor": "",
                   "threshold": 2
                  },
    "send_delay": 1,
    "cid": "none",
    "client_test": "False"
}

import sys
import os.path
import time
from cbcommslib import CbApp
from cbconfig import *
import requests
import json
from twisted.internet import reactor
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from entry_exit import EntryExit, CheckExit
from nightwander import NightWander
from hotdrinks import HotDrinks

# For entry/exit
IN_PIR_TO_DOOR_TIME               = 30   
DOOR_CLOSE_TO_IN_PIR_TIME         = 10
DOOR_OPEN_TO_IN_PIR_TIME          = 30
MAX_DOOR_OPEN_TIME                = 60
MAX_INTERVAL                      = 30*60 # Will post values after this even if they haven't changed

def betweenTimes(t, t1, t2):
    # True if epoch t is between times of day t1 and t2 (in 24-hour clock format: "23:10")
    t1secs = (60*int(t1.split(":")[0]) + int(t1.split(":")[1])) * 60
    t2secs = (60*int(t2.split(":")[0]) + int(t2.split(":")[1])) * 60
    stamp = time.strftime("%Y %b %d %H:%M", time.localtime(t)).split()
    today = stamp
    today[3] = "00:00"
    today_e = time.mktime(time.strptime(" ".join(today), "%Y %b %d %H:%M"))
    yesterday_e = today_e - 24*3600
    #print "today_e: ", today_e, "yesterday_e: ", yesterday_e
    tt1 = [yesterday_e + t1secs, today_e + t1secs]
    tt2 = [yesterday_e + t2secs, today_e + t2secs]
    #print "tt1: ", tt1, " tt2: ", tt2
    smallest = 50000
    decision = False
    if t - tt1[0] < smallest and t - tt1[0] > 0:
        smallest = t - tt1[0]
        decision = True
    if t - tt2[0] < smallest and t -tt2[0] > 0:
        smallest = t - tt2[0]
        decision = False
    if t - tt1[1] < smallest and t -tt1[1] > 0:
        smallest = t - tt1[1]
        decision = True
    if t - tt2[1] < smallest and t - tt2[1] > 0:
        smallest = t - tt2[1]
        decision = False
    return decision

class DataManager:
    """ Managers data storage for all sensors """
    def __init__(self, bridge_id, idToName):
        self.idToName = idToName
        self.baseAddress = bridge_id + "/"
        self.s = []
        self.waiting = False

    def sendValues(self):
        msg = {"m": "data",
               "d": self.s
               }
        self.cbLog("debug", "sendValues. Sending: " + str(json.dumps(msg, indent=4)))
        self.client.send(msg)
        self.s = []
        self.waiting = False

    def storeValues(self, values):
        self.s.append(values)
        if not self.waiting:
            self.waiting = True
            reactor.callLater(config["send_delay"], self.sendValues)

    def storeAccel(self, deviceID, timeStamp, a):
        values = {"name": self.baseAddress + deviceID + "/accel/x",
                  "points": [[int(timeStamp*1000), a[0]]]
                 }
        self.storeValues(values)
        values = {"name": self.baseAddress + deviceID + "/accel/y",
                  "points": [[int(timeStamp*1000), a[1]]]
                 }
        self.storeValues(values)
        values = {"name": self.baseAddress + deviceID + "/accel/z",
                  "points": [[int(timeStamp*1000), a[2]]]
                 }
        self.storeValues(values)

    def storeTemp(self, deviceID, timeStamp, temp):
        values = {"name": self.baseAddress + deviceID + "/temperature",
                  "points": [[int(timeStamp*1000), temp]]
                 }
        self.storeValues(values)

    def storeIrTemp(self, deviceID, timeStamp, temp):
        values = {"name": self.baseAddress + deviceID + "/ir_temperature",
                  "points": [[int(timeStamp*1000), temp]]
                 }
        self.storeValues(values)

    def storeHumidity(self, deviceID, timeStamp, h):
        values = {"name": self.baseAddress + deviceID + "/humidity",
                   "points": [[int(timeStamp*1000), h]]
                 }
        self.storeValues(values)

    def storeButtons(self, deviceID, timeStamp, buttons):
        values = [
                  {"n":"left_button", "v":buttons["leftButton"], "t":timeStamp},
                  {"n":"right_button", "v":buttons["rightButton"], "t":timeStamp}
                 ]
        self.storeValues(values, deviceID)

    def storeGyro(self, deviceID, timeStamp, v):
        values = {"name": self.baseAddress + deviceID + "/gyro/x",
                  "points": [[int(timeStamp*1000), v[0]]]
                 }
        self.storeValues(values)
        values = {"name": self.baseAddress + deviceID + "/gyro/y",
                  "points": [[int(timeStamp*1000), v[1]]]
                 }
        self.storeValues(values)
        values = {"name": self.baseAddress + deviceID + "/gyro/z",
                  "points": [[int(timeStamp*1000), v[2]]]
                 }
        self.storeValues(values)

    def storeMagnet(self, deviceID, timeStamp, v):
        values = {"name": self.baseAddress + deviceID + "/magnet/x",
                  "points": [[int(timeStamp*1000), v[0]]]
                 }
        self.storeValues(values)
        values = {"name": self.baseAddress + deviceID + "/magnet/y",
                  "points": [[int(timeStamp*1000), v[1]]]
                 }
        self.storeValues(values)
        values = {"name": self.baseAddress + deviceID + "/magnet/z",
                  "points": [[int(timeStamp*1000), v[2]]]
                 }
        self.storeValues(values)

    def storeBinary(self, deviceID, timeStamp, b):
        values = {"name": self.baseAddress + deviceID + "/binary",
                  "points": [[int(timeStamp*1000), b]]
                 }
        self.storeValues(values)

    def storeLuminance(self, deviceID, timeStamp, v):
        values = {"name": self.baseAddress + deviceID + "/luminance",
                  "points": [[int(timeStamp*1000), v]]
                 }
        self.storeValues(values)

    def storePower(self, deviceID, timeStamp, v):
        values = {"name": self.baseAddress + deviceID + "/power",
                  "points": [[int(timeStamp*1000), v]]
                 }
        self.storeValues(values)

    def storeBattery(self, deviceID, timeStamp, v):
        values = {"name": self.baseAddress + deviceID + "/battery",
                  "points": [[int(timeStamp*1000), v]]
                 }
        self.storeValues(values)

    def storeConnected(self, deviceID, timeStamp, v):
        values = {"name": self.baseAddress + deviceID + "/connected",
                  "points": [[int(timeStamp*1000), v]]
                 }
        self.storeValues(values)

    def storeActivity(self, location, timeStamp, action, v):
        values = {"name": self.baseAddress + location + "/" + action,
                  "points": [[int(timeStamp*1000), v]]
                 }
        self.storeValues(values)

class Accelerometer:
    def __init__(self, id):
        self.previous = [0.0, 0.0, 0.0]
        self.id = id

    def processAccel(self, resp):
        accel = [resp["data"]["x"], resp["data"]["y"], resp["data"]["z"]]
        timeStamp = resp["timeStamp"]
        event = False
        for a in range(3):
            if abs(accel[a] - self.previous[a]) > config["accel_min_change"]:
                event = True
                break
        if event:
            self.dm.storeAccel(self.id, timeStamp, accel)
            self.previous = accel

class TemperatureMeasure():
    def __init__(self, id):
        self.id = id
        self.prevTemp = 0.0
        self.prevTime = time.time()

    def processTemp (self, resp):
        #self.cbLog("debug", "processTemp: " + self.id + " - " + str(resp))
        timeStamp = resp["timeStamp"] 
        temp = resp["data"]
        if abs(temp-self.prevTemp) >= config["temp_min_change"] or timeStamp - self.prevTime > MAX_INTERVAL:
            self.dm.storeTemp(self.id, timeStamp, temp) 
            self.prevTemp = temp
            self.prevTime = timeStamp

class IrTemperatureMeasure():
    def __init__(self, id):
        self.id = id
        self.prevTemp = 0.0

    def processIrTemp (self, resp):
        timeStamp = resp["timeStamp"] 
        temp = resp["data"]
        if abs(temp-self.prevTemp) >= config["irtemp_min_change"]:
            self.dm.storeIrTemp(self.id, timeStamp, temp) 
            self.prevTemp = temp

class Buttons():
    def __init__(self, id):
        self.id = id

    def processButtons(self, resp):
        timeStamp = resp["timeStamp"] 
        buttons = resp["data"]
        self.dm.storeButtons(self.id, timeStamp, buttons)

class Gyro():
    def __init__(self, id):
        self.id = id
        self.previous = [0.0, 0.0, 0.0]

    def processGyro(self, resp):
        gyro = [resp["data"]["x"], resp["data"]["y"], resp["data"]["z"]]
        timeStamp = resp["timeStamp"] 
        event = False
        for a in range(3):
            if abs(gyro[a] - self.previous[a]) > config["gyro_min_change"]:
                event = True
                break
        if event:
            self.dm.storeGyro(self.id, timeStamp, gyro)
            self.previous = gyro

class Magnet():
    def __init__(self, id):
        self.id = id
        self.previous = [0.0, 0.0, 0.0]

    def processMagnet(self, resp):
        mag = [resp["data"]["x"], resp["data"]["y"], resp["data"]["z"]]
        timeStamp = resp["timeStamp"] 
        event = False
        for a in range(3):
            if abs(mag[a] - self.previous[a]) > config["magnet_min_change"]:
                event = True
                break
        if event:
            self.dm.storeMagnet(self.id, timeStamp, mag)
            self.previous = mag

class Humid():
    """ Either send temp every minute or when it changes. """
    def __init__(self, id):
        self.id = id
        self.previous = 0.0
        self.prevTime = time.time()

    def processHumidity (self, resp):
        #self.cbLog("debug", "processHumidity: " + self.id + " - " + str(resp))
        h = resp["data"]
        timeStamp = resp["timeStamp"] 
        if abs(self.previous - h) >= config["humidity_min_change"] or timeStamp - self.prevTime > MAX_INTERVAL:
            self.dm.storeHumidity(self.id, timeStamp, h) 
            self.previous = h
            self.prevTime = timeStamp

class Binary():
    def __init__(self, id):
        self.id = id
        self.previous = 0
        self.previousTime = 0

    def processBinary(self, resp):
        timeStamp = resp["timeStamp"] 
        b = resp["data"]
        if b == "on":
            bi = 1
        else:
            bi = 0
        if bi != self.previous:
            if timeStamp != self.previousTime:
                self.dm.storeBinary(self.id, timeStamp-1.0, self.previous)
                self.dm.storeBinary(self.id, timeStamp, bi)
                self.previous = bi
                self.previousTime = timeStamp

class Luminance():
    def __init__(self, id):
        self.id = id
        self.previous = 0
        self.prevTime = time.time()

    def processLuminance(self, resp):
        #self.cbLog("debug", "processLuminance: " + self.id + " - " + str(resp))
        v = resp["data"]
        timeStamp = resp["timeStamp"] 
        if abs(v-self.previous) >= config["luminance_min_change"] or timeStamp - self.prevTime > MAX_INTERVAL:
            self.dm.storeLuminance(self.id, timeStamp, v) 
            self.previous = v
            self.prevTime = timeStamp

class Power():
    def __init__(self, id):
        self.id = id
        self.previous = 0
        self.previousTime = time.time()

    def processPower(self, resp):
        v = resp["data"]
        timeStamp = resp["timeStamp"] 
        if abs(v-self.previous) >= config["power_min_change"] or timeStamp - self.previousTime > MAX_INTERVAL:
            if timeStamp - self.previousTime > 2:
                self.dm.storePower(self.id, timeStamp-1.0, self.previous)
            self.dm.storePower(self.id, timeStamp, v) 
            self.previous = v
            self.previousTime = timeStamp

class Battery():
    def __init__(self, id):
        self.id = id
        self.previous = 0
        self.previousTime = time.time()

    def processBattery(self, resp):
        v = resp["data"]
        timeStamp = resp["timeStamp"] 
        if abs(v-self.previous) >= config["battery_min_change"] or timeStamp - self.previousTime > MAX_INTERVAL:
            self.dm.storeBattery(self.id, timeStamp, v) 
            self.previous = v
            self.previousTime = timeStamp

class Connected():
    def __init__(self, id):
        self.id = id
        self.previous = 0
        self.previousTime = time.time()

    def processConnected(self, resp):
        v = resp["data"]
        timeStamp = resp["timeStamp"] 
        if v:
            b = 1
        else:
            b = 0
        if b != self.previous or timeStamp - self.previousTime > MAX_INTERVAL:
            self.dm.storeConnected(self.id, timeStamp-1.0, self.previous)
            self.dm.storeConnected(self.id, timeStamp, b) 
            self.previous = b
            self.previousTime = timeStamp

class Client():
    def __init__(self, aid):
        self.aid = aid
        self.count = 0
        self.messages = []

    def send(self, data):
        message = {
                   "source": self.aid,
                   "destination": config["cid"],
                   "body": data
                  }
        message["body"]["n"] = self.count
        self.count += 1
        self.messages.append(message)
        self.sendMessage(message, "conc")

    def receive(self, message):
        #self.cbLog("debug", "Message from client: " + str(message))
        if "body" in message:
            if "n" in message["body"]:
                #self.cbLog("debug", "Received ack from client: " + str(message["body"]["n"]))
                for m in self.messages:
                    if m["body"]["n"] == m:
                        self.messages.remove(m)
                        self.cbLog("debug", "Removed message " + str(m) + " from queue")
        else:
            self.cbLog("warning", "Received message from client with no body")

class pillbox():
    def __init__(self):
        self.magnet_av = [0.0, 0.0, 0.0]

    def updateMagnet(self, mag):
        self.current = mag

    def calcAverage(self):
        points_to_average = 16

class App(CbApp):
    def __init__(self, argv):
        self.appClass = "monitor"
        self.state = "stopped"
        self.status = "ok"
        self.accel = []
        self.gyro = []
        self.magnet = []
        self.temp = []
        self.irTemp = []
        self.buttons = []
        self.humidity = []
        self.binary = []
        self.luminance = []
        self.power = []
        self.battery = []
        self.connected = []
        self.devices = []
        self.devServices = [] 
        self.idToName = {} 
        self.entryExitIDs = []
        self.hotDrinkIDs = []
        #CbApp.__init__ MUST be called
        CbApp.__init__(self, argv)

    def setState(self, action):
        if action == "clear_error":
            self.state = "running"
        else:
            self.state = action
        msg = {"id": self.id,
               "status": "state",
               "state": self.state}
        self.sendManagerMessage(msg)

    def onConcMessage(self, message):
        self.client.receive(message)

    def onAdaptorData(self, message):
        """
        This method is called in a thread by cbcommslib so it will not cause
        problems if it takes some time to complete (other than to itself).
        """
        #self.cbLog("debug", "onadaptorData, message: " + str(json.dumps(message, indent=4)))
        if message["characteristic"] == "acceleration":
            for a in self.accel:
                if a.id == self.idToName[message["id"]]: 
                    a.processAccel(message)
                    break
        elif message["characteristic"] == "temperature":
            for t in self.temp:
                if t.id == self.idToName[message["id"]]:
                    t.processTemp(message)
                    break
        elif message["characteristic"] == "ir_temperature":
            for t in self.irTemp:
                if t.id == self.idToName[message["id"]]:
                    t.processIrTemp(message)
                    break
        elif message["characteristic"] == "gyro":
            for g in self.gyro:
                if g.id == self.idToName[message["id"]]:
                    g.processGyro(message)
                    break
        elif message["characteristic"] == "magnetometer":
            for g in self.magnet:
                if g.id == self.idToName[message["id"]]:
                    g.processMagnet(message)
                    break
        elif message["characteristic"] == "buttons":
            for b in self.buttons:
                if b.id == self.idToName[message["id"]]:
                    b.processButtons(message)
                    break
        elif message["characteristic"] == "humidity":
            for b in self.humidity:
                if b.id == self.idToName[message["id"]]:
                    b.processHumidity(message)
                    break
        elif message["characteristic"] == "binary_sensor":
            for b in self.binary:
                if b.id == self.idToName[message["id"]]:
                    b.processBinary(message)
                    break
            for n in self.entryExitIDs:
                if n == message["id"]:
                    self.entryExit.onChange(message["id"], message["timeStamp"], message["data"])
                    break
            for n in config["night_sensors"]:
                if n == message["id"]:
                    self.nightWander.onChange(message["id"], message["timeStamp"], message["data"])
                    break
        elif message["characteristic"] == "power":
            for b in self.power:
                if b.id == self.idToName[message["id"]]:
                    b.processPower(message)
                    break
            if config["hot_drinks"]["enable"] == "True":
                if message["id"] == self.hotDrinksID:
                    self.hotDrinks.onChange(message["timeStamp"], message["data"])
        elif message["characteristic"] == "battery":
            for b in self.battery:
                if b.id == self.idToName[message["id"]]:
                    b.processBattery(message)
                    break
        elif message["characteristic"] == "connected":
            for b in self.connected:
                if b.id == self.idToName[message["id"]]:
                    b.processConnected(message)
                    break
        elif message["characteristic"] == "luminance":
            for b in self.luminance:
                if b.id == self.idToName[message["id"]]:
                    b.processLuminance(message)
                    break

    def onAdaptorService(self, message):
        #self.cbLog("debug", "onAdaptorService, message: " + str(json.dumps(message, indent=4)))
        self.devServices.append(message)
        serviceReq = []
        for p in message["service"]:
            # Based on services offered & whether we want to enable them
            if p["characteristic"] == "temperature":
                if config["temperature"] == 'True':
                    self.temp.append(TemperatureMeasure((self.idToName[message["id"]])))
                    self.temp[-1].dm = self.dm
                    self.temp[-1].cbLog = self.cbLog
                    serviceReq.append({"characteristic": "temperature",
                                       "interval": config["slow_polling_interval"]})
            elif p["characteristic"] == "ir_temperature":
                if config["irtemperature"] == 'True':
                    self.irTemp.append(IrTemperatureMeasure(self.idToName[message["id"]]))
                    self.irTemp[-1].dm = self.dm
                    serviceReq.append({"characteristic": "ir_temperature",
                                       "interval": config["slow_polling_interval"]})
            elif p["characteristic"] == "acceleration":
                if config["accel"] == 'True':
                    self.accel.append(Accelerometer((self.idToName[message["id"]])))
                    serviceReq.append({"characteristic": "acceleration",
                                       "interval": config["accel_polling_interval"]})
                    self.accel[-1].dm = self.dm
            elif p["characteristic"] == "gyro":
                if config["gyro"] == 'True':
                    self.gyro.append(Gyro(self.idToName[message["id"]]))
                    self.gyro[-1].dm = self.dm
                    serviceReq.append({"characteristic": "gyro",
                                       "interval": config["gyro_polling_interval"]})
            elif p["characteristic"] == "magnetometer":
                if config["magnet"] == 'True': 
                    self.magnet.append(Magnet(self.idToName[message["id"]]))
                    self.magnet[-1].dm = self.dm
                    serviceReq.append({"characteristic": "magnetometer",
                                       "interval": config["magnet_polling_interval"]})
            elif p["characteristic"] == "buttons":
                if config["buttons"] == 'True':
                    self.buttons.append(Buttons(self.idToName[message["id"]]))
                    self.buttons[-1].dm = self.dm
                    serviceReq.append({"characteristic": "buttons",
                                       "interval": 0})
            elif p["characteristic"] == "humidity":
                if config["humidity"] == 'True':
                    self.humidity.append(Humid(self.idToName[message["id"]]))
                    self.humidity[-1].dm = self.dm
                    self.humidity[-1].cbLog = self.cbLog
                    serviceReq.append({"characteristic": "humidity",
                                       "interval": config["slow_polling_interval"]})
            elif p["characteristic"] == "binary_sensor":
                if config["binary"] == 'True':
                    self.binary.append(Binary(self.idToName[message["id"]]))
                    self.binary[-1].dm = self.dm
                    self.binary[-1].cbLog = self.cbLog
                    serviceReq.append({"characteristic": "binary_sensor",
                                       "interval": 0})
            elif p["characteristic"] == "power":
                if config["power"] == 'True':
                    self.power.append(Power(self.idToName[message["id"]]))
                    self.power[-1].dm = self.dm
                    serviceReq.append({"characteristic": "power",
                                       "interval": 0})
            elif p["characteristic"] == "battery":
                if config["battery"] == 'True':
                    self.battery.append(Battery(self.idToName[message["id"]]))
                    self.battery[-1].dm = self.dm
                    serviceReq.append({"characteristic": "battery",
                                       "interval": 0})
            elif p["characteristic"] == "connected":
                if config["connected"] == 'True':
                    self.connected.append(Connected(self.idToName[message["id"]]))
                    self.connected[-1].dm = self.dm
                    serviceReq.append({"characteristic": "connected",
                                       "interval": 0})
            elif p["characteristic"] == "luminance":
                if config["luminance"] == 'True':
                    self.luminance.append(Luminance(self.idToName[message["id"]]))
                    self.luminance[-1].dm = self.dm
                    self.luminance[-1].cbLog = self.cbLog
                    serviceReq.append({"characteristic": "luminance",
                                       "interval": config["slow_polling_interval"]})
        msg = {"id": self.id,
               "request": "service",
               "service": serviceReq}
        self.sendMessage(msg, message["id"])
        self.setState("running")

    def onConfigureMessage(self, managerConfig):
        global config
        configFile = CB_CONFIG_DIR + "sch2_app.config"
        try:
            with open(configFile, 'r') as f:
                newConfig = json.load(f)
                self.cbLog("debug", "Read sch2_app.config")
                config.update(newConfig)
        except Exception as ex:
            self.cbLog("warning", "sch2_app.config does not exist or file is corrupt")
            self.cbLog("warning", "Exception: " + str(type(ex)) + str(ex.args))
        for c in config:
            if c.lower in ("true", "t", "1"):
                config[c] = True
            elif c.lower in ("false", "f", "0"):
                config[c] = False
        self.cbLog("debug", "Config: " + str(json.dumps(config, indent=4)))
        idToName2 = {}
        for adaptor in managerConfig["adaptors"]:
            adtID = adaptor["id"]
            if adtID not in self.devices:
                # Because managerConfigure may be re-called if devices are added
                name = adaptor["name"]
                friendly_name = adaptor["friendly_name"]
                self.cbLog("debug", "managerConfigure app. Adaptor id: " +  adtID + " name: " + name + " friendly_name: " + friendly_name)
                idToName2[adtID] = friendly_name
                self.idToName[adtID] = friendly_name.replace(" ", "_")
                self.devices.append(adtID)
        self.client = Client(self.id)
        self.client.sendMessage = self.sendMessage
        self.client.cbLog = self.cbLog
        self.dm = DataManager(self.bridge_id, self.idToName)
        self.dm.cbLog = self.cbLog
        self.dm.client = self.client
        self.entryExit = EntryExit()
        self.entryExit.cbLog = self.cbLog
        self.entryExit.dm = self.dm
        self.entryExitIDs = self.entryExit.initExits(idToName2, config["entry-exit"], config["entry-exits"])
        self.cbLog("debug", "onConfigureMessage, entryExitIDs: " + str(self.entryExitIDs))
        self.nightWander = NightWander(self.id, config)
        self.nightWander.cbLog = self.cbLog
        self.nightWander.client = self.client
        self.nightWander.dm = self.dm
        self.nightWander.setNames(idToName2)
        if config["hot_drinks"]["enable"] == 'True':
            self.hotDrinks = HotDrinks()
            self.hotDrinks.cbLog = self.cbLog
            self.hotDrinks.dm = self.dm
            self.hotDrinksID = self.hotDrinks.initIDs(idToName2, config["hot_drinks"])
        self.setState("starting")

if __name__ == '__main__':
    App(sys.argv)
