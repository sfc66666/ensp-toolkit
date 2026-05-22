#!/usr/bin/env python3
"""
Campus Enterprise Network - Complete eNSP Topology + Configs

Network Architecture:
  - Dual Core VRRP (S5700 x2) for hot-standby redundancy
  - Three access zones: 机房/VLAN10, 教室/VLAN20, 宿舍楼/VLAN30
  - Full DHCP dynamic address allocation
  - Time-based QoS: rate-limit dormitory after midnight (00:00-06:00)
  - OSPF internal routing + NAT on firewall for internet access
"""

import sys, os
# ensp package is at tools/ensp/, so add tools/ to path
ENS_PKG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__).replace('\\', '/')))
TOOLS_DIR = os.path.dirname(ENS_PKG_DIR)
sys.path.insert(0, TOOLS_DIR)
from ensp.topo_builder import TopoBuilder
from ensp.device_config import VRPConfig

OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "campus_network")

# ═══════════════════════════════════════════════════════════════
# 1. BUILD TOPOLOGY
# ═══════════════════════════════════════════════════════════════

tb = TopoBuilder("campus_network", output_dir=OUTPUT_DIR)

# ── External ──
isp = tb.add_device("ISP", "Router", x=900, y=80)
ar1 = tb.add_device("AR1", "AR2240", x=900, y=200)

# ── Firewall ──
fw1 = tb.add_device("FW1", "USG6000V", x=900, y=320)

# ── Core Layer (Dual VRRP) ──
core1 = tb.add_device("CoreSW1", "S5700", x=600, y=460)
core2 = tb.add_device("CoreSW2", "S5700", x=1150, y=460)

# ── Access Layer ──
acc_jf = tb.add_device("AccSW-JF", "S3700", x=300, y=680)   # 机房
acc_js = tb.add_device("AccSW-JS", "S3700", x=750, y=680)   # 教室
acc_ss = tb.add_device("AccSW-SS", "S3700", x=1150, y=680)  # 宿舍楼

# ── Terminals ──
pc_jf1 = tb.add_device("PC-JF1", "PC", x=150, y=820, dhcp=True, gateway="192.168.10.254")
pc_jf2 = tb.add_device("PC-JF2", "PC", x=300, y=820, dhcp=True, gateway="192.168.10.254")
pc_js1 = tb.add_device("PC-JS1", "PC", x=600, y=820, dhcp=True, gateway="192.168.20.254")
pc_js2 = tb.add_device("PC-JS2", "PC", x=750, y=820, dhcp=True, gateway="192.168.20.254")
pc_ss1 = tb.add_device("PC-SS1", "PC", x=1000, y=820, dhcp=True, gateway="192.168.30.254")
pc_ss2 = tb.add_device("PC-SS2", "PC", x=1150, y=820, dhcp=True, gateway="192.168.30.254")

# ── Servers ──
srv_dhcp = tb.add_device("Server-DHCP", "Server", x=350, y=300, ip="192.168.100.10", mask="255.255.255.0", gateway="192.168.100.254")
srv_web  = tb.add_device("Server-Web", "Server", x=500, y=300, ip="192.168.100.20", mask="255.255.255.0", gateway="192.168.100.254")

# ── Links: External ──
tb.add_link(isp, ar1, "GE", "GE")
tb.add_link(ar1, fw1, "GE", "GE")

# ── Links: Firewall → Dual Core ──
tb.add_link(fw1, core1, "GE", "GE")
tb.add_link(fw1, core2, "GE", "GE")

# ── Links: Management Switch for Servers ──
tb.add_link(core1, srv_dhcp, "GE", "Ethernet")
tb.add_link(core1, srv_web, "GE", "Ethernet")

# ── Links: Core ↔ Core (interconnect for VRRP heartbeat) ──
tb.add_link(core1, core2, "GE", "GE")

