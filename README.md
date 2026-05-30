# eNSP Toolkit

Python toolkit for programmatically generating Huawei **eNSP** (Enterprise Network
Simulation Platform) network topologies and VRP device configurations.

Stop dragging devices around in eNSP by hand — define your topology and configs
in Python, export a `.topo` file and per-device `vrpcfg.zip` that eNSP opens
directly.

## Installation

```bash
# Clone anywhere
git clone https://github.com/sfc66666/ensp-toolkit.git
cd ensp-toolkit

# Editable install — makes `import ensp` work everywhere
pip install -e .
```

Or use it without installing by adding the repo to your `sys.path`:

```python
import sys
sys.path.insert(0, "/path/to/ensp-toolkit")
from ensp import TopoBuilder, VRPConfig
```

---

## 5-Minute Quick Start

Build a simple LAN with one switch and two PCs:

```python
from ensp import TopoBuilder, VRPConfig

# ── 1. Create topology ──────────────────────────────────────
tb = TopoBuilder("my_lan", output_dir="./output")

sw  = tb.add_device("SW1",  "S3700", x=400, y=300)
pc1 = tb.add_device("PC1",  "PC",    x=200, y=500,
                    ip="192.168.1.10", mask="255.255.255.0",
                    gateway="192.168.1.1")
pc2 = tb.add_device("PC2",  "PC",    x=600, y=500,
                    dhcp=True)  # ← DHCP client (no manual IP needed)

tb.add_link(sw, pc1)   # default: Ethernet
tb.add_link(sw, pc2)

tb.save()               # writes .topo + vrpcfg.zip per device

# ── 2. Generate switch config ───────────────────────────────
cfg = VRPConfig("SW1")
cfg.add_vlan(10, "Office")
cfg.set_interface("Vlanif10", ip="192.168.1.1 255.255.255.0",
                  undo_shutdown=True)
cfg.set_interface("Ethernet0/0/1",
                  link_type="access", access_vlan=10, undo_shutdown=True)
cfg.set_interface("Ethernet0/0/2",
                  link_type="access", access_vlan=10, undo_shutdown=True)

print(cfg.build())
```

**Output** (open `output/my_lan.topo` in eNSP, import `vrpcfg.zip` per device):

```
[V200R003C00]
#
 sysname SW1
#
vlan 10
 description Office
#
interface Ethernet0/0/1
 port link-type access
 port default vlan 10
 undo shutdown
#
interface Ethernet0/0/2
 port link-type access
 port default vlan 10
 undo shutdown
#
interface Vlanif10
 ip address 192.168.1.1 255.255.255.0
 undo shutdown
#
user-interface con 0
 authentication-mode password
user-interface vty 0 4
user-interface vty 16 20
#
return
```

---

## VLAN Routing with OSPF + DHCP

A more realistic setup: core switch doing inter-VLAN routing with DHCP:

```python
from ensp import TopoBuilder, VRPConfig

tb = TopoBuilder("vlan_routing", output_dir="./output")

core  = tb.add_device("CoreSW",  "S5700", x=500, y=200)
acc1  = tb.add_device("AccSW1",  "S3700", x=250, y=450)
acc2  = tb.add_device("AccSW2",  "S3700", x=750, y=450)
pc10  = tb.add_device("PC-V10",  "PC",    x=100, y=600, dhcp=True,
                      gateway="192.168.10.254")
pc20  = tb.add_device("PC-V20",  "PC",    x=900, y=600, dhcp=True,
                      gateway="192.168.20.254")

tb.add_link(core, acc1, "GE", "GE")
tb.add_link(core, acc2, "GE", "GE")
tb.add_link(acc1, pc10)
tb.add_link(acc2, pc20)
tb.save()

# Core switch config with DHCP server
cfg = VRPConfig("CoreSW")
cfg.add_vlan(10, "Engineering")
cfg.add_vlan(20, "Sales")
cfg.enable_dhcp_global()

cfg.add_dhcp_pool("pool10", "192.168.10.0", "255.255.255.0",
    gateway="192.168.10.254", dns_list=["8.8.8.8", "114.114.114.114"])
cfg.add_dhcp_pool("pool20", "192.168.20.0", "255.255.255.0",
    gateway="192.168.20.254", dns_list=["8.8.8.8"])

# Uplinks (trunk)
cfg.set_interface("GigabitEthernet0/0/0",
    link_type="trunk", trunk_allow="10 20", undo_shutdown=True)
cfg.set_interface("GigabitEthernet0/0/1",
    link_type="trunk", trunk_allow="10 20", undo_shutdown=True)

# VLAN interfaces (L3 gateways)
cfg.set_interface("Vlanif10", ip="192.168.10.254 255.255.255.0",
                  undo_shutdown=True, dhcp_select_global=True)
cfg.set_interface("Vlanif20", ip="192.168.20.254 255.255.255.0",
                  undo_shutdown=True, dhcp_select_global=True)

# OSPF (assume uplink to firewall at 10.0.0.0/30)
cfg.set_interface("GigabitEthernet0/0/2",
                  ip="10.0.0.2 255.255.255.252", undo_shutdown=True)
cfg.set_ospf(process_id=1, router_id="1.1.1.1",
    networks=[("192.168.10.0", "0.0.0.255"),
              ("192.168.20.0", "0.0.0.255"),
              ("10.0.0.0", "0.0.0.3")])

print(cfg.build())
```

