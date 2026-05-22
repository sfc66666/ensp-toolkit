"""eNSP Topology builder - generates .topo XML files and project directories."""

import os
import uuid
import random
import zipfile
import xml.etree.ElementTree as ET
from xml.dom import minidom
from .models import DEVICE_MODELS, _new_id, _mac, _fw_mac, _pc_mac


class Device:
    """Represents a single device in the topology."""

    def __init__(self, name, model, x=None, y=None, config=None, ip=None, mask=None, gateway=None):
        self.name = name
        self.model = model
        self.id = _new_id()
        self.x = x if x is not None else random.randint(100, 1400)
        self.y = y if y is not None else random.randint(100, 900)
        self.config = config or {}
        self.ip = ip
        self.mask = mask
        self.gateway = gateway

        model_def = DEVICE_MODELS.get(model)
        if not model_def:
            raise ValueError(f"Unknown device model: {model}")

        self.model_def = model_def
        self._used_ports = {}  # if_type -> next_index
        self._com_port = None

    def _get_mac(self):
        gen = self.model_def.get("gen_mac")
        if gen:
            return gen()
        return _mac()

    def allocate_port(self, if_type="Ethernet"):
        """Allocate next available port index for a given interface type."""
        idx = self._used_ports.get(if_type, 0)
        self._used_ports[if_type] = idx + 1
        return idx

    def get_vrp_interface(self, if_type="Ethernet", port_index=None):
        """Get the VRP interface name for a port."""
        if port_index is None:
            port_index = self._used_ports.get(if_type, 0) - 1
        fn = self.model_def.get("vrp_if_map", {}).get(if_type)
        if fn:
            return fn(port_index)
        return f"{if_type}0/0/{port_index}"

    def to_xml(self):
        """Generate XML element for this device."""
        mac = self._get_mac()
        com_port = self._com_port or "0"

        model = self.model
        if model == "USG6000V":
            dev = ET.Element("dev", {
                "id": self.id, "name": self.name,
                "poe": "0", "model": model,
                "settings": "",
                "system_mac": mac,
                "com_port": com_port,
                "bootmode": "0",
                "cx": f"{self.x:.6f}",
                "cy": f"{self.y:.6f}",
                "edit_left": str(int(self.x) + 27),
                "edit_top": str(int(self.y) + 54),
            })
        else:
            settings = self._build_settings()
            dev = ET.Element("dev", {
                "id": self.id, "name": self.name,
                "poe": "0", "model": model,
                "settings": settings,
                "system_mac": mac,
                "com_port": com_port,
                "bootmode": "0",
                "cx": f"{self.x:.6f}",
                "cy": f"{self.y:.6f}",
                "edit_left": str(int(self.x) + 27),
                "edit_top": str(int(self.y) + 54),
            })

        for slot_def in self.model_def["slots"]:
            slot = ET.SubElement(dev, "slot")
            if "number" in slot_def:
                slot.set("number", slot_def["number"])
                slot.set("isMainBoard", slot_def["isMainBoard"])
            elif "id" in slot_def:
                slot.set("id", slot_def["id"])
            for iface in slot_def["interfaces"]:
                ET.SubElement(slot, "interface", iface)

        return dev

    def _build_settings(self):
        """Build settings string for PC/Server/Client devices."""
        model = self.model
        if model == "PC":
            ip = self.ip or "192.168.1.1"
            mask = self.mask or "255.255.255.0"
            gw = self.gateway or "192.168.1.254"
            dns = self.config.get("dns", "0.0.0.0")
            mc = _pc_mac()
            return (f" -simpc_ip {ip}  -simpc_mask {mask}  -simpc_gateway {gw}"
                    f"  -simpc_mac {mc}  -simpc_mc_dstip 0.0.0.0"
                    f"  -simpc_mc_dstmac 00-00-00-00-00-00"
                    f"  -simpc_dns1 {dns}  -simpc_dns2 0.0.0.0"
                    f"  -simpc_ipv6 ::  -simpc_prefix 128  -simpc_gatewayv6 ::"
                    f"  -simpc_dhcp_state 0  -simpc_dhcpv6_state 0  -simpc_dns_auto_state 0"
                    f"  -simpc_igmp_version 1  -simpc_group_ip_start 0.0.0.0"
                    f"  -simpc_src_ip_start 0.0.0.0  -simpc_group_num 0  -simpc_group_step 0"
                    f"  -simpc_src_num 0  -simpc_src_step 0  -simpc_type MODE_IS_INCLUDE ")
        elif model == "Server":
            ip = self.ip or "192.168.1.10"
            mask = self.mask or "255.255.255.0"
            gw = self.gateway or "192.168.1.254"
            eth_mac = _pc_mac()
            return (f"-domain 0 -eth {eth_mac} -ipaddr {ip} -ipmask {mask}"
                    f" -gateway {gw} -ipv6addr 2000::2 -ipv6gateway 2000::1"
                    f" -prefixlen 64 -ipv4dns 0.0.0.0 -ipv6dns 3000::1 -dnslist NULL")
        elif model == "Client":
            ip = self.ip or "192.168.1.100"
            mask = self.mask or "255.255.255.0"
            gw = self.gateway or "192.168.1.254"
            eth_mac = _pc_mac()
            return (f"-domain 0 -eth {eth_mac} -ipaddr {ip} -ipmask {mask}"
                    f" -gateway {gw} -ipv6addr 2000::2 -ipv6gateway 2000::1"
                    f" -prefixlen 64 -ipv4dns 0.0.0.0 -ipv6dns 3000::1 -dnslist NULL")
        return ""


