#!/bin/bash

# Configuration
BUCKET_NAME="flask-app-453786152561"
REGION="us-east-1"

echo "🚀 Deploying Flask app to S3..."

# Upload static files
echo "📁 Uploading static files..."
aws s3 sync static/ s3://$BUCKET_NAME/static/ --region $REGION

# Upload HTML template (static version for S3)
echo "📄 Uploading HTML template..."
aws s3 cp templates/index-static.html s3://$BUCKET_NAME/index.html --region $REGION

# Upload favicon (optional)
echo "🎨 Uploading favicon..."
aws s3 cp static/favicon.ico s3://$BUCKET_NAME/favicon.ico --region $REGION 2>/dev/null || echo "No favicon found, skipping..."

echo "✅ Deployment complete!"
echo "🌐 Your website is available at:"
echo "   http://$BUCKET_NAME.s3-website-$REGION.amazonaws.com"

# Note: You'll need to replace this with your actual CloudFront distribution ID
# echo "🔄 Creating CloudFront invalidation..."
# aws cloudfront create-invalidation --distribution-id YOUR_DISTRIBUTION_ID --paths "/*"
