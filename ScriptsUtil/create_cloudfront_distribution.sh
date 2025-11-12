#!/bin/bash
set -e

echo "Creating CloudFront distribution for Streamlit Dashboard..."

# --- Variables ---
ALB_DNS_NAME="$1"
if [ -z "$ALB_DNS_NAME" ]; then
    echo "Usage: $0 <ALB_DNS_NAME>"
    echo "Get ALB DNS with: aws elbv2 describe-load-balancers --names streamlit-alb --query 'LoadBalancers[0].DNSName' --output text --region us-east-1"
    exit 1
fi

REGION="us-east-1"
DISTRIBUTION_NAME="streamlit-dashboard-cloudfront"

echo "Using ALB DNS: $ALB_DNS_NAME"

# --- 1. Create CloudFront Distribution ---
echo "1. Creating CloudFront distribution..."

DISTRIBUTION_CONFIG=$(cat <<EOF
{
    "CallerReference": "streamlit-dashboard-$(date +%s)",
    "Comment": "CloudFront distribution for Streamlit Dashboard EPMAPS POC",
    "DefaultCacheBehavior": {
        "TargetOriginId": "streamlit-alb-origin",
        "ViewerProtocolPolicy": "redirect-to-https",
        "AllowedMethods": {
            "Quantity": 7,
            "Items": ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"],
            "CachedMethods": {
                "Quantity": 2,
                "Items": ["GET", "HEAD"]
            }
        },
        "ForwardedValues": {
            "QueryString": true,
            "Cookies": {
                "Forward": "all"
            },
            "Headers": {
                "Quantity": 8,
                "Items": [
                    "Authorization",
                    "CloudFront-Forwarded-Proto",
                    "CloudFront-Is-Desktop-Viewer",
                    "CloudFront-Is-Mobile-Viewer",
                    "CloudFront-Is-Tablet-Viewer",
                    "CloudFront-Viewer-Country",
                    "Host",
                    "User-Agent"
                ]
            }
        },
        "TrustedSigners": {
            "Enabled": false,
            "Quantity": 0
        },
        "MinTTL": 0,
        "DefaultTTL": 0,
        "MaxTTL": 0,
        "Compress": true
    },
    "CacheBehaviors": {
        "Quantity": 2,
        "Items": [
            {
                "PathPattern": "/_stcore/*",
                "TargetOriginId": "streamlit-alb-origin",
                "ViewerProtocolPolicy": "redirect-to-https",
                "AllowedMethods": {
                    "Quantity": 7,
                    "Items": ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"],
                    "CachedMethods": {
                        "Quantity": 2,
                        "Items": ["GET", "HEAD"]
                    }
                },
                "ForwardedValues": {
                    "QueryString": true,
                    "Cookies": {
                        "Forward": "all"
                    },
                    "Headers": {
                        "Quantity": 1,
                        "Items": ["*"]
                    }
                },
                "TrustedSigners": {
                    "Enabled": false,
                    "Quantity": 0
                },
                "MinTTL": 0,
                "DefaultTTL": 0,
                "MaxTTL": 0
            },
            {
                "PathPattern": "/stream",
                "TargetOriginId": "streamlit-alb-origin",
                "ViewerProtocolPolicy": "redirect-to-https",
                "AllowedMethods": {
                    "Quantity": 7,
                    "Items": ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"],
                    "CachedMethods": {
                        "Quantity": 2,
                        "Items": ["GET", "HEAD"]
                    }
                },
                "ForwardedValues": {
                    "QueryString": true,
                    "Cookies": {
                        "Forward": "all"
                    },
                    "Headers": {
                        "Quantity": 1,
                        "Items": ["*"]
                    }
                },
                "TrustedSigners": {
                    "Enabled": false,
                    "Quantity": 0
                },
                "MinTTL": 0,
                "DefaultTTL": 0,
                "MaxTTL": 0
            }
        ]
    },
    "Origins": {
        "Quantity": 1,
        "Items": [
            {
                "Id": "streamlit-alb-origin",
                "DomainName": "$ALB_DNS_NAME",
                "CustomOriginConfig": {
                    "HTTPPort": 80,
                    "HTTPSPort": 443,
                    "OriginProtocolPolicy": "http-only",
                    "OriginSslProtocols": {
                        "Quantity": 3,
                        "Items": ["TLSv1", "TLSv1.1", "TLSv1.2"]
                    },
                    "OriginReadTimeout": 60,
                    "OriginKeepaliveTimeout": 5
                }
            }
        ]
    },
    "Enabled": true,
    "PriceClass": "PriceClass_100",
    "HttpVersion": "http2",
    "IsIPV6Enabled": true,
    "WebACLId": ""
}
EOF
)

# Create the distribution
DISTRIBUTION_ID=$(aws cloudfront create-distribution \
    --distribution-config "$DISTRIBUTION_CONFIG" \
    --query 'Distribution.Id' \
    --output text \
    --region $REGION)

echo "  CloudFront Distribution ID: $DISTRIBUTION_ID"

# --- 2. Wait for deployment ---
echo "2. Waiting for CloudFront distribution to deploy (this may take 10-15 minutes)..."
aws cloudfront wait distribution-deployed \
    --id $DISTRIBUTION_ID \
    --region $REGION

# --- 3. Get CloudFront domain name ---
CLOUDFRONT_DOMAIN=$(aws cloudfront get-distribution \
    --id $DISTRIBUTION_ID \
    --query 'Distribution.DomainName' \
    --output text \
    --region $REGION)

echo "=== CloudFront Distribution Created Successfully ==="
echo "Distribution ID: $DISTRIBUTION_ID"
echo "CloudFront Domain: $CLOUDFRONT_DOMAIN"
echo "Dashboard URL: https://$CLOUDFRONT_DOMAIN"
echo ""
echo "Note: The distribution may take up to 15 minutes to fully propagate globally."
echo "You can check status with: aws cloudfront get-distribution --id $DISTRIBUTION_ID --query 'Distribution.Status' --output text"