class Link:
    """Represents a connection between two devices."""

    def __init__(self, src_device, dst_device,
                 src_if_type="Ethernet", dst_if_type="Ethernet",
                 line_name="Copper"):
        self.src = src_device
        self.dst = dst_device
        self.src_if_type = src_if_type
        self.dst_if_type = dst_if_type
        self.line_name = line_name

        self.src_port = src_device.allocate_port(src_if_type)
        self.dst_port = dst_device.allocate_port(dst_if_type)

    def to_xml(self):
        """Generate XML element for this link."""
        line = ET.Element("line", {
            "srcDeviceID": self.src.id,
            "destDeviceID": self.dst.id,
        })

        # Calculate bounding rects based on device positions
        src_rect_x = self.src.x + 24
        src_rect_y = self.src.y + 24
        dst_rect_x = self.dst.x + 24
        dst_rect_y = self.dst.y + 24

        ET.SubElement(line, "interfacePair", {
            "lineName": self.line_name,
            "srcIndex": str(self.src_port),
            "srcBoundRectIsMoved": "0",
            "srcBoundRect_X": f"{src_rect_x:.6f}",
            "srcBoundRect_Y": f"{src_rect_y:.6f}",
            "srcOffset_X": "0.000000",
            "srcOffset_Y": "0.000000",
            "tarIndex": str(self.dst_port),
            "tarBoundRectIsMoved": "0",
            "tarBoundRect_X": f"{dst_rect_x:.6f}",
            "tarBoundRect_Y": f"{dst_rect_y:.6f}",
            "tarOffset_X": "0.000000",
            "tarOffset_Y": "0.000000",
        })
        return line


