"""
Generates Mermaid.js diagram source from a list of selected OCI service names.
The diagram is built programmatically — not AI-generated.
"""

_SERVICE_NODE_MAP = {
    "vcn":           ('VCN["🌐 VCN"]', "Network"),
    "compute":       ('COMPUTE["💻 Compute Instance"]', "Compute"),
    "adb":           ('ADB["🗄️ Autonomous DB"]', "Database"),
    "lb":            ('LB["⚖️ Load Balancer"]', "Network"),
    "object_storage":('OBJ["📦 Object Storage"]', "Storage"),
    "functions":     ('FUNC["λ OCI Functions"]', "Compute"),
    "api_gateway":   ('APIGW["🚪 API Gateway"]', "Network"),
    "oke":           ('OKE["☸️ OKE Cluster"]', "Compute"),
    "kms":           ('KMS["🔑 KMS Vault"]', "Security"),
    "iam":           ('IAM["👤 IAM Policies"]', "Security"),
    "nat_gateway":   ('NAT["🔀 NAT Gateway"]', "Network"),
    "service_gateway":('SGW["🛡️ Service Gateway"]', "Network"),
}

_DEFAULT_CONNECTIONS = [
    ("LB", "COMPUTE"),
    ("LB", "APIGW"),
    ("APIGW", "FUNC"),
    ("COMPUTE", "ADB"),
    ("FUNC", "ADB"),
    ("COMPUTE", "OBJ"),
    ("FUNC", "OBJ"),
    ("COMPUTE", "VCN"),
    ("ADB", "VCN"),
    ("NAT", "VCN"),
    ("SGW", "VCN"),
]


def generate_mermaid_diagram(services: list[str]) -> str:
    services_lower = [s.lower().replace("-", "_") for s in services]
    selected_nodes = {}
    for svc in services_lower:
        if svc in _SERVICE_NODE_MAP:
            node_def, group = _SERVICE_NODE_MAP[svc]
            node_id = node_def.split("[")[0]
            selected_nodes[node_id] = (node_def, group)

    if not selected_nodes:
        return "graph TB\n    PROVISO[Proviso - No services selected]"

    lines = ["graph TB"]
    lines.append("    subgraph OCI_INFRA[OCI Infrastructure]")
    for node_def, _ in selected_nodes.values():
        lines.append(f"        {node_def}")
    lines.append("    end")

    for src, dst in _DEFAULT_CONNECTIONS:
        if src in selected_nodes and dst in selected_nodes:
            lines.append(f"    {src} --> {dst}")

    lines.append("    style OCI_INFRA fill:#f0f4ff,stroke:#4a90d9")
    return "\n".join(lines)
