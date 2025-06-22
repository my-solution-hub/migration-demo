# Alibaba Cloud credentials
# variable "access_key" {
#   description = "Alibaba Cloud Access Key ID"
#   type        = string
#   sensitive   = true
# }

# variable "secret_key" {
#   description = "Alibaba Cloud Access Key Secret"
#   type        = string
#   sensitive   = true
# }

# variable "region" {
#   description = "Alibaba Cloud region"
#   type        = string
#   default     = "cn-hangzhou"
# }

# VPC configuration
variable "vpc_name" {
  description = "Name of the VPC"
  type        = string
  default     = "terraform-vpc"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "vswitch_1_cidr" {
  description = "CIDR block for first vSwitch"
  type        = string
  default     = "10.0.1.0/24"
}

variable "vswitch_2_cidr" {
  description = "CIDR block for second vSwitch"
  type        = string
  default     = "10.0.2.0/24"
}

variable "environment" {
  description = "Environment tag"
  type        = string
  default     = "development"
}
