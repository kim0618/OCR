#!/bin/bash
# IMDSv2 토큰 먼저 받기
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 60")
PUBLIC_IP=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/public-ipv4)

if [ -z "$PUBLIC_IP" ]; then
  echo "ERROR: failed to get public IP from metadata service"
  exit 1
fi

cat > ~/OCR/mysuit-ocr/.env.local << ENVEOF
BACKEND_URL=http://127.0.0.1:9099
NEXT_PUBLIC_BACKEND_URL=http://${PUBLIC_IP}:9099
ENVEOF

echo "[$(date +'%F %T')] Updated with PUBLIC_IP=${PUBLIC_IP}"
cat ~/OCR/mysuit-ocr/.env.local
