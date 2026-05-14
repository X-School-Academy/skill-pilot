# GitHub Actions CI/CD

## OIDC Integration (No Long-lived Keys)

### 1. Create OIDC Provider
One-time setup per AWS account.

```bash
# Create OIDC provider
aws iam create-open-id-connect-provider \
    --url "https://token.actions.githubusercontent.com" \
    --client-id-list "sts.amazonaws.com" \
    --thumbprint-list "6938fd4d98bab03faadb97b34396831e3780aea1" \
    --tags Key=Purpose,Value=GitHubActions

# List OIDC providers
aws iam list-open-id-connect-providers

# Get provider details
aws iam get-open-id-connect-provider \
    --open-id-connect-provider-arn arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com
```

### 2. Create IAM Role

**Basic Trust Policy (`github-trust.json`):**
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                },
                "StringLike": {
                    "token.actions.githubusercontent.com:sub": "repo:my-org/my-repo:*"
                }
            }
        }
    ]
}
```

**Restricted Trust Policy (main branch only):**
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
                    "token.actions.githubusercontent.com:sub": "repo:my-org/my-repo:ref:refs/heads/main"
                }
            }
        }
    ]
}
```

**Environment-based Trust Policy:**
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                },
                "StringLike": {
                    "token.actions.githubusercontent.com:sub": "repo:my-org/my-repo:environment:production"
                }
            }
        }
    ]
}
```

**Multi-repo Trust Policy:**
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                },
                "StringLike": {
                    "token.actions.githubusercontent.com:sub": [
                        "repo:my-org/frontend:*",
                        "repo:my-org/backend:*",
                        "repo:my-org/infrastructure:ref:refs/heads/main"
                    ]
                }
            }
        }
    ]
}
```

```bash
# Create role
aws iam create-role \
    --role-name GitHubDeployRole \
    --assume-role-policy-document file://github-trust.json \
    --description "Role for GitHub Actions deployments" \
    --max-session-duration 3600 \
    --tags Key=Purpose,Value=CICD

# Attach managed policies
aws iam attach-role-policy \
    --role-name GitHubDeployRole \
    --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

aws iam attach-role-policy \
    --role-name GitHubDeployRole \
    --policy-arn arn:aws:iam::aws:policy/AmazonECR-FullAccess

# Or attach custom policy
aws iam put-role-policy \
    --role-name GitHubDeployRole \
    --policy-name DeploymentPolicy \
    --policy-document file://deploy-policy.json
```

## Workflow Configurations

### Basic S3 Deployment
```yaml
name: Deploy to S3
on:
  push:
    branches: [main]

permissions:
  id-token: write   # Required for OIDC
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/GitHubDeployRole
          aws-region: us-east-1

      - name: Deploy to S3
        run: aws s3 sync ./dist s3://my-bucket/ --delete
```

### ECR Push and ECS Deploy
```yaml
name: Build and Deploy
on:
  push:
    branches: [main]

permissions:
  id-token: write
  contents: read

env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: my-app
  ECS_SERVICE: my-service
  ECS_CLUSTER: my-cluster
  CONTAINER_NAME: app

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/GitHubDeployRole
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build and push image
        id: build-image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          echo "image=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG" >> $GITHUB_OUTPUT

      - name: Deploy to ECS
        uses: aws-actions/amazon-ecs-deploy-task-definition@v1
        with:
          task-definition: task-definition.json
          service: ${{ env.ECS_SERVICE }}
          cluster: ${{ env.ECS_CLUSTER }}
          wait-for-service-stability: true
```

### Lambda Deployment
```yaml
name: Deploy Lambda
on:
  push:
    branches: [main]
    paths:
      - 'src/**'
      - 'requirements.txt'

permissions:
  id-token: write
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/GitHubDeployRole
          aws-region: us-east-1

      - name: Package and deploy
        run: |
          pip install -r requirements.txt -t package/
          cp -r src/* package/
          cd package && zip -r ../function.zip .
          aws lambda update-function-code \
            --function-name my-function \
            --zip-file fileb://function.zip
```

