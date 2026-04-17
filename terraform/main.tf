terraform {
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = ">= 5.0.0"
    }
  }
  backend "local" {}
}

provider "oci" {
  region           = var.region
  tenancy_ocid     = var.tenancy_ocid
  user_ocid        = var.user_ocid
  fingerprint      = var.fingerprint
  private_key_path = var.private_key_path
}

# ── VCN ────────────────────────────────────────────────────────
resource "oci_core_vcn" "proviso_vcn" {
  compartment_id = var.compartment_ocid
  cidr_block     = "10.10.0.0/16"
  display_name   = "${var.project_name}-vcn"

  freeform_tags = local.common_tags
}

# ── Internet Gateway ───────────────────────────────────────────
resource "oci_core_internet_gateway" "igw" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.proviso_vcn.id
  display_name   = "${var.project_name}-igw"
  enabled        = true
  freeform_tags  = local.common_tags
}

# ── NAT Gateway ────────────────────────────────────────────────
resource "oci_core_nat_gateway" "nat" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.proviso_vcn.id
  display_name   = "${var.project_name}-nat"
  freeform_tags  = local.common_tags
}

# ── Service Gateway ────────────────────────────────────────────
data "oci_core_services" "all_services" {}

resource "oci_core_service_gateway" "sgw" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.proviso_vcn.id
  display_name   = "${var.project_name}-sgw"

  services {
    service_id = data.oci_core_services.all_services.services[0].id
  }

  freeform_tags = local.common_tags
}

# ── Public Subnet (API / LB tier) ─────────────────────────────
resource "oci_core_subnet" "public_subnet" {
  compartment_id             = var.compartment_ocid
  vcn_id                     = oci_core_vcn.proviso_vcn.id
  cidr_block                 = "10.10.1.0/24"
  display_name               = "${var.project_name}-public-subnet"
  prohibit_public_ip_on_vnic = false
  route_table_id             = oci_core_route_table.public_rt.id
  freeform_tags              = local.common_tags
}

# ── Private Subnet (App + DB tier) ────────────────────────────
resource "oci_core_subnet" "private_subnet" {
  compartment_id             = var.compartment_ocid
  vcn_id                     = oci_core_vcn.proviso_vcn.id
  cidr_block                 = "10.10.2.0/24"
  display_name               = "${var.project_name}-private-subnet"
  prohibit_public_ip_on_vnic = true
  route_table_id             = oci_core_route_table.private_rt.id
  freeform_tags              = local.common_tags
}

# ── Route Tables ───────────────────────────────────────────────
resource "oci_core_route_table" "public_rt" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.proviso_vcn.id
  display_name   = "${var.project_name}-public-rt"

  route_rules {
    destination       = "0.0.0.0/0"
    network_entity_id = oci_core_internet_gateway.igw.id
  }

  freeform_tags = local.common_tags
}

resource "oci_core_route_table" "private_rt" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.proviso_vcn.id
  display_name   = "${var.project_name}-private-rt"

  route_rules {
    destination       = "0.0.0.0/0"
    network_entity_id = oci_core_nat_gateway.nat.id
  }

  freeform_tags = local.common_tags
}

locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
