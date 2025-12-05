#!/usr/bin/env python3
"""
OpenAPI Agent Example Usage Script

This script demonstrates how to use the LangChain-based OpenAPI Agent to:
1. Parse OpenAPI 3.0.0 API documentation
2. Generate test cases
3. Execute tests
4. Analyze results

Usage:
    python openapi_agent_example.py --url <openapi_url> [--config <config_file>]
    python openapi_agent_example.py --file <openapi_file> [--config <config_file>]
    python openapi_agent_example.py --workflow --url <openapi_url> [--config <config_file>]
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add the parent directory to the path to import our modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from utils.smart_auto.api_agent_integration import (
    create_openapi_agent,
    test_api_from_openapi
)
from utils.smart_auto.openapi_parser_tool import ParsedAPIInfo
from utils.smart_auto.test_case_generator_tool import GeneratedTestSuite
from utils.smart_auto.test_executor_tool import TestSuiteExecutionResult, TestAnalysisResult


def load_config(config_path: str = None) -> dict:
    """Load configuration from YAML file."""
    if config_path is None:
        # Default config path
        config_path = Path(__file__).parent / "openapi_agent_config.yaml"
    
    try:
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Extract the relevant configuration values
        openai_config = config.get('openai', {})
        
        return {
            'openai_api_key': openai_config.get('api_key', ''),
            'openai_model': openai_config.get('model', 'gpt-3.5-turbo'),
            'temperature': openai_config.get('temperature', 0.1),
            'base_url': openai_config.get('base_url', None),
            'verbose': config.get('logging', {}).get('level') == 'DEBUG'
        }
    except Exception as e:
        print(f"Warning: Could not load config from {config_path}: {e}")
        return {}


def print_parsed_api(api_info):
    """Print parsed API information in a readable format."""
    print("\n" + "=" * 50)
    print("PARSED OPENAPI API INFORMATION")
    print("=" * 50)
    print(f"API Title: {api_info.get('title', 'Unknown')}")
    print(f"API Version: {api_info.get('version', 'Unknown')}")
    print(f"Base URL: {api_info.get('base_url', 'Unknown')}")
    print(f"Description: {api_info.get('description', 'No description')}")
    print(f"Total Endpoints: {len(api_info.get('endpoints', []))}")
    
    print("\nEndpoints:")
    for i, endpoint in enumerate(api_info.get('endpoints', [])[:10], 1):  # Show first 10
        print(f"  {i}. {endpoint.get('method', 'Unknown')} {endpoint.get('path', 'Unknown')} - {endpoint.get('summary', 'No summary')}")
    
    if len(api_info.get('endpoints', [])) > 10:
        print(f"  ... and {len(api_info.get('endpoints', [])) - 10} more endpoints")


def print_test_suite(test_suite):
    """Print generated test suite in a readable format."""
    print("\n" + "=" * 50)
    print("GENERATED TEST SUITE")
    print("=" * 50)
    
    if not test_suite:
        print("No test suite available.")
        return
    
    # Handle the case where test_suite contains multiple test suites
    if "test_suites" in test_suite:
        test_suites = test_suite["test_suites"]
        summary = test_suite.get("summary", {})
        
        print(f"Total Test Suites: {len(test_suites)}")
        
        # Print summary if available
        if summary:
            print(f"Summary: {summary}")
        
        # Print first few test suites as examples
        for i, suite in enumerate(test_suites[:3]):
            print(f"\nTest Suite {i+1}:")
            print(f"  Name: {suite.get('name', 'Unknown')}")
            print(f"  Description: {suite.get('description', 'No description')}")
            print(f"  Test Cases: {len(suite.get('test_cases', []))}")
            
            # Print first few test cases as examples
            test_cases = suite.get('test_cases', [])
            if test_cases:
                print("  Sample Test Cases:")
                for j, test_case in enumerate(test_cases[:2]):
                    print(f"    {j+1}. {test_case.get('name', 'Unnamed test')}")
                    print(f"       Method: {test_case.get('method', 'Unknown')}")
                    print(f"       Path: {test_case.get('path', 'Unknown')}")
        
        if len(test_suites) > 3:
            print(f"\n... and {len(test_suites) - 3} more test suites")
        
        # Calculate total test cases across all suites
        total_test_cases = sum(len(suite.get('test_cases', [])) for suite in test_suites)
        print(f"\nTotal Test Cases Across All Suites: {total_test_cases}")
        return
    
    # Handle the case where test_suite is a single test suite
    print(f"Test Suite Name: {test_suite.get('name', 'Unknown')}")
    print(f"Description: {test_suite.get('description', 'No description')}")
    print(f"Total Test Cases: {len(test_suite.get('test_cases', []))}")
    
    print("\nTest Cases:")
    for i, test_case in enumerate(test_suite.get('test_cases', [])[:10], 1):  # Show first 10
        print(f"  {i}. {test_case.get('name', 'Unknown')} - {test_case.get('description', 'No description')}")
        print(f"     Method: {test_case.get('method', 'Unknown')}")
        print(f"     Path: {test_case.get('path', 'Unknown')}")
        print(f"     Test Type: {test_case.get('test_type', 'Unknown')}")
    
    if len(test_suite.get('test_cases', [])) > 10:
        print(f"  ... and {len(test_suite.get('test_cases', [])) - 10} more test cases")


def print_test_results(execution_result):
    """Print test execution results in a readable format."""
    print("\n" + "=" * 50)
    print("TEST EXECUTION RESULTS")
    print("=" * 50)
    
    if not execution_result:
        print("No execution results available.")
        return
    
    # Handle the case where execution_result contains test_results and execution_results
    if "test_results" in execution_result and "execution_results" in execution_result:
        test_results = execution_result["test_results"]
        execution_results = execution_result["execution_results"]
        
        # Calculate totals
        total_tests = len(test_results)
        passed_tests = sum(1 for r in test_results if r.get("status") == "passed")
        failed_tests = sum(1 for r in test_results if r.get("status") == "failed")
        error_tests = sum(1 for r in test_results if r.get("status") == "error")
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Errors: {error_tests}")
        
        if total_tests > 0:
            print(f"Success Rate: {passed_tests/total_tests:.2%}")
        else:
            print("Success Rate: 0.00%")
        
        # Print summary for each test suite
        print("\nTest Suite Summaries:")
        for i, result in enumerate(execution_results):
            suite_name = result.get("suite_name", f"Suite {i+1}")
            suite_passed = result.get("passed_tests", 0)
            suite_total = result.get("total_tests", 0)
            print(f"  {suite_name}: {suite_passed}/{suite_total} tests passed")
        
        # Print first few test results as examples
        if test_results:
            print("\nSample Test Results:")
            for i, result in enumerate(test_results[:5]):
                test_name = result.get("test_name", "Unnamed test")
                status = result.get("status", "unknown")
                method = result.get("method", "Unknown")
                url = result.get("url", "Unknown")
                exec_time = result.get("execution_time", 0)
                
                print(f"  {i+1}. {test_name}")
                print(f"     Status: {status.upper()}")
                print(f"     Method: {method}")
                print(f"     URL: {url}")
                print(f"     Execution Time: {exec_time:.3f}s")
                
                if status == "failed" or status == "error":
                    error_msg = result.get("error_message", "No error message")
                    print(f"     Error: {error_msg}")
        
        if len(test_results) > 5:
            print(f"\n... and {len(test_results) - 5} more test results")
        
        return
    
    # Handle the case where execution_result is a single test suite result
    total_tests = execution_result.get('total_tests', 0)
    passed_tests = execution_result.get('passed_tests', 0)
    failed_tests = execution_result.get('failed_tests', 0)
    error_tests = execution_result.get('error_tests', 0)
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Errors: {error_tests}")
    
    if total_tests > 0:
        print(f"Success Rate: {passed_tests/total_tests:.2%}")
    else:
        print("Success Rate: 0.00%")
    
    # Print first few test results as examples
    test_results = execution_result.get('test_results', [])
    if test_results:
        print("\nSample Test Results:")
        for i, result in enumerate(test_results[:5]):
            test_name = result.get("test_name", "Unnamed test")
            status = result.get("status", "unknown")
            method = result.get("method", "Unknown")
            url = result.get("url", "Unknown")
            exec_time = result.get("execution_time", 0)
            
            print(f"  {i+1}. {test_name}")
            print(f"     Status: {status.upper()}")
            print(f"     Method: {method}")
            print(f"     URL: {url}")
            print(f"     Execution Time: {exec_time:.3f}s")
            
            if status == "failed" or status == "error":
                error_msg = result.get("error_message", "No error message")
                print(f"     Error: {error_msg}")
        
        if len(test_results) > 5:
            print(f"\n... and {len(test_results) - 5} more test results")


def print_analysis_results(analysis_results):
    """Print test analysis results in a readable format."""
    print("\n" + "=" * 50)
    print("TEST ANALYSIS RESULTS")
    print("=" * 50)
    
    if not analysis_results:
        print("No analysis results available.")
        return
    
    # Basic analysis
    basic = analysis_results.get('basic', {})
    if basic:
        print("Basic Analysis:")
        print(f"  Total Tests: {basic.get('total_tests', 0)}")
        print(f"  Passed Tests: {basic.get('passed_tests', 0)}")
        print(f"  Failed Tests: {basic.get('failed_tests', 0)}")
        print(f"  Error Tests: {basic.get('error_tests', 0)}")
        print(f"  Success Rate: {basic.get('success_rate', 0):.2%}")
    
    # Performance analysis
    performance = analysis_results.get('performance', {})
    if performance:
        print("\nPerformance Analysis:")
        print(f"  Average Response Time: {performance.get('avg_response_time', 0):.2f} seconds")
        print(f"  Max Response Time: {performance.get('max_response_time', 0):.2f} seconds")
        print(f"  Min Response Time: {performance.get('min_response_time', 0):.2f} seconds")
        print(f"  Average Response Size: {performance.get('avg_response_size', 0)} bytes")
        
        # Show performance issues if any
        performance_issues = performance.get('performance_issues', [])
        if performance_issues:
            print("\n  Performance Issues:")
            for issue in performance_issues:
                print(f"    - {issue.get('description', 'Unknown issue')}")
    
    # Security analysis
    security = analysis_results.get('security', {})
    if security:
        print("\nSecurity Analysis:")
        print(f"  Security Score: {security.get('security_score', 0)}/100")
        
        security_issues = security.get('security_issues', [])
        if security_issues:
            print("\n  Security Issues:")
            for issue in security_issues:
                severity = issue.get('severity', 'unknown')
                description = issue.get('description', 'Unknown issue')
                print(f"    - [{severity.upper()}] {description}")
        else:
            print("  No security issues detected.")
    
    # Recommendations
    recommendations = analysis_results.get('recommendations', [])
    if recommendations:
        print("\nRecommendations:")
        for i, recommendation in enumerate(recommendations, 1):
            print(f"  {i}. {recommendation}")


def main():
    """Main function to run the OpenAPI Agent example."""
    parser = argparse.ArgumentParser(description="OpenAPI Agent Example Usage")
    parser.add_argument("--url", help="URL of the OpenAPI 3.0.0 API documentation")
    parser.add_argument("--file", help="Path to an OpenAPI 3.0.0 API documentation file")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--workflow", action="store_true", 
                        help="Run the complete workflow (parse, generate, execute, analyze)")
    parser.add_argument("--output", help="Output file for saving results")
    
    args = parser.parse_args()
    
    if not args.url and not args.file:
        print("Error: Either --url or --file must be specified")
        parser.print_help()
        return 1
    
    # Load configuration
    config = load_config(args.config)
    
    # Create OpenAPI Agent
    agent = create_openapi_agent(
        openai_api_key=config.get("openai_api_key", ""),
        openai_model=config.get("openai_model", "gpt-3.5-turbo"),
        temperature=config.get("temperature", 0.1),
        verbose=config.get("verbose", True),
        base_url=config.get("base_url", None)
    )
    
    try:
        if args.workflow:
            # Run the complete workflow
            print("Starting complete OpenAPI 3.0.0 API testing workflow...")
            
            # Parse OpenAPI
            if args.url:
                api_info_result = agent.parse_openapi(api_doc_source=args.url, source_type="url")
            else:
                api_info_result = agent.parse_openapi(api_doc_source=args.file, source_type="file")
            
            if not api_info_result["success"]:
                print(f"Error parsing OpenAPI: {api_info_result.get('error', 'Unknown error')}")
                return 1
                
            api_info = api_info_result["data"]
            print_parsed_api(api_info)
            
            # Generate test cases
            test_suite_result = agent.generate_test_cases(
                openapi_source=args.url if args.url else args.file,
                source_type="url" if args.url else "file"
            )
            
            if not test_suite_result["success"]:
                print(f"Error generating test cases: {test_suite_result.get('error', 'Unknown error')}")
                return 1
                
            test_suite = test_suite_result["data"]
            print(f"DEBUG: test_suite keys: {test_suite.keys()}")
            if "test_suites" in test_suite:
                print(f"DEBUG: Number of test suites: {len(test_suite['test_suites'])}")
                if test_suite['test_suites']:
                    print(f"DEBUG: First test suite keys: {test_suite['test_suites'][0].keys()}")
            print_test_suite(test_suite)
            
            # Execute tests
            test_suites = test_suite.get("test_suites", [])
            all_execution_results = []
            all_test_results = []
            
            # Get base URL from OpenAPI spec
            base_url = api_info.get("base_url", "")
            print(f"DEBUG: base_url from api_info: {base_url}")
            
            # If the base_url is a relative path, combine it with the OpenAPI URL host
            if base_url and not base_url.startswith("http"):
                # Extract host from the OpenAPI URL
                if args.url:
                    from urllib.parse import urlparse
                    parsed_url = urlparse(args.url)
                    host = f"{parsed_url.scheme}://{parsed_url.netloc}"
                    base_url = f"{host}{base_url}"
                    print(f"DEBUG: combined base_url: {base_url}")
            
            # Environment configuration for test execution
            environment = {
                "base_url": base_url,
                "headers": {
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            }
            
            print(f"\nUsing base URL for tests: {base_url}")
            
            for suite in test_suites:
                execution_result_data = agent.execute_tests(suite, environment)
                if execution_result_data["success"]:
                    all_execution_results.append(execution_result_data["data"])
                    # Collect test results for analysis
                    test_results = execution_result_data["data"].get("test_results", [])
                    all_test_results.extend(test_results)
            
            # Print execution results
            print_test_results({"test_results": all_test_results, "execution_results": all_execution_results})
            
            # Analyze results
            analysis_result_data = agent.analyze_test_results(all_test_results)
            
            if not analysis_result_data["success"]:
                print(f"Error analyzing results: {analysis_result_data.get('error', 'Unknown error')}")
                return 1
                
            analysis_result = analysis_result_data["data"]
            print_analysis_results(analysis_result)
            
            # Save results if output file specified
            if args.output:
                results = {
                    "api_info": api_info,
                    "test_suite": test_suite,
                    "execution_result": execution_result,
                    "analysis_result": analysis_result
                }
                
                with open(args.output, 'w') as f:
                    json.dump(results, f, indent=2, default=str)
                
                print(f"\nResults saved to {args.output}")
            
            return 0
        else:
            # Run individual steps
            if args.url:
                api_info_result = agent.parse_openapi(api_doc_source=args.url, source_type="url")
            else:
                api_info_result = agent.parse_openapi(api_doc_source=args.file, source_type="file")
            
            if not api_info_result["success"]:
                print(f"Error parsing OpenAPI: {api_info_result.get('error', 'Unknown error')}")
                return 1
                
            api_info = api_info_result["data"]
            print_parsed_api(api_info)
            
            # Generate test cases
            test_suite_result = agent.generate_test_cases(
                openapi_source=args.url if args.url else args.file,
                source_type="url" if args.url else "file"
            )
            
            if not test_suite_result["success"]:
                print(f"Error generating test cases: {test_suite_result.get('error', 'Unknown error')}")
                return 1
                
            test_suite = test_suite_result["data"]
            print_test_suite(test_suite)
            
            return 0
    except Exception as e:
        print(f"Error running OpenAPI agent: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())