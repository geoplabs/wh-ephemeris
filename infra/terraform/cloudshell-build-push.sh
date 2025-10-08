#!/bin/bash

# CloudShell Build and Push Script for WH-Ephemeris
# This script uses AWS CodeBuild to build the Docker image since CloudShell doesn't have Docker

set -e

# Configuration
AWS_ACCOUNT_ID="863518458871"
AWS_REGION="us-east-1"
ECR_REPOSITORY="wh-ephemeris"
IMAGE_TAG="prod-latest"
CODEBUILD_PROJECT="wh-ephemeris-build"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Building WH-Ephemeris Docker Image via AWS CodeBuild${NC}"
echo -e "${BLUE}Account: ${AWS_ACCOUNT_ID}${NC}"
echo -e "${BLUE}Region: ${AWS_REGION}${NC}"

# Verify AWS account
CURRENT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
if [ "$CURRENT_ACCOUNT" != "$AWS_ACCOUNT_ID" ]; then
    echo -e "${RED}❌ Wrong AWS account. Expected: ${AWS_ACCOUNT_ID}, Got: ${CURRENT_ACCOUNT}${NC}"
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

# Create CodeBuild project if it doesn't exist
echo -e "${YELLOW}🏗️ Setting up CodeBuild project...${NC}"

# Create buildspec.yml for CodeBuild
cat > /tmp/buildspec.yml << 'EOF'
version: 0.2
phases:
  pre_build:
    commands:
      - echo Logging in to Amazon ECR...
      - aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com
  build:
    commands:
      - echo Build started on `date`
      - echo Building the Docker image with integrated ephemeris...
      - docker build -f docker/Dockerfile.enhanced -t $IMAGE_REPO_URI:$IMAGE_TAG .
      - docker tag $IMAGE_REPO_URI:$IMAGE_TAG $IMAGE_REPO_URI:$(date +%Y%m%d-%H%M%S)
  post_build:
    commands:
      - echo Build completed on `date`
      - echo Pushing the Docker images...
      - docker push $IMAGE_REPO_URI:$IMAGE_TAG
      - docker push $IMAGE_REPO_URI:$(date +%Y%m%d-%H%M%S)
      - echo Writing image definitions file...
      - printf '[{"name":"app","imageUri":"%s"}]' $IMAGE_REPO_URI:$IMAGE_TAG > imagedefinitions.json
artifacts:
  files:
    - imagedefinitions.json
EOF

# Create CodeBuild service role if it doesn't exist
CODEBUILD_ROLE_NAME="wh-ephemeris-codebuild-role"
echo -e "${YELLOW}🔐 Setting up CodeBuild IAM role...${NC}"

if ! aws iam get-role --role-name ${CODEBUILD_ROLE_NAME} > /dev/null 2>&1; then
    # Create trust policy
    cat > /tmp/codebuild-trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "codebuild.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

    # Create role
    aws iam create-role \
        --role-name ${CODEBUILD_ROLE_NAME} \
        --assume-role-policy-document file:///tmp/codebuild-trust-policy.json

    # Attach policies
    aws iam attach-role-policy \
        --role-name ${CODEBUILD_ROLE_NAME} \
        --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess

    aws iam attach-role-policy \
        --role-name ${CODEBUILD_ROLE_NAME} \
        --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser

    echo -e "${GREEN}✅ CodeBuild role created${NC}"
else
    echo -e "${GREEN}✅ CodeBuild role exists${NC}"
fi

# Get the role ARN
CODEBUILD_ROLE_ARN=$(aws iam get-role --role-name ${CODEBUILD_ROLE_NAME} --query 'Role.Arn' --output text)

# Create or update CodeBuild project
echo -e "${YELLOW}🏗️ Creating CodeBuild project...${NC}"

# Check if project exists
if aws codebuild batch-get-projects --names ${CODEBUILD_PROJECT} > /dev/null 2>&1; then
    echo -e "${YELLOW}Updating existing CodeBuild project...${NC}"
    aws codebuild update-project \
        --name ${CODEBUILD_PROJECT} \
        --source type=NO_SOURCE,buildspec=/tmp/buildspec.yml \
        --artifacts type=NO_ARTIFACTS \
        --environment type=LINUX_CONTAINER,image=aws/codebuild/standard:7.0,computeType=BUILD_GENERAL1_MEDIUM,privilegedMode=true \
        --service-role ${CODEBUILD_ROLE_ARN}
