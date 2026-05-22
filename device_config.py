"""Generate Huawei VRP device configurations for eNSP devices.

Supports common scenarios:
- VLAN configuration (access/trunk/hybrid)
- STP/MSTP
- Link aggregation (Eth-Trunk)
- OSPF routing
- Static routing
- DHCP server
- ACL and traffic policy
- NAT (on firewalls/routers)
- VRRP
"""


class VRPConfig:
    """Builder for Huawei VRP device configuration."""

    def __init__(self, hostname="Device"):
        self.hostname = hostname
        self._lines = []
        self._vlan_ids = set()
        self._ospf_areas = {}
        self._static_routes = []
        self._dhcp_pools = []
        self._acls = []
        self._interfaces = {}  # name -> list of config lines
        self._default_route = None
        self._nat_rules = []
        self._vrrp_groups = []
        self._stp_config = None

    def add_line(self, line):
        self._lines.append(line)

    # ── VLAN ──────────────────────────────────────────
    def add_vlan(self, vlan_id, name=None):
        self._vlan_ids.add(vlan_id)
        if not hasattr(self, "_vlans"):
            self._vlans = {}
        if name:
            self._vlans[vlan_id] = name

    def add_vlan_batch(self, ids):
        for v in ids:
            self._vlan_ids.add(v)

    # ── Interface ─────────────────────────────────────
    def set_interface(self, ifname, **kwargs):
        if ifname not in self._interfaces:
            self._interfaces[ifname] = []
        cfg = self._interfaces[ifname]

        if "ip" in kwargs:
            cfg.append(f" ip address {kwargs['ip']}")
        if "description" in kwargs:
            cfg.append(f" description {kwargs['description']}")
        if "link_type" in kwargs:
            cfg.append(f" port link-type {kwargs['link_type']}")
        if "default_vlan" in kwargs:
            cfg.append(f" port default vlan {kwargs['default_vlan']}")
        if "trunk_allow" in kwargs:
            cfg.append(f" port trunk allow-pass vlan {kwargs['trunk_allow']}")
        if "access_vlan" in kwargs:
            cfg.append(f" port default vlan {kwargs['access_vlan']}")
        if "pvid" in kwargs:
            cfg.append(f" port hybrid pvid vlan {kwargs['pvid']}")
        if "hybrid_tagged" in kwargs:
            cfg.append(f" port hybrid tagged vlan {kwargs['hybrid_tagged']}")
        if "hybrid_untagged" in kwargs:
            cfg.append(f" port hybrid untagged vlan {kwargs['hybrid_untagged']}")
        if "stp_disable" in kwargs and kwargs["stp_disable"]:
            cfg.append(" stp disable")
        if "undo_shutdown" in kwargs and kwargs["undo_shutdown"]:
            cfg.append(" undo shutdown")
        if "trust_dscp" in kwargs and kwargs["trust_dscp"]:
            cfg.append(" trust dscp")
        if "traffic_policy_in" in kwargs:
            cfg.append(f" traffic-policy {kwargs['traffic_policy_in']} inbound")
        if "traffic_policy_out" in kwargs:
            cfg.append(f" traffic-policy {kwargs['traffic_policy_out']} outbound")
        if "nat_outbound" in kwargs:
            cfg.append(f" nat outbound {kwargs['nat_outbound']}")
        if "nat_server" in kwargs:
            for rule in kwargs["nat_server"]:
                cfg.append(f" nat server protocol {rule}")
        if "eth_trunk" in kwargs:
            cfg = [f"interface {ifname}"] + cfg
            cfg.insert(1, f" eth-trunk {kwargs['eth_trunk']}")
            self._interfaces[ifname] = cfg
            return
        if "qos_queue_profile" in kwargs:
            cfg.append(f" qos queue-profile {kwargs['qos_queue_profile']}")

    # ── STP ───────────────────────────────────────────
    def set_stp(self, mode="stp", region_name=None, revision_level=None, instance_configs=None):
        self._stp_config = {
            "mode": mode,
            "region_name": region_name,
            "revision_level": revision_level,
            "instance_configs": instance_configs or [],
        }

    # ── Eth-Trunk ─────────────────────────────────────
    def add_eth_trunk(self, trunk_id, members, mode="manual", **if_kwargs):
        ifname = f"Eth-Trunk{trunk_id}"
        self._interfaces[ifname] = []
        self.set_interface(ifname, **if_kwargs)
        for member_if in members:
            self.set_interface(member_if,
                               eth_trunk=trunk_id,
                               undo_shutdown=True)

    # ── OSPF ──────────────────────────────────────────
    def set_ospf(self, process_id=1, router_id=None, area="0.0.0.0", networks=None, default_advertise=False):
        self._ospf_config = {
            "process_id": process_id,
            "router_id": router_id,
            "area": area,
            "networks": networks or [],
            "default_advertise": default_advertise,
        }

    def add_ospf_network(self, network, wildcard, area="0.0.0.0"):
        if area not in self._ospf_areas:
            self._ospf_areas[area] = []
        self._ospf_areas[area].append((network, wildcard))

    # ── Static routes ─────────────────────────────────
    def add_static_route(self, dest, mask, next_hop, preference=None):
        entry = f"ip route-static {dest} {mask} {next_hop}"
        if preference is not None:
            entry += f" preference {preference}"
        self._static_routes.append(entry)

    def set_default_route(self, next_hop):
        self._default_route = next_hop

    # ── DHCP ──────────────────────────────────────────
    def add_dhcp_pool(self, pool_name, network, mask, gateway, dns_list=None, excluded_ips=None, lease=None):
        self._dhcp_pools.append({
            "name": pool_name,
            "network": network,
            "mask": mask,
            "gateway": gateway,
            "dns_list": dns_list or [],
            "excluded_ips": excluded_ips or [],
            "lease": lease,
        })

    def enable_dhcp_global(self):
        self._dhcp_enabled = True

    # ── ACL ───────────────────────────────────────────
    def add_acl(self, number, rules):
        self._acls.append({"number": number, "rules": rules, "name": None})

    def add_acl_named(self, name, number, rules):
        self._acls.append({"number": number, "rules": rules, "name": name})

    # ── NAT ───────────────────────────────────────────
    def add_nat_outbound(self, acl_number, interface=None):
        self._nat_rules.append({
            "type": "outbound",
            "acl": acl_number,
            "interface": interface,
        })

    def add_nat_server(self, protocol, global_ip, global_port, inside_ip, inside_port):
        self._nat_rules.append({
            "type": "server",
            "protocol": protocol,
            "global_ip": global_ip,
            "global_port": global_port,
            "inside_ip": inside_ip,
            "inside_port": inside_port,
        })

    # ── VRRP ──────────────────────────────────────────
    def add_vrrp(self, ifname, vrid, virtual_ip, priority=100, preempt=True):
        self._vrrp_groups.append({
            "interface": ifname,
            "vrid": vrid,
            "virtual_ip": virtual_ip,
            "priority": priority,
            "preempt": preempt,
        })

    # ── QoS ───────────────────────────────────────────
    def add_traffic_policy(self, name, classifiers_behaviors, direction="inbound", ifname=None):
        if not hasattr(self, "_traffic_policies"):
            self._traffic_policies = []
        self._traffic_policies.append({
            "name": name,
            "classifiers_behaviors": classifiers_behaviors,
            "direction": direction,
            "interface": ifname,
        })

    # ── Build ─────────────────────────────────────────
    def build(self):
        lines = ["[V200R003C00]", "#"]

        # System
        lines.append(f" sysname {self.hostname}")
        lines.append("#")
        lines.append(" clock timezone China-Standard-Time minus 08:00:00")
        lines.append("#")

        # VLANs
        if self._vlan_ids:
            for vid in sorted(self._vlan_ids):
                name = getattr(self, "_vlans", {}).get(vid, "")
                if name:
                    lines.append(f"vlan {vid}")
                    lines.append(f" description {name}")
                    lines.append("#")
                else:
                    lines.append(f"vlan {vid}")
                    lines.append("#")
            if len(self._vlan_ids) > 1:
                lines.append("#")

        # STP
        if self._stp_config:
            cfg = self._stp_config
            lines.append(f"stp mode {cfg['mode']}")
            if cfg.get("region_name"):
                lines.append(f"stp region-configuration")
                lines.append(f" region-name {cfg['region_name']}")
                if cfg.get("revision_level"):
                    lines.append(f" revision-level {cfg['revision_level']}")
                for inst in cfg.get("instance_configs", []):
                    lines.append(f" instance {inst['id']} vlan {inst['vlans']}")
                lines.append(f" active region-configuration")
            lines.append("#")

        # ACLs
        for acl in self._acls:
            if acl["name"]:
                lines.append(f"acl name {acl['name']} {acl['number']}")
            else:
                lines.append(f"acl number {acl['number']}")
            for rule in acl["rules"]:
                lines.append(f" {rule}")
            lines.append("#")

        # Traffic classifiers and behaviors
        if hasattr(self, "_traffic_policies"):
            classifiers = {}
            behaviors = {}
            for tp in self._traffic_policies:
                for cb_name, cb_info in tp["classifiers_behaviors"].items():
                    if "classifier" in cb_info:
                        classifiers[cb_name] = cb_info["classifier"]
                    if "behavior" in cb_info:
                        behaviors[cb_name] = cb_info["behavior"]

            for name, cfg in classifiers.items():
                lines.append(f"traffic classifier {name} operator or")
                for rule in cfg.get("rules", []):
                    lines.append(f" if-match {rule}")
                lines.append("#")

            for name, cfg in behaviors.items():
                lines.append(f"traffic behavior {name}")
                for action in cfg.get("actions", []):
                    lines.append(f" {action}")
                lines.append("#")

            for tp in self._traffic_policies:
                lines.append(f"traffic policy {tp['name']}")
                for cb_name, _ in tp["classifiers_behaviors"].items():
                    lines.append(f" classifier {cb_name} behavior {cb_name}")
                lines.append("#")

        # QoS queue-profile / drop-profile
        if hasattr(self, "_qos"):
            for dp in self._qos.get("drop_profiles", []):
                lines.append(f"drop-profile {dp['name']}")
                lines.append(" wred dscp")
                for entry in dp.get("entries", []):
                    lines.append(f"  dscp {entry}")
                lines.append("#")
            for qp in self._qos.get("queue_profiles", []):
                lines.append(f"qos queue-profile {qp['name']}")
                for line in qp.get("config", []):
                    lines.append(f" {line}")
                lines.append("#")

        # Interfaces
        for ifname, cfg_lines in sorted(self._interfaces.items()):
            lines.append(f"interface {ifname}")
            for cl in cfg_lines:
                lines.append(cl)
            lines.append("#")

        # VRRP
        for vrrp in self._vrrp_groups:
            ifname = vrrp["interface"]
            # Append to interface config
            # We need to find the right position in lines
            pass

        # OSPF
        ospf_cfg = getattr(self, "_ospf_config", None)
        if ospf_cfg:
            pid = ospf_cfg["process_id"]
            rid = ospf_cfg["router_id"]
            lines.append(f"ospf {pid}")
            if rid:
                lines.append(f" router-id {rid}")
            if ospf_cfg.get("default_advertise"):
                lines.append(" default-route-advertise")
            area = ospf_cfg.get("area", "0.0.0.0")
            lines.append(f" area {area}")
            for net, wc in ospf_cfg.get("networks", []):
                lines.append(f"  network {net} {wc}")
            lines.append("#")

        # Additional OSPF areas
        for area, nets in self._ospf_areas.items():
            if not ospf_cfg or area != ospf_cfg.get("area", "0.0.0.0"):
                pid = ospf_cfg["process_id"] if ospf_cfg else 1
                lines.append(f"ospf {pid}")
                lines.append(f" area {area}")
                for net, wc in nets:
                    lines.append(f"  network {net} {wc}")
                lines.append("#")

        # Static routes
        for route in self._static_routes:
            lines.append(route)
        if self._default_route:
            lines.append(f"ip route-static 0.0.0.0 0.0.0.0 {self._default_route}")
        if self._static_routes or self._default_route:
            lines.append("#")

        # DHCP
        dhcp_enabled = getattr(self, "_dhcp_enabled", False)
        if dhcp_enabled:
            lines.append("dhcp enable")
            lines.append("#")
        for pool in self._dhcp_pools:
            lines.append(f"ip pool {pool['name']}")
            lines.append(f" gateway-list {pool['gateway']}")
            lines.append(f" network {pool['network']} mask {pool['mask']}")
            if pool.get("dns_list"):
                lines.append(f" dns-list {' '.join(pool['dns_list'])}")
            if pool.get("excluded_ips"):
                for excl in pool["excluded_ips"]:
                    lines.append(f" excluded-ip-address {excl}")
            if pool.get("lease"):
                lines.append(f" lease {pool['lease']}")
            lines.append("#")

        # NAT
        for nat in self._nat_rules:
            if nat["type"] == "outbound":
                line = f"nat outbound {nat['acl']}"
                lines.append(line)
            elif nat["type"] == "server":
                proto = nat["protocol"]
                gip, gport = nat["global_ip"], nat["global_port"]
                iip, iport = nat["inside_ip"], nat["inside_port"]
                lines.append(f"nat server protocol {proto} global {gip} {gport} inside {iip} {iport}")
        if self._nat_rules:
            lines.append("#")

        # User interface
        lines.extend([
            "user-interface con 0",
            " authentication-mode password",
            "user-interface vty 0 4",
            "user-interface vty 16 20",
            "#",
            "return",
        ])

        return "\n".join(lines)