# ── Links: Access → Dual Core (each access switch has redundant uplinks) ──
tb.add_link(acc_jf, core1, "GE", "GE")
tb.add_link(acc_jf, core2, "GE", "GE")
tb.add_link(acc_js, core1, "GE", "GE")
tb.add_link(acc_js, core2, "GE", "GE")
tb.add_link(acc_ss, core1, "GE", "GE")
tb.add_link(acc_ss, core2, "GE", "GE")

# ── Links: Terminals ──
tb.add_link(acc_jf, pc_jf1)
tb.add_link(acc_jf, pc_jf2)
tb.add_link(acc_js, pc_js1)
tb.add_link(acc_js, pc_js2)
tb.add_link(acc_ss, pc_ss1)
tb.add_link(acc_ss, pc_ss2)

tb.save()

# ═══════════════════════════════════════════════════════════════
# 2. DEVICE CONFIGURATIONS
# ═══════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("DEVICE CONFIGURATIONS")
print("=" * 60)

# ────────────────────────────────────────────────────────────
# CoreSW1 Configuration
# ────────────────────────────────────────────────────────────
cfg_core1 = VRPConfig("CoreSW1")

# VLANs
for vid, name in [(10, "Computer_Lab"), (20, "Classroom"), (30, "Dormitory"), (100, "Management")]:
    cfg_core1.add_vlan(vid, name)

# STP
cfg_core1.set_stp(mode="mstp", region_name="Campus",
    instance_configs=[
        {"id": 1, "vlans": "10 20"},
        {"id": 2, "vlans": "30"},
    ])

# DHCP
cfg_core1.enable_dhcp_global()
cfg_core1.add_dhcp_pool("vlan10_pool", "192.168.10.0", "255.255.255.0",
    gateway="192.168.10.254", dns_list=["8.8.8.8", "114.114.114.114"],
    excluded_ips=["192.168.10.254 192.168.10.250"])
cfg_core1.add_dhcp_pool("vlan20_pool", "192.168.20.0", "255.255.255.0",
    gateway="192.168.20.254", dns_list=["8.8.8.8", "114.114.114.114"],
    excluded_ips=["192.168.20.254 192.168.20.250"])
cfg_core1.add_dhcp_pool("vlan30_pool", "192.168.30.0", "255.255.255.0",
    gateway="192.168.30.254", dns_list=["8.8.8.8", "114.114.114.114"],
    excluded_ips=["192.168.30.254 192.168.30.250"])

# Uplink to FW
cfg_core1.set_interface("GigabitEthernet0/0/1", ip="10.0.0.2 255.255.255.252", undo_shutdown=True)

# Interconnect to CoreSW2
cfg_core1.set_interface("GigabitEthernet0/0/3", ip="10.0.100.1 255.255.255.252", undo_shutdown=True)

# Downlinks to Access Switches (Trunk)
for port, name in [(4, "AccSW-JF-1"), (5, "AccSW-JS-1"), (6, "AccSW-SS-1")]:
    cfg_core1.set_interface(f"GigabitEthernet0/0/{port}",
        description=name, link_type="trunk", trunk_allow="10 20 30 100", undo_shutdown=True)

# Management
cfg_core1.set_interface("GigabitEthernet0/0/2", ip="192.168.100.252 255.255.255.0", undo_shutdown=True)
cfg_core1.set_interface("GigabitEthernet0/0/7", description="Server-DHCP", link_type="access", access_vlan=100, undo_shutdown=True)
cfg_core1.set_interface("GigabitEthernet0/0/8", description="Server-Web", link_type="access", access_vlan=100, undo_shutdown=True)

# VLAN interfaces with VRRP (CoreSW1 is master for VLAN 10,20; backup for VLAN 30)
cfg_core1.set_interface("Vlanif10", ip="192.168.10.252 255.255.255.0")
cfg_core1.add_vrrp("Vlanif10", vrid=10, virtual_ip="192.168.10.254", priority=120)
cfg_core1.set_interface("Vlanif20", ip="192.168.20.252 255.255.255.0")
cfg_core1.add_vrrp("Vlanif20", vrid=20, virtual_ip="192.168.20.254", priority=120)
cfg_core1.set_interface("Vlanif30", ip="192.168.30.252 255.255.255.0")
cfg_core1.add_vrrp("Vlanif30", vrid=30, virtual_ip="192.168.30.254", priority=100)
cfg_core1.set_interface("Vlanif100", ip="192.168.100.254 255.255.255.0")