### Multi-Environment Deployment
```yaml
name: Deploy
on:
  push:
    branches: [main, develop]
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to deploy'
        required: true
        type: choice
        options:
          - staging
          - production

permissions:
  id-token: write
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ github.event.inputs.environment || (github.ref == 'refs/heads/main' && 'production' || 'staging') }}
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials (Staging)
        if: github.ref != 'refs/heads/main'
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::111111111111:role/GitHubDeployRole
          aws-region: us-east-1

      - name: Configure AWS credentials (Production)
        if: github.ref == 'refs/heads/main'
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::222222222222:role/GitHubDeployRole
          aws-region: us-east-1

      - name: Deploy
        run: |
          echo "Deploying to ${{ github.event.inputs.environment || 'auto-detected' }}"
          # deployment commands
```

## AWS CodeBuild Integration

### Create CodeBuild Project
```bash
# Create CodeBuild project
aws codebuild create-project \
    --name my-build-project \
    --source '{
        "type": "GITHUB",
        "location": "https://github.com/my-org/my-repo.git",
        "buildspec": "buildspec.yml",
        "auth": {
            "type": "OAUTH"
        }
    }' \
    --artifacts '{
        "type": "S3",
        "location": "my-artifacts-bucket",
        "name": "build-output"
    }' \
    --environment '{
        "type": "LINUX_CONTAINER",
        "image": "aws/codebuild/amazonlinux2-x86_64-standard:5.0",
        "computeType": "BUILD_GENERAL1_SMALL",
        "privilegedMode": true,
        "environmentVariables": [
            {"name": "AWS_DEFAULT_REGION", "value": "us-east-1"},
            {"name": "ECR_REPO", "value": "123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app"}
        ]
    }' \
    --service-role arn:aws:iam::123456789012:role/CodeBuildServiceRole

# Create webhook for GitHub
aws codebuild create-webhook \
    --project-name my-build-project \
    --filter-groups '[[
        {"type": "EVENT", "pattern": "PUSH"},
        {"type": "HEAD_REF", "pattern": "^refs/heads/main$"}
    ]]'
```

### CodeBuild buildspec.yml
```yaml
version: 0.2

env:
  variables:
    AWS_DEFAULT_REGION: us-east-1
  secrets-manager:
    DOCKER_HUB_TOKEN: docker-hub-credentials:token

phases:
  pre_build:
    commands:
      - echo Logging in to Amazon ECR...
      - aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $ECR_REPO
      - COMMIT_HASH=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c 1-7)
      - IMAGE_TAG=${COMMIT_HASH:=latest}

  build:
    commands:
      - echo Build started on `date`
      - docker build -t $ECR_REPO:$IMAGE_TAG .
      - docker tag $ECR_REPO:$IMAGE_TAG $ECR_REPO:latest

  post_build:
    commands:
      - echo Build completed on `date`
      - docker push $ECR_REPO:$IMAGE_TAG
      - docker push $ECR_REPO:latest
      - printf '[{"name":"app","imageUri":"%s"}]' $ECR_REPO:$IMAGE_TAG > imagedefinitions.json

artifacts:
  files:
    - imagedefinitions.json

cache:
  paths:
    - '/root/.docker/**/*'
```

### Manage CodeBuild
```bash
# Start build
aws codebuild start-build \
    --project-name my-build-project \
    --source-version main

# Start build with overrides
aws codebuild start-build \
    --project-name my-build-project \
    --environment-variables-override '[
        {"name": "DEPLOY_ENV", "value": "staging"}
    ]'

# Get build status
aws codebuild batch-get-builds \
    --ids my-build-project:build-id \
    --query 'builds[0].{Status:buildStatus,Phase:currentPhase}'

# List builds
aws codebuild list-builds-for-project \
    --project-name my-build-project \
    --sort-order DESCENDING

# Stop build
aws codebuild stop-build --id my-build-project:build-id

# List projects
aws codebuild list-projects

# Delete project
aws codebuild delete-project --name my-build-project
```

## CodePipeline