# ── Pre-built topology recipes ──────────────────────────────────

def recipe_simple_lan():
    """Simple LAN: 1 switch + 2 PCs."""
    return {
        "description": "Simple LAN with 1 switch and 2 PCs",
        "devices": [
            {"name": "SW1", "model": "S3700", "x": 400, "y": 300},
            {"name": "PC1", "model": "PC", "x": 200, "y": 400,
             "ip": "192.168.1.1", "mask": "255.255.255.0", "gateway": "192.168.1.254"},
            {"name": "PC2", "model": "PC", "x": 600, "y": 400,
             "ip": "192.168.1.2", "mask": "255.255.255.0", "gateway": "192.168.1.254"},
        ],
        "links": [
            ("SW1", "PC1"),
            ("SW1", "PC2"),
        ],
        "configs": {
            "SW1": lambda: (
                VRPConfig("SW1")
                ._add_vlan_10()
            ),
        }
    }


def recipe_vlan_routing():
    """VLAN routing with L3 switch: core switch + access switches + PCs."""
    return {
        "description": "VLAN routing - Core L3 switch with access switches",
        "devices": [
            {"name": "CoreSW", "model": "S5700", "x": 500, "y": 200},
            {"name": "AccSW1", "model": "S3700", "x": 250, "y": 450},
            {"name": "AccSW2", "model": "S3700", "x": 750, "y": 450},
            {"name": "PC-VLAN10", "model": "PC", "x": 100, "y": 600,
             "ip": "192.168.10.1", "mask": "255.255.255.0", "gateway": "192.168.10.254"},
            {"name": "PC-VLAN20", "model": "PC", "x": 900, "y": 600,
             "ip": "192.168.20.1", "mask": "255.255.255.0", "gateway": "192.168.20.254"},
        ],
        "links": [
            ("CoreSW", "AccSW1", "GE", "GE"),
            ("CoreSW", "AccSW2", "GE", "GE"),
            ("AccSW1", "PC-VLAN10"),
            ("AccSW2", "PC-VLAN20"),
        ],
    }
