#!/bin/bash

# Test script for /v1/forecasts/yearly/forecast endpoint
# Prerequisites:
#   1. Server running on port 8081
#   2. OPENAI_API_KEY set in .env or environment
#   3. test_yearly_forecast_story.json in current directory

echo "Testing /v1/forecasts/yearly/forecast endpoint..."
echo "=================================================="
echo ""

# Check if server is running
if ! curl -s http://localhost:8081/health > /dev/null 2>&1; then
    echo "❌ Server is not running on port 8081"
    echo "Start it with: python -m uvicorn api.app:app --reload --port 8081"
    exit 1
fi

echo "✅ Server is running"
echo ""

# Make the request
echo "Sending request (this may take 30-60 seconds for LLM processing)..."
echo ""

curl -X POST http://localhost:8081/v1/forecasts/yearly/forecast \
  -H "Content-Type: application/json" \
  -d @test_yearly_forecast_story.json \
  -w "\n\nHTTP Status: %{http_code}\nTotal Time: %{time_total}s\n" \
  -o response_yearly_story.json

echo ""
echo "=================================================="
echo "Response saved to: response_yearly_story.json"
echo ""

# Check if successful
if [ -f response_yearly_story.json ]; then
    # Check for error in response
    if grep -q "detail" response_yearly_story.json; then
        echo "❌ Request failed. Error:"
        cat response_yearly_story.json | python -m json.tool 2>/dev/null || cat response_yearly_story.json
    else
        echo "✅ Request successful!"
        echo ""
        echo "Response structure:"
        echo "  - report.meta"
        echo "  - report.year_at_glance"
        echo "  - report.eclipses_and_lunations"
        echo "  - report.months (12 sections)"
        echo "  - report.appendix_all_events"
        echo "  - report.glossary"
        echo "  - report.interpretation_index"
        echo "  - pdf_download_url"
        echo ""
        
        # Extract PDF URL
        PDF_URL=$(cat response_yearly_story.json | python -c "import json, sys; print(json.load(sys.stdin).get('pdf_download_url', 'N/A'))" 2>/dev/null)
        if [ "$PDF_URL" != "N/A" ]; then
            echo "📄 PDF available at: $PDF_URL"
        fi
    fi
fi

echo ""
echo "=================================================="
echo "To view the full response:"
echo "  cat response_yearly_story.json | python -m json.tool | less"