# DHCP select global on VLAN interfaces
cfg_core1.set_interface("Vlanif10", dhcp_select_global=True)
cfg_core1.set_interface("Vlanif20", dhcp_select_global=True)
cfg_core1.set_interface("Vlanif30", dhcp_select_global=True)

# OSPF
cfg_core1.set_ospf(process_id=1, router_id="1.1.1.1",
    networks=[
        ("192.168.10.0", "0.0.0.255"),
        ("192.168.20.0", "0.0.0.255"),
        ("192.168.30.0", "0.0.0.255"),
        ("192.168.100.0", "0.0.0.255"),
        ("10.0.0.0", "0.0.0.3"),
        ("10.0.100.0", "0.0.0.3"),
    ])

print("\n--- CoreSW1 ---")
print(cfg_core1.build())

# ────────────────────────────────────────────────────────────
# CoreSW2 Configuration
# ────────────────────────────────────────────────────────────
cfg_core2 = VRPConfig("CoreSW2")

for vid, name in [(10, "Computer_Lab"), (20, "Classroom"), (30, "Dormitory"), (100, "Management")]:
    cfg_core2.add_vlan(vid, name)

cfg_core2.set_stp(mode="mstp", region_name="Campus",
    instance_configs=[
        {"id": 1, "vlans": "10 20"},
        {"id": 2, "vlans": "30"},
    ])

cfg_core2.enable_dhcp_global()
# Same DHCP pools on CoreSW2 (only one will respond due to VRRP)
cfg_core2.add_dhcp_pool("vlan10_pool", "192.168.10.0", "255.255.255.0",
    gateway="192.168.10.254", dns_list=["8.8.8.8", "114.114.114.114"],
    excluded_ips=["192.168.10.254 192.168.10.250"])
cfg_core2.add_dhcp_pool("vlan20_pool", "192.168.20.0", "255.255.255.0",
    gateway="192.168.20.254", dns_list=["8.8.8.8", "114.114.114.114"],
    excluded_ips=["192.168.20.254 192.168.20.250"])
cfg_core2.add_dhcp_pool("vlan30_pool", "192.168.30.0", "255.255.255.0",
    gateway="192.168.30.254", dns_list=["8.8.8.8", "114.114.114.114"],
    excluded_ips=["192.168.30.254 192.168.30.250"])

cfg_core2.set_interface("GigabitEthernet0/0/1", ip="10.0.0.6 255.255.255.252", undo_shutdown=True)
cfg_core2.set_interface("GigabitEthernet0/0/3", ip="10.0.100.2 255.255.255.252", undo_shutdown=True)

for port, name in [(4, "AccSW-JF-2"), (5, "AccSW-JS-2"), (6, "AccSW-SS-2")]:
    cfg_core2.set_interface(f"GigabitEthernet0/0/{port}",
        description=name, link_type="trunk", trunk_allow="10 20 30 100", undo_shutdown=True)

cfg_core2.set_interface("GigabitEthernet0/0/2", ip="192.168.100.253 255.255.255.0", undo_shutdown=True)

# VRRP - CoreSW2 is backup for VLAN 10,20; master for VLAN 30
cfg_core2.set_interface("Vlanif10", ip="192.168.10.253 255.255.255.0")
cfg_core2.add_vrrp("Vlanif10", vrid=10, virtual_ip="192.168.10.254", priority=100)
cfg_core2.set_interface("Vlanif20", ip="192.168.20.253 255.255.255.0")
cfg_core2.add_vrrp("Vlanif20", vrid=20, virtual_ip="192.168.20.254", priority=100)
cfg_core2.set_interface("Vlanif30", ip="192.168.30.253 255.255.255.0")
cfg_core2.add_vrrp("Vlanif30", vrid=30, virtual_ip="192.168.30.254", priority=120)
cfg_core2.set_interface("Vlanif100", ip="192.168.100.251 255.255.255.0")

