# VPC outputs
output "vpc_id" {
  description = "ID of the VPC"
  value       = alicloud_vpc.main.id
}

output "vpc_name" {
  description = "Name of the VPC"
  value       = alicloud_vpc.main.vpc_name
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = alicloud_vpc.main.cidr_block
}

# vSwitch outputs
output "vswitch_1_id" {
  description = "ID of the first vSwitch"
  value       = alicloud_vswitch.vswitch_1.id
}

output "vswitch_1_cidr" {
  description = "CIDR block of the first vSwitch"
  value       = alicloud_vswitch.vswitch_1.cidr_block
}

output "vswitch_1_zone" {
  description = "Availability zone of the first vSwitch"
  value       = alicloud_vswitch.vswitch_1.zone_id
}

output "vswitch_2_id" {
  description = "ID of the second vSwitch"
  value       = alicloud_vswitch.vswitch_2.id
}

output "vswitch_2_cidr" {
  description = "CIDR block of the second vSwitch"
  value       = alicloud_vswitch.vswitch_2.cidr_block
}

output "vswitch_2_zone" {
  description = "Availability zone of the second vSwitch"
  value       = alicloud_vswitch.vswitch_2.zone_id
}

# Available zones
output "available_zones" {
  description = "List of available zones"
  value       = data.alicloud_zones.available.zones[*].id
}
