---
name: setup-aws-ec2
description: Provision an AWS EC2 Ubuntu instance with VPC, subnet, internet gateway, and SSH-only security group. AWS CLI snippets in this skill are reference only; execute AWS operations through the aws-api-call-aws agent skill and use aws-api-suggest-aws-commands for help resolving AWS command issues.
---

# Setup AWS EC2 Instance

Provision all AWS networking and compute resources for a new Ubuntu EC2 server:
VPC, public subnet, internet gateway, route table, security group, and the EC2 instance itself.

## When to Use This Skill

- Launching a new EC2 instance for any project
- No suitable EC2 instance exists yet for the task
- Need a clean, isolated VPC setup for a server workload

## Your Roles in This Skill

- **SysOps Engineer**: Provision and configure AWS networking and EC2 instance
- **Security Engineer**: Restrict inbound access to SSH only by default

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

## Preconditions

- AWS credentials configured in `config/.env` — run skill `enable-aws-cli` if needed

Verify:
- Use skill `key-safe` to confirm `AWS_ACCESS_KEY_ID` and `AWS_REGION` are available.

## Execution Rule

- Treat every AWS CLI command shown in this skill as reference for the intended AWS operation only.
- Do not run raw `aws ...` shell commands directly from this skill.
- Execute each AWS operation through agent skill `aws-api-call-aws`.
- If an AWS command shape, flag, parameter, or failure is unclear, use agent skill `aws-api-suggest-aws-commands` to get the corrected command pattern, then run the resolved operation through `aws-api-call-aws`.

## Workflow Usage Requirement

When this skill is used in a workflow agent node:

- Output result as plain text. If the user asked to save it to a file, write it there.
- Include concise context in the output (instance ID, public IP, region, and security-group status) so downstream agents can safely continue.

## Skip Condition

Ask user if an EC2 instance already exists for this task. If yes, get the instance ID and verify:

```
aws ec2 describe-instances --instance-ids <id> --region <region>
  → check State.Name = "running"
```

If running, report it and exit. If stopped, offer to start it.

Use the shown `describe-instances` command only as a reference pattern; perform the actual check through `aws-api-call-aws`.

## Instructions

### Step 1: Confirm parameters with user

Ask user to confirm or provide:
- **Instance name** (default: `app-server`)
- **Instance type** (default: `t4g.small`; show pricing if unsure)
- **Region** (read from `.env` via skill `key-safe`)
- **VPC name** (default: `vpc-<instance-name>`)
- **Security group extra ports** (default: SSH only; ask if any ports should be open)

**Pricing context for default recommendation:**

```
t4g.small — 2 vCPU, 2 GiB RAM, ARM Graviton2
  ~$0.0212/hr → ~$15.30/month
  Free tier eligible (new accounts: 750 hrs/month for 6 months)
  40% better price-performance than T3 (x86)
```

### Step 2: Read region from .env

Use skill `key-safe` to get `AWS_REGION`.

Use this value for all AWS API calls via `aws-ec2` skill.

### Step 3: Find latest Ubuntu 24.04 LTS AMI

Use `aws-ec2` skill:

The command below is reference only. Run the equivalent operation through `aws-api-call-aws`.

```
aws ec2 describe-images
  --owners 099720109477
  --filters Name=name,Values=ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-arm64-server-*
            Name=state,Values=available
  --query sort_by(Images, &CreationDate)[-1].ImageId
  --region <region>
```

Note: use `arm64` filter for t4g, `amd64` for t3.x instances.

### Step 4: Create VPC

Reference commands only; execute through `aws-api-call-aws`:

```
aws ec2 create-vpc --cidr-block 10.0.0.0/16 --region <region>
  → tag: Name=<vpc-name>
aws ec2 modify-vpc-attribute --vpc-id <VPC_ID> --enable-dns-hostnames
```

### Step 5: Create public subnet

Reference commands only; execute through `aws-api-call-aws`:

```
aws ec2 create-subnet --vpc-id <VPC_ID> --cidr-block 10.0.1.0/24 --region <region>
  → tag: Name=<vpc-name>-subnet
aws ec2 modify-subnet-attribute --subnet-id <SUBNET_ID> --map-public-ip-on-launch
```

### Step 6: Internet gateway and routing

Reference commands only; execute through `aws-api-call-aws`:

```
aws ec2 create-internet-gateway → tag: Name=<vpc-name>-igw
aws ec2 attach-internet-gateway --internet-gateway-id <IGW_ID> --vpc-id <VPC_ID>
aws ec2 create-route-table --vpc-id <VPC_ID> → tag: Name=<vpc-name>-rt
aws ec2 create-route --route-table-id <RT_ID> --destination-cidr-block 0.0.0.0/0 --gateway-id <IGW_ID>
aws ec2 associate-route-table --route-table-id <RT_ID> --subnet-id <SUBNET_ID>
```

### Step 7: Security group

Reference commands only; execute through `aws-api-call-aws`:

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

Reference commands only; execute through `aws-api-call-aws`:

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

Reference commands only; execute polling and lookups through `aws-api-call-aws`:

```
aws ec2 describe-instance-status --instance-ids <INSTANCE_ID>
aws ec2 describe-instances --instance-ids <INSTANCE_ID>
  --query Reservations[0].Instances[0].PublicIpAddress
```

### Step 10: Report result

Output result as plain text. If the user asked to save it to a file, write it there.

## Output

Plain text result shown to user:

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

For any AWS command uncertainty or failure, first consult `aws-api-suggest-aws-commands`, then execute the resolved operation with `aws-api-call-aws`.
