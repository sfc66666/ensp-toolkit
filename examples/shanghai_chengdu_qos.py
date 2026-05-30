#!/usr/bin/env python3
"""
Shanghai HQ + Chengdu Branch — Enterprise QoS Network

┌─ Shanghai HQ ──────────────────────────────────────────────────┐
│  Dual-core VRRP (S5700×2) + Firewall (USG6000V)                │
│  Office VLAN 10 (10.1.10.0/24) + Video VLAN 20 (10.1.20.0/24) │
│  QoS: Video DSCP EF (priority) > Office DSCP AF41 (guaranteed) │
│  Servers: DHCP + File + Video surveillance (VLAN 100)           │
└────────────────────────────────────────────────────────────────┘
          │  WAN 172.16.0.0/30 (Serial)
┌─ Chengdu Branch ───────────────────────────────────────────────┐
│  Single core S5700                                              │
│  Office VLAN 10 (10.2.10.0/24) + Video VLAN 20 (10.2.20.0/24) │
│  Same QoS policy as HQ                                          │
└────────────────────────────────────────────────────────────────┘

Run:  python examples/shanghai_chengdu_qos.py
Output → ~/Desktop/shanghai_chengdu_qos/
"""

import sys, os

# ── Path setup ───────────────────────────────────────────────
_ENS_PKG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__).replace("\\", "/")))
_TOOLS_DIR = os.path.dirname(_ENS_PKG_DIR)
sys.path.insert(0, _TOOLS_DIR)
from ensp.topo_builder import TopoBuilder
from ensp.device_config import VRPConfig

OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "shanghai_chengdu_qos")

# ═══════════════════════════════════════════════════════════════
# 1. BUILD TOPOLOGY
# ═══════════════════════════════════════════════════════════════

tb = TopoBuilder("shanghai_chengdu_qos", output_dir=OUTPUT_DIR)

# ── Shanghai HQ ──────────────────────────────────────────────
isp_sh = tb.add_device("ISP-Shanghai", "Router", x=100, y=50)
ar_sh  = tb.add_device("AR-Shanghai",  "AR2240",  x=100, y=170)
fw_sh  = tb.add_device("FW-Shanghai",  "USG6000V", x=100, y=300)

core1_sh = tb.add_device("CoreSW1-SH", "S5700", x=-150, y=450)
core2_sh = tb.add_device("CoreSW2-SH", "S5700", x=300,  y=450)

acc_office_sh = tb.add_device("AccSW-Office-SH", "S3700", x=-150, y=650)
acc_video_sh  = tb.add_device("AccSW-Video-SH",  "S3700", x=300,  y=650)

# Shanghai terminals — Office (VLAN 10)
for i in range(1, 4):
    tb.add_device(f"PC-Office{i}-SH", "PC", x=-250 + i * 80, y=800,
                  dhcp=True, gateway="10.1.10.254")
# Shanghai terminals — Video (VLAN 20)
for i in range(1, 4):
    tb.add_device(f"PC-Video{i}-SH", "PC", x=200 + i * 80, y=800,
                  dhcp=True, gateway="10.1.20.254")

# Shanghai servers
srv_dhcp_sh  = tb.add_device("Server-DHCP-SH", "Server", x=-300, y=300,
                              ip="10.1.100.10", mask="255.255.255.0", gateway="10.1.100.254")
srv_file_sh  = tb.add_device("Server-File-SH", "Server", x=-200, y=300,
                              ip="10.1.100.20", mask="255.255.255.0", gateway="10.1.100.254")
srv_video_sh = tb.add_device("Server-Video-SH", "Server", x=-100, y=300,
                              ip="10.1.100.30", mask="255.255.255.0", gateway="10.1.100.254")

# ── Chengdu Branch ───────────────────────────────────────────
isp_cd = tb.add_device("ISP-Chengdu", "Router", x=750, y=50)
ar_cd  = tb.add_device("AR-Chengdu",  "AR2240", x=750, y=170)

core_cd = tb.add_device("CoreSW-CD", "S5700", x=750, y=400)

acc_office_cd = tb.add_device("AccSW-Office-CD", "S3700", x=600, y=600)
acc_video_cd  = tb.add_device("AccSW-Video-CD", "S3700", x=900, y=600)

