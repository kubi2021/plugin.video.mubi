#!/usr/bin/env python3
"""
Enterprise-grade test runner that validates test quality and provides comprehensive reporting.
This script ensures tests meet enterprise standards before allowing merges.
"""
import subprocess
import sys
import json
import time
from pathlib import Path
import argparse
import re


class EnterpriseTestRunner:
    """Enterprise-grade test runner with quality validation."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_dir = self.project_root / "tests"
        self.results = {
            'coverage': {},
            'quality_metrics': {},
            'performance': {},
            'errors': []
        }
    
    def run_coverage_analysis(self):
        """Run comprehensive coverage analysis."""
        print("🔍 Running coverage analysis...")
        
        cmd = [
            sys.executable, "-m", "pytest", 
            str(self.test_dir),
            "--cov=resources",
            "--cov-report=json",
            "--cov-report=term-missing",
            "--cov-fail-under=80",  # Require 80% minimum
            "-v"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            
            # Parse coverage JSON if available
            coverage_file = self.project_root / "coverage.json"
            if coverage_file.exists():
                with open(coverage_file) as f:
                    coverage_data = json.load(f)
                    self.results['coverage'] = coverage_data
            
            return result.returncode == 0, result.stdout, result.stderr
            
        except Exception as e:
            self.results['errors'].append(f"Coverage analysis failed: {e}")
            return False, "", str(e)
    
    def run_integration_tests(self):
        """Run integration tests specifically."""
        print("🔗 Running integration tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            str(self.test_dir / "test_integration.py"),
            str(self.test_dir / "test_e2e.py"),
            "-v", "--tb=short"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            return result.returncode == 0, result.stdout, result.stderr
        except Exception as e:
            self.results['errors'].append(f"Integration tests failed: {e}")
            return False, "", str(e)
    
    def run_quality_framework_tests(self):
        """Run quality framework validation tests."""
        print("⚡ Running quality framework tests...")

        cmd = [
            sys.executable, "-m", "pytest",
            str(self.test_dir / "test_quality_framework.py"),
            "-v", "--tb=short"
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            return result.returncode == 0, result.stdout, result.stderr
        except Exception as e:
            self.results['errors'].append(f"Quality framework tests failed: {e}")
            return False, "", str(e)

    def run_security_tests(self):
        """Run security validation tests."""
        print("🔒 Running security tests...")

        cmd = [
            sys.executable, "-m", "pytest",
            str(self.test_dir / "test_security.py"),
            "-v", "--tb=short"
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            return result.returncode == 0, result.stdout, result.stderr
        except Exception as e:
            self.results['errors'].append(f"Security tests failed: {e}")
            return False, "", str(e)

    def run_stress_tests(self):
        """Run stress tests."""
        print("💪 Running stress tests...")

        cmd = [
            sys.executable, "-m", "pytest",
            str(self.test_dir / "test_stress.py"),
            "-v", "--tb=short", "-x"  # Stop on first failure for stress tests
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            return result.returncode == 0, result.stdout, result.stderr
        except Exception as e:
            self.results['errors'].append(f"Stress tests failed: {e}")
            return False, "", str(e)
    
    def analyze_test_quality_metrics(self):
        """Analyze test quality metrics."""
        print("📊 Analyzing test quality metrics...")
        
        metrics = {
            'total_tests': 0,
            'integration_tests': 0,
            'unit_tests': 0,
            'test_files': 0,
            'missing_test_files': [],
            'assertion_quality': 'unknown',
            'mock_usage': 'unknown'
        }
        
        # Count test files and tests
        test_files = list(self.test_dir.glob("test_*.py"))
        metrics['test_files'] = len(test_files)
        
        # Analyze each test file
        for test_file in test_files:
            try:
                with open(test_file, 'r') as f:
                    content = f.read()
                    
                # Count test functions
                test_functions = re.findall(r'def test_\w+', content)
                metrics['total_tests'] += len(test_functions)
                
                # Categorize tests
                if 'integration' in test_file.name or 'e2e' in test_file.name:
                    metrics['integration_tests'] += len(test_functions)
                else:
                    metrics['unit_tests'] += len(test_functions)
                    
            except Exception as e:
                self.results['errors'].append(f"Error analyzing {test_file}: {e}")
        
        # Check for missing test files
        source_files = list((self.project_root / "resources" / "lib").glob("*.py"))
        for source_file in source_files:
            if source_file.name not in ['__init__.py']:
                expected_test = self.test_dir / f"test_{source_file.stem}.py"
                if not expected_test.exists():
                    metrics['missing_test_files'].append(source_file.name)
        
        self.results['quality_metrics'] = metrics
        return metrics
    
    def run_performance_tests(self):
        """Run performance validation tests."""
        print("🚀 Running performance tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            str(self.test_dir),
            "-k", "performance",
            "--durations=10",
            "-v"
        ]
        
        try:
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            end_time = time.time()
            
            self.results['performance'] = {
                'total_time': end_time - start_time,
                'success': result.returncode == 0,
                'output': result.stdout
            }
            
            return result.returncode == 0, result.stdout, result.stderr
            
        except Exception as e:
            self.results['errors'].append(f"Performance tests failed: {e}")
            return False, "", str(e)
    
    def validate_enterprise_standards(self):
        """Validate that tests meet enterprise standards."""
        print("🏢 Validating enterprise standards...")
        
        standards = {
            'minimum_coverage': 80,
            'minimum_integration_tests': 5,
            'maximum_missing_test_files': 3,
            'maximum_test_duration': 30  # seconds
        }
        
        violations = []
        
        # Check coverage
        if 'totals' in self.results.get('coverage', {}):
            coverage_percent = self.results['coverage']['totals']['percent_covered']
            if coverage_percent < standards['minimum_coverage']:
                violations.append(f"Coverage {coverage_percent:.1f}% below minimum {standards['minimum_coverage']}%")
        
        # Check integration tests
        metrics = self.results.get('quality_metrics', {})
        integration_count = metrics.get('integration_tests', 0)
        if integration_count < standards['minimum_integration_tests']:
            violations.append(f"Only {integration_count} integration tests, need {standards['minimum_integration_tests']}")
        
        # Check missing test files
        missing_files = len(metrics.get('missing_test_files', []))
        if missing_files > standards['maximum_missing_test_files']:
            violations.append(f"{missing_files} missing test files, maximum allowed {standards['maximum_missing_test_files']}")
        
        # Check performance
        test_duration = self.results.get('performance', {}).get('total_time', 0)
        if test_duration > standards['maximum_test_duration']:
            violations.append(f"Tests took {test_duration:.1f}s, maximum allowed {standards['maximum_test_duration']}s")
        
        return violations
    
    def generate_report(self):
        """Generate comprehensive test report."""
        print("\n" + "="*80)
        print("🎯 ENTERPRISE TEST QUALITY REPORT")
        print("="*80)
        
        # Coverage Report
        if 'totals' in self.results.get('coverage', {}):
            coverage = self.results['coverage']['totals']['percent_covered']
            print(f"📊 Coverage: {coverage:.1f}%")
        
        # Quality Metrics
        metrics = self.results.get('quality_metrics', {})
        print(f"🧪 Total Tests: {metrics.get('total_tests', 0)}")
        print(f"🔗 Integration Tests: {metrics.get('integration_tests', 0)}")
        print(f"⚙️  Unit Tests: {metrics.get('unit_tests', 0)}")
        print(f"📁 Test Files: {metrics.get('test_files', 0)}")
        
        missing_files = metrics.get('missing_test_files', [])
        if missing_files:
            print(f"❌ Missing Test Files: {', '.join(missing_files)}")
        
        # Performance
        perf = self.results.get('performance', {})
        if 'total_time' in perf:
            print(f"⏱️  Test Duration: {perf['total_time']:.1f}s")
        
        # Standards Validation
        violations = self.validate_enterprise_standards()
        if violations:
            print("\n❌ ENTERPRISE STANDARDS VIOLATIONS:")
            for violation in violations:
                print(f"   • {violation}")
            return False
        else:
            print("\n✅ ALL ENTERPRISE STANDARDS MET!")
            return True
    
    def run_all(self):
        """Run all test validations."""
        print("🚀 Starting Enterprise Test Validation...")
        
        success = True
        
        # Run all test categories
        test_categories = [
            ("Coverage Analysis", self.run_coverage_analysis),
            ("Integration Tests", self.run_integration_tests),
            ("Quality Framework", self.run_quality_framework_tests),
            ("Security Tests", self.run_security_tests),
            ("Stress Tests", self.run_stress_tests),
            ("Performance Tests", self.run_performance_tests)
        ]
        
        for name, test_func in test_categories:
            try:
                result, stdout, stderr = test_func()
                if not result:
                    print(f"❌ {name} failed")
                    if stderr:
                        print(f"Error: {stderr}")
                    success = False
                else:
                    print(f"✅ {name} passed")
            except Exception as e:
                print(f"❌ {name} crashed: {e}")
                success = False
        
        # Analyze quality metrics
        self.analyze_test_quality_metrics()
        
        # Generate final report
        standards_met = self.generate_report()
        
        return success and standards_met


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Enterprise Test Runner")
    parser.add_argument("--coverage-only", action="store_true", help="Run only coverage analysis")
    parser.add_argument("--integration-only", action="store_true", help="Run only integration tests")
    parser.add_argument("--quality-only", action="store_true", help="Run only quality framework tests")
    parser.add_argument("--security-only", action="store_true", help="Run only security tests")
    parser.add_argument("--stress-only", action="store_true", help="Run only stress tests")
    parser.add_argument("--skip-stress", action="store_true", help="Skip stress tests (for faster runs)")

    args = parser.parse_args()

    runner = EnterpriseTestRunner()

    if args.coverage_only:
        success, _, _ = runner.run_coverage_analysis()
    elif args.integration_only:
        success, _, _ = runner.run_integration_tests()
    elif args.quality_only:
        success, _, _ = runner.run_quality_framework_tests()
    elif args.security_only:
        success, _, _ = runner.run_security_tests()
    elif args.stress_only:
        success, _, _ = runner.run_stress_tests()
    else:
        success = runner.run_all()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