---

## Dual-Core VRRP Redundancy

Hot-standby gateway using VRRP across two core switches:

```python
cfg_core1 = VRPConfig("CoreSW1")
cfg_core1.add_vlan(10, "Production")
cfg_core1.set_interface("Vlanif10", ip="192.168.10.252 255.255.255.0",
                        undo_shutdown=True)
cfg_core1.add_vrrp("Vlanif10", vrid=10, virtual_ip="192.168.10.254",
                   priority=120)                # Master (higher priority)

cfg_core2 = VRPConfig("CoreSW2")
cfg_core2.add_vlan(10, "Production")
cfg_core2.set_interface("Vlanif10", ip="192.168.10.253 255.255.255.0",
                        undo_shutdown=True)
cfg_core2.add_vrrp("Vlanif10", vrid=10, virtual_ip="192.168.10.254",
                   priority=100,                # Backup
                   auth_key="vrrp-secret")      # VRRP authentication

print(cfg_core1.build())
# interface Vlanif10
#  ip address 192.168.10.252 255.255.255.0
#  undo shutdown
#  vrrp vrid 10 virtual-ip 192.168.10.254
#  vrrp vrid 10 priority 120
#  vrrp vrid 10 preempt-mode timer delay 0
```

---

## Firewall with NAT + Time-Based QoS

eNSP USG6000V firewall with security zones, NAT, and per-ACL rate limiting:

```python
cfg = VRPConfig("FW1")

# External (untrust) and internal (trust) interfaces
cfg.set_interface("GigabitEthernet1/0/0",
    ip="100.1.1.1 255.255.255.0", undo_shutdown=True)       # WAN
cfg.set_interface("GigabitEthernet1/0/1",
    ip="10.0.0.1 255.255.255.252", undo_shutdown=True)      # → Core

# Security zones
cfg.add_line("firewall zone trust")
cfg.add_line(" set priority 85")
cfg.add_line(" add interface GigabitEthernet1/0/1")
cfg.add_line("#")
cfg.add_line("firewall zone untrust")
cfg.add_line(" set priority 5")
cfg.add_line(" add interface GigabitEthernet1/0/0")
cfg.add_line("#")

# Security policy (trust → untrust permit)
cfg.add_line("security-policy")
cfg.add_line(" rule name trust_to_untrust")
cfg.add_line("  source-zone trust")
cfg.add_line("  destination-zone untrust")
cfg.add_line("  action permit")
cfg.add_line("#")

# NAT (hide all internal traffic behind WAN IP)
cfg.add_acl_named("nat_acl", 2000, [
    "rule 5 permit ip source 192.168.0.0 0.0.255.255",
])
cfg.set_interface("GigabitEthernet1/0/0", nat_outbound="2000")

# Time-based QoS: rate-limit guest subnet after hours
cfg.add_line("time-range GUEST_LIMIT 22:00 to 06:00 daily")
cfg.add_line("#")
cfg.add_acl_named("guest_traffic", 3000, [
    "rule 5 permit ip source 192.168.99.0 0.0.0.255"
    " time-range GUEST_LIMIT",
])
cfg.add_line("traffic classifier guest_night operator or")
cfg.add_line(" if-match acl 3000")
cfg.add_line("#")
cfg.add_line("traffic behavior limit_2m")
cfg.add_line(" car cir 2048 cbs 256000 pbs 512000"
             " green pass yellow pass red discard")
cfg.add_line("#")
cfg.add_line("traffic policy QOS_POLICY")
cfg.add_line(" classifier guest_night behavior limit_2m")
cfg.add_line("#")
cfg.set_interface("GigabitEthernet1/0/1", traffic_policy_in="QOS_POLICY")

# OSPF to cores
cfg.set_ospf(process_id=1, router_id="10.0.0.1",
    networks=[("10.0.0.0", "0.0.0.3")])

print(cfg.build())
```