# Chengdu terminals — Office (VLAN 10)
for i in range(1, 4):
    tb.add_device(f"PC-Office{i}-CD", "PC", x=500 + i * 80, y=750,
                  dhcp=True, gateway="10.2.10.254")
# Chengdu terminals — Video (VLAN 20)
for i in range(1, 4):
    tb.add_device(f"PC-Video{i}-CD", "PC", x=750 + i * 80, y=750,
                  dhcp=True, gateway="10.2.20.254")

# ── Links: Shanghai ──────────────────────────────────────────
tb.add_link(isp_sh, ar_sh, "GE", "GE")
tb.add_link(ar_sh, fw_sh, "GE", "GE")
tb.add_link(fw_sh, core1_sh, "GE", "GE")
tb.add_link(fw_sh, core2_sh, "GE", "GE")
tb.add_link(core1_sh, core2_sh, "GE", "GE")            # VRRP heartbeat

tb.add_link(core1_sh, srv_dhcp_sh, "GE", "Ethernet")
tb.add_link(core1_sh, srv_file_sh, "GE", "Ethernet")
tb.add_link(core1_sh, srv_video_sh, "GE", "Ethernet")

tb.add_link(acc_office_sh, core1_sh, "GE", "GE")
tb.add_link(acc_office_sh, core2_sh, "GE", "GE")
tb.add_link(acc_video_sh, core1_sh, "GE", "GE")
tb.add_link(acc_video_sh, core2_sh, "GE", "GE")

# Shanghai PCs to access switches
for dev in tb.devices:
    if dev.name.startswith("PC-Office") and dev.name.endswith("-SH"):
        tb.add_link(acc_office_sh, dev)
    elif dev.name.startswith("PC-Video") and dev.name.endswith("-SH"):
        tb.add_link(acc_video_sh, dev)

# ── Links: Chengdu ───────────────────────────────────────────
tb.add_link(isp_cd, ar_cd, "GE", "GE")
tb.add_link(ar_cd, core_cd, "GE", "GE")

tb.add_link(acc_office_cd, core_cd, "GE", "GE")
tb.add_link(acc_video_cd, core_cd, "GE", "GE")

for dev in tb.devices:
    if dev.name.startswith("PC-Office") and dev.name.endswith("-CD"):
        tb.add_link(acc_office_cd, dev)
    elif dev.name.startswith("PC-Video") and dev.name.endswith("-CD"):
        tb.add_link(acc_video_cd, dev)

# ── WAN link: Shanghai ↔ Chengdu ────────────────────────────
tb.add_link(ar_sh, ar_cd, "GE", "GE")

tb.save()

# ═══════════════════════════════════════════════════════════════
# 2. DEVICE CONFIGURATIONS
# ═══════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("  SHANGHAI HQ + CHENGDU BRANCH — QOS NETWORK CONFIGS")
print("=" * 70)


