# EC2 Instance — app-server

## Instance Details

| Field           | Value                        |
|-----------------|------------------------------|
| Instance ID     | i-0c91d6d3ea988927f          |
| Instance name   | app-server                   |
| Instance type   | t4g.small                    |
| Public IP       | 54.79.12.72                  |
| Region          | ap-southeast-2               |
| State           | running                      |
| AMI             | ami-0f3b37a47cd6bd4fe (Ubuntu 24.04 LTS, ARM64) |
| VPC             | vpc-07fd40e9d9931cd83 (vpc-app-server)          |
| Subnet          | subnet-037794ef464e7b002 (ap-southeast-2a)       |
| Security group  | sg-009f7f72dc6c79a61 (app-server-sg)            |
| Storage         | 20 GiB gp3 (/dev/sda1)       |
| SSH port        | 22 (0.0.0.0/0)               |

## Connect

```bash
ssh ubuntu@54.79.12.72
```

> Note: No key pair was attached at launch. Use EC2 Instance Connect for SSH access.

## Previous Instance

The previous instance `i-0fc4503a4a27bc3ce` was terminated and replaced by `i-0c91d6d3ea988927f` on 2026-03-18.
