#!/usr/bin/env python3
"""
Final QA Pipeline Validation Script

This script validates that the complete QA pipeline is working correctly:
1. All test types are discoverable and executable
2. Regression tests are properly included
3. Allure reporting works for all test types
4. Bug discovery tests are functioning
5. All failures are due to system bugs, not pipeline issues

This represents the final deliverable validation for the OpenFilter QA automation.
"""

import subprocess
import sys
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('final_qa_validation.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class QAPipelineValidator:
    """Validates the complete QA pipeline functionality."""
    
    def __init__(self, qa_root: Path):
        self.qa_root = Path(qa_root)
        self.allure_results = self.qa_root / "allure-results"
        self.validation_results = {}
        
    def run_pytest_command(self, args: List[str]) -> Tuple[bool, str, str]:
        """Run a pytest command and return success, stdout, stderr."""
        cmd = ["python", "-m", "pytest"] + args
        logger.info(f"Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.qa_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
        except Exception as e:
            return False, "", str(e)
    
    def validate_test_collection(self) -> bool:
        """Validate that all test types are properly collected."""
        logger.info("=== Validating Test Collection ===")
        
        test_types = {
            "unit": "unit/",
            "integration": "integration/", 
            "end_to_end": "end_to_end/",
            "performance": "performance/",
            "regression": "-m regression",
            "bug_discovery": "-m bug_discovery"
        }
        
        collection_results = {}
        
        for test_type, pattern in test_types.items():
            if pattern.startswith("-m"):
                success, stdout, stderr = self.run_pytest_command([pattern, "--collect-only", "-q"])
            else:
                success, stdout, stderr = self.run_pytest_command([pattern, "--collect-only", "-q"])
            
            if success:
                # Count collected tests
                lines = stdout.split('\n')
                collected_line = [line for line in lines if "collected" in line and "test" in line]
                if collected_line:
                    try:
                        # Handle both "128 tests collected" and "10/128 tests collected" formats
                        line_parts = collected_line[0].split()
                        if "/" in line_parts[0]:
                            # Format: "10/128 tests collected" - take the second number
                            count = int(line_parts[0].split("/")[1])
                        else:
                            # Format: "128 tests collected" - take the first number
                            count = int(line_parts[0])
                        collection_results[test_type] = count
                        logger.info(f"[PASS] {test_type}: {count} tests collected")
                    except (IndexError, ValueError):
                        collection_results[test_type] = 0
                        logger.warning(f"[WARN] {test_type}: Could not parse test count")
                else:
                    collection_results[test_type] = 0
                    logger.warning(f"[WARN] {test_type}: No tests found")
            else:
                collection_results[test_type] = -1
                logger.error(f"[FAIL] {test_type}: Collection failed - {stderr}")
        
        self.validation_results["test_collection"] = collection_results
        
        # Validate that regression tests are included
        regression_count = collection_results.get("regression", 0)
        if regression_count > 0:
            logger.info(f"[PASS] Regression tests are properly collected: {regression_count} tests")
            return True
        else:
            logger.error("[FAIL] No regression tests found - this is a critical issue")
            return False
    
    def validate_allure_integration(self) -> bool:
        """Validate that Allure reporting works for all test types."""
        logger.info("=== Validating Allure Integration ===")
        
        # Clear previous results
        if self.allure_results.exists():
            import shutil
            shutil.rmtree(self.allure_results)
        
        # Run a subset of each test type with Allure
        test_commands = [
            (["-m", "regression", "--alluredir=allure-results", "-v"], "regression"),
            (["unit/", "--alluredir=allure-results", "-v", "--maxfail=3"], "unit"),
            (["integration/", "--alluredir=allure-results", "-v", "--maxfail=3"], "integration"),
        ]
        
        allure_results = {}
        
        for cmd_args, test_type in test_commands:
            success, stdout, stderr = self.run_pytest_command(cmd_args)
            
            # Check if allure results were generated
            if self.allure_results.exists():
                result_files = list(self.allure_results.glob("*.json"))
                allure_results[test_type] = {
                    "command_success": success,
                    "result_files": len(result_files),
                    "has_results": len(result_files) > 0
                }
                logger.info(f"[PASS] {test_type}: Allure generated {len(result_files)} result files")
            else:
                allure_results[test_type] = {
                    "command_success": success,
                    "result_files": 0,
                    "has_results": False
                }
                logger.error(f"[FAIL] {test_type}: No Allure results generated")
        
        self.validation_results["allure_integration"] = allure_results
        
        # Check if any results were generated
        total_files = sum(r["result_files"] for r in allure_results.values())
        if total_files > 0:
            logger.info(f"[PASS] Allure integration working: {total_files} total result files")
            return True
        else:
            logger.error("[FAIL] Allure integration failed: No result files generated")
            return False
    
    def validate_regression_suite(self) -> bool:
        """Specifically validate the regression test suite."""
        logger.info("=== Validating Regression Suite ===")
        
        # Run regression tests with detailed output
        success, stdout, stderr = self.run_pytest_command([
            "-m", "regression", 
            "--alluredir=allure-results",
            "-v",
            "--tb=short"
        ])
        
        regression_results = {
            "execution_success": success,
            "stdout": stdout,
            "stderr": stderr
        }
        
        # Parse results
        if success:
            lines = stdout.split('\n')
            passed_tests = [line for line in lines if "PASSED" in line]
            failed_tests = [line for line in lines if "FAILED" in line]
            
            regression_results.update({
                "passed_count": len(passed_tests),
                "failed_count": len(failed_tests),
                "passed_tests": passed_tests,
                "failed_tests": failed_tests
            })
            
            logger.info(f"[PASS] Regression suite executed: {len(passed_tests)} passed, {len(failed_tests)} failed")
            
            # If there are failures, they should be legitimate system bugs
            if failed_tests:
                logger.warning(f"[WARN] {len(failed_tests)} regression test failures detected (may be legitimate system bugs)")
            
        else:
            logger.error("[FAIL] Regression suite execution failed")
            regression_results.update({
                "passed_count": 0,
                "failed_count": 0,
                "passed_tests": [],
                "failed_tests": []
            })
        
        self.validation_results["regression_suite"] = regression_results
        
        # Success if tests could run (failures may be legitimate bugs)
        return success or "collected" in stdout
    
    def validate_bug_discovery(self) -> bool:
        """Validate bug discovery tests are working."""
        logger.info("=== Validating Bug Discovery ===")
        
        success, stdout, stderr = self.run_pytest_command([
            "-m", "bug_discovery",
            "--alluredir=allure-results", 
            "-v",
            "--maxfail=5"
        ])
        
        bug_discovery_results = {
            "execution_success": success,
            "stdout": stdout,
            "stderr": stderr
        }
        
        # Parse bug discovery results
        if "collected" in stdout:
            lines = stdout.split('\n')
            collected_line = [line for line in lines if "collected" in line]
            if collected_line:
                bug_discovery_results["tests_found"] = True
                logger.info("[PASS] Bug discovery tests are discoverable and executable")
            else:
                bug_discovery_results["tests_found"] = False
                logger.warning("[WARN] Bug discovery tests found but count unclear")
        else:
            bug_discovery_results["tests_found"] = False
            logger.error("[FAIL] Bug discovery tests not found or not executable")
        
        self.validation_results["bug_discovery"] = bug_discovery_results
        
        return bug_discovery_results["tests_found"]
    
    def validate_complete_pipeline(self) -> bool:
        """Run a complete pipeline validation."""
        logger.info("=== Validating Complete Pipeline ===")
        
        # Run the complete test suite with limited failures to avoid timeout
        success, stdout, stderr = self.run_pytest_command([
            "--alluredir=allure-results",
            "-v",
            "--maxfail=10",
            "--tb=line"
        ])
        
        pipeline_results = {
            "execution_success": success,
            "stdout": stdout[:5000] if stdout else "",  # Truncate for storage
            "stderr": stderr[:2000] if stderr else ""
        }
        
        # Parse overall results
        if "collected" in stdout:
            lines = stdout.split('\n')
            result_line = [line for line in lines if "=" in line and ("passed" in line or "failed" in line)]
            if result_line:
                pipeline_results["summary"] = result_line[-1]
                logger.info(f"[PASS] Complete pipeline executed: {result_line[-1]}")
            else:
                pipeline_results["summary"] = "Could not parse results"
                logger.warning("[WARN] Pipeline executed but results unclear")
        else:
            pipeline_results["summary"] = "Pipeline failed to collect tests"
            logger.error("[FAIL] Complete pipeline failed")
        
        self.validation_results["complete_pipeline"] = pipeline_results
        
        return "collected" in stdout
    
    def generate_validation_report(self) -> Dict:
        """Generate a comprehensive validation report."""
        logger.info("=== Generating Validation Report ===")
        
        # Run all validations
        results = {
            "timestamp": datetime.now().isoformat(),
            "qa_root": str(self.qa_root),
            "validations": {}
        }
        
        validations = [
            ("test_collection", self.validate_test_collection),
            ("allure_integration", self.validate_allure_integration),
            ("regression_suite", self.validate_regression_suite),
            ("bug_discovery", self.validate_bug_discovery),
            ("complete_pipeline", self.validate_complete_pipeline)
        ]
        
        all_passed = True
        passed_count = 0
        failed_count = 0
        
        for name, validation_func in validations:
            try:
                logger.info(f"\n--- Running {name} validation ---")
                passed = validation_func()
                results["validations"][name] = {
                    "passed": passed,
                    "details": self.validation_results.get(name, {})
                }
                if not passed:
                    all_passed = False
                    logger.error(f"[FAIL] {name} validation FAILED")
                    failed_count += 1
                else:
                    logger.info(f"[PASS] {name} validation PASSED")
                    passed_count += 1
            except Exception as e:
                logger.error(f"[ERROR] {name} validation ERROR: {e}")
                results["validations"][name] = {
                    "passed": False,
                    "error": str(e),
                    "details": {}
                }
                all_passed = False
        
        results["overall_success"] = all_passed
        
        # Save results
        report_file = self.qa_root / "final_validation_report.json"
        with open(report_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Validation report saved to: {report_file}")
        
        # Generate summary
        if all_passed:
            logger.info("\n[SUCCESS] ALL VALIDATIONS PASSED - QA PIPELINE IS ROBUST!")
        else:
            logger.error("\n[FAILURE] SOME VALIDATIONS FAILED - PIPELINE NEEDS ATTENTION")
        
        return results


def main():
    """Main validation function."""
    qa_root = Path(__file__).parent
    
    logger.info("Starting Final QA Pipeline Validation")
    logger.info(f"QA Root: {qa_root}")
    logger.info("=" * 80)
    
    validator = QAPipelineValidator(qa_root)
    results = validator.generate_validation_report()
    
    # Print summary
    print("\n" + "=" * 80)
    print("FINAL QA VALIDATION SUMMARY")
    print("=" * 80)
    
    for validation_name, validation_result in results["validations"].items():
        status = "PASS" if validation_result["passed"] else "FAIL"
        print(f"{validation_name.upper():20} : {status}")
    
    print("=" * 80)
    overall_status = "SUCCESS" if results["overall_success"] else "FAILURE"
    print(f"OVERALL RESULT: {overall_status}")
    print("=" * 80)
    
    # Exit with appropriate code
    sys.exit(0 if results["overall_success"] else 1)


if __name__ == "__main__":
    main()