# ────────────────────────────────────────────────────────────
# SHANGHAI: CoreSW1 (VRRP Master: Office VLAN 10, Backup: Video VLAN 20)
# ────────────────────────────────────────────────────────────
def configure_shanghai_core1():
    cfg = VRPConfig("CoreSW1-SH")
    for vid, name in [(10, "Office"), (20, "Video"), (100, "Management")]:
        cfg.add_vlan(vid, name)

    cfg.set_stp(mode="mstp", region_name="ShanghaiHQ",
        instance_configs=[{"id": 1, "vlans": "10"}, {"id": 2, "vlans": "20"}])

    cfg.enable_dhcp_global()
    cfg.add_dhcp_pool("office_pool", "10.1.10.0", "255.255.255.0",
        gateway="10.1.10.254", dns_list=["8.8.8.8", "114.114.114.114"],
        excluded_ips=["10.1.10.254"])
    cfg.add_dhcp_pool("video_pool", "10.1.20.0", "255.255.255.0",
        gateway="10.1.20.254", dns_list=["8.8.8.8"],
        excluded_ips=["10.1.20.254"])

    # Uplink to firewall
    cfg.set_interface("GigabitEthernet0/0/1",
        ip="10.0.0.2 255.255.255.252", undo_shutdown=True)
    # Interconnect to CoreSW2
    cfg.set_interface("GigabitEthernet0/0/3",
        ip="10.0.100.1 255.255.255.252", undo_shutdown=True)

    # Downlinks to access (trunk)
    for port, desc in [(4, "AccSW-Office"), (5, "AccSW-Video")]:
        cfg.set_interface(f"GigabitEthernet0/0/{port}",
            description=desc, link_type="trunk", trunk_allow="10 20 100",
            undo_shutdown=True)

    # Management + servers
    cfg.set_interface("GigabitEthernet0/0/2",
        ip="10.1.100.252 255.255.255.0", undo_shutdown=True)
    for port, desc in [(7, "Server-DHCP"), (8, "Server-File"), (9, "Server-Video")]:
        cfg.set_interface(f"GigabitEthernet0/0/{port}",
            description=desc, link_type="access", access_vlan=100, undo_shutdown=True)

    # VLAN interfaces with VRRP
    cfg.set_interface("Vlanif10", ip="10.1.10.252 255.255.255.0",
                      undo_shutdown=True, dhcp_select_global=True)
    cfg.add_vrrp("Vlanif10", vrid=10, virtual_ip="10.1.10.254", priority=120)
    cfg.set_interface("Vlanif20", ip="10.1.20.252 255.255.255.0",
                      undo_shutdown=True, dhcp_select_global=True)
    cfg.add_vrrp("Vlanif20", vrid=20, virtual_ip="10.1.20.254", priority=100)
    cfg.set_interface("Vlanif100", ip="10.1.100.254 255.255.255.0",
                      undo_shutdown=True)

    cfg.set_ospf(process_id=1, router_id="1.1.1.1",
        networks=[("10.1.10.0", "0.0.0.255"), ("10.1.20.0", "0.0.0.255"),
                  ("10.1.100.0", "0.0.0.255"), ("10.0.0.0", "0.0.0.3"),
                  ("10.0.100.0", "0.0.0.3")])
    return cfg


# ────────────────────────────────────────────────────────────
# SHANGHAI: CoreSW2 (VRRP Master: Video VLAN 20, Backup: Office VLAN 10)
# ────────────────────────────────────────────────────────────
def configure_shanghai_core2():
    cfg = VRPConfig("CoreSW2-SH")
    for vid, name in [(10, "Office"), (20, "Video"), (100, "Management")]:
        cfg.add_vlan(vid, name)

    cfg.set_stp(mode="mstp", region_name="ShanghaiHQ",
        instance_configs=[{"id": 1, "vlans": "10"}, {"id": 2, "vlans": "20"}])

    cfg.enable_dhcp_global()
    cfg.add_dhcp_pool("office_pool", "10.1.10.0", "255.255.255.0",
        gateway="10.1.10.254", dns_list=["8.8.8.8", "114.114.114.114"],
        excluded_ips=["10.1.10.254"])
    cfg.add_dhcp_pool("video_pool", "10.1.20.0", "255.255.255.0",
        gateway="10.1.20.254", dns_list=["8.8.8.8"],
        excluded_ips=["10.1.20.254"])

    cfg.set_interface("GigabitEthernet0/0/1",
        ip="10.0.0.6 255.255.255.252", undo_shutdown=True)
    cfg.set_interface("GigabitEthernet0/0/3",
        ip="10.0.100.2 255.255.255.252", undo_shutdown=True)

    for port, desc in [(4, "AccSW-Office"), (5, "AccSW-Video")]:
        cfg.set_interface(f"GigabitEthernet0/0/{port}",
            description=desc, link_type="trunk", trunk_allow="10 20 100",
            undo_shutdown=True)

    cfg.set_interface("GigabitEthernet0/0/2",
        ip="10.1.100.253 255.255.255.0", undo_shutdown=True)

    cfg.set_interface("Vlanif10", ip="10.1.10.253 255.255.255.0",
                      undo_shutdown=True, dhcp_select_global=True)
    cfg.add_vrrp("Vlanif10", vrid=10, virtual_ip="10.1.10.254", priority=100)
    cfg.set_interface("Vlanif20", ip="10.1.20.253 255.255.255.0",
                      undo_shutdown=True, dhcp_select_global=True)
    cfg.add_vrrp("Vlanif20", vrid=20, virtual_ip="10.1.20.254", priority=120)
    cfg.set_interface("Vlanif100", ip="10.1.100.251 255.255.255.0",
                      undo_shutdown=True)

    cfg.set_ospf(process_id=1, router_id="1.1.1.2",
        networks=[("10.1.10.0", "0.0.0.255"), ("10.1.20.0", "0.0.0.255"),
                  ("10.1.100.0", "0.0.0.255"), ("10.0.0.4", "0.0.0.3"),
                  ("10.0.100.0", "0.0.0.3")])
    return cfg