cfg_core2.set_interface("Vlanif10", dhcp_select_global=True)
cfg_core2.set_interface("Vlanif20", dhcp_select_global=True)
cfg_core2.set_interface("Vlanif30", dhcp_select_global=True)

cfg_core2.set_ospf(process_id=1, router_id="2.2.2.2",
    networks=[
        ("192.168.10.0", "0.0.0.255"),
        ("192.168.20.0", "0.0.0.255"),
        ("192.168.30.0", "0.0.0.255"),
        ("192.168.100.0", "0.0.0.255"),
        ("10.0.0.4", "0.0.0.3"),
        ("10.0.100.0", "0.0.0.3"),
    ])

print("\n--- CoreSW2 ---")
print(cfg_core2.build())

# ────────────────────────────────────────────────────────────
# AccSW-JF (机房) Configuration
# ────────────────────────────────────────────────────────────
cfg_acc_jf = VRPConfig("AccSW-JF")
cfg_acc_jf.add_vlan(10, "Computer_Lab")
cfg_acc_jf.add_vlan(100, "Management")

# Uplinks to core (Eth-Trunk for redundancy)
cfg_acc_jf.add_eth_trunk(1, ["Ethernet0/0/21", "Ethernet0/0/22"],
    link_type="trunk", trunk_allow="10 100")

# Access ports for PCs
for port in range(1, 21):
    cfg_acc_jf.set_interface(f"Ethernet0/0/{port}",
        link_type="access", access_vlan=10, undo_shutdown=True)

cfg_acc_jf.set_stp(mode="mstp", region_name="Campus",
    instance_configs=[{"id": 1, "vlans": "10 20"}])

print("\n--- AccSW-JF (机房) ---")
print(cfg_acc_jf.build())

# ────────────────────────────────────────────────────────────
# AccSW-JS (教室) Configuration
# ────────────────────────────────────────────────────────────
cfg_acc_js = VRPConfig("AccSW-JS")
cfg_acc_js.add_vlan(20, "Classroom")
cfg_acc_js.add_vlan(100, "Management")

cfg_acc_js.add_eth_trunk(1, ["Ethernet0/0/21", "Ethernet0/0/22"],
    link_type="trunk", trunk_allow="20 100")

for port in range(1, 21):
    cfg_acc_js.set_interface(f"Ethernet0/0/{port}",
        link_type="access", access_vlan=20, undo_shutdown=True)

cfg_acc_js.set_stp(mode="mstp", region_name="Campus",
    instance_configs=[{"id": 1, "vlans": "10 20"}])

print("\n--- AccSW-JS (教室) ---")
print(cfg_acc_js.build())

# ────────────────────────────────────────────────────────────
# AccSW-SS (宿舍楼) Configuration
# ────────────────────────────────────────────────────────────
cfg_acc_ss = VRPConfig("AccSW-SS")
cfg_acc_ss.add_vlan(30, "Dormitory")
cfg_acc_ss.add_vlan(100, "Management")

cfg_acc_ss.add_eth_trunk(1, ["Ethernet0/0/21", "Ethernet0/0/22"],
    link_type="trunk", trunk_allow="30 100")

for port in range(1, 21):
    cfg_acc_ss.set_interface(f"Ethernet0/0/{port}",
        link_type="access", access_vlan=30, undo_shutdown=True)

cfg_acc_ss.set_stp(mode="mstp", region_name="Campus",
    instance_configs=[{"id": 2, "vlans": "30"}])

print("\n--- AccSW-SS (宿舍楼) ---")
print(cfg_acc_ss.build())

# ────────────────────────────────────────────────────────────
# AR1 (Border Router) Configuration
# ────────────────────────────────────────────────────────────
cfg_ar1 = VRPConfig("AR1")

