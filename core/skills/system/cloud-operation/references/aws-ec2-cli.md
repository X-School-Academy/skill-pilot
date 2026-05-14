# AWS EC2 — CLI Reference

Command reference, core concepts, and troubleshooting for EC2 operations.

## Execution Rule

- Treat every AWS CLI command in this file as reference for the intended AWS operation only.
- Do not run raw `aws ...` shell commands directly.
- Execute each AWS operation through `aws-api` skill (`call_aws` tool).
- If an AWS command shape, flag, parameter, or failure is unclear, use `aws-api` skill (`suggest_aws_commands` tool) to get the corrected command pattern, then run the resolved operation through `aws-api` (`call_aws`).

## Core Concepts

### Instance Types

| Category | Example | Use Case |
|----------|---------|----------|
| General Purpose | t3, m6i | Web servers, dev environments |
| Compute Optimized | c6i | Batch processing, gaming |
| Memory Optimized | r6i | Databases, caching |
| Storage Optimized | i3, d3 | Data warehousing |
| Accelerated | p4d, g5 | ML, graphics |

### Purchasing Options

| Option | Description |
|--------|-------------|
| On-Demand | Pay by the hour/second |
| Reserved | 1-3 year commitment, up to 72% discount |
| Spot | Unused capacity, up to 90% discount |
| Savings Plans | Flexible commitment-based discount |

### AMI (Amazon Machine Image)

Template containing OS, software, and configuration for launching instances.

### Security Groups

Virtual firewalls controlling inbound and outbound traffic at the instance level.

## Common Patterns

### Launch an Instance

```bash
# Create key pair
aws ec2 create-key-pair \
  --key-name my-key \
  --query 'KeyMaterial' \
  --output text > my-key.pem
chmod 400 my-key.pem

# Create security group
aws ec2 create-security-group \
  --group-name web-server-sg \
  --description "Web server security group" \
  --vpc-id vpc-12345678

# Allow SSH and HTTP
aws ec2 authorize-security-group-ingress \
  --group-id sg-12345678 --protocol tcp --port 22 --cidr 10.0.0.0/8

aws ec2 authorize-security-group-ingress \
  --group-id sg-12345678 --protocol tcp --port 80 --cidr 0.0.0.0/0

# Launch instance
aws ec2 run-instances \
  --image-id ami-0123456789abcdef0 \
  --instance-type t3.micro \
  --key-name my-key \
  --security-group-ids sg-12345678 \
  --subnet-id subnet-12345678 \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=web-server}]'

aws ec2 describe-instances --instance-ids i-1234567890abcdef0
```

### User Data Script

```bash
aws ec2 run-instances \
  --image-id ami-0123456789abcdef0 \
  --instance-type t3.micro \
  --key-name my-key \
  --security-group-ids sg-12345678 \
  --subnet-id subnet-12345678 \
  --user-data '#!/bin/bash
    apt update -y
    apt install -y nginx
    systemctl start nginx
    systemctl enable nginx
  '
```

### Attach IAM Role

```bash
aws iam create-instance-profile --instance-profile-name web-server-profile
aws iam add-role-to-instance-profile \
  --instance-profile-name web-server-profile \
  --role-name web-server-role

aws ec2 run-instances \
  --image-id ami-0123456789abcdef0 \
  --instance-type t3.micro \
  --iam-instance-profile Name=web-server-profile \
  ...
```

### Create AMI from Instance

```bash
aws ec2 create-image \
  --instance-id i-1234567890abcdef0 \
  --name "my-custom-ami-$(date +%Y%m%d)" \
  --no-reboot
```

### Spot Instance Request

```bash
aws ec2 request-spot-instances \
  --instance-count 1 \
  --type "one-time" \
  --launch-specification '{
    "ImageId": "ami-0123456789abcdef0",
    "InstanceType": "c5.large",
    "KeyName": "my-key",
    "SecurityGroupIds": ["sg-12345678"],
    "SubnetId": "subnet-12345678"
  }' \
  --spot-price "0.05"
```

### EBS Volume Management

```bash
aws ec2 create-volume \
  --availability-zone us-east-1a \
  --size 100 \
  --volume-type gp3 \
  --iops 3000 \
  --encrypted

aws ec2 attach-volume \
  --volume-id vol-12345678 \
  --instance-id i-1234567890abcdef0 \
  --device /dev/sdf

aws ec2 create-snapshot \
  --volume-id vol-12345678 \
  --description "Daily backup"
```

### EC2 Instance Connect

```bash
# Push SSH key temporarily (expires in 60 seconds)
aws ec2-instance-connect send-ssh-public-key \
  --instance-id i-1234567890abcdef0 \
  --instance-os-user ec2-user \
  --ssh-public-key file://~/.ssh/id_rsa.pub
```

