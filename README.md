Mininet
=======

Mininet (http://mininet.org) allows users to create entire networks on a single machine via the use of network namespaces. Network namespaces provide individual processes with separate network interfaces, routing tables and ARP tables.


The Mininet Client Interface
----------------------------

Mininet features a CLI that can be used to interact with the hosts. The CLI is started using the following command (issued as root):

sudo mn --custom <topology file> --topo <topology name>,<par 1>,<par 2>
adding the -x flag opens up an xterm console for each host

IMPORTANT: Whenever Mininet crashes, the system must be cleaned up:
```
mn -c
```
The following commands can be used from within the CLI:
* `nodes` - displays all the nodes (hosts and switches)
* `net` - displays the links between the nodes
* `dump` - dump useful information regarding the nodes (like IP address, interface names etc.)
`<host> <command>` - runs the command on the specified host (`h1 echo hello`); host names can be used as part of the command and the CLI will replace them with the appropriate IP (e.g. `h2 ping h3`)
 * `xterm <host>` - starts xterm; all programs executed from within said xterm will inherit the host's network namespace
 * `pingall` - makes all host pairs ping each other. This is a quick way of testing if your topology has connectivity across the board.
 * `link <node 1> <node 2> [up/down]` - enables/disables the link between two nodes
 * `intfs` - lists all interfaces by node
 * `exit` exits the CLI (`ctrl + D` also works)

**TASK 1**: Run "sudo mn" to start the Mininet CLI; Mininet will create a default topology.

 * View the nodes in this topology, as well as the network links.
 * Check network connectivity.
 * Check different hosts to see what network interfaces are available. How about the filesystem?
 * While running ping, bring one of the links down, and then back up again. Notice the gap in the echo replies received.


Topologies
----------

A custom Mininet topology is defined using a Python class. The following example (taken from the mininet VM in /home/mininet/mininet/custom/topo-2sw-2host.py) is a simple topology made up of two hosts and two switches; the switches are directly connected and each host is connected to a switch.

```
from mininet.topo import Topo

class MyTopo( Topo ):
    "Simple topology example."

    def __init__( self ):
        "Create custom topo."

        # Initialize topology
        Topo.__init__( self )

        # Add hosts and switches
        leftHost = self.addHost( 'h1' )
        rightHost = self.addHost( 'h2' )
        leftSwitch = self.addSwitch( 's3' )
        rightSwitch = self.addSwitch( 's4' )

        # Add links
        self.addLink( leftHost, leftSwitch )
        self.addLink( leftSwitch, rightSwitch )
        self.addLink( rightSwitch, rightHost )

topos = { 'mytopo': ( lambda: MyTopo() ) }
```

To run this topology type:

```
sudo mn --custom topo-2sw-2host.py --topo mytopo
```


**TASK 2**: Create a tree topology containing two layers of switches. On the lower layer, two top-of-rack switches connect two machines each (i.e. there are two machines in each rack, and two racks in the topology). The root of the topology is a switch connecting the two top-of-rack switches. Check connectivity.


**TASK 3**: Use the previously created topology to see what happens when the core is oversubscribed.
 * Rate-limit all interfaces to 10Mbps (hint: `sudo mn <args ...> --link=tc,bw=100>`)
 * Run a long iperf (hint: `iperf -c <...> -t 1000`) between a pair of hosts and see what impact statring a second iperf has:
   * Long iperf between h1 and h2, second iperf between h3 and h4
   * Long iperf between h1 and h3, second iperf between h2 and h4
   * Long iperf between h1 and h3, second iperf between h4 and h2
 * Which of these scenarios degrades the first iperf and why?

Fat Trees
---------

![Fatter than a sumo wrestler](https://raw.githubusercontent.com/vlolteanu/lab-mininet/master/fat_tree.png)

**TASK 4**: Use the provided script (`fat-tree.py`) to simulate a K=4 fat tree with 10Mbps links. (Call `clean_topology.sh` followed by `mn -c` if anything goes wrong.)
    
 * Create a 4-to-4 iperf traffic pattern, where 4 hosts from one pod each source iperf traffic to a host from a different pod. (The target pod should be the same for all 4 destinations.)
 * Start the flows one at a time and take note of how they perform after each one is added.
 * Chances very high are that at least one pair of connections won't get 10Mbps. Why is that?
 * There's a small, but non-trivial change that they will all achieve 10Mbps.
    
