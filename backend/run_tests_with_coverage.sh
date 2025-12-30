#!/bin/bash
# Run backend tests with coverage reporting
# Usage: ./run_tests_with_coverage.sh [options]
#
# Options:
#   --no-cov          Run tests without coverage
#   --integration     Run only integration tests
#   --unit            Run only unit tests
#   --html-only       Generate only HTML report (no terminal output)
#   --open            Open HTML report in browser after running

set -e

# Color output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Backend Test Suite with Coverage ===${NC}\n"

# Default options
COV_ARGS="--cov=. --cov-report=html --cov-report=term-missing --cov-report=json --cov-config=.coveragerc"
TEST_ARGS=""
OPEN_REPORT=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-cov)
            COV_ARGS=""
            echo -e "${YELLOW}Running without coverage${NC}"
            shift
            ;;
        --integration)
            TEST_ARGS="-m integration"
            echo -e "${YELLOW}Running integration tests only${NC}"
            shift
            ;;
        --unit)
            TEST_ARGS="-m unit"
            echo -e "${YELLOW}Running unit tests only${NC}"
            shift
            ;;
        --html-only)
            COV_ARGS="--cov=. --cov-report=html --cov-config=.coveragerc"
            echo -e "${YELLOW}Generating HTML report only${NC}"
            shift
            ;;
        --open)
            OPEN_REPORT=true
            shift
            ;;
        *)
            echo -e "${YELLOW}Unknown option: $1${NC}"
            shift
            ;;
    esac
done

# Run tests
echo -e "${BLUE}Running tests...${NC}\n"
python -m pytest $COV_ARGS $TEST_ARGS

# Check if coverage reports were generated
if [[ -n "$COV_ARGS" ]]; then
    echo -e "\n${GREEN}✓ Tests completed!${NC}\n"

    # Display coverage summary
    if [ -f "coverage.json" ]; then
        echo -e "${BLUE}Coverage Summary:${NC}"
        python -c "
import json
with open('coverage.json') as f:
    data = json.load(f)
    total_cov = data['totals']['percent_covered']
    print(f'  Total Coverage: {total_cov:.2f}%')
    if total_cov >= 90:
        print('  Status: ✓ Excellent (>= 90%)')
    elif total_cov >= 80:
        print('  Status: ✓ Good (>= 80%)')
    elif total_cov >= 70:
        print('  Status: ⚠ Fair (>= 70%)')
    else:
        print('  Status: ✗ Needs Improvement (< 70%)')
"
        echo ""
    fi

    # Show report locations
    echo -e "${BLUE}Coverage Reports Generated:${NC}"
    echo "  📊 HTML Report: htmlcov/index.html"
    echo "  📄 JSON Report: coverage.json"
    echo ""

    # Open HTML report in browser if requested
    if [ "$OPEN_REPORT" = true ]; then
        echo -e "${GREEN}Opening HTML coverage report...${NC}"
        if command -v xdg-open > /dev/null; then
            xdg-open htmlcov/index.html
        elif command -v open > /dev/null; then
            open htmlcov/index.html
        else
            echo -e "${YELLOW}Could not open browser automatically. Please open htmlcov/index.html manually.${NC}"
        fi
    else
        echo -e "${BLUE}Tip:${NC} Run with --open to automatically open the HTML report"
    fi
else
    echo -e "\n${GREEN}✓ Tests completed (without coverage)!${NC}\n"
fi
