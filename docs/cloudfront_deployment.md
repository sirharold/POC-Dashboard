# CloudFront Deployment Guide

## Overview
This guide explains how to deploy the Streamlit Dashboard EPMAPS POC through AWS CloudFront for global distribution and improved performance.

## Prerequisites
- Application already deployed on AWS Fargate with ALB (use `deploy_fargate.sh`)
- AWS CLI configured with appropriate permissions
- CloudFront distribution creation permissions

## Deployment Steps

### 1. Deploy Application to Fargate (if not done)
```bash
cd ScriptsUtil
./deploy_fargate.sh
```

### 2. Get ALB DNS Name
```bash
ALB_DNS=$(aws elbv2 describe-load-balancers --names streamlit-alb --query 'LoadBalancers[0].DNSName' --output text --region us-east-1)
echo "ALB DNS: $ALB_DNS"
```

### 3. Create CloudFront Distribution
```bash
cd ScriptsUtil
./create_cloudfront_distribution.sh $ALB_DNS
```

This script will:
- Create a CloudFront distribution pointing to your ALB
- Configure appropriate cache behaviors for Streamlit
- Set up HTTP to HTTPS redirect
- Configure proper headers forwarding
- Wait for deployment completion (10-15 minutes)

### 4. Access Application
After deployment completes, access your dashboard via:
```
https://YOUR_CLOUDFRONT_DOMAIN.cloudfront.net
```

## CloudFront Configuration Details

### Cache Behaviors
1. **Default Behavior**: Minimal caching (TTL=0) for dynamic content
2. **/_stcore/***: Streamlit core files with all headers forwarded
3. **/stream**: WebSocket fallback endpoints

### Headers Forwarded
- Authorization
- CloudFront-Forwarded-Proto
- CloudFront-Is-*-Viewer
- CloudFront-Viewer-Country
- Host
- User-Agent

### Security Configuration
- HTTPS redirect enabled
- CORS disabled for CloudFront compatibility
- XSRF protection disabled
- All HTTP methods allowed (GET, POST, PUT, DELETE, etc.)

## WebSocket Compatibility

### Current Behavior
- Streamlit uses WebSockets for real-time updates
- CloudFront blocks WebSockets by default
- Application includes fallback to HTTP polling

### Auto-Refresh
- `st.fragment(run_every=30)` provides 30-second auto-refresh
- Falls back to HTTP requests when WebSockets unavailable
- No impact on core functionality

## Monitoring and Troubleshooting

### Check Distribution Status
```bash
aws cloudfront get-distribution --id YOUR_DISTRIBUTION_ID --query 'Distribution.Status' --output text
```

### Common Issues
1. **502 Bad Gateway**: Check ALB health checks and security groups
2. **Slow loading**: Normal during initial CloudFront propagation
3. **Auto-refresh not working**: Expected with CloudFront, manual refresh works

### CloudWatch Logs
Monitor application logs in CloudWatch:
```
Log Group: /ecs/streamlit-dashboard-task
```

### Performance Testing
```bash
# Test direct ALB access
curl -I http://$ALB_DNS

# Test CloudFront access
curl -I https://YOUR_CLOUDFRONT_DOMAIN.cloudfront.net
```

## Cost Considerations
- CloudFront PriceClass_100 (US, Canada, Europe)
- Minimal data transfer costs for dashboard usage
- No additional ALB charges

## Security Notes
- HTTPS enforced for all external access
- Internal ALB communication remains HTTP
- No sensitive data cached by CloudFront
- Headers properly forwarded for AWS authentication

## Rollback Procedure
If issues occur:
1. Direct ALB access remains available
2. Delete CloudFront distribution if needed:
```bash
aws cloudfront delete-distribution --id YOUR_DISTRIBUTION_ID --if-match ETAG
```

## Next Steps
- Monitor performance and costs
- Consider custom domain with Route 53
- Implement WAF rules if needed
- Add CloudWatch alarms for distribution health