cfg_ar1.set_interface("GigabitEthernet0/0/0", ip="202.1.1.2 255.255.255.0", undo_shutdown=True,
    description="To-ISP")
cfg_ar1.set_interface("GigabitEthernet0/0/1", ip="100.100.100.2 255.255.255.0", undo_shutdown=True,
    description="To-FW1")
cfg_ar1.set_interface("GigabitEthernet0/0/2", ip="10.0.10.1 255.255.255.0", undo_shutdown=True,
    description="To-Core-OSPF")

cfg_ar1.set_default_route("202.1.1.1")
cfg_ar1.add_static_route("192.168.0.0", "255.255.0.0", "10.0.10.2")

# OSPF for internal routes
cfg_ar1.set_ospf(process_id=1, router_id="10.10.10.10",
    networks=[("10.0.10.0", "0.0.0.255")],
    default_advertise=True)

print("\n--- AR1 (Border Router) ---")
print(cfg_ar1.build())

# ────────────────────────────────────────────────────────────
# FW1 (Firewall) Configuration - with Night QoS
# ────────────────────────────────────────────────────────────
cfg_fw1 = VRPConfig("FW1")

# External interface
cfg_fw1.set_interface("GigabitEthernet1/0/0", ip="100.100.100.1 255.255.255.0", undo_shutdown=True,
    description="To-AR1")

# Internal interfaces to dual core
cfg_fw1.set_interface("GigabitEthernet1/0/1", ip="10.0.0.1 255.255.255.252", undo_shutdown=True,
    description="To-CoreSW1")
cfg_fw1.set_interface("GigabitEthernet1/0/2", ip="10.0.0.5 255.255.255.252", undo_shutdown=True,
    description="To-CoreSW2")

# Security zones
cfg_fw1.add_line("firewall zone trust")
cfg_fw1.add_line(" set priority 85")
cfg_fw1.add_line(" add interface GigabitEthernet1/0/1")
cfg_fw1.add_line(" add interface GigabitEthernet1/0/2")
cfg_fw1.add_line("#")
cfg_fw1.add_line("firewall zone untrust")
cfg_fw1.add_line(" set priority 5")
cfg_fw1.add_line(" add interface GigabitEthernet1/0/0")
cfg_fw1.add_line("#")

# Security policy
cfg_fw1.add_line("security-policy")
cfg_fw1.add_line(" rule name trust_to_untrust")
cfg_fw1.add_line("  source-zone trust")
cfg_fw1.add_line("  destination-zone untrust")
cfg_fw1.add_line("  action permit")
cfg_fw1.add_line("#")

# Time-range for night rate limiting (midnight 00:00 - 06:00)
cfg_fw1.add_line("time-range NIGHT_LIMIT 00:00 to 06:00 daily")
cfg_fw1.add_line("#")

# ACL for dormitory subnet (VLAN 30 = 192.168.30.0/24)
cfg_fw1.add_acl_named("dormitory_traffic", 3000, [
    "rule 5 permit ip source 192.168.30.0 0.0.0.255 destination any time-range NIGHT_LIMIT",
])
cfg_fw1.add_acl_named("internal_traffic", 3001, [
    "rule 5 permit ip source 192.168.0.0 0.0.255.255",
])

# NAT outbound (all internal traffic)
cfg_fw1.set_interface("GigabitEthernet1/0/0", nat_outbound="3001")

# Traffic policy for night rate limiting
cfg_fw1.add_line("traffic classifier night_dormitory operator or")
cfg_fw1.add_line(" if-match acl 3000")
cfg_fw1.add_line("#")
cfg_fw1.add_line("traffic behavior limit_night")
cfg_fw1.add_line(" car cir 2048 cbs 256000 pbs 512000 green pass yellow pass red discard")
cfg_fw1.add_line("#")
cfg_fw1.add_line("traffic policy QoS_NIGHT")
cfg_fw1.add_line(" classifier night_dormitory behavior limit_night")
cfg_fw1.add_line("#")
cfg_fw1.set_interface("GigabitEthernet1/0/1", traffic_policy_in="QoS_NIGHT")
cfg_fw1.set_interface("GigabitEthernet1/0/2", traffic_policy_in="QoS_NIGHT")