# ────────────────────────────────────────────────────────────
# SHANGHAI: Firewall with QoS — Video(EF) prioritized over Office(AF)
# ────────────────────────────────────────────────────────────
def configure_shanghai_firewall():
    cfg = VRPConfig("FW-Shanghai")

    cfg.set_interface("GigabitEthernet1/0/0",
        ip="100.100.100.1 255.255.255.0", undo_shutdown=True,
        description="To-AR-Shanghai")
    cfg.set_interface("GigabitEthernet1/0/1",
        ip="10.0.0.1 255.255.255.252", undo_shutdown=True,
        description="To-CoreSW1-SH")
    cfg.set_interface("GigabitEthernet1/0/2",
        ip="10.0.0.5 255.255.255.252", undo_shutdown=True,
        description="To-CoreSW2-SH")

    # Security zones
    cfg.add_line("firewall zone trust")
    cfg.add_line(" set priority 85")
    cfg.add_line(" add interface GigabitEthernet1/0/1")
    cfg.add_line(" add interface GigabitEthernet1/0/2")
    cfg.add_line("#")
    cfg.add_line("firewall zone untrust")
    cfg.add_line(" set priority 5")
    cfg.add_line(" add interface GigabitEthernet1/0/0")
    cfg.add_line("#")

    cfg.add_line("security-policy")
    cfg.add_line(" rule name trust_to_untrust")
    cfg.add_line("  source-zone trust")
    cfg.add_line("  destination-zone untrust")
    cfg.add_line("  action permit")
    cfg.add_line("#")

    # ── QoS Configuration ──────────────────────────────────
    # ACL 3000: Video traffic (10.1.20.0/24)
    cfg.add_acl_named("video_acl", 3000, [
        "rule 5 permit ip source 10.1.20.0 0.0.0.255",
    ])
    # ACL 3001: Office traffic (10.1.10.0/24)
    cfg.add_acl_named("office_acl", 3001, [
        "rule 5 permit ip source 10.1.10.0 0.0.0.255",
    ])

    # Video: EF (Expedited Forwarding) — priority queue, low latency
    cfg.add_line("traffic classifier video_traffic operator or")
    cfg.add_line(" if-match acl 3000")
    cfg.add_line("#")
    cfg.add_line("traffic behavior video_ef")
    cfg.add_line(" remark dscp ef")
    cfg.add_line(" queue ef wfq")
    cfg.add_line(" car cir 10240 cbs 1280000 pbs 2560000 green pass yellow pass red discard")
    cfg.add_line("#")

    # Office: AF41 (Assured Forwarding) — guaranteed bandwidth
    cfg.add_line("traffic classifier office_traffic operator or")
    cfg.add_line(" if-match acl 3001")
    cfg.add_line("#")
    cfg.add_line("traffic behavior office_af")
    cfg.add_line(" remark dscp af41")
    cfg.add_line(" queue af wfq")
    cfg.add_line(" car cir 5120 cbs 640000 pbs 1280000 green pass yellow pass red discard")
    cfg.add_line("#")

    # Apply QoS policy on internal interfaces
    cfg.add_line("traffic policy ENTERPRISE_QOS")
    cfg.add_line(" classifier video_traffic behavior video_ef")
    cfg.add_line(" classifier office_traffic behavior office_af")
    cfg.add_line("#")

    cfg.set_interface("GigabitEthernet1/0/1", traffic_policy_in="ENTERPRISE_QOS")
    cfg.set_interface("GigabitEthernet1/0/2", traffic_policy_in="ENTERPRISE_QOS")

    # NAT
    cfg.add_acl_named("nat_acl", 2000, [
        "rule 5 permit ip source 10.1.0.0 0.0.255.255",
    ])
    cfg.set_interface("GigabitEthernet1/0/0", nat_outbound="2000")

    # OSPF
    cfg.set_ospf(process_id=1, router_id="0.0.0.3",
        networks=[("10.0.0.0", "0.0.0.3"), ("10.0.0.4", "0.0.0.3"),
                  ("100.100.100.0", "0.0.0.255")])
    return cfg


