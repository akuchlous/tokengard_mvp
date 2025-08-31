#!/bin/bash

# AWS Deployment Script for TokenGuard
# This script deploys the Flask app to AWS S3 and CloudFront

set -e  # Exit on any error

# Configuration
BUCKET_NAME="tokengard-app"
REGION="us-east-1"
CLOUDFRONT_DISTRIBUTION_ID=""  # Set this after creating CloudFront distribution

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting AWS deployment for TokenGuard...${NC}"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check AWS credentials
echo -e "${YELLOW}🔐 Checking AWS credentials...${NC}"
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured. Run 'aws configure' first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ AWS credentials verified${NC}"

# Check if bucket exists, create if not
echo -e "${YELLOW}🪣 Checking S3 bucket...${NC}"
if ! aws s3 ls "s3://$BUCKET_NAME" &> /dev/null; then
    echo -e "${YELLOW}📦 Creating S3 bucket: $BUCKET_NAME${NC}"
    aws s3 mb "s3://$BUCKET_NAME" --region "$REGION"
    
    # Configure bucket for static website hosting
    aws s3 website "s3://$BUCKET_NAME" --index-document index.html --error-document error.html
    
    # Set bucket policy for public read access
    aws s3api put-bucket-policy --bucket "$BUCKET_NAME" --policy '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "PublicReadGetObject",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": "arn:aws:s3:::'$BUCKET_NAME'/*"
            }
        ]
    }'
    
    echo -e "${GREEN}✅ S3 bucket created and configured${NC}"
else
    echo -e "${GREEN}✅ S3 bucket already exists${NC}"
fi

# Build the application (for now, just copy static files)
echo -e "${YELLOW}🔨 Building application...${NC}"
mkdir -p build

# Copy static files
cp -r static build/
cp -r templates build/

# Create a simple index.html for S3 hosting
cat > build/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TokenGuard - Secure Authentication System</title>
    <link rel="stylesheet" href="/static/css/main.css">
</head>
<body>
    <div class="hero-section">
        <div class="hero-content">
            <h1 class="hero-title">TokenGuard</h1>
            <p class="hero-subtitle">Secure authentication system</p>
            <div class="hero-buttons">
                <a href="/auth/login" class="btn btn-primary btn-lg">
                    <span class="btn-text">Sign In</span>
                </a>
                <a href="/auth/register" class="btn btn-secondary btn-lg">
                    <span class="btn-text">Sign Up</span>
                </a>
            </div>
        </div>
    </div>
    <script src="/static/js/common.js"></script>
</body>
</html>
EOF

echo -e "${GREEN}✅ Application built${NC}"

# Upload to S3
echo -e "${YELLOW}📤 Uploading to S3...${NC}"
aws s3 sync build/ "s3://$BUCKET_NAME" --delete

echo -e "${GREEN}✅ Files uploaded to S3${NC}"

# Get the website URL
WEBSITE_URL=$(aws s3api get-bucket-website --bucket "$BUCKET_NAME" --query 'WebsiteEndpoint' --output text)
echo -e "${GREEN}🌐 Website URL: http://$WEBSITE_URL${NC}"

# Invalidate CloudFront cache if distribution ID is set
if [ ! -z "$CLOUDFRONT_DISTRIBUTION_ID" ]; then
    echo -e "${YELLOW}🔄 Invalidating CloudFront cache...${NC}"
    aws cloudfront create-invalidation --distribution-id "$CLOUDFRONT_DISTRIBUTION_ID" --paths "/*"
    echo -e "${GREEN}✅ CloudFront cache invalidated${NC}"
else
    echo -e "${YELLOW}⚠️  CloudFront distribution ID not set. Skipping cache invalidation.${NC}"
    echo -e "${YELLOW}   Set CLOUDFRONT_DISTRIBUTION_ID in this script after creating CloudFront distribution.${NC}"
fi

echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo -e "${GREEN}🌐 Your app is now live at: http://$WEBSITE_URL${NC}"
echo -e "${YELLOW}📝 Note: This is a static deployment. For full Flask functionality, consider using:${NC}"
echo -e "${YELLOW}   - AWS Elastic Beanstalk${NC}"
echo -e "${YELLOW}   - AWS ECS/Fargate${NC}"
echo -e "${YELLOW}   - AWS Lambda + API Gateway${NC}"
