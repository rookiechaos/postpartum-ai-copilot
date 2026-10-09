#!/bin/bash
# Postpartum AI Copilot - integration test script (requires running backend + frontend)
# Usage: ./test.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

API_BASE="${API_BASE:-http://localhost:8000}"
FRONTEND_BASE="${FRONTEND_BASE:-http://localhost:3000}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Postpartum AI Copilot - Test Script${NC}"
echo -e "${GREEN}========================================${NC}\n"

echo -e "${YELLOW}Checking backend...${NC}"
if curl -f -s "$API_BASE/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend is running${NC}"
else
    echo -e "${RED}✗ Backend is not running. Start it first:${NC}"
    echo -e "${YELLOW}  cd backend && uvicorn main:app --reload${NC}"
    exit 1
fi

echo -e "${YELLOW}Checking frontend...${NC}"
if curl -f -s "$FRONTEND_BASE" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Frontend is running${NC}"
else
    echo -e "${RED}✗ Frontend is not running. Start it first:${NC}"
    echo -e "${YELLOW}  cd frontend && npm run dev${NC}"
    exit 1
fi

TEST_EMAIL="test_$(date +%s)@example.com"
TEST_PASSWORD="TestPassword123!"

echo -e "\n${YELLOW}Registering test user...${NC}"
curl -s -X POST "$API_BASE/api/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\"}" > /dev/null

echo -e "${YELLOW}Logging in...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "$API_BASE/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\"}")

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || true)

if [ -z "$ACCESS_TOKEN" ]; then
    echo -e "${RED}✗ Login failed — chat/crisis endpoints require JWT${NC}"
    echo "   Response: $LOGIN_RESPONSE"
    exit 1
fi

ME_RESPONSE=$(curl -s "$API_BASE/api/auth/me" -H "Authorization: Bearer $ACCESS_TOKEN")
USER_ID=$(echo "$ME_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('user_id',''))" 2>/dev/null || true)

if [ -z "$USER_ID" ]; then
    echo -e "${RED}✗ Could not resolve user_id from /api/auth/me${NC}"
    exit 1
fi

AUTH_HEADER="Authorization: Bearer $ACCESS_TOKEN"
echo -e "${GREEN}✓ Authenticated${NC}\n"
echo -e "${GREEN}Starting API tests...${NC}\n"

echo -e "${YELLOW}1. Health check...${NC}"
HEALTH_RESPONSE=$(curl -s "$API_BASE/health")
if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    echo -e "${GREEN}   ✓ Health check passed${NC}"
else
    echo -e "${RED}   ✗ Health check failed${NC}"
    exit 1
fi

echo -e "${YELLOW}2. Chat API...${NC}"
CHAT_RESPONSE=$(curl -s -X POST "$API_BASE/api/chat" \
  -H "Content-Type: application/json" \
  -H "$AUTH_HEADER" \
  -d '{"query": "Hello, this is a test"}')

if echo "$CHAT_RESPONSE" | grep -qE '"response"|"task_id"'; then
    echo -e "${GREEN}   ✓ Chat API passed${NC}"
else
    echo -e "${RED}   ✗ Chat API failed${NC}"
    echo "   Response: $CHAT_RESPONSE"
fi

echo -e "${YELLOW}3. Add tracking entry...${NC}"
TRACKING_RESPONSE=$(curl -s -X POST "$API_BASE/api/tracking" \
  -H "Content-Type: application/json" \
  -H "$AUTH_HEADER" \
  -d "{
    \"entry_type\": \"feeding\",
    \"feeding_type\": \"breast\",
    \"duration_minutes\": 20,
    \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
  }")

if echo "$TRACKING_RESPONSE" | grep -q "id"; then
    echo -e "${GREEN}   ✓ Tracking entry created${NC}"
else
    echo -e "${RED}   ✗ Tracking entry failed${NC}"
    echo "   Response: $TRACKING_RESPONSE"
fi

echo -e "${YELLOW}4. Get tracking entries...${NC}"
GET_TRACKING_RESPONSE=$(curl -s "$API_BASE/api/tracking/$USER_ID?days=7" -H "$AUTH_HEADER")
if echo "$GET_TRACKING_RESPONSE" | grep -qE '\[\]|"id"'; then
    echo -e "${GREEN}   ✓ Get tracking entries passed${NC}"
else
    echo -e "${RED}   ✗ Get tracking entries failed${NC}"
fi

echo -e "${YELLOW}5. Tracking summary...${NC}"
SUMMARY_RESPONSE=$(curl -s "$API_BASE/api/tracking/$USER_ID/summary?days=7" -H "$AUTH_HEADER")
if echo "$SUMMARY_RESPONSE" | grep -qE 'patterns|"message"'; then
    echo -e "${GREEN}   ✓ Summary passed${NC}"
else
    echo -e "${YELLOW}   ⚠ Summary returned unexpected response (may be insufficient data)${NC}"
fi

echo -e "${YELLOW}6. Emotional check-in...${NC}"
CHECKIN_RESPONSE=$(curl -s -X POST "$API_BASE/api/emotional-checkin" \
  -H "Content-Type: application/json" \
  -H "$AUTH_HEADER" \
  -d "{\"user_id\": \"$USER_ID\", \"overwhelmed_level\": 5, \"anxiety_level\": 4, \"support_level\": 6}")

if echo "$CHECKIN_RESPONSE" | grep -q "assessment"; then
    echo -e "${GREEN}   ✓ Emotional check-in passed${NC}"
else
    echo -e "${RED}   ✗ Emotional check-in failed${NC}"
fi

echo -e "${YELLOW}7. Crisis mode...${NC}"
CRISIS_RESPONSE=$(curl -s -X POST "$API_BASE/api/crisis" \
  -H "Content-Type: application/json" \
  -H "$AUTH_HEADER" \
  -d '{"query": "Baby won'\''t stop crying", "urgency": "high"}')

if echo "$CRISIS_RESPONSE" | grep -qE '"response"|"task_id"'; then
    echo -e "${GREEN}   ✓ Crisis mode passed${NC}"
else
    echo -e "${RED}   ✗ Crisis mode failed${NC}"
fi

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}All tests completed${NC}"
echo -e "${GREEN}========================================${NC}\n"
echo -e "${YELLOW}Test user: $TEST_EMAIL${NC}\n"