class TopoBuilder:
    """
    Build eNSP topology projects.

    Usage:
        tb = TopoBuilder("MyTopo", output_dir="/path/to/output")
        s1 = tb.add_device("LSW1", "S5700", x=300, y=300)
        s2 = tb.add_device("LSW2", "S5700", x=600, y=300)
        tb.add_link(s1, s2)
        tb.save()
    """

    def __init__(self, name, output_dir=None):
        self.name = name
        self.output_dir = output_dir or os.path.join(os.getcwd(), name)
        self.devices = []
        self.links = []
        self._com_port_counter = 2000

    def add_device(self, name, model, x=None, y=None, **kwargs):
        """Add a device to the topology."""
        if model not in DEVICE_MODELS:
            raise ValueError(f"Unknown model '{model}'. Available: {list(DEVICE_MODELS.keys())}")

        dev = Device(name, model, x=x, y=y, **kwargs)

        # Assign com_port for console-based devices
        if model not in ("PC", "Server", "Client", "Cloud"):
            dev._com_port = str(self._com_port_counter)
            self._com_port_counter += 1

        self.devices.append(dev)
        return dev

    def add_link(self, src, dst, src_if="Ethernet", dst_if="Ethernet", line_name="Copper"):
        """Connect two devices with a link."""
        link = Link(src, dst, src_if, dst_if, line_name)
        self.links.append(link)
        return link

    def save(self):
        """Generate and save the .topo file and device config directories."""
        os.makedirs(self.output_dir, exist_ok=True)

        # Build XML
        root = ET.Element("topo", {"version": "1.3.00.200T"})

        devices_el = ET.SubElement(root, "devices")
        for dev in self.devices:
            devices_el.append(dev.to_xml())

        lines_el = ET.SubElement(root, "lines")
        for link in self.links:
            lines_el.append(link.to_xml())

        shapes_el = ET.SubElement(root, "shapes")
        txttips_el = ET.SubElement(root, "txttips")

        # Pretty-print XML (but keep eNSP-compatible formatting)
        rough = ET.tostring(root, encoding="unicode")
        # Add XML declaration manually for eNSP compatibility
        xml_str = '<?xml version="1.0" encoding="UNICODE" ?>\n'
        xml_str += rough

        topo_path = os.path.join(self.output_dir, f"{self.name}.topo")
        # Normalize: replace backslashes with forward slashes for consistency
        topo_path = topo_path.replace('\\', '/')
        with open(topo_path, "w", encoding="utf-8", newline="\r\n") as f:
            f.write(xml_str)

        # Create device config directories
        self._save_device_configs()

        print(f"Topology saved to: {topo_path}")
        print(f"  Devices: {len(self.devices)}")
        print(f"  Links:   {len(self.links)}")
        return topo_path

    def _save_device_configs(self):
        """Save device configuration files."""
        for dev in self.devices:
            if dev.model in ("PC", "Server", "Client", "Cloud"):
                continue  # No config files for endpoints

            dev_dir = os.path.join(self.output_dir, dev.id)
            os.makedirs(dev_dir, exist_ok=True)

            cfg_path = os.path.join(dev_dir, "vrpcfg.zip")
            cfg_content = self._generate_device_config(dev)

            with zipfile.ZipFile(cfg_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("vrpcfg.cfg", cfg_content)

    def _generate_device_config(self, dev):
        """Generate base VRP configuration for a device."""
        hostname = dev.name
        lines = [
            "[V200R003C00]",
            "#",
            f" sysname {hostname}",
            "#",
            " clock timezone China-Standard-Time minus 08:00:00",
            "#",
        ]

        # Add interface configs based on links
        seen_ifaces = set()
        for link in self.links:
            if link.src == dev:
                iface_name = dev.get_vrp_interface(link.src_if_type, link.src_port)
                if iface_name not in seen_ifaces:
                    seen_ifaces.add(iface_name)
                    lines.append(f"interface {iface_name}")
                    # Add IP if device has per-interface IP config
                    if_ip = dev.config.get(f"ip_{iface_name}")
                    if if_ip:
                        lines.append(f" ip address {if_ip}")
                    lines.append("#")
            if link.dst == dev:
                iface_name = dev.get_vrp_interface(link.dst_if_type, link.dst_port)
                if iface_name not in seen_ifaces:
                    seen_ifaces.add(iface_name)
                    lines.append(f"interface {iface_name}")
                    if_ip = dev.config.get(f"ip_{iface_name}")
                    if if_ip:
                        lines.append(f" ip address {if_ip}")
                    lines.append("#")

        # Add user-interface
        lines.extend([
            "user-interface con 0",
            " authentication-mode password",
            "user-interface vty 0 4",
            "user-interface vty 16 20",
            "#",
            "return",
        ])

        return "\n".join(lines)

    def set_device_positions_auto(self):
        """Auto-layout devices in a roughly sensible grid."""
        cols = max(1, int(len(self.devices) ** 0.5 + 0.5))
        spacing_x = 250
        spacing_y = 200
        start_x = 100
        start_y = 100
        for i, dev in enumerate(self.devices):
            col = i % cols
            row = i // cols
            dev.x = start_x + col * spacing_x
            dev.y = start_y + row * spacing_y
