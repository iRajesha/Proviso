output "vcn_id" {
  description = "VCN OCID"
  value       = oci_core_vcn.proviso_vcn.id
}

output "public_subnet_id" {
  description = "Public subnet OCID"
  value       = oci_core_subnet.public_subnet.id
}

output "private_subnet_id" {
  description = "Private subnet OCID"
  value       = oci_core_subnet.private_subnet.id
}
