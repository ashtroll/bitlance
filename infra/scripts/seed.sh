#!/bin/bash
set -e

echo "Seeding database with test data..."

# Create test employer
curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"employer@test.com","username":"testemployer","password":"Password123!","role":"employer","full_name":"Test Employer"}' \
  | python3 -m json.tool

# Create test freelancer
curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"freelancer@test.com","username":"testfreelancer","password":"Password123!","role":"freelancer","full_name":"Test Freelancer"}' \
  | python3 -m json.tool

echo "Seed complete."