# ────────────────────────────────────────────────────────────
# SHANGHAI: Border Router
# ────────────────────────────────────────────────────────────
def configure_shanghai_router():
    cfg = VRPConfig("AR-Shanghai")
    cfg.set_interface("GigabitEthernet0/0/0",
        ip="202.1.1.2 255.255.255.0", undo_shutdown=True, description="To-ISP")
    cfg.set_interface("GigabitEthernet0/0/1",
        ip="100.100.100.2 255.255.255.0", undo_shutdown=True, description="To-FW")
    # WAN link to Chengdu
    cfg.set_interface("GigabitEthernet0/0/2",
        ip="172.16.0.1 255.255.255.252", undo_shutdown=True, description="WAN-To-Chengdu")

    cfg.set_default_route("202.1.1.1")
    # Route Chengdu subnets via WAN
    cfg.add_static_route("10.2.0.0", "255.255.0.0", "172.16.0.2")

    # ── QoS on WAN interface ────────────────────────────────
    # Limit total WAN bandwidth, prioritize video
    cfg.add_acl_named("wan_video", 3010, [
        "rule 5 permit ip source 10.1.20.0 0.0.0.255 destination 10.2.0.0 0.0.255.255",
    ])
    cfg.add_acl_named("wan_office", 3011, [
        "rule 5 permit ip source 10.1.10.0 0.0.0.255 destination 10.2.0.0 0.0.255.255",
    ])
    cfg.add_line("traffic classifier wan_video operator or")
    cfg.add_line(" if-match acl 3010")
    cfg.add_line("#")
    cfg.add_line("traffic behavior wan_video_ef")
    cfg.add_line(" remark dscp ef")
    cfg.add_line(" car cir 4096 cbs 512000 pbs 1024000 green pass yellow pass red discard")
    cfg.add_line("#")
    cfg.add_line("traffic classifier wan_office operator or")
    cfg.add_line(" if-match acl 3011")
    cfg.add_line("#")
    cfg.add_line("traffic behavior wan_office_af")
    cfg.add_line(" remark dscp af41")
    cfg.add_line(" car cir 2048 cbs 256000 pbs 512000 green pass yellow pass red discard")
    cfg.add_line("#")
    cfg.add_line("traffic policy WAN_QOS")
    cfg.add_line(" classifier wan_video behavior wan_video_ef")
    cfg.add_line(" classifier wan_office behavior wan_office_af")
    cfg.add_line("#")
    cfg.set_interface("GigabitEthernet0/0/2", traffic_policy_out="WAN_QOS")

    cfg.set_ospf(process_id=1, router_id="0.0.0.4",
        networks=[("100.100.100.0", "0.0.0.255"), ("172.16.0.0", "0.0.0.3")],
        default_advertise=True)
    return cfg


# ────────────────────────────────────────────────────────────
# SHANGHAI: Access Switches
# ────────────────────────────────────────────────────────────
def configure_access_switch(name, vlan_id, vlan_name):
    cfg = VRPConfig(name)
    cfg.add_vlan(vlan_id, vlan_name)
    cfg.add_vlan(100, "Management")
    cfg.add_eth_trunk(1, ["Ethernet0/0/21", "Ethernet0/0/22"],
        link_type="trunk", trunk_allow=f"{vlan_id} 100")
    for port in range(1, 11):
        cfg.set_interface(f"Ethernet0/0/{port}",
            link_type="access", access_vlan=vlan_id, undo_shutdown=True)
    cfg.set_stp(mode="mstp", region_name="ShanghaiHQ",
        instance_configs=[{"id": 1 if vlan_id == 10 else 2, "vlans": str(vlan_id)}])
    return cfg