---

## Complete Campus Network Example

See [`examples/campus_network.py`](examples/campus_network.py) for a
fully-worked 16-device campus network featuring:

- Dual-core VRRP hot standby (S5700 × 2)
- 3 access zones (机房 / 教室 / 宿舍) with DHCP
- Firewall with security zones, NAT, and time-based QoS
- OSPF internal routing with default-route advertisement

Run it:
```bash
python examples/campus_network.py
# Output → ~/Desktop/campus_network/
```

---

## Device Models

| Model | Description | Interfaces |
|-------|-------------|------------|
| `S3700` | Layer 3 access switch | 22 Ethernet + 2 GE |
| `S5700` | Layer 3 core switch | 24 GE |
| `AR2240` | Enterprise router | 3 GE |
| `USG6000V` | Next-gen firewall | 8 GE |
| `Router` | Generic router | 2 Eth + 4 GE + 4 Serial |
| `PC` | Endpoint (static or DHCP) | 1 Ethernet |
| `Server` | Server endpoint | 1 Ethernet |
| `Client` | Client endpoint (HTTP) | 1 Ethernet |
| `Cloud` | Host bridge | 1 Ethernet |

---

## VRPConfig API Reference

### VLAN & Interfaces

| Method | Description |
|--------|-------------|
| `add_vlan(id, name?)` | Create a VLAN |
| `add_vlan_batch(ids)` | Create multiple VLANs |
| `set_interface(name, **opts)` | Configure an interface |

**`set_interface` options**: `ip`, `description`, `link_type`, `access_vlan`,
`trunk_allow`, `default_vlan`, `pvid`, `hybrid_tagged`, `hybrid_untagged`,
`undo_shutdown`, `stp_disable`, `trust_dscp`, `traffic_policy_in`,
`traffic_policy_out`, `nat_outbound`, `nat_server`, `eth_trunk`,
`qos_queue_profile`, `dhcp_select_global`

### Routing

| Method | Description |
|--------|-------------|
| `add_static_route(dest, mask, next_hop)` | IPv4 static route |
| `set_default_route(next_hop)` | Default route (0.0.0.0/0) |
| `set_ospf(pid, router_id, networks, ...)` | OSPF process with area 0 |
| `add_ospf_network(net, wc, area)` | Add network to OSPF area |

### High Availability

| Method | Description |
|--------|-------------|
| `set_stp(mode, region_name, instances)` | STP / MSTP |
| `add_eth_trunk(id, members, **opts)` | Link aggregation |
| `add_vrrp(ifname, vrid, vip, prio, preempt, auth_key)` | VRRP group |

### DHCP & NAT

| Method | Description |
|--------|-------------|
| `enable_dhcp_global()` | Enable DHCP server globally |
| `add_dhcp_pool(name, net, mask, gw, ...)` | Create DHCP pool |
| `add_acl(number, rules)` | Numbered ACL |
| `add_acl_named(name, number, rules)` | Named ACL |
| `add_nat_outbound(acl)` | Source NAT (hide behind interface IP) |
| `add_nat_server(proto, gip, gport, iip, iport)` | Destination NAT / port forward |

### Low-Level

| Method | Description |
|--------|-------------|
| `add_line(raw)` | Inject raw VRP line (firewall zones, time-range, etc.) |
| `add_traffic_policy(name, cb_pairs)` | Traffic classifier + behavior + policy |
| `build()` | Render complete VRP config string |

---

## Output Structure

```
output/
├── my_network.topo              # Topology XML → open in eNSP
├── {UUID}/                      # Per-device directory
│   └── vrpcfg.zip               # Contains vrpcfg.cfg → import in device console
└── ...
```

**Workflow**: Open `my_network.topo` in eNSP → start devices → right-click each
device → "Import Configuration" → select its `vrpcfg.zip`.

---

## License

MIT
