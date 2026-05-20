# AWS — Provision EC2 Instance

Provision all AWS networking and compute resources for a new Ubuntu EC2 server: VPC, public subnet, internet gateway, route table, security group, and the EC2 instance itself.

## When to Use

- Launching a new EC2 instance for any project
- No suitable EC2 instance exists yet
- Need a clean, isolated VPC setup for a server workload

## Preconditions

- AWS credentials configured — run `aws-enable-cli` action if needed.
- Verify: use skill `key-safe-sudo` to confirm `AWS_ACCESS_KEY_ID` and `AWS_REGION` are available.

## Execution Rule

All AWS CLI commands in this file are reference only. Execute every operation through `aws-api` skill (`call_aws` tool). For unclear command shapes or failures, use `aws-api` skill (`suggest_aws_commands` tool) first.

## Skip Condition

Ask if an EC2 instance already exists. If yes, verify via `aws-api` (`call_aws`):

```
aws ec2 describe-instances --instance-ids <id> --region <region>
  → check State.Name = "running"
```

If running, report it and exit. If stopped, offer to start it.

## Instructions

### Step 1: Confirm parameters

Ask user to confirm or provide:

- **Instance name** (default: `app-server`)
- **Instance type** (default: `t4g.small`; show pricing if unsure)
- **Root disk size** (default: `20 GiB` gp3)
- **Region** (read from `.env` via skill `key-safe-sudo`)
- **VPC name** (default: `vpc-<instance-name>`)
- **Extra open ports** (default: SSH only)

**Pricing for default:**

```
t4g.small — 2 vCPU, 2 GiB RAM, ARM Graviton2
  ~$0.0212/hr → ~$15.30/month
  Free tier eligible (750 hrs/month for 6 months on new accounts)
  40% better price-performance than T3 (x86)
```

### Step 2: Read region

Use skill `key-safe-sudo` to get `AWS_REGION`.

### Step 3: Find latest Ubuntu 24.04 LTS AMI

Reference (execute via `aws-api` (`call_aws`)):

```
aws ec2 describe-images
  --owners 099720109477
  --filters Name=name,Values=ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-arm64-server-*
            Name=state,Values=available
  --query sort_by(Images, &CreationDate)[-1].ImageId
  --region <region>
```

Use `arm64` filter for t4g, `amd64` for t3.x instances.

### Step 4: Create VPC

```
aws ec2 create-vpc --cidr-block 10.0.0.0/16 --region <region>
  → tag: Name=<vpc-name>
aws ec2 modify-vpc-attribute --vpc-id <VPC_ID> --enable-dns-hostnames
```

### Step 5: Create public subnet

```
aws ec2 create-subnet --vpc-id <VPC_ID> --cidr-block 10.0.1.0/24 --region <region>
  → tag: Name=<vpc-name>-subnet
aws ec2 modify-subnet-attribute --subnet-id <SUBNET_ID> --map-public-ip-on-launch
```

### Step 6: Internet gateway and routing

```
aws ec2 create-internet-gateway → tag: Name=<vpc-name>-igw
aws ec2 attach-internet-gateway --internet-gateway-id <IGW_ID> --vpc-id <VPC_ID>
aws ec2 create-route-table --vpc-id <VPC_ID> → tag: Name=<vpc-name>-rt
aws ec2 create-route --route-table-id <RT_ID> --destination-cidr-block 0.0.0.0/0 --gateway-id <IGW_ID>
aws ec2 associate-route-table --route-table-id <RT_ID> --subnet-id <SUBNET_ID>
```

### Step 7: Security group

```
aws ec2 create-security-group
  --group-name <instance-name>-sg
  --description "<instance-name> security group"
  --vpc-id <VPC_ID>

# Always allow SSH
aws ec2 authorize-security-group-ingress --group-id <SG_ID> --protocol tcp --port 22 --cidr 0.0.0.0/0

# Add any extra ports the user requested
```

### Step 8: Launch EC2 instance

```
aws ec2 run-instances
  --image-id <AMI_ID>
  --instance-type <instance-type>
  --subnet-id <SUBNET_ID>
  --security-group-ids <SG_ID>
  --block-device-mappings DeviceName=/dev/sda1,Ebs={VolumeSize=20,VolumeType=gp3}
  --count 1
  --region <region>
  → tag: Name=<instance-name>
```

### Step 9: Wait for running state

Poll until state = `running` and status checks pass:

```
aws ec2 describe-instance-status --instance-ids <INSTANCE_ID>
aws ec2 describe-instances --instance-ids <INSTANCE_ID>
  --query Reservations[0].Instances[0].PublicIpAddress
```

### Step 10: Report result

```
EC2 Instance ID:   i-xxxxxxxxxxxx
Instance name:     <name>
Instance type:     t4g.small
Public IP:         x.x.x.x
Region:            <region>
State:             running
Security group:    SSH port 22 + <any extra ports>
AMI:               <ami-id> (Ubuntu 24.04 LTS)
```

## Common Issues

- **AMI not found**: verify region and architecture filter (arm64 vs amd64)
- **VPC limit reached**: default is 5 VPCs per region — reuse existing or request limit increase
- **Status checks pending**: normal for first boot; wait up to 10 minutes
- **No public IP**: verify subnet has `map-public-ip-on-launch` enabled
