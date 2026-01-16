#!/bin/bash
set -e

# Deploy script for AWS Batch solution

echo "=== CSV to Kafka AWS Batch Deployment ==="

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=${AWS_REGION:-us-east-1}

echo "AWS Account: $AWS_ACCOUNT_ID"
echo "AWS Region: $AWS_REGION"

# Deploy infrastructure
echo "Deploying infrastructure..."
cd terraform
terraform init
terraform apply -auto-approve
ECR_REPO=$(terraform output -raw ecr_repository_url)
cd ..

# Build and push Docker image
echo "Building Docker image..."
cd app
docker build -t csv-to-kafka-batch:latest .

echo "Pushing to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPO
docker tag csv-to-kafka-batch:latest $ECR_REPO:latest
docker push $ECR_REPO:latest

cd ..

echo "=== Deployment Complete ==="
echo "Submit job:"
echo "aws batch submit-job --job-name csv-kafka-job --job-queue csv-kafka-job-queue --job-definition csv-kafka-job-def"
