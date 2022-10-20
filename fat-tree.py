#!/usr/bin/python3

from mininet.link import TCLink
from mininet.net import Mininet
from mininet.node import OVSController
from mininet.log import setLogLevel, info
from mininet.cli import CLI
import argparse

host_objs = []
core_objs = []
spine_objs = []
tor_objs = []
connections = {}


def smallfat(K, bw, cli, ping, iperf):
    cores = K
    spines = int(K * K / 2)
    pods = K
    pod_size = int(K / 2)
    hosts = pods * pod_size
    tors = spines
    link_bw = int(bw)

    net = Mininet(link = TCLink)

    net.addController('ctr', controller=OVSController, protocols="OpenFlow13")

    current_hosts = 0
    # Add hosts and switches
    for i in range(pods):
        nr = 8 * i
        for j in range(pod_size * pod_size):
            host_name = 'u' + str(current_hosts)
            current_hosts += 1
            host_params = {
                'name': host_name,
                'mac': '',
                'ip': '10.0.0.' + str(nr + j + 1),
                'default': 'via 10.0.0.' + str(nr),
                'netmask': '/29'
            }
            if nr + j + 1 < 10:
                host_params['mac'] = '00:00:00:00:00:0' + str(nr + j + 1)
            else:
                host_params['mac'] = '00:00:00:00:00:' + str(nr + j + 1)
            host = net.addHost(host_params['name'], mac=host_params['mac'], ip=host_params['ip'] + host_params['netmask'], defaultRoute=host_params['default'])
            host_objs.append((host, host_params))
            connections[host_name] = {}
            connections[host_name]['links'] = []
            connections[host_name]['reachable_ips'] = {}

    for i in range(cores):
        core_name = 'c' + str(i)
        core = net.addSwitch(core_name, protocols='OpenFlow13')
        core_objs.append((core, core_name))
        connections[core_name] = {}
        connections[core_name]['links'] = []
        connections[core_name]['reachable_ips'] = {}

    for i in range(spines):
        spine_name = 's' + str(i)
        spine = net.addSwitch(spine_name, protocols='OpenFlow13')
        spine_objs.append((spine, spine_name))
        connections[spine_name] = {}
        connections[spine_name]['links'] = []
        connections[spine_name]['reachable_ips'] = {}

        tor_name = 't' + str(i)
        tor = net.addSwitch(tor_name, protocols='OpenFlow13')
        tor_objs.append((tor, tor_name))
        connections[tor_name] = {}
        connections[tor_name]['links'] = []
        connections[tor_name]['reachable_ips'] = {}

    # Add links - tor-host
    for tor_nr in range(tors):
        (tor, tor_name) = tor_objs[tor_nr]
        for i in range(tor_nr * pod_size, (tor_nr + 1) * pod_size):
            (host, host_params) = host_objs[i]
            host_name = host_params['name']

            link_name = tor_name + '-' + host_name
            link_name_rev = host_name + '-' + tor_name
            net.addLink(tor, host, intfName1=link_name, intfName2=link_name_rev, bw=link_bw) #1000)

            connections[tor_name]['links'].append(link_name)
            connections[host_name]['links'].append(link_name_rev)

            connections[tor_name]['reachable_ips'][host_name] = [host_params['ip']]

    # Add links - spine-tor
    for pod_nr in range(pods):
        for i in range(pod_nr * pod_size, (pod_nr + 1) * pod_size):
            (spine, spine_name) = spine_objs[i]

            for j in range(pod_nr * pod_size, (pod_nr + 1) * pod_size):
                (tor, tor_name) = tor_objs[j]

                link_name = spine_name + '-' + tor_name
                link_name_rev = tor_name + '-' + spine_name
                net.addLink(spine, tor, intfName1=link_name, intfName2=link_name_rev, bw=link_bw)

                connections[spine_name]['links'].append(link_name)
                connections[tor_name]['links'].append(link_name_rev)

                tor_ips = [ip for ip_list in connections[tor_name]['reachable_ips'].values() for ip in ip_list]
                tor_ips = list(dict.fromkeys(tor_ips))
                connections[spine_name]['reachable_ips'][tor_name] = tor_ips

    # Add links - core-spine
    for i in range(int(cores / 2)):
        (core, core_name) = core_objs[i]

        for j in range(0, spines, 2):    
            (spine, spine_name) = spine_objs[j]

            link_name = core_name + '-' + spine_name
            link_name_rev = spine_name + '-' + core_name
            net.addLink(core, spine, intfName1=link_name, intfName2=link_name_rev, bw=link_bw)
            
            connections[core_name]['links'].append(link_name)
            connections[spine_name]['links'].append(link_name_rev)

            spine_ips = list(connections[spine_name]['reachable_ips'].values())
            connections[core_name]['reachable_ips'][spine_name] = []
            for ips in spine_ips:
                connections[core_name]['reachable_ips'][spine_name].extend(ips)

    for i in range(int(cores / 2), cores):
        (core, core_name) = core_objs[i]

        for j in range(1, spines, 2):    
            (spine, spine_name) = spine_objs[j]

            link_name = core_name + '-' + spine_name
            link_name_rev = spine_name + '-' + core_name
            net.addLink(core, spine, intfName1=link_name, intfName2=link_name_rev, bw=link_bw)

            connections[core_name]['links'].append(link_name)
            connections[spine_name]['links'].append(link_name_rev)

            spine_ips = list(connections[spine_name]['reachable_ips'].values())
            connections[core_name]['reachable_ips'][spine_name] = []
            for ips in spine_ips:
                connections[core_name]['reachable_ips'][spine_name].extend(ips)

    net.start()

    ## core flows - only downward

    for (core, core_name) in core_objs:
        for spine_name in connections[core_name]['reachable_ips']:
            link_name = core_name + '-' + spine_name
            for ip in connections[core_name]['reachable_ips'][spine_name]:
                core.cmd('ovs-ofctl -O OpenFlow13 add-flow ' + core_name + ' ip,nw_dst=' + ip + ',actions=output=' + link_name)

    ## spine flows

    # downward flows
    for (spine, spine_name) in spine_objs:
        for tor_name in connections[spine_name]['reachable_ips']:
            link_name = spine_name + '-' + tor_name
            for ip in connections[spine_name]['reachable_ips'][tor_name]:
                core.cmd('ovs-ofctl -O OpenFlow13 add-flow ' + spine_name + ' ip,nw_dst=' + ip + ',actions=output=' + link_name)

    # learn what the cores can reach
    for (spine, spine_name) in spine_objs:
        for (core, core_name) in core_objs:
            link_name = spine_name + '-' + core_name
            if link_name not in connections[spine_name]['links']:
                continue

            core_known = connections[core_name]['reachable_ips']
            connections[spine_name]['reachable_ips'][core_name] = []
            for other_spine in core_known:
                if spine_name == other_spine:
                    continue
                
                connections[spine_name]['reachable_ips'][core_name].extend(core_known[other_spine])

    # downward flows
    for (spine, spine_name) in spine_objs:
        upward_options = []
        for switch_name in connections[spine_name]['reachable_ips']:
            if switch_name[0] == 't':
                continue

            link_name = spine_name + '-' + switch_name
            upward_options.append(link_name)
            
        cmd = 'ovs-ofctl -O OpenFlow13 add-group ' + spine_name +' group_id=1,type=select,selection_method=dp_hash'
        for option in upward_options:
            cmd = cmd + ',bucket=actions=output=' + option

        spine.cmd(cmd)
        for switch_name in connections[spine_name]['reachable_ips']:
            if switch_name[0] == 't':
                continue

            for ip in connections[spine_name]['reachable_ips'][switch_name]:
                spine.cmd('ovs-ofctl -O OpenFlow13 add-flow ' + spine_name + ' ip,nw_dst=' + ip + ',actions=group:1')
            break

    ## tor flows
    
    # downward flows
    for (tor, tor_name) in tor_objs:
        for host_name in connections[tor_name]['reachable_ips']:
            link_name = tor_name + '-' + host_name
            for ip in connections[tor_name]['reachable_ips'][host_name]:
                tor.cmd('ovs-ofctl -O OpenFlow13 add-flow ' + tor_name + ' ip,nw_dst=' + ip + ',actions=output=' + link_name)

    # learn what the spines can reach
    for (tor, tor_name) in tor_objs:
        for (spine, spine_name) in spine_objs:
            link_name = tor_name + '-' + spine_name
            if link_name not in connections[tor_name]['links']:
                continue

            spine_known = connections[spine_name]['reachable_ips']
            connections[tor_name]['reachable_ips'][spine_name] = []
            for other_switch in spine_known:
                if tor_name == other_switch:
                    continue
                
                connections[tor_name]['reachable_ips'][spine_name].extend(spine_known[other_switch])

    # downward flows
    for (tor, tor_name) in tor_objs:
        upward_options = []
        for switch_name in connections[tor_name]['reachable_ips']:
            if switch_name[0] == 'u':
                continue

            link_name = tor_name + '-' + switch_name
            upward_options.append(link_name)
            
        cmd = 'ovs-ofctl -O OpenFlow13 add-group ' + tor_name +' group_id=1,type=select,selection_method=dp_hash'
        for option in upward_options:
            cmd = cmd + ',bucket=actions=output=' + option

        tor.cmd(cmd)
        for switch_name in connections[tor_name]['reachable_ips']:
            if switch_name[0] == 'u':
                continue

            ips = connections[tor_name]['reachable_ips'][switch_name]
            ips = list(dict.fromkeys(ips))

            for ip in ips:
                tor.cmd('ovs-ofctl -O OpenFlow13 add-flow ' + tor_name + ' ip,nw_dst=' + ip + ',actions=group:1')
            break

    # host arp entries and routes
    for (host, host_params) in host_objs:
        host_name = host_params['name']
        host_link = connections[host_name]['links'][0]
        
        for (_, other_host_params) in host_objs:
            other_host_name = other_host_params['name']
            other_host_ip = other_host_params['ip']
            other_host_ntw = other_host_params['default'][4:]
            other_host_mac = other_host_params['mac']
            other_host_netmask = other_host_params['netmask']

            if host_name == other_host_name:
                continue
            
            host.cmd('ip r add ' + other_host_ntw + other_host_netmask + ' dev ' + host_link)
            
            host.cmd('arp -s ' + other_host_ip + ' ' + other_host_mac)

    if ping:
        net.pingAll()
    
    if iperf:
        net.iperf(None)

    if cli:
        CLI(net)

    net.stop()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-K', type=int, default=4)
    parser.add_argument('--bw', type=int, default=10)
    parser.add_argument('--no-cli', action='store_true')
    parser.add_argument('--pingall', action='store_true')
    parser.add_argument('--iperf', action='store_true')

    args = parser.parse_args()

    # setLogLevel( 'info' )
    smallfat(K=args.K, bw=args.bw, cli=(not args.no_cli), ping=args.pingall, iperf=args.iperf)