# OSPF
cfg_fw1.set_ospf(process_id=1, router_id="3.3.3.3",
    networks=[
        ("10.0.0.0", "0.0.0.3"),
        ("10.0.0.4", "0.0.0.3"),
    ])

print("\n--- FW1 (Firewall + Night QoS) ---")
print(cfg_fw1.build())

# ────────────────────────────────────────────────────────────
# ISP Router
# ────────────────────────────────────────────────────────────
cfg_isp = VRPConfig("ISP")
cfg_isp.set_interface("GigabitEthernet0/0/0", ip="202.1.1.1 255.255.255.0", undo_shutdown=True,
    description="To-AR1")
cfg_isp.set_interface("LoopBack0", ip="8.8.8.8 255.255.255.255")
cfg_isp.add_static_route("192.168.0.0", "255.255.0.0", "202.1.1.2")
cfg_isp.add_static_route("100.100.100.0", "255.255.255.0", "202.1.1.2")

print("\n--- ISP ---")
print(cfg_isp.build())


# ═══════════════════════════════════════════════════════════════
# 3. WRITE CONFIGS TO DEVICE DIRECTORIES
# ═══════════════════════════════════════════════════════════════

import zipfile

device_configs = {
    core1.id: cfg_core1.build(),
    core2.id: cfg_core2.build(),
    acc_jf.id: cfg_acc_jf.build(),
    acc_js.id: cfg_acc_js.build(),
    acc_ss.id: cfg_acc_ss.build(),
    ar1.id: cfg_ar1.build(),
    fw1.id: cfg_fw1.build(),
    isp.id: cfg_isp.build(),
}

for dev_id, cfg_text in device_configs.items():
    dev_dir = os.path.join(OUTPUT_DIR, dev_id)
    os.makedirs(dev_dir, exist_ok=True)
    cfg_path = os.path.join(dev_dir, "vrpcfg.zip")
    with zipfile.ZipFile(cfg_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("vrpcfg.cfg", cfg_text)
    print(f"Saved config: {dev_dir}/vrpcfg.zip")


print("\n" + "=" * 60)
print("CAMPUS NETWORK GENERATION COMPLETE")
print(f"Output: {OUTPUT_DIR}")
print("=" * 60)
print("""
Network Summary:
  ┌──────────┐
  │   ISP    │ 202.1.1.1
  └────┬─────┘
       │ 202.1.1.0/24
  ┌────┴─────┐
  │   AR1    │ Border Router (Static + OSPF default-route)
  └────┬─────┘
       │ 100.100.100.0/24
  ┌────┴─────┐
  │   FW1    │ Firewall: NAT + Night QoS (00:00-06:00 CAR 2Mbps)
  └──┬───┬───┘
     │   │ 10.0.0.0/30, 10.0.0.4/30
  ┌──┴─┐ ┌┴───┐
  │CSW1│ │CSW2│  Dual Core VRRP (HSB)
  └──┬─┘ └┬───┘
  ═══╪═════╪═══ Trunk Links (Eth-Trunk)
  ┌──┴──┐┌─┴────┐┌──┴──┐
  │JF-SW││JS-SW ││SS-SW│  Access Layer
  │机房 ││教室  ││宿舍 │
  └──┬──┘└──┬───┘└──┬──┘
  VLAN10  VLAN20  VLAN30
  192.168.10.0/24  192.168.20.0/24  192.168.30.0/24
  (DHCP)           (DHCP)           (DHCP + Night Limit)

VRRP Groups:
  CoreSW1 master: VLAN 10,20 (priority 120)
  CoreSW2 master: VLAN 30 (priority 120)

Night QoS (00:00-06:00):
  Dormitory (VLAN 30) → CAR 2048kbps (2Mbps)
  Other zones unaffected
""")
