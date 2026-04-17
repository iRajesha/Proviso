variable "region" {
  description = "OCI region"
  type        = string
  default     = "us-chicago-1"
}

variable "tenancy_ocid" {
  description = "OCI tenancy OCID"
  type        = string
}

variable "user_ocid" {
  description = "OCI user OCID"
  type        = string
}

variable "fingerprint" {
  description = "API key fingerprint"
  type        = string
}

variable "private_key_path" {
  description = "Path to OCI API private key PEM"
  type        = string
  default     = "~/.oci/oci_api_key.pem"
}

variable "compartment_ocid" {
  description = "Target compartment OCID"
  type        = string
}

variable "project_name" {
  description = "Project name used for resource naming and tagging"
  type        = string
  default     = "proviso"
}

variable "environment" {
  description = "Deployment environment (dev/staging/prod)"
  type        = string
  default     = "dev"
}

variable "adb_admin_password" {
  description = "ADB admin password (min 12 chars, uppercase, lowercase, number, special char)"
  type        = string
  sensitive   = true
}
