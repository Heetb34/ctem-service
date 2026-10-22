#!/usr/bin/env bash
set -euo pipefail
awslocal s3api create-bucket --bucket evidence --region us-east-1
awslocal s3api put-bucket-versioning --bucket evidence --versioning-configuration Status=Enabled
awslocal s3api put-object-lock-configuration \
  --bucket evidence \
  --object-lock-configuration 'ObjectLockEnabled=Enabled,Rule={DefaultRetention={Mode=COMPLIANCE,Days=30}}'
# Block all public access
awslocal s3api put-public-access-block --bucket evidence \
  --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
echo "evidence bucket ready with Object Lock (COMPLIANCE, 30d)"
