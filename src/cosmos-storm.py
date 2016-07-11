__author__ = 'saurabh.agrawal'

import string
import time
import threading
import requests
import socket
import re
from urlparse import urljoin


METRIC_PREFIX=open("/etc/default/cosmos-service", "r").read().rstrip()
#INTERVAL=30

HOSTNAME=socket.getfqdn()
HOST_TAG="host="+HOSTNAME
STORM_URL='http://'+HOSTNAME+':7700'

WINDOW_NAMES = {'600':'TenMinute', '10800':'ThreeHour', '86400':'OneDay', ':all-time':'AllTime'}
WINDOW_ATTRS = ['emitted', 'transferred', 'acked', 'failed']
SPOUT_ATTRS = ['executors', 'emitted', 'transferred', 'acked', 'tasks', 'failed', 'completeLatency']
BOLT_ATTRS = ['executors', 'emitted', 'transferred', 'acked', 'executeLatency', 'tasks', 'executed', 'processLatency', 'capacity', 'failed']

def getTimeSinceEpoch():
    return int(time.time())

def refreshStormTopologies():
    absolute_url = urljoin(STORM_URL, "/api/v1/topology/summary")
    r = requests.get(absolute_url)
    return [obj['encodedId'] for obj in r.json()['topologies']]

def getStormTopologyStats(topologyId):
    absolute_url = urljoin(STORM_URL, "/api/v1/topology/"+topologyId)
    payload = {'sys': 'false'}
    r = requests.get(absolute_url, params=payload)
    return r.json()

def gauge(prefix, attributes, obj):
    for attr in attributes:
        val = obj[attr]
        printMetric(prefix, attr, val)

def printMetric(prefix, key, value):
    namespace = prefix[:]
    namespace.insert(0, METRIC_PREFIX)
    namespace.append(key)
    now = getTimeSinceEpoch()
    metric = string.join(namespace, '.')

    # replace all non alphanumeric characters with an underscore
    metric = re.sub('[^\w\.\-]', '_', metric)
    print now, metric, value, HOST_TAG

def parseResponse(response):
    topologyName = response['name']

    prefix = ['topology', topologyName]

    # SUMMARY
    summary_prefix = prefix[:]
    summary_prefix.append('summary')
    gauge(summary_prefix, ['executorsTotal', 'workersTotal', 'tasksTotal'], response)

    # WINDOW STATS
    for window_stats in response['topologyStats']:
        window_name = WINDOW_NAMES[window_stats['window']]
        window_prefix = prefix[:]
        window_prefix.extend(['window', window_name])
        gauge(window_prefix, WINDOW_ATTRS, window_stats)

    # SPOUT STATS
    for spout_stats in response['spouts']:
        spout_name = spout_stats['encodedSpoutId']
        spout_prefix = prefix[:]
        spout_prefix.extend(['spout', spout_name])
        gauge(spout_prefix, SPOUT_ATTRS, spout_stats)

    # BOLT STATS
    for bolt_stats in response['bolts']:
        bolt_name = bolt_stats['encodedBoltId']
        bolt_prefix = prefix[:]
        bolt_prefix.extend(['bolt', bolt_name])
        gauge(bolt_prefix, BOLT_ATTRS, bolt_stats)

def startPolling():
    topologies = refreshStormTopologies()
    for topology_id in topologies:
        storm_response = getStormTopologyStats(topology_id)
        parseResponse(storm_response)

#    threading.Timer(INTERVAL, startPolling).start()

if __name__ == "__main__":
    startPolling()
