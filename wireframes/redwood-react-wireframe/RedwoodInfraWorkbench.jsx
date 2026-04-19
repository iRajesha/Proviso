import { useMemo, useState } from "react";
import "./redwood-infra-workbench.css";

const STARTER_TERRAFORM = `terraform {
  required_version = ">= 1.5.0"
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "~> 5.0"
    }
  }
}

provider "oci" {
  region = "ap-hyderabad-1"
}

resource "oci_core_vcn" "main" {
  compartment_id = var.compartment_ocid
  display_name   = "proviso-vcn"
  cidr_block     = "10.0.0.0/16"
}

resource "oci_core_subnet" "public_web" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.main.id
  display_name   = "public-web-subnet"
  cidr_block     = "10.0.1.0/24"
  prohibit_public_ip_on_vnic = false
}
`;

const STARTER_MESSAGES = [
  {
    role: "assistant",
    text: "Describe the OCI infrastructure you want. I will keep the Terraform draft updated in the editor.",
  },
];

const QUICK_PROMPTS = [
  "Add one private app subnet",
  "Restrict SSH to 10.10.0.0/24",
  "Add an NSG for web traffic",
];

function applyInfraChange(tf, instruction) {
  const normalized = instruction.toLowerCase();
  let updated = tf;
  const changes = [];

  if (
    normalized.includes("private") &&
    normalized.includes("subnet") &&
    !updated.includes('resource "oci_core_subnet" "private_app"')
  ) {
    updated += `
resource "oci_core_subnet" "private_app" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.main.id
  display_name   = "private-app-subnet"
  cidr_block     = "10.0.2.0/24"
  prohibit_public_ip_on_vnic = true
}
`;
    changes.push("Added private app subnet.");
  }

  if (
    normalized.includes("ssh") &&
    normalized.includes("10.10.0.0/24") &&
    !updated.includes('resource "oci_core_network_security_group" "app_nsg"')
  ) {
    updated += `
resource "oci_core_network_security_group" "app_nsg" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.main.id
  display_name   = "app-nsg"
}

resource "oci_core_network_security_group_security_rule" "allow_ssh_office" {
  network_security_group_id = oci_core_network_security_group.app_nsg.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = "10.10.0.0/24"
  source_type               = "CIDR_BLOCK"
  description               = "Allow SSH from office CIDR only"
}
`;
    changes.push("Restricted SSH ingress to office CIDR.");
  }

  if (
    normalized.includes("nsg") &&
    normalized.includes("web") &&
    !updated.includes('resource "oci_core_network_security_group_security_rule" "allow_https"')
  ) {
    updated += `
resource "oci_core_network_security_group_security_rule" "allow_https" {
  network_security_group_id = oci_core_network_security_group.app_nsg.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = "0.0.0.0/0"
  source_type               = "CIDR_BLOCK"
  tcp_options {
    destination_port_range {
      min = 443
      max = 443
    }
  }
  description = "Allow HTTPS"
}
`;
    changes.push("Added HTTPS web rule in NSG.");
  }

  if (changes.length === 0) {
    return {
      terraform: tf,
      summary:
        "No structural Terraform block was auto-added. You can still edit the draft directly in the editor.",
    };
  }

  return {
    terraform: updated.trimEnd() + "\n",
    summary: changes.join(" "),
  };
}

function buildAssistantReply(userText, summary) {
  return `Acknowledged. ${summary} If you want, ask for another change such as private routing, load balancer, or autoscaling.`;
}

export default function RedwoodInfraWorkbench() {
  const [messages, setMessages] = useState(STARTER_MESSAGES);
  const [draftMessage, setDraftMessage] = useState("");
  const [terraform, setTerraform] = useState(STARTER_TERRAFORM);
  const [changeLog, setChangeLog] = useState([
    "Initialized base VCN and one public web subnet.",
  ]);

  const lineCount = useMemo(() => terraform.split("\n").length, [terraform]);

  function sendMessage(textOverride) {
    const text = (textOverride ?? draftMessage).trim();
    if (!text) return;

    const result = applyInfraChange(terraform, text);
    const assistantText = buildAssistantReply(text, result.summary);

    setTerraform(result.terraform);
    setChangeLog((prev) => [result.summary, ...prev].slice(0, 6));
    setMessages((prev) => [
      ...prev,
      { role: "user", text },
      { role: "assistant", text: assistantText },
    ]);
    setDraftMessage("");
  }

  return (
    <div className="rw-app">
      <header className="rw-header">
        <div>
          <p className="rw-kicker">Proviso Wireframe</p>
          <h1>OCI Infra Chat + Terraform Editor</h1>
        </div>
        <button className="rw-primary">Generate Candidate Draft</button>
      </header>

      <main className="rw-workbench">
        <section className="rw-panel rw-chat">
          <div className="rw-panel-head">
            <h2>Requirements Chat</h2>
            <span className="rw-pill">Live assistant</span>
          </div>

          <div className="rw-msg-list">
            {messages.map((msg, idx) => (
              <article key={`${msg.role}-${idx}`} className={`rw-msg rw-${msg.role}`}>
                <p className="rw-msg-role">
                  {msg.role === "assistant" ? "Solution" : "You"}
                </p>
                <p className="rw-msg-text">{msg.text}</p>
              </article>
            ))}
          </div>

          <div className="rw-quick-prompt-row">
            {QUICK_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                className="rw-chip"
                onClick={() => sendMessage(prompt)}
                type="button"
              >
                {prompt}
              </button>
            ))}
          </div>

          <div className="rw-composer">
            <textarea
              value={draftMessage}
              onChange={(e) => setDraftMessage(e.target.value)}
              placeholder="Example: add private subnet and keep compute instances private"
              rows={3}
            />
            <button className="rw-primary" onClick={() => sendMessage()} type="button">
              Send
            </button>
          </div>
        </section>

        <section className="rw-panel rw-editor">
          <div className="rw-panel-head">
            <h2>Terraform Editor</h2>
            <span className="rw-pill rw-neutral">{lineCount} lines</span>
          </div>

          <div className="rw-editor-toolbar">
            <button type="button">main.tf</button>
            <button type="button">variables.tf</button>
            <button type="button">outputs.tf</button>
            <button type="button" className="rw-primary ghost">
              Validate
            </button>
          </div>

          <textarea
            className="rw-code"
            value={terraform}
            onChange={(e) => setTerraform(e.target.value)}
            spellCheck={false}
          />

          <div className="rw-change-log">
            <h3>Recent changes</h3>
            <ul>
              {changeLog.map((entry, idx) => (
                <li key={`${entry}-${idx}`}>{entry}</li>
              ))}
            </ul>
          </div>
        </section>
      </main>
    </div>
  );
}