## CLI Reference

### Instance Management

| Command | Description |
|---------|-------------|
| `aws ec2 run-instances` | Launch instances |
| `aws ec2 describe-instances` | List instances |
| `aws ec2 start-instances` | Start stopped instances |
| `aws ec2 stop-instances` | Stop running instances |
| `aws ec2 reboot-instances` | Reboot instances |
| `aws ec2 terminate-instances` | Terminate instances |
| `aws ec2 modify-instance-attribute` | Modify instance settings |

### Security Groups

| Command | Description |
|---------|-------------|
| `aws ec2 create-security-group` | Create security group |
| `aws ec2 describe-security-groups` | List security groups |
| `aws ec2 authorize-security-group-ingress` | Add inbound rule |
| `aws ec2 revoke-security-group-ingress` | Remove inbound rule |

### AMIs

| Command | Description |
|---------|-------------|
| `aws ec2 describe-images` | List AMIs |
| `aws ec2 create-image` | Create AMI from instance |
| `aws ec2 copy-image` | Copy AMI to another region |
| `aws ec2 deregister-image` | Delete AMI |

### EBS Volumes

| Command | Description |
|---------|-------------|
| `aws ec2 create-volume` | Create EBS volume |
| `aws ec2 attach-volume` | Attach to instance |
| `aws ec2 detach-volume` | Detach from instance |
| `aws ec2 create-snapshot` | Create snapshot |
| `aws ec2 modify-volume` | Resize/modify volume |

## Useful Queries

```bash
# Latest Ubuntu 24.04 LTS arm64 AMI (Canonical)
aws ec2 describe-images \
  --owners 099720109477 \
  --filters Name=name,Values=ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-arm64-server-* \
            Name=state,Values=available \
  --query 'sort_by(Images, &CreationDate)[-1].ImageId'

# List Amazon-owned AMIs
aws ec2 describe-images \
  --owners amazon \
  --filters Name=state,Values=available \
            Name=name,Values='al2023-ami-*-x86_64' \
  --query 'sort_by(Images,&CreationDate)[].{Name:Name,ImageId:ImageId}' \
  --output table

# Instance types available in current region
aws ec2 describe-instance-type-offerings \
  --location-type region \
  --filters Name=instance-type,Values='t4g.*' \
  --query 'InstanceTypeOfferings[].InstanceType' \
  --output table

# Specs for an instance type
aws ec2 describe-instance-types \
  --instance-types t4g.small \
  --query 'InstanceTypes[].{Type:InstanceType,vCPU:VCpuInfo.DefaultVCpus,MemoryMiB:MemoryInfo.SizeInMiB}' \
  --output table
```

## Best Practices

- **Use IAM roles** on instances instead of access keys
- **Restrict security groups** — principle of least privilege
- **Use private subnets** for backend instances
- **Enable IMDSv2** to prevent SSRF attacks
- **Encrypt EBS volumes** at rest

```bash
# Require IMDSv2
aws ec2 modify-instance-metadata-options \
  --instance-id i-1234567890abcdef0 \
  --http-tokens required \
  --http-endpoint enabled
```

## Troubleshooting

### Cannot SSH to Instance

1. Security group allows port 22 from your IP
2. Instance has public IP (or use SSM)
3. Key pair matches instance
4. Instance state is `running`
5. Network ACL allows traffic

```bash
aws ec2 describe-security-groups --group-ids sg-12345678
aws ec2 describe-instances \
  --instance-ids i-1234567890abcdef0 \
  --query "Reservations[].Instances[].{State:State.Name,PublicIP:PublicIpAddress}"

# Alternative: use Session Manager (no SSH required)
aws ssm start-session --target i-1234567890abcdef0
```

### Instance Won't Start

```bash
aws ec2 describe-instances \
  --instance-ids i-1234567890abcdef0 \
  --query "Reservations[].Instances[].StateReason"
```

Causes: instance limit reached, insufficient AZ capacity, EBS issue, invalid AMI.

### Instance Unreachable

```bash
aws ec2 describe-instance-status --instance-ids i-1234567890abcdef0
aws ec2 get-console-output --instance-id i-1234567890abcdef0
```

### High CPU

```bash
aws ec2 monitor-instances --instance-ids i-1234567890abcdef0

aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-1234567890abcdef0 \
  --start-time $(date -d '1 hour ago' -u +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Average
```

## References

- [EC2 User Guide](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/)
- [EC2 CLI Reference](https://docs.aws.amazon.com/cli/latest/reference/ec2/)
