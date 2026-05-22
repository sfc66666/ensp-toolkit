# eNSP Toolkit

Python toolkit for programmatically generating Huawei eNSP (Enterprise Network Simulation Platform) network topologies and device configurations.

## Features

- **Topology Builder** — Create eNSP `.topo` files programmatically with `TopoBuilder`
- **VRP Config Generator** — Generate Huawei VRP device configurations with `VRPConfig`
- **6+ device models** — S3700, S5700, AR2240, USG6000V, Router, PC/Server/Client
- **Full VRP support** — VLAN, STP, OSPF, DHCP, ACL, NAT, VRRP, Eth-Trunk, QoS

## Quick Start

```python
from ensp import TopoBuilder, VRPConfig

# Create a topology with 2 switches and 2 PCs
tb = TopoBuilder("my_network", output_dir="./output")

core = tb.add_device("CoreSW", "S5700", x=400, y=200)
acc = tb.add_device("AccSW", "S3700", x=400, y=450)
pc1 = tb.add_device("PC1", "PC", x=200, y=600,
    ip="192.168.1.1", mask="255.255.255.0", gateway="192.168.1.254")
pc2 = tb.add_device("PC2", "PC", x=600, y=600,
    ip="192.168.1.2", mask="255.255.255.0", gateway="192.168.1.254")

tb.add_link(core, acc, "GE", "GE")
tb.add_link(acc, pc1)
tb.add_link(acc, pc2)

tb.save()  # Generates .topo file and device config directories

# Generate a switch configuration
cfg = VRPConfig("CoreSW")
cfg.add_vlan(10, "Office")
cfg.add_vlan(20, "Guest")
cfg.set_interface("GigabitEthernet0/0/0",
    link_type="trunk", trunk_allow="10 20", undo_shutdown=True)
cfg.set_interface("Vlanif10", ip="192.168.10.254 255.255.255.0")
cfg.set_interface("Vlanif20", ip="192.168.20.254 255.255.255.0")

print(cfg.build())
```

## Device Models

| Model | Description | Interfaces |
|-------|-------------|------------|
| `S3700` | Layer 3 access switch | 22 Eth + 2 GE |
| `S5700` | Layer 3 core switch | 24 GE |
| `AR2240` | Enterprise router | 3 GE |
| `USG6000V` | Next-gen firewall | 8 GE |
| `Router` | Generic router | 2 Eth + 4 GE + 4 Serial |
| `PC` | Endpoint | 1 Eth |
| `Server` | Server endpoint | 1 Eth |
| `Client` | Client endpoint | 1 Eth |
| `Cloud` | Host bridge | 1 Eth |

## VRP Config Generator

```python
cfg = VRPConfig("MyRouter")

# VLAN
cfg.add_vlan(10, "Engineering")
cfg.add_vlan_batch([20, 30, 40])

# Layer 2 interfaces
cfg.set_interface("GigabitEthernet0/0/0",
    link_type="trunk", trunk_allow="10 20 30", undo_shutdown=True)
cfg.set_interface("Ethernet0/0/1",
    link_type="access", access_vlan=10, undo_shutdown=True)

# Layer 3 interfaces
cfg.set_interface("Vlanif10", ip="192.168.10.254 255.255.255.0")
cfg.set_interface("GigabitEthernet0/0/2", ip="10.0.0.1 255.255.255.252")

# OSPF
cfg.set_ospf(process_id=1, router_id="1.1.1.1",
    networks=[("192.168.10.0", "0.0.0.255"), ("10.0.0.0", "0.0.0.3")])

# Static routes
cfg.add_static_route("192.168.100.0", "255.255.255.0", "10.0.0.2")

# DHCP
cfg.enable_dhcp_global()
cfg.add_dhcp_pool("vlan10_pool", "192.168.10.0", "255.255.255.0",
    gateway="192.168.10.254", dns_list=["8.8.8.8"])

# ACL + NAT
cfg.add_acl(2000, [
    "rule 5 permit source 192.168.10.0 0.0.0.255",
])
cfg.add_nat_outbound(2000)

# STP
cfg.set_stp(mode="mstp", region_name="HQ",
    instance_configs=[{"id": 1, "vlans": "10 20"}])

# Link aggregation
cfg.add_eth_trunk(1, ["GigabitEthernet0/0/3", "GigabitEthernet0/0/4"],
    link_type="trunk", trunk_allow="all")

# VRRP
cfg.add_vrrp("Vlanif10", vrid=1, virtual_ip="192.168.10.1", priority=120)

print(cfg.build())
```

## Output Structure

```
output/
├── my_network.topo              # Topology XML (open in eNSP)
├── {UUID}/                      # Per-device config directory
│   └── vrpcfg.zip               # Contains vrpcfg.cfg
└── ...
```

Open `my_network.topo` in eNSP, start the devices, and import the generated configs into each device console.
