#!/bin/bash
# OpenFilter QA Pipeline - Navigation Script
# This script navigates to the correct project directory and runs the QA pipeline

set -e

echo "🚀 OpenFilter QA Pipeline"
echo "========================="
echo "📂 Navigating to project directory..."

# Check if we need to go into the nested directory
if [ -d "PlainsightAI-takehome" ]; then
    echo "🔄 Found nested project directory, changing to PlainsightAI-takehome/"
    cd PlainsightAI-takehome
fi

# Now check if we're in the correct location
if [ ! -d "qa_tests" ]; then
    echo "❌ Error: qa_tests directory not found!"
    echo "Current directory: $(pwd)"
    echo "Available directories:"
    ls -la
    exit 1
fi

echo "✅ Found qa_tests directory"
echo "🔄 Changing to qa_tests directory..."
cd qa_tests

echo "🐍 Running QA pipeline..."
echo ""

# Run the Python QA pipeline
python run_qa_pipeline.py

echo ""
echo "✅ QA Pipeline execution complete!"
echo "📁 You can find the report in: $(pwd)/allure-report/"
