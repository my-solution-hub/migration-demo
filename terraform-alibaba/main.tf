# Configure the Alibaba Cloud Provider
terraform {
  required_providers {
    alicloud = {
      source  = "aliyun/alicloud"
      version = "~> 1.251.0"
    }
  }
  required_version = ">= 1.0"
}

# Configure the Alibaba Cloud Provider
provider "alicloud" {
  # access_key = var.access_key
  # secret_key = var.secret_key
  # region     = var.region
}

# Get available zones
data "alicloud_zones" "available" {
  available_resource_creation = "VSwitch"
}

# Create VPC
resource "alicloud_vpc" "main" {
  vpc_name   = var.vpc_name
  cidr_block = var.vpc_cidr
  
  tags = {
    Name        = var.vpc_name
    Environment = var.environment
    Project     = "terraform-alibaba-vpc"
  }
}

# Create first vSwitch in first available zone
resource "alicloud_vswitch" "vswitch_1" {
  vpc_id       = alicloud_vpc.main.id
  cidr_block   = var.vswitch_1_cidr
  zone_id      = data.alicloud_zones.available.zones[0].id
  vswitch_name = "${var.vpc_name}-vswitch-1"
  
  tags = {
    Name        = "${var.vpc_name}-vswitch-1"
    Environment = var.environment
    Zone        = data.alicloud_zones.available.zones[0].id
  }
}

# Create second vSwitch in second available zone
resource "alicloud_vswitch" "vswitch_2" {
  vpc_id       = alicloud_vpc.main.id
  cidr_block   = var.vswitch_2_cidr
  zone_id      = data.alicloud_zones.available.zones[1].id
  vswitch_name = "${var.vpc_name}-vswitch-2"
  
  tags = {
    Name        = "${var.vpc_name}-vswitch-2"
    Environment = var.environment
    Zone        = data.alicloud_zones.available.zones[1].id
  }
}
