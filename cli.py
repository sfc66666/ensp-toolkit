#!/usr/bin/env python3
"""
eNSP Toolkit — Interactive Topology Generator

Ask the user a few questions, then generate a complete eNSP topology +
VRP configurations. No Python knowledge required.

Usage:
    python -m ensp.cli
    python cli.py
"""

import os
import sys
import zipfile

# Path setup
_ENSP_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLS_DIR = os.path.dirname(_ENSP_DIR)
sys.path.insert(0, _TOOLS_DIR)

from ensp.topo_builder import TopoBuilder
from ensp.device_config import VRPConfig

OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "ensp_output")


def ask(prompt, default=None):
    """Ask a question, return user input with default support."""
    if default:
        answer = input(f"{prompt} [{default}]: ").strip()
        return answer if answer else default
    while True:
        answer = input(f"{prompt}: ").strip()
        if answer:
            return answer


def ask_int(prompt, default):
    """Ask for an integer."""
    while True:
        answer = input(f"{prompt} [{default}]: ").strip()
        if not answer:
            return default
        try:
            return int(answer)
        except ValueError:
            print("  Please enter a number.")


def ask_choice(prompt, options):
    """Ask user to pick from a list."""
    print(f"\n{prompt}")
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    while True:
        try:
            choice = int(input("Choose [1]: ").strip() or "1")
            if 1 <= choice <= len(options):
                return options[choice - 1]
        except ValueError:
            pass
        print(f"  Please enter 1-{len(options)}.")


def ask_yesno(prompt, default="y"):
    """Ask a yes/no question."""
    suffix = "[Y/n]" if default == "y" else "[y/N]"
    answer = input(f"{prompt} {suffix}: ").strip().lower()
    if not answer:
        answer = default
    return answer == "y"


def select_devices():
    """Let user pick which device types they need."""
    print("\n" + "=" * 60)
    print("  STEP 1: Network devices")
    print("=" * 60)

    devices = []
    templates = {
        "Core Switch (S5700, 24GE, L3 routing)": {"model": "S5700", "role": "core"},
        "Access Switch (S3700, 22Eth+2GE, L2/L3)": {"model": "S3700", "role": "access"},
        "Router (AR2240, 3GE, WAN/Internet)": {"model": "AR2240", "role": "router"},
        "Firewall (USG6000V, 8GE, security+NAT)": {"model": "USG6000V", "role": "firewall"},
    }

    print("\nWhich devices do you need? (you can pick multiple)")
    for i, (name, info) in enumerate(templates.items(), 1):
        if ask_yesno(f"  Add {name}?", "y"):
            count = ask_int(f"    How many?", 1)
            for j in range(count):
                label = f"{info['role']}{j+1}" if count > 1 else info['role']
                devices.append({"name": f"{info['model']}-{label}", "model": info["model"],
                                "role": info["role"]})
    return devices


def select_business():
    """Let user define business VLANs."""
    print("\n" + "=" * 60)
    print("  STEP 2: Business types (VLANs)")
    print("=" * 60)

    presets = {
        "Office (办公)": {"vlan": 10, "subnet": "10.0.10.0", "dscp": "af41", "bw": "5"},
        "Video (视频)": {"vlan": 20, "subnet": "10.0.20.0", "dscp": "ef", "bw": "10"},
        "Voice (语音)": {"vlan": 30, "subnet": "10.0.30.0", "dscp": "ef", "bw": "2"},
        "Guest (访客)": {"vlan": 40, "subnet": "10.0.40.0", "dscp": "be", "bw": "2"},
        "Management (管理)": {"vlan": 100, "subnet": "10.0.100.0", "dscp": "af41", "bw": "1"},
        "Custom (自定义)": None,
    }

    selected = []
    print("\nSelect business types:")
    for i, (name, preset) in enumerate(presets.items(), 1):
        if ask_yesno(f"  {name}?", "y" if i <= 3 else "n"):
            if preset is None:
                vlan = ask_int("    VLAN ID", len(selected) * 10 + 10)
                name_custom = ask("    Name", f"Business{len(selected)+1}")
                subnet = ask("    Subnet (e.g. 10.0.50.0)", f"10.0.{vlan}.0")
                dscp = ask_choice("    DSCP priority", ["ef (Expedited, video/voice)", "af41 (Assured, office)", "be (Best Effort)"])
                bw = ask_int("    Bandwidth guarantee (Mbps)", 5)
                dscp_code = {"ef (Expedited, video/voice)": "ef", "af41 (Assured, office)": "af41", "be (Best Effort)": "be"}[dscp]
                selected.append({"name": name_custom, "vlan": vlan, "subnet": subnet, "dscp": dscp_code, "bw": bw})
            else:
                selected.append({"name": name, "vlan": preset["vlan"], "subnet": preset["subnet"],
                                 "dscp": preset["dscp"], "bw": preset["bw"]})
    return selected