else
    echo -e "${YELLOW}Creating new CodeBuild project...${NC}"
    aws codebuild create-project \
        --name ${CODEBUILD_PROJECT} \
        --source type=NO_SOURCE,buildspec="$(cat /tmp/buildspec.yml)" \
        --artifacts type=NO_ARTIFACTS \
        --environment type=LINUX_CONTAINER,image=aws/codebuild/standard:7.0,computeType=BUILD_GENERAL1_MEDIUM,privilegedMode=true \
        --service-role ${CODEBUILD_ROLE_ARN}
fi

echo -e "${GREEN}✅ CodeBuild project ready${NC}"

# Clone the repository to CodeBuild's workspace (simulate source)
echo -e "${YELLOW}📥 Preparing source code...${NC}"

# Create a zip file of the current directory
zip -r /tmp/wh-ephemeris-source.zip . -x "*.git*" "node_modules/*" "*.pyc" "__pycache__/*"

# Upload to S3 for CodeBuild
S3_BUCKET="wh-ephemeris-codebuild-${AWS_ACCOUNT_ID}"
aws s3 mb s3://${S3_BUCKET} 2>/dev/null || true
aws s3 cp /tmp/wh-ephemeris-source.zip s3://${S3_BUCKET}/source.zip

# Update CodeBuild project to use S3 source
aws codebuild update-project \
    --name ${CODEBUILD_PROJECT} \
    --source type=S3,location=${S3_BUCKET}/source.zip,buildspec="$(cat /tmp/buildspec.yml)"

echo -e "${GREEN}✅ Source code uploaded${NC}"

# Start the build
echo -e "${YELLOW}🔨 Starting Docker build...${NC}"
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}"

BUILD_ID=$(aws codebuild start-build \
    --project-name ${CODEBUILD_PROJECT} \
    --environment-variables-override \
        name=AWS_DEFAULT_REGION,value=${AWS_REGION} \
        name=AWS_ACCOUNT_ID,value=${AWS_ACCOUNT_ID} \
        name=IMAGE_REPO_URI,value=${ECR_URI} \
        name=IMAGE_TAG,value=${IMAGE_TAG} \
    --query 'build.id' --output text)

echo -e "${BLUE}Build ID: ${BUILD_ID}${NC}"
echo -e "${YELLOW}⏳ Waiting for build to complete...${NC}"

# Wait for build to complete
while true; do
    BUILD_STATUS=$(aws codebuild batch-get-builds --ids ${BUILD_ID} --query 'builds[0].buildStatus' --output text)
    
    if [ "$BUILD_STATUS" = "SUCCEEDED" ]; then
        echo -e "${GREEN}✅ Build completed successfully!${NC}"
        break
    elif [ "$BUILD_STATUS" = "FAILED" ] || [ "$BUILD_STATUS" = "FAULT" ] || [ "$BUILD_STATUS" = "STOPPED" ] || [ "$BUILD_STATUS" = "TIMED_OUT" ]; then
        echo -e "${RED}❌ Build failed with status: ${BUILD_STATUS}${NC}"
        echo -e "${YELLOW}Check CloudWatch logs for details:${NC}"
        echo -e "https://console.aws.amazon.com/codesuite/codebuild/projects/${CODEBUILD_PROJECT}/history"
        exit 1
    else
        echo -e "${BLUE}Build status: ${BUILD_STATUS}... waiting${NC}"
        sleep 30
    fi
done

# Update terraform.tfvars
echo -e "${YELLOW}📝 Updating terraform.tfvars...${NC}"
TFVARS_FILE="infra/terraform/terraform.tfvars"
NEW_IMAGE_URI="${ECR_URI}:${IMAGE_TAG}"

# Backup and update
cp ${TFVARS_FILE} ${TFVARS_FILE}.backup
sed -i "s|container_image = \".*\"|container_image = \"${NEW_IMAGE_URI}\"|g" ${TFVARS_FILE}

echo -e "${GREEN}✅ Updated terraform.tfvars with image: ${NEW_IMAGE_URI}${NC}"

# Cleanup
rm -f /tmp/buildspec.yml /tmp/codebuild-trust-policy.json /tmp/wh-ephemeris-source.zip

echo -e "\n${GREEN}🎉 Build and Push Complete!${NC}"
echo -e "${BLUE}Next Steps:${NC}"
echo -e "1. Review updated terraform.tfvars file"
echo -e "2. Run: ${YELLOW}terraform plan${NC}"
echo -e "3. Run: ${YELLOW}terraform apply${NC}"
echo -e "\n${BLUE}Image Details:${NC}"
echo -e "Repository: ${ECR_URI}"
echo -e "Tag: ${IMAGE_TAG}"
echo -e "Features: ✅ Swiss Ephemeris Integrated ✅ FastAPI ✅ Production Ready"

