#!/usr/bin/env python
# between_times.py
# Copyright (C) ContinuumBridge Limited, 2014-2015 - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Peter Claydon
#

import time

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