def select_features(businesses):
    """Let user enable optional features."""
    print("\n" + "=" * 60)
    print("  STEP 3: Network features")
    print("=" * 60)

    features = {}
    features["dhcp"] = ask_yesno("  Enable DHCP server?", "y")
    features["vrrp"] = ask_yesno("  Enable VRRP redundancy (dual core)?", "y")
    features["ospf"] = ask_yesno("  Enable OSPF dynamic routing?", "y")
    features["qos"] = ask_yesno("  Enable QoS traffic classification?", "y")
    features["nat"] = ask_yesno("  Enable NAT (internet access)?", "y")
    features["stp"] = ask_yesno("  Enable STP (loop prevention)?", "y")
    features["eth_trunk"] = ask_yesno("  Enable link aggregation (Eth-Trunk)?", "y")

    if features["vrrp"]:
        print("\n  VRRP priority assignment (higher = master):")
        for biz in businesses:
            biz["vrrp_prio"] = ask_int(f"    {biz['name']} (VLAN {biz['vlan']}) priority", 120 if businesses.index(biz) == 0 else 100)

    return features


def ask_topology_name():
    """Ask for project name."""
    print("\n" + "=" * 60)
    print("  eNSP Topology Generator")
    print("=" * 60)
    name = ask("Project name", "my_network")
    return name


# ═══════════════════════════════════════════════════════════════
# CONFIG GENERATORS
# ═══════════════════════════════════════════════════════════════

def build_core_switch(name, businesses, features):
    """Generate VRP config for core switch."""
    cfg = VRPConfig(name)

    for biz in businesses:
        cfg.add_vlan(biz["vlan"], biz["name"])

    if features.get("stp"):
        instances = []
        for i, biz in enumerate(businesses, 1):
            instances.append({"id": i, "vlans": str(biz["vlan"])})
        cfg.set_stp(mode="mstp", region_name="MainSite",
                    instance_configs=instances)

    if features.get("dhcp"):
        cfg.enable_dhcp_global()
        for biz in businesses:
            pool_name = f"pool_{biz['name'].lower().replace(' ', '_')}"
            gw_ip = biz["subnet"].rsplit(".", 1)[0] + ".254"
            cfg.add_dhcp_pool(pool_name, biz["subnet"], "255.255.255.0",
                              gateway=gw_ip, dns_list=["8.8.8.8"])

    # VLAN interfaces
    for biz in businesses:
        ifname = f"Vlanif{biz['vlan']}"
        ip = biz["subnet"].rsplit(".", 1)[0] + (".252" if features.get("vrrp") else ".254")
        cfg.set_interface(ifname, ip=f"{ip} 255.255.255.0", undo_shutdown=True)
        if features.get("dhcp"):
            cfg.set_interface(ifname, dhcp_select_global=True)
        if features.get("vrrp"):
            virtual_ip = biz["subnet"].rsplit(".", 1)[0] + ".254"
            cfg.add_vrrp(ifname, vrid=biz["vlan"], virtual_ip=virtual_ip,
                         priority=biz.get("vrrp_prio", 100))

    if features.get("ospf"):
        networks = []
        for biz in businesses:
            wc = "0.0.0.255"
            networks.append((biz["subnet"], wc))
        cfg.set_interface("GigabitEthernet0/0/1",
                          ip="10.0.0.2 255.255.255.252", undo_shutdown=True)
        networks.append(("10.0.0.0", "0.0.0.3"))
        cfg.set_ospf(process_id=1, router_id="1.1.1.1", networks=networks)

    return cfg


def build_qos_config(businesses, apply_iface="GigabitEthernet1/0/1"):
    """Generate firewall QoS: traffic classifiers + behaviors + policy."""
    lines = []

    dscp_map = {
        "ef": ("video_traffic", "video_ef", "ef", "Priority Queue"),
        "af41": ("office_traffic", "office_af", "af41", "Guaranteed BW"),
    }

    for i, biz in enumerate(businesses):
        acl_num = 3000 + i
        classifier_name = f"{biz['name'].lower().replace(' ', '_')}_cls"
        behavior_name = f"{biz['name'].lower().replace(' ', '_')}_bhv"
        dscp_val = biz.get("dscp", "be")
        bw = biz.get("bw", 5)
        cir = int(bw) * 1024  # convert Mbps to kbps

        lines.append(f"acl name {classifier_name}_acl {acl_num}")
        lines.append(f" rule 5 permit ip source {biz['subnet']} 0.0.0.255")
        lines.append("#")
        lines.append(f"traffic classifier {classifier_name} operator or")
        lines.append(f" if-match acl {acl_num}")
        lines.append("#")
        lines.append(f"traffic behavior {behavior_name}")
        lines.append(f" remark dscp {dscp_val}")
        if dscp_val == "ef":
            lines.append(" queue ef wfq")
        lines.append(f" car cir {cir} cbs {cir*125} pbs {cir*250} green pass yellow pass red discard")
        lines.append("#")

    lines.append("traffic policy ENTERPRISE_QOS")
    for biz in businesses:
        cls_name = f"{biz['name'].lower().replace(' ', '_')}_cls"
        bhv_name = f"{biz['name'].lower().replace(' ', '_')}_bhv"
        lines.append(f" classifier {cls_name} behavior {bhv_name}")
    lines.append("#")

    return lines


