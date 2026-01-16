#!/bin/bash
set -e

# Deploy script for ECS Fargate solution

echo "=== CSV to Kafka ECS Fargate Deployment ==="

# Get AWS account ID and region
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=${AWS_REGION:-us-east-1}

echo "AWS Account: $AWS_ACCOUNT_ID"
echo "AWS Region: $AWS_REGION"

# Deploy infrastructure
echo "Deploying infrastructure with Terraform..."
cd terraform
terraform init
terraform apply -auto-approve
ECR_REPO=$(terraform output -raw ecr_repository_url)
cd ..

echo "ECR Repository: $ECR_REPO"

# Build and push Docker image
echo "Building Docker image..."
cd app
docker build -t csv-to-kafka:latest .

echo "Logging into ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPO

echo "Tagging and pushing image..."
docker tag csv-to-kafka:latest $ECR_REPO:latest
docker push $ECR_REPO:latest

cd ..

echo "=== Deployment Complete ==="
echo "To run the task:"
echo "aws ecs run-task \\"
echo "  --cluster csv-to-kafka-cluster \\"
echo "  --task-definition csv-to-kafka-task \\"
echo "  --launch-type FARGATE \\"
echo "  --network-configuration \"awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx]}\""
