# Terraform Alibaba Cloud VPC Project

This Terraform project creates a VPC with 2 vSwitches on Alibaba Cloud, designed to work alongside the migration demo project.

## Architecture

The project creates:
- **VPC**: A Virtual Private Cloud with configurable CIDR block
- **2 vSwitches**: Distributed across different availability zones
- **Proper Tagging**: For resource organization and management

## Prerequisites

1. **Terraform**: Install Terraform >= 1.0
   ```bash
   # macOS
   brew install terraform
   
   # Or download from https://terraform.io/downloads
   ```

2. **Alibaba Cloud Account**: With programmatic access
   - Access Key ID
   - Access Key Secret
   - region

  ``` shell
  ALIBABA_CLOUD_ACCESS_KEY_ID=xxx
  ALIBABA_CLOUD_ACCESS_KEY_SECRET=xxx
  export ALIBABA_CLOUD_REGION=ap-southeast-1

  ```

1. **Alibaba Cloud CLI** (optional but recommended):

   ```bash
   # macOS
   brew install aliyun-cli
   ```

## Quick Start

### 1. Configure Credentials

**Option A: Using terraform.tfvars (Recommended)**
```bash
# Copy the example file
cp terraform.tfvars.example terraform.tfvars

# Edit with your credentials
vim terraform.tfvars
```

**Option B: Using Environment Variables**
```bash
export TF_VAR_access_key="your_access_key_id"
export TF_VAR_secret_key="your_access_key_secret"
```

**Option C: Using Alibaba Cloud CLI Profile**
```bash
# Configure CLI (will create ~/.aliyun/config.json)
aliyun configure

# Then use in terraform (modify provider block in main.tf)
provider "alicloud" {
  profile = "default"
  region  = var.region
}
```

### 2. Initialize and Deploy

```bash
# Initialize Terraform
terraform init

# Review the plan
terraform plan

# Apply the configuration
terraform apply
```

### 3. Verify Deployment

```bash
# Show outputs
terraform output

# Example output:
# vpc_id = "vpc-uf6f7l4fg90oxkcdtw0tn"
# vswitch_1_id = "vsw-uf6a7l3fg80oxkcdtw0tn"
# vswitch_2_id = "vsw-uf6b8l4fg90oxkcdtw0tn"
```

## Configuration Options

### Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `access_key` | Alibaba Cloud Access Key ID | - | Yes |
| `secret_key` | Alibaba Cloud Access Key Secret | - | Yes |
| `region` | Alibaba Cloud region | `cn-hangzhou` | No |
| `vpc_name` | Name of the VPC | `terraform-vpc` | No |
| `vpc_cidr` | CIDR block for VPC | `10.0.0.0/16` | No |
| `vswitch_1_cidr` | CIDR block for first vSwitch | `10.0.1.0/24` | No |
| `vswitch_2_cidr` | CIDR block for second vSwitch | `10.0.2.0/24` | No |
| `environment` | Environment tag | `development` | No |

### Supported Regions

Common Alibaba Cloud regions:
- `cn-hangzhou` (China East 1)
- `cn-shanghai` (China East 2)
- `cn-beijing` (China North 2)
- `cn-shenzhen` (China South 1)
- `ap-southeast-1` (Singapore)
- `us-west-1` (US West)

## Integration with Migration Demo

This Terraform project complements the migration demo by providing:

1. **Source Infrastructure**: Create VPC infrastructure on Alibaba Cloud
2. **Testing Target**: Use the created VPC ID for migration testing
3. **Comparison**: Compare original vs migrated infrastructure

### Example Integration

```bash
# 1. Deploy Alibaba Cloud infrastructure
cd terraform-alibaba
terraform apply

# 2. Get VPC ID from output
VPC_ID=$(terraform output -raw vpc_id)

# 3. Use in migration demo
cd ../src
uv run migration_workflow.py \
  --project-name terraform-migration-test \
  --target-dir ./output \
  --vpc-id $VPC_ID \
  --region cn-hangzhou
```

## File Structure

```
terraform-alibaba/
├── main.tf                    # Main Terraform configuration
├── variables.tf               # Variable definitions
├── outputs.tf                 # Output definitions
├── terraform.tfvars.example   # Example variables file
├── README.md                  # This file
└── .terraform/                # Terraform state (created after init)
```

## Security Best Practices

1. **Credentials**: Never commit `terraform.tfvars` with real credentials
2. **State File**: Consider using remote state for production
3. **Security Groups**: Customize rules based on your requirements
4. **Network Segmentation**: Adjust CIDR blocks for your network design

### Remote State Configuration (Optional)

For production use, configure remote state:

```hcl
terraform {
  backend "oss" {
    bucket = "your-terraform-state-bucket"
    prefix = "terraform-alibaba-vpc"
    key    = "terraform.tfstate"
    region = "cn-hangzhou"
  }
}
```

## Cleanup

To destroy the infrastructure:

```bash
terraform destroy
```

## Troubleshooting

### Common Issues

**Authentication Error**
```
Error: InvalidAccessKeyId.NotFound
```
- Verify your Access Key ID and Secret
- Check if credentials have proper permissions

**Region Not Available**
```
Error: Zone not available
```
- Try a different region
- Check if the region supports VPC creation

**CIDR Conflicts**
```
Error: InvalidCidrBlock.Overlap
```
- Ensure vSwitch CIDR blocks don't overlap
- Verify CIDR blocks are within VPC range

### Debug Mode

Enable detailed logging:
```bash
export TF_LOG=DEBUG
terraform apply
```

## Contributing

This project is part of the larger migration demo. See the main README for contribution guidelines.

## License

MIT License - see LICENSE file for details.
