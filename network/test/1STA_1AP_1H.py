#!/usr/bin/python

"""Setting position of the nodes and enable sockets"""
import subprocess
import sys

import mn_wifi
from mininet.log import setLogLevel, info
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi
from mn_wifi.telemetry import util_dir
from mn_wifi.node import AP
import os
import time
from mn_wifi.link import wmediumd
from mn_wifi.wmediumdConnector import interference

start = time.time()
from threading import Thread as thread

class Stats:
    def __init__(self, nodes):
        self.nodes = nodes
        self.filename = '{}-mn-telemetry.txt'
        self.thread_ = None
    @classmethod
    def get_ifaces(cls, nodes, inNamespaceNodes, phys):
        cmd = 'ls /sys/class/ieee80211/{}/device/net/'
        ifaces = {}
        j = 0
        wlan = 1
        for phy in phys:
            try:
                ifaces_ = subprocess.check_output(cmd.format(phy), stderr=subprocess.PIPE,
                                                  shell=True).decode().split("\n")
            except:
                node = inNamespaceNodes[j]
                ifaces_ = subprocess.check_output('%s %s %s' % (util_dir, node, cmd.format(phy)),
                                                  shell=True).decode().split("\n")
            ifaces_.pop()
            if nodes[j] not in ifaces:
                ifaces[nodes[j]] = []
            ifaces[nodes[j]].append(ifaces_.pop())

            if wlan == len(nodes[j].params['wlan']):
                j += 1
                wlan = 1
            else:
                wlan += 1

        return ifaces

    @classmethod
    def get_phys(cls, nodes, inNamespaceNodes):
        cmd = 'ls /sys/class/ieee80211/'
        isAP = False
        phys = []
        for node in nodes:
            if isinstance(node, AP) and not isAP:
                phys += subprocess.check_output(cmd,
                                                shell=True).decode().split("\n")
                isAP = True
            else:
                if not isinstance(node, AP):
                    phys += subprocess.check_output('%s %s %s' % (util_dir, node, cmd),
                                                    shell=True).decode().split("\n")
        phy_list = []
        phys = sorted(phys)
        for phy in phys:
            if 'mn' in phy:
                phy_list.append(phy)

        ifaces = cls.get_ifaces(nodes, inNamespaceNodes, phy_list)
        return phy_list, ifaces

    def start(self):

        inNamespaceNodes = []
        nodes_x = {}
        nodes_y = {}
        names = []
        time_ = time.time() - start
        for node in self.nodes:
            if not isinstance(node, AP):
                inNamespaceNodes.append(node)
            if os.path.exists('%s' % (self.filename.format(node))):
                os.system('rm %s' % (self.filename.format(node)))
            if node.name not in names:
                names.append(node.name)

        self.phys, self.ifaces = self.get_phys(self.nodes, inNamespaceNodes)

        while self.thread_._keep_alive:
            for node in self.nodes:
                x, y, z = mn_wifi.telemetry.get_position(node)
                for wlan in range(len(node.params['wlan'])):
                    names.append(self.ifaces[node][wlan])
                    nodes_x[node], nodes_y[node] = [], []
                    rssi = mn_wifi.telemetry.get_rssi(node, self.ifaces[node][wlan])
                    os.system("echo '%s, %s, %s, %s' >> %s" % (time_, x, y, rssi, self.filename.format(node)))
            time.sleep(0.5)



def topology(args):
    net = Mininet_wifi(topo=None,
                       build=False,
                       link=wmediumd,
                       wmediumd_mode=interference)

    info("*** Creating nodes\n")
    net.addStation('sta1', mac='00:00:00:00:00:02', ip='10.0.0.1/8',
                   position='0,0,0')

    h1 = net.addHost('h1', ip='10.0.0.2/8')#, position='5,0,0')
    ap1 = net.addAccessPoint('ap1', ssid='new-ssid', mode='g', channel='1', position='100,100,0')
    ap2 = net.addAccessPoint('ap2', ssid='ssid-ap2', channel='6', position='200,100,0')
    net.setPropagationModel(model="logDistance",sL = 4, exp=4)
    #net.setPropagationModel(model="logNormalShadowing", sL=2, exp=4, variance=2)
    info("*** Configuring wifi nodes\n")
    net.configureWifiNodes()

    info("*** Creating links\n")
    net.addLink(ap1, h1)

    if '-p' not in args:
        net.plotGraph(max_x=500, max_y=500)
    nodes = net.stations  #+ net.aps
    net.telemetry(nodes=nodes, single=True, max_x=1000, max_y=1000)
    stat = Stats(nodes)
    stat.thread_ = thread(target=stat.start)
    stat.thread_.daemon = True
    stat.thread_._keep_alive = True
    stat.thread_.start()

    info("*** Starting Network\n")
    net.addNAT(linkTo='ap1').configDefault()
    net.build()
    ap1.start([])

    info("*** Staring Socket Server\n")

    net.socketServer(ip='127.0.0.1', port=12345)

    info("*** Running CLI\n")
    CLI(net)

    info("*** Stopping network\n")
    net.stop()


if __name__ == '__main__':
    os.system('sudo service network-manager stop')
    setLogLevel('info')
    topology(sys.argv)