def generate_topology(name, businesses, features):
    """Build the complete topology and configs."""
    print(f"\n  Generating topology '{name}'...")

    tb = TopoBuilder(name, output_dir=os.path.join(OUTPUT_DIR, name))

    # Core layer
    core1 = tb.add_device("CoreSW1", "S5700", x=300, y=200)
    if features.get("vrrp"):
        core2 = tb.add_device("CoreSW2", "S5700", x=600, y=200)

    # Access layer
    acc_switches = []
    for i, biz in enumerate(businesses):
        x = 150 + i * 300
        acc = tb.add_device(f"AccSW-{biz['name']}", "S3700", x=x, y=400)
        acc_switches.append(acc)
        # Link to core(s)
        tb.add_link(acc, core1, "GE", "GE")
        if features.get("vrrp"):
            tb.add_link(acc, core2, "GE", "GE")

    # PCs per business
    pc_count = 2
    for i, biz in enumerate(businesses):
        gw = biz["subnet"].rsplit(".", 1)[0] + ".254"
        for j in range(pc_count):
            x = 50 + i * 300 + j * 100
            pc = tb.add_device(f"PC-{biz['name']}-{j+1}", "PC", x=x, y=550,
                               dhcp=features.get("dhcp", False), gateway=gw)
            tb.add_link(acc_switches[i], pc)

    # Firewall
    if features.get("qos") or features.get("nat"):
        fw = tb.add_device("FW1", "USG6000V", x=450, y=50)
        tb.add_link(fw, core1, "GE", "GE")
        if features.get("vrrp"):
            tb.add_link(fw, core2, "GE", "GE")

    # Router + ISP
    ar = tb.add_device("AR1", "AR2240", x=450, y=-100)
    isp = tb.add_device("ISP", "Router", x=450, y=-250)
    tb.add_link(isp, ar, "GE", "GE")
    tb.add_link(ar, fw, "GE", "GE")

    if features.get("vrrp"):
        tb.add_link(core1, core2, "GE", "GE")

    tb.save()

    # ── Generate configs ────────────────────────────────────
    cfgs = {}

    # Core 1
    cfgs["CoreSW1"] = build_core_switch("CoreSW1", businesses, features)

    # Core 2 (VRRP backup)
    if features.get("vrrp"):
        cfg2 = build_core_switch("CoreSW2", businesses, features)
        # Adjust priorities
        for biz in businesses:
            biz_prio = biz.get("vrrp_prio", 100)
            cfg2._vrrp_groups = []
            ifname = f"Vlanif{biz['vlan']}"
            virtual_ip = biz["subnet"].rsplit(".", 1)[0] + ".254"
            cfg2.add_vrrp(ifname, vrid=biz["vlan"], virtual_ip=virtual_ip,
                          priority=220 - biz_prio)  # inverse priority
        cfgs["CoreSW2"] = cfg2

    # Firewall with QoS
    if features.get("qos"):
        cfg_fw = VRPConfig("FW1")
        cfg_fw.set_interface("GigabitEthernet1/0/0",
                             ip="100.100.100.1 255.255.255.0", undo_shutdown=True)
        cfg_fw.set_interface("GigabitEthernet1/0/1",
                             ip="10.0.0.1 255.255.255.252", undo_shutdown=True)

        cfg_fw.add_line("firewall zone trust")
        cfg_fw.add_line(" set priority 85")
        cfg_fw.add_line(" add interface GigabitEthernet1/0/1")
        cfg_fw.add_line("#")
        cfg_fw.add_line("firewall zone untrust")
        cfg_fw.add_line(" set priority 5")
        cfg_fw.add_line(" add interface GigabitEthernet1/0/0")
        cfg_fw.add_line("#")
        cfg_fw.add_line("security-policy")
        cfg_fw.add_line(" rule name trust_to_untrust")
        cfg_fw.add_line("  source-zone trust")
        cfg_fw.add_line("  destination-zone untrust")
        cfg_fw.add_line("  action permit")
        cfg_fw.add_line("#")

        qos_lines = build_qos_config(businesses)
        for line in qos_lines:
            cfg_fw.add_line(line)
        cfg_fw.set_interface("GigabitEthernet1/0/1", traffic_policy_in="ENTERPRISE_QOS")

        if features.get("nat"):
            cfg_fw.add_acl_named("nat_acl", 2000,
                                 [f"rule 5 permit ip source {businesses[0]['subnet'].rsplit('.', 1)[0]}.0 0.0.255.255"])
            cfg_fw.set_interface("GigabitEthernet1/0/0", nat_outbound="2000")

        if features.get("ospf"):
            cfg_fw.set_ospf(process_id=1, router_id="0.0.0.3",
                            networks=[("10.0.0.0", "0.0.0.3"), ("100.100.100.0", "0.0.0.255")])

        cfgs["FW1"] = cfg_fw

    # Router
    cfg_ar = VRPConfig("AR1")
    cfg_ar.set_interface("GigabitEthernet0/0/0",
                         ip="202.1.1.2 255.255.255.0", undo_shutdown=True)
    cfg_ar.set_interface("GigabitEthernet0/0/1",
                         ip="100.100.100.2 255.255.255.0", undo_shutdown=True)
    cfg_ar.set_default_route("202.1.1.1")
    if features.get("ospf"):
        cfg_ar.set_ospf(process_id=1, router_id="0.0.0.4",
                        networks=[("100.100.100.0", "0.0.0.255")],
                        default_advertise=True)
    cfgs["AR1"] = cfg_ar

    # ISP
    cfg_isp = VRPConfig("ISP")
    cfg_isp.set_interface("GigabitEthernet0/0/0",
                          ip="202.1.1.1 255.255.255.0", undo_shutdown=True)
    cfg_isp.set_interface("LoopBack0", ip="8.8.8.8 255.255.255.255")
    for biz in businesses:
        cfg_isp.add_static_route(biz["subnet"], "255.255.255.0", "202.1.1.2")
    cfgs["ISP"] = cfg_isp

    # Access switches
    for i, biz in enumerate(businesses):
        cfg_acc = VRPConfig(f"AccSW-{biz['name']}")
        cfg_acc.add_vlan(biz["vlan"], biz["name"])
        for port in range(1, 11):
            cfg_acc.set_interface(f"Ethernet0/0/{port}",
                                  link_type="access", access_vlan=biz["vlan"], undo_shutdown=True)
        if features.get("eth_trunk"):
            cfg_acc.add_eth_trunk(1, ["Ethernet0/0/21", "Ethernet0/0/22"],
                                  link_type="trunk", trunk_allow=str(biz["vlan"]))
        cfgs[f"AccSW-{biz['name']}"] = cfg_acc

    return tb, cfgs


