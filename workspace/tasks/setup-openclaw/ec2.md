# EC2 Instance — app-server

## Instance Details

| Field           | Value                        |
|-----------------|------------------------------|
| Instance ID     | i-0fc4503a4a27bc3ce          |
| Instance name   | app-server                   |
| Instance type   | t4g.small                    |
| Public IP       | 3.105.228.17                 |
| Region          | ap-southeast-2               |
| State           | running                      |
| AMI             | ami-08d415e54d25f4366 (Ubuntu 24.04 LTS, ARM64) |
| VPC             | vpc-07fd40e9d9931cd83 (vpc-app-server)          |
| Subnet          | subnet-037794ef464e7b002 (ap-southeast-2a)       |
| Security group  | sg-009f7f72dc6c79a61 (app-server-sg)            |
| Storage         | 20 GiB gp3 (/dev/sda1)       |
| SSH port        | 22 (0.0.0.0/0)               |

## Connect

```bash
ssh ubuntu@3.105.228.17
```

> Note: No key pair was attached at launch. Use EC2 Instance Connect or reprovision with a key pair to enable SSH access.