### Create Pipeline
```bash
# Create pipeline
aws codepipeline create-pipeline \
    --pipeline file://pipeline.json

# Get pipeline state
aws codepipeline get-pipeline-state \
    --name my-pipeline

# Start pipeline execution
aws codepipeline start-pipeline-execution \
    --name my-pipeline

# List pipelines
aws codepipeline list-pipelines

# Get pipeline
aws codepipeline get-pipeline \
    --name my-pipeline

# Delete pipeline
aws codepipeline delete-pipeline \
    --name my-pipeline
```

**pipeline.json:**
```json
{
    "pipeline": {
        "name": "my-pipeline",
        "roleArn": "arn:aws:iam::123456789012:role/CodePipelineServiceRole",
        "stages": [
            {
                "name": "Source",
                "actions": [
                    {
                        "name": "GitHub",
                        "actionTypeId": {
                            "category": "Source",
                            "owner": "AWS",
                            "provider": "CodeStarSourceConnection",
                            "version": "1"
                        },
                        "configuration": {
                            "ConnectionArn": "arn:aws:codestar-connections:us-east-1:123456789012:connection/abc-123",
                            "FullRepositoryId": "my-org/my-repo",
                            "BranchName": "main"
                        },
                        "outputArtifacts": [{"name": "SourceOutput"}]
                    }
                ]
            },
            {
                "name": "Build",
                "actions": [
                    {
                        "name": "CodeBuild",
                        "actionTypeId": {
                            "category": "Build",
                            "owner": "AWS",
                            "provider": "CodeBuild",
                            "version": "1"
                        },
                        "configuration": {
                            "ProjectName": "my-build-project"
                        },
                        "inputArtifacts": [{"name": "SourceOutput"}],
                        "outputArtifacts": [{"name": "BuildOutput"}]
                    }
                ]
            },
            {
                "name": "Deploy",
                "actions": [
                    {
                        "name": "ECS",
                        "actionTypeId": {
                            "category": "Deploy",
                            "owner": "AWS",
                            "provider": "ECS",
                            "version": "1"
                        },
                        "configuration": {
                            "ClusterName": "my-cluster",
                            "ServiceName": "my-service",
                            "FileName": "imagedefinitions.json"
                        },
                        "inputArtifacts": [{"name": "BuildOutput"}]
                    }
                ]
            }
        ]
    }
}
```

## Useful Queries

```bash
# Get OIDC provider ARN
aws iam list-open-id-connect-providers \
    --query 'OpenIDConnectProviderList[?contains(Arn, `github`)].Arn'

# List roles with GitHub trust
aws iam list-roles \
    --query 'Roles[?contains(AssumeRolePolicyDocument|to_string(@), `github`)].RoleName'

# Get recent CodeBuild builds
aws codebuild list-builds \
    --sort-order DESCENDING \
    --max-items 10

# Get failed builds
aws codebuild batch-get-builds \
    --ids $(aws codebuild list-builds-for-project \
        --project-name my-project \
        --query 'ids[:5]' \
        --output text) \
    --query 'builds[?buildStatus==`FAILED`].{ID:id,Phase:phases[-1].phaseType}'

# Get pipeline execution history
aws codepipeline list-pipeline-executions \
    --pipeline-name my-pipeline \
    --query 'pipelineExecutionSummaries[*].{ID:pipelineExecutionId,Status:status,Time:startTime}'
```

## Best Practices

| Practice | Description |
|:---------|:------------|
| **OIDC** | Use OIDC instead of long-lived access keys |
| **Branch restrictions** | Limit trust policy to specific branches |
| **Environment protection** | Use GitHub environments for approvals |
| **Least privilege** | Grant minimal permissions to deploy role |
| **Audit logging** | Enable CloudTrail for AssumeRoleWithWebIdentity |
| **Session duration** | Set short max-session-duration on roles |
| **Multi-account** | Use separate roles/accounts per environment |
| **Secrets** | Use Secrets Manager, not GitHub secrets for AWS |
| **CodeBuild cache** | Enable caching to speed up builds |
| **Webhook filters** | Filter CodeBuild webhooks to relevant events |