"""eNSP device model definitions."""

import uuid
import random


def _mac():
    """Generate a random MAC address in Huawei eNSP format."""
    return "{:02X}-{:02X}-{:02X}-{:02X}-{:02X}-{:02X}".format(
        0x4C, 0x1F, 0xCC,
        random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)
    )


def _fw_mac():
    """Generate a firewall MAC address."""
    return "00-E0-FC-{:02X}-{:02X}-{:02X}".format(
        random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)
    )


def _pc_mac():
    """Generate a PC MAC address."""
    return "54-89-98-{:02X}-{:02X}-{:02X}".format(
        random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)
    )


def _new_id():
    return str(uuid.uuid4()).upper()


# Device model definitions: each model has slots and interfaces
# For Huawei devices, interface naming follows VRP conventions
DEVICE_MODELS = {
    "S3700": {
        "description": "Huawei S3700 Layer 3 Switch (22 Ethernet + 2 GE)",
        "slots": [
            {
                "number": "slot17", "isMainBoard": "1",
                "interfaces": [
                    {"sztype": "Ethernet", "interfacename": "Ethernet", "count": "22"},
                    {"sztype": "Ethernet", "interfacename": "GE", "count": "2"},
                ]
            }
        ],
        "vrp_if_map": {
            # Maps topo interface indices to VRP interface names
            "Ethernet": lambda i: f"Ethernet0/0/{i}",
            "GE": lambda i: f"GigabitEthernet0/0/{i}",
        },
        "console_type": "vrp",
    },
    "S5700": {
        "description": "Huawei S5700 Layer 3 Switch (24 GE)",
        "slots": [
            {
                "number": "slot17", "isMainBoard": "1",
                "interfaces": [
                    {"sztype": "Ethernet", "interfacename": "GE", "count": "24"},
                ]
            }
        ],
        "vrp_if_map": {
            "GE": lambda i: f"GigabitEthernet0/0/{i}",
        },
        "console_type": "vrp",
    },
    "AR2240": {
        "description": "Huawei AR2240 Router",
        "slots": [
            {
                "number": "slot17", "isMainBoard": "1",
                "interfaces": [
                    {"sztype": "Ethernet", "interfacename": "GE", "count": "1"},
                    {"sztype": "Ethernet", "interfacename": "GE", "count": "2"},
                ]
            }
        ],
        "vrp_if_map": {
            "GE": lambda i: f"GigabitEthernet0/0/{i}",
        },
        "console_type": "vrp",
    },
    "Router": {
        "description": "Generic Router (2 Eth + 4 GE + 4 Serial)",
        "slots": [
            {
                "number": "slot17", "isMainBoard": "1",
                "interfaces": [
                    {"sztype": "Ethernet", "interfacename": "Ethernet", "count": "2"},
                    {"sztype": "Ethernet", "interfacename": "GE", "count": "4"},
                    {"sztype": "Serial", "interfacename": "Serial", "count": "4"},
                ]
            }
        ],
        "vrp_if_map": {
            "Ethernet": lambda i: f"Ethernet0/0/{i}",
            "GE": lambda i: f"GigabitEthernet0/0/{i}",
            "Serial": lambda i: f"Serial0/0/{i}",
        },
        "console_type": "vrp",
    },
    "USG6000V": {
        "description": "Huawei USG6000V Firewall",
        "slots": [
            {
                "id": "1",
                "interfaces": [
                    {"category": "Ethernet", "type": "GE", "slotIndex": "0", "cardIndex": "0", "interfaceIndex": "0"},
                    {"category": "Ethernet", "type": "GE", "slotIndex": "1", "cardIndex": "0", "interfaceIndex": "0"},
                    {"category": "Ethernet", "type": "GE", "slotIndex": "1", "cardIndex": "0", "interfaceIndex": "1"},
                    {"category": "Ethernet", "type": "GE", "slotIndex": "1", "cardIndex": "0", "interfaceIndex": "2"},
                    {"category": "Ethernet", "type": "GE", "slotIndex": "1", "cardIndex": "0", "interfaceIndex": "3"},
                    {"category": "Ethernet", "type": "GE", "slotIndex": "1", "cardIndex": "0", "interfaceIndex": "4"},
                    {"category": "Ethernet", "type": "GE", "slotIndex": "1", "cardIndex": "0", "interfaceIndex": "5"},
                    {"category": "Ethernet", "type": "GE", "slotIndex": "1", "cardIndex": "0", "interfaceIndex": "6"},
                ]
            }
        ],
        "vrp_if_map": {
            "GE": lambda i: f"GigabitEthernet1/0/{i}",
        },
        "console_type": "vrp",
        "gen_mac": _fw_mac,
    },
    "Server": {
        "description": "Server endpoint",
        "slots": [
            {
                "number": "slot17", "isMainBoard": "1",
                "interfaces": [
                    {"sztype": "Ethernet", "interfacename": "Ethernet", "count": "1"},
                ]
            }
        ],
        "console_type": "none",
        "gen_mac": _pc_mac,
    },
    "PC": {
        "description": "PC endpoint",
        "slots": [
            {
                "number": "slot17", "isMainBoard": "1",
                "interfaces": [
                    {"sztype": "Ethernet", "interfacename": "Ethernet", "count": "1"},
                ]
            }
        ],
        "console_type": "none",
        "gen_mac": _pc_mac,
    },
    "Client": {
        "description": "Client endpoint (supports HTTP/etc)",
        "slots": [
            {
                "number": "slot17", "isMainBoard": "1",
                "interfaces": [
                    {"sztype": "Ethernet", "interfacename": "Ethernet", "count": "1"},
                ]
            }
        ],
        "console_type": "none",
        "gen_mac": _pc_mac,
    },
    "Cloud": {
        "description": "Cloud (bridge to host network)",
        "slots": [
            {
                "number": "slot17", "isMainBoard": "1",
                "interfaces": [
                    {"sztype": "Ethernet", "interfacename": "Ethernet", "count": "1"},
                ]
            }
        ],
        "console_type": "none",
    },
}
