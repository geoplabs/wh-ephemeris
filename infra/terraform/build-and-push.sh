#!/bin/bash

# Build and Push Enhanced Docker Image to ECR
# This script builds the enhanced Dockerfile with integrated ephemeris downloads
# and pushes it to your ECR repository for Terraform deployment

set -e

# Configuration
AWS_ACCOUNT_ID="863518458871"
AWS_REGION="us-east-1"  # NVirginia region for your account
ECR_REPOSITORY="wh-ephemeris"
IMAGE_TAG="prod-latest"
DOCKERFILE_PATH="docker/Dockerfile.enhanced"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Building and Pushing WH-Ephemeris Enhanced Docker Image${NC}"
echo -e "${BLUE}Account: ${AWS_ACCOUNT_ID}${NC}"
echo -e "${BLUE}Region: ${AWS_REGION}${NC}"
echo -e "${BLUE}Repository: ${ECR_REPOSITORY}${NC}"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker and try again.${NC}"
    exit 1
fi

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo -e "${RED}❌ AWS CLI is not configured. Please run 'aws configure' first.${NC}"
    exit 1
fi

# Verify we're using the correct AWS account
CURRENT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
if [ "$CURRENT_ACCOUNT" != "$AWS_ACCOUNT_ID" ]; then
    echo -e "${RED}❌ Wrong AWS account. Expected: ${AWS_ACCOUNT_ID}, Got: ${CURRENT_ACCOUNT}${NC}"
    echo -e "${YELLOW}Please switch to the correct AWS profile or configure credentials for account ${AWS_ACCOUNT_ID}${NC}"
    exit 1
fi

echo -e "${GREEN}✅ AWS Account verified: ${CURRENT_ACCOUNT}${NC}"

# Create ECR repository if it doesn't exist
echo -e "${YELLOW}📦 Checking ECR repository...${NC}"
if ! aws ecr describe-repositories --repository-names ${ECR_REPOSITORY} --region ${AWS_REGION} > /dev/null 2>&1; then
    echo -e "${YELLOW}Creating ECR repository: ${ECR_REPOSITORY}${NC}"
    aws ecr create-repository \
        --repository-name ${ECR_REPOSITORY} \
        --region ${AWS_REGION} \
        --image-scanning-configuration scanOnPush=true \
        --encryption-configuration encryptionType=AES256
    echo -e "${GREEN}✅ ECR repository created${NC}"
else
    echo -e "${GREEN}✅ ECR repository exists${NC}"
fi

# Get ECR login token
echo -e "${YELLOW}🔐 Logging into ECR...${NC}"
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Build the enhanced Docker image
echo -e "${YELLOW}🔨 Building enhanced Docker image with integrated ephemeris...${NC}"
echo -e "${BLUE}This will download Swiss Ephemeris data during build (may take 2-3 minutes)${NC}"

docker build \
    -f ${DOCKERFILE_PATH} \
    -t ${ECR_REPOSITORY}:${IMAGE_TAG} \
    -t ${ECR_REPOSITORY}:$(date +%Y%m%d-%H%M%S) \
    --build-arg BUILDKIT_INLINE_CACHE=1 \
    .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Docker image built successfully${NC}"
else
    echo -e "${RED}❌ Docker build failed${NC}"
    exit 1
fi

# Tag for ECR
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}"
docker tag ${ECR_REPOSITORY}:${IMAGE_TAG} ${ECR_URI}:${IMAGE_TAG}
docker tag ${ECR_REPOSITORY}:${IMAGE_TAG} ${ECR_URI}:$(date +%Y%m%d-%H%M%S)

# Push to ECR
echo -e "${YELLOW}📤 Pushing to ECR...${NC}"
docker push ${ECR_URI}:${IMAGE_TAG}
docker push ${ECR_URI}:$(date +%Y%m%d-%H%M%S)

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Image pushed successfully to ECR${NC}"
else
    echo -e "${RED}❌ Failed to push image to ECR${NC}"
    exit 1
fi

# Update terraform.tfvars with the correct image URI
echo -e "${YELLOW}📝 Updating terraform.tfvars with new image URI...${NC}"
TFVARS_FILE="infra/terraform/terraform.tfvars"
NEW_IMAGE_URI="${ECR_URI}:${IMAGE_TAG}"

# Backup original tfvars
cp ${TFVARS_FILE} ${TFVARS_FILE}.backup

# Update container_image in terraform.tfvars
sed -i.bak "s|container_image = \".*\"|container_image = \"${NEW_IMAGE_URI}\"|g" ${TFVARS_FILE}

echo -e "${GREEN}✅ Updated terraform.tfvars with image: ${NEW_IMAGE_URI}${NC}"

# Show next steps
echo -e "\n${GREEN}🎉 Build and Push Complete!${NC}"
echo -e "${BLUE}Next Steps:${NC}"
echo -e "1. Review updated terraform.tfvars file"
echo -e "2. Run: ${YELLOW}cd infra/terraform${NC}"
echo -e "3. Run: ${YELLOW}terraform plan${NC}"
echo -e "4. Run: ${YELLOW}terraform apply${NC}"
echo -e "\n${BLUE}Image Details:${NC}"
echo -e "Repository: ${ECR_URI}"
echo -e "Tag: ${IMAGE_TAG}"
echo -e "Features: ✅ Swiss Ephemeris Integrated ✅ FastAPI ✅ Production Ready"

# Clean up local images to save space
echo -e "\n${YELLOW}🧹 Cleaning up local images...${NC}"
docker rmi ${ECR_REPOSITORY}:${IMAGE_TAG} || true
docker system prune -f

echo -e "${GREEN}✅ Cleanup complete${NC}"