def save_configs(tb, cfgs):
    """Write VRP configs to device directories."""
    for dev in tb.devices:
        cfg_obj = cfgs.get(dev.name)
        if cfg_obj is None:
            continue
        dev_dir = os.path.join(OUTPUT_DIR, tb.name, dev.id)
        os.makedirs(dev_dir, exist_ok=True)
        cfg_path = os.path.join(dev_dir, "vrpcfg.zip")
        with zipfile.ZipFile(cfg_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("vrpcfg.cfg", cfg_obj.build())
    print(f"  Configs saved to {OUTPUT_DIR}/{tb.name}/")


def print_summary(name, businesses, features):
    """Print network summary."""
    print("\n" + "=" * 60)
    print(f"  NETWORK: {name}")
    print("=" * 60)
    print(f"\n  Features: ", end="")
    active = [k.upper() for k, v in features.items() if v]
    print(", ".join(active))

    print(f"\n  {'Business':<15} {'VLAN':<6} {'Subnet':<18} {'DSCP':<8} {'BW'}")
    print(f"  {'-'*15} {'-'*6} {'-'*18} {'-'*8} {'-'*4}")
    for biz in businesses:
        print(f"  {biz['name']:<15} {biz['vlan']:<6} {biz['subnet']:<18} {biz['dscp'].upper():<8} {biz['bw']} Mbps")

    print(f"\n  Output: {OUTPUT_DIR}/{name}/")
    print(f"  1. Open '{name}.topo' in eNSP")
    print(f"  2. Start devices → right-click → Import Configuration → vrpcfg.zip")
    print(f"  3. Start simulation!")


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    print("\n" + "=" * 60)
    print("  eNSP INTERACTIVE TOPOLOGY GENERATOR")
    print("  Answer a few questions, get a complete eNSP project")
    print("=" * 60)

    name = ask_topology_name()
    businesses = select_business()
    if not businesses:
        print("  No businesses selected. Exiting.")
        return
    features = select_features(businesses)

    print(f"\n  Building '{name}'...")
    tb, cfgs = generate_topology(name, businesses, features)
    save_configs(tb, cfgs)
    print_summary(name, businesses, features)


if __name__ == "__main__":
    main()