# ────────────────────────────────────────────────────────────
# CHENGDU: Core Switch
# ────────────────────────────────────────────────────────────
def configure_chengdu_core():
    cfg = VRPConfig("CoreSW-CD")
    for vid, name in [(10, "Office"), (20, "Video"), (100, "Management")]:
        cfg.add_vlan(vid, name)

    cfg.enable_dhcp_global()
    cfg.add_dhcp_pool("office_pool", "10.2.10.0", "255.255.255.0",
        gateway="10.2.10.254", dns_list=["8.8.8.8"],
        excluded_ips=["10.2.10.254"])
    cfg.add_dhcp_pool("video_pool", "10.2.20.0", "255.255.255.0",
        gateway="10.2.20.254", dns_list=["8.8.8.8"],
        excluded_ips=["10.2.20.254"])

    # Uplink to AR-Chengdu
    cfg.set_interface("GigabitEthernet0/0/1",
        ip="10.0.200.2 255.255.255.252", undo_shutdown=True)

    # Downlinks to access (trunk)
    cfg.set_interface("GigabitEthernet0/0/4",
        description="AccSW-Office", link_type="trunk", trunk_allow="10 20 100",
        undo_shutdown=True)
    cfg.set_interface("GigabitEthernet0/0/5",
        description="AccSW-Video", link_type="trunk", trunk_allow="10 20 100",
        undo_shutdown=True)

    # VLAN interfaces
    cfg.set_interface("Vlanif10", ip="10.2.10.254 255.255.255.0",
                      undo_shutdown=True, dhcp_select_global=True)
    cfg.set_interface("Vlanif20", ip="10.2.20.254 255.255.255.0",
                      undo_shutdown=True, dhcp_select_global=True)
    cfg.set_interface("Vlanif100", ip="10.2.100.254 255.255.255.0",
                      undo_shutdown=True)

    cfg.set_ospf(process_id=1, router_id="2.2.2.1",
        networks=[("10.2.10.0", "0.0.0.255"), ("10.2.20.0", "0.0.0.255"),
                  ("10.2.100.0", "0.0.0.255"), ("10.0.200.0", "0.0.0.3")])
    return cfg


# ────────────────────────────────────────────────────────────
# CHENGDU: Router
# ────────────────────────────────────────────────────────────
def configure_chengdu_router():
    cfg = VRPConfig("AR-Chengdu")
    cfg.set_interface("GigabitEthernet0/0/0",
        ip="203.1.1.2 255.255.255.0", undo_shutdown=True, description="To-ISP-CD")
    cfg.set_interface("GigabitEthernet0/0/1",
        ip="10.0.200.1 255.255.255.252", undo_shutdown=True, description="To-CoreSW-CD")
    # WAN link to Shanghai
    cfg.set_interface("GigabitEthernet0/0/2",
        ip="172.16.0.2 255.255.255.252", undo_shutdown=True, description="WAN-To-Shanghai")

    cfg.set_default_route("203.1.1.1")
    # Route Shanghai subnets via WAN
    cfg.add_static_route("10.1.0.0", "255.255.0.0", "172.16.0.1")

    # ── QoS on WAN (mirror Shanghai's policy) ──────────────
    cfg.add_acl_named("wan_video_cd", 3010, [
        "rule 5 permit ip source 10.2.20.0 0.0.0.255 destination 10.1.0.0 0.0.255.255",
    ])
    cfg.add_acl_named("wan_office_cd", 3011, [
        "rule 5 permit ip source 10.2.10.0 0.0.0.255 destination 10.1.0.0 0.0.255.255",
    ])
    cfg.add_line("traffic classifier wan_video_cd operator or")
    cfg.add_line(" if-match acl 3010")
    cfg.add_line("#")
    cfg.add_line("traffic behavior wan_video_ef")
    cfg.add_line(" car cir 4096 cbs 512000 pbs 1024000 green pass yellow pass red discard")
    cfg.add_line("#")
    cfg.add_line("traffic classifier wan_office_cd operator or")
    cfg.add_line(" if-match acl 3011")
    cfg.add_line("#")
    cfg.add_line("traffic behavior wan_office_af")
    cfg.add_line(" car cir 2048 cbs 256000 pbs 512000 green pass yellow pass red discard")
    cfg.add_line("#")
    cfg.add_line("traffic policy WAN_QOS_CD")
    cfg.add_line(" classifier wan_video_cd behavior wan_video_ef")
    cfg.add_line(" classifier wan_office_cd behavior wan_office_af")
    cfg.add_line("#")
    cfg.set_interface("GigabitEthernet0/0/2", traffic_policy_out="WAN_QOS_CD")

    cfg.set_ospf(process_id=1, router_id="2.2.2.2",
        networks=[("10.0.200.0", "0.0.0.3"), ("172.16.0.0", "0.0.0.3")])
    return cfg


# ────────────────────────────────────────────────────────────
# ISP Routers
# ────────────────────────────────────────────────────────────
def configure_isp(name, wan_ip, peer_ip, internal_nets):
    cfg = VRPConfig(name)
    cfg.set_interface("GigabitEthernet0/0/0", ip=f"{wan_ip} 255.255.255.0",
                      undo_shutdown=True)
    cfg.set_interface("LoopBack0", ip="8.8.8.8 255.255.255.255")
    for net, mask in internal_nets:
        cfg.add_static_route(net, mask, peer_ip)
    return cfg


# ═══════════════════════════════════════════════════════════════
# 3. BUILD ALL CONFIGS
# ═══════════════════════════════════════════════════════════════

cfgs = {
    "CoreSW1-SH": configure_shanghai_core1(),
    "CoreSW2-SH": configure_shanghai_core2(),
    "FW-Shanghai": configure_shanghai_firewall(),
    "AR-Shanghai": configure_shanghai_router(),
    "AccSW-Office-SH": configure_access_switch("AccSW-Office-SH", 10, "Office"),
    "AccSW-Video-SH": configure_access_switch("AccSW-Video-SH", 20, "Video"),
    "CoreSW-CD": configure_chengdu_core(),
    "AR-Chengdu": configure_chengdu_router(),
    "AccSW-Office-CD": configure_access_switch("AccSW-Office-CD", 10, "Office"),
    "AccSW-Video-CD": configure_access_switch("AccSW-Video-CD", 20, "Video"),
    "ISP-Shanghai": configure_isp("ISP-Shanghai", "202.1.1.1", "202.1.1.2",
                                  [("10.1.0.0", "255.255.0.0"), ("10.2.0.0", "255.255.0.0")]),
    "ISP-Chengdu": configure_isp("ISP-Chengdu", "203.1.1.1", "203.1.1.2",
                                 [("10.2.0.0", "255.255.0.0")]),
}

for name, cfg in cfgs.items():
    print(f"\n--- {name} ---")
    print(cfg.build())

# ═══════════════════════════════════════════════════════════════
# 4. WRITE CONFIGS TO DEVICE DIRECTORIES
# ═══════════════════════════════════════════════════════════════

import zipfile

for dev in tb.devices:
    cfg_obj = cfgs.get(dev.name)
    if cfg_obj is None:
        continue
    dev_dir = os.path.join(OUTPUT_DIR, dev.id)
    os.makedirs(dev_dir, exist_ok=True)
    cfg_path = os.path.join(dev_dir, "vrpcfg.zip")
    with zipfile.ZipFile(cfg_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("vrpcfg.cfg", cfg_obj.build())
    print(f"Saved: {dev.name} → {dev_dir}/vrpcfg.zip")

print("\n" + "=" * 70)
print("  GENERATION COMPLETE")
print(f"  Output: {OUTPUT_DIR}")
print("=" * 70)
print(f"""
Network Summary:
  Shanghai HQ -- 10.1.0.0/16
    Office VLAN 10:  10.1.10.0/24  (VRRP .254, DSCP AF41)
    Video  VLAN 20:  10.1.20.0/24  (VRRP .254, DSCP EF)
    Mgmt   VLAN 100: 10.1.100.0/24

  Chengdu Branch -- 10.2.0.0/16
    Office VLAN 10:  10.2.10.0/24  (DSCP AF41)
    Video  VLAN 20:  10.2.20.0/24  (DSCP EF)

  WAN: 172.16.0.0/30 (Shanghai <-> Chengdu)

  QoS Hierarchy:
    Video  -> DSCP EF  -> 10 Mbps  -> Priority Queue
    Office -> DSCP AF41 -> 5 Mbps   -> Guaranteed BW
    Other  -> DSCP BE  -> Best Effort
""")
