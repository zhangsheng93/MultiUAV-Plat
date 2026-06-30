import unittest
import json
import hashlib
import os
import copy
import sys
import tempfile
import glob
from utils import calculate_export_id, is_export_id_valid

def validate_statistics(data):
    """
    Validates the consistency of statistics within the exported data.
    
    Args:
        data (dict): The loaded JSON data.
        
    Returns:
        bool: True if statistics are consistent, False otherwise.
    """
    stats = data.get('statistics', {})
    results = data.get('results', [])
    
    calc_passed_tasks = 0
    calc_failed_tasks = 0
    calc_total_failed_tasks = 0
    sum_task_pass_rates = 0.0
    calc_total_checks = 0
    calc_passed_checks = 0
    
    total_tasks = len(results)
    
    print("Verifying statistics consistency...")
    
    all_stats_valid = True
    
    for task in results:
        t_stats = task.get('statistics', {})
        details = task.get('details', [])
        status = task.get('status')
        if not task.get('session_id') or not task.get('task_id'):
            print(f"  FAIL: Task '{task.get('task_name')}' missing CheckUI import keys session_id/task_id")
            all_stats_valid = False
        
        # 1. Verify Task Internal Consistency
        total_checks_claimed = t_stats.get('total_checks_apis', 0)
        passed_checks_claimed = t_stats.get('passed_checks_apis', 0)
        failed_checks_claimed = t_stats.get('failed_checks_apis', 0)
        pass_rate_claimed = t_stats.get('pass_rate', 0.0)
        
        # Check basic math: passed + failed = total
        if passed_checks_claimed + failed_checks_claimed != total_checks_claimed:
             print(f"  FAIL: Task '{task.get('task_name')}' check counts sum mismatch. Passed {passed_checks_claimed} + Failed {failed_checks_claimed} != Total {total_checks_claimed}")
             all_stats_valid = False

        # Calculate from details if present
        leaf_details = [d for d in details if d.get('type') == 'leaf']
        passed_from_details = sum(1 for d in leaf_details if d.get('result', False))
        total_from_details = len(leaf_details)
        
        # If details are present, they must match the claimed stats
        if total_from_details > 0:
            if passed_from_details != passed_checks_claimed:
                print(f"  FAIL: Task '{task.get('task_name')}' passed checks mismatch. Claimed: {passed_checks_claimed}, Found in details: {passed_from_details}")
                all_stats_valid = False
            
            if total_from_details != total_checks_claimed:
                print(f"  FAIL: Task '{task.get('task_name')}' total checks mismatch. Claimed: {total_checks_claimed}, Found in details: {total_from_details}")
                all_stats_valid = False
        else:
            # If details are empty, passed checks must be 0
            if passed_checks_claimed != 0:
                print(f"  FAIL: Task '{task.get('task_name')}' has no details but claims {passed_checks_claimed} passed checks.")
                all_stats_valid = False

        # Verify rate calculation
        calc_rate = (passed_checks_claimed / total_checks_claimed) if total_checks_claimed > 0 else 0.0
        if abs(calc_rate - pass_rate_claimed) > 0.0001:
             print(f"  FAIL: Task '{task.get('task_name')}' pass rate mismatch. Claimed: {pass_rate_claimed}, Calc: {calc_rate}")
             all_stats_valid = False

        # 2. Accumulate for Session Stats
        sum_task_pass_rates += calc_rate
        calc_total_checks += total_checks_claimed
        calc_passed_checks += passed_checks_claimed
        
        if status == 'passed':
            calc_passed_tasks += 1
        else:
            calc_failed_tasks += 1
            # "Total failed" definition: passed == 0 (and total > 0) OR no checks at all
            if (total_checks_claimed > 0 and passed_checks_claimed == 0) or total_checks_claimed == 0:
                calc_total_failed_tasks += 1

    # 3. Verify Session Stats
    s_total = stats.get('total_tasks', 0)
    s_passed = stats.get('passed_tasks_count', 0)
    s_failed = stats.get('failed_tasks_count', 0)
    s_total_failed = stats.get('total_failed_task_count', 0)
    s_task_pass_rate = stats.get('task_pass_rate', 0.0)
    s_avg_check_pass_rate = stats.get('average_check_pass_rate', 0.0)
    s_total_failed_rate = stats.get('total_failed_task_rate', 0.0)
    s_total_checks = stats.get('total_checks', 0)
    s_passed_checks = stats.get('passed_checks', 0)
    s_failed_checks = stats.get('failed_checks', 0)
    s_check_pass_rate = stats.get('check_pass_rate', 0.0)
    
    if s_total != total_tasks:
        print(f"  FAIL: Total tasks mismatch. Claimed: {s_total}, Found: {total_tasks}")
        all_stats_valid = False
        
    if s_passed != calc_passed_tasks:
        print(f"  FAIL: Passed tasks mismatch. Claimed: {s_passed}, Calc: {calc_passed_tasks}")
        all_stats_valid = False
        
    if s_failed != calc_failed_tasks:
        print(f"  FAIL: Failed tasks mismatch. Claimed: {s_failed}, Calc: {calc_failed_tasks}")
        all_stats_valid = False
        
    if s_total_failed != calc_total_failed_tasks:
        print(f"  FAIL: Completely failed tasks mismatch. Claimed: {s_total_failed}, Calc: {calc_total_failed_tasks}")
        all_stats_valid = False

    calc_session_pass_rate = calc_passed_tasks / total_tasks if total_tasks > 0 else 0.0
    if abs(calc_session_pass_rate - s_task_pass_rate) > 0.0001:
        print(f"  FAIL: Session task pass rate mismatch. Claimed: {s_task_pass_rate}, Calc: {calc_session_pass_rate}")
        all_stats_valid = False
        
    calc_avg_check_pass_rate = sum_task_pass_rates / total_tasks if total_tasks > 0 else 0.0
    if abs(calc_avg_check_pass_rate - s_avg_check_pass_rate) > 0.0001:
        print(f"  FAIL: Avg check pass rate mismatch. Claimed: {s_avg_check_pass_rate}, Calc: {calc_avg_check_pass_rate}")
        all_stats_valid = False
    
    calc_total_failed_rate = calc_total_failed_tasks / total_tasks if total_tasks > 0 else 0.0
    if abs(calc_total_failed_rate - s_total_failed_rate) > 0.0001:
        print(f"  FAIL: Total failed rate mismatch. Claimed: {s_total_failed_rate}, Calc: {calc_total_failed_rate}")
        all_stats_valid = False

    calc_failed_checks = calc_total_checks - calc_passed_checks
    if s_total_checks != calc_total_checks:
        print(f"  FAIL: Total checks mismatch. Claimed: {s_total_checks}, Calc: {calc_total_checks}")
        all_stats_valid = False

    if s_passed_checks != calc_passed_checks:
        print(f"  FAIL: Passed checks mismatch. Claimed: {s_passed_checks}, Calc: {calc_passed_checks}")
        all_stats_valid = False

    if s_failed_checks != calc_failed_checks:
        print(f"  FAIL: Failed checks mismatch. Claimed: {s_failed_checks}, Calc: {calc_failed_checks}")
        all_stats_valid = False

    calc_check_pass_rate = calc_passed_checks / calc_total_checks if calc_total_checks > 0 else 0.0
    if abs(calc_check_pass_rate - s_check_pass_rate) > 0.0001:
        print(f"  FAIL: Check pass rate mismatch. Claimed: {s_check_pass_rate}, Calc: {calc_check_pass_rate}")
        all_stats_valid = False
        
    if all_stats_valid:
        print("PASS: Statistics consistency check passed")
        
    return all_stats_valid

def verify_export_file_integrity(file_path):
    """
    Verifies that the 'id' hash in the exported JSON file matches the content,
    AND that the statistics are internally consistent.
    
    Args:
        file_path (str): Path to the JSON file to verify.
        
    Returns:
        bool: True if valid (integrity + stats), False otherwise.
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return False

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if 'id' not in data:
            print(f"Error: 'id' field missing in {file_path}")
            return False
            
        original_hash = data['id']
        
        # Create a copy to calculate hash
        data_to_hash = copy.deepcopy(data)
        # Remove the ID field as it was not part of the original hash calculation
        data_to_hash.pop('id', None)
        
        # Serialize with same settings as exporter
        results_json = json.dumps(data_to_hash, sort_keys=True)
        
        # Calculate MD5
        calculated_hash = hashlib.md5(results_json.encode('utf-8')).hexdigest()
        
        if calculated_hash != original_hash:
            print(f"FAIL: Hash mismatch for {file_path}")
            print(f"  Expected (in file): {original_hash}")
            print(f"  Calculated:         {calculated_hash}")
            return False
            
        print(f"PASS: Integrity hash check passed for {file_path}")
        
        # Verify Statistics
        if not validate_statistics(data):
            return False
            
        return True
            
    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON from {file_path}")
        return False
    except Exception as e:
        print(f"Verification failed with error: {e}")
        return False

class TestExportIntegrity(unittest.TestCase):
    def setUp(self):
        # Create a dummy export structure mimicking gui_controller output
        self.sample_data = {
            # "id" will be added later
            "export_timestamp": "2023-01-01T12:00:00",
            "tool": "MultiUAV-Plat GUI Controller",
            "version": "test-version",
            "server_version": None,
            "statistics": {
                "total_tasks": 1,
                "passed_tasks_count": 1,
                "failed_tasks_count": 0,
                "total_failed_task_count": 0,
                "task_pass_rate": 1.0,
                "total_failed_task_rate": 0.0,
                "average_check_pass_rate": 1.0,
                "total_checks": 1,
                "passed_checks": 1,
                "failed_checks": 0,
                "check_pass_rate": 1.0
            },
            "results": [
                {
                    "session_id": "test_session_123",
                    "session_name": "Test Session",
                    "task_id": "t1",
                    "task_name": "Test Task",
                    "status": "passed",
                    "timestamp": "2023-01-01T12:00:00",
                    "error": None,
                    "statistics": {
                         "total_checks_apis": 1,
                         "passed_checks_apis": 1,
                         "failed_checks_apis": 0,
                         "pass_rate": 1.0
                    },
                    "details": [
                        {"type": "leaf", "result": True, "endpoint": "/api/test"}
                    ]
                }
            ]
        }
        
        # Calculate valid hash
        self.valid_hash = calculate_export_id(self.sample_data)
        
        # Create complete record
        self.export_record = copy.deepcopy(self.sample_data)
        self.export_record['id'] = self.valid_hash
        
    def test_valid_file_verification(self):
        """Test that a valid file passes verification."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tf:
            json.dump(self.export_record, tf, indent=2, ensure_ascii=False, sort_keys=False)
            valid_file_path = tf.name
            
        try:
            # Capture stdout
            from io import StringIO
            original_stdout = sys.stdout
            sys.stdout = StringIO()
            
            result = verify_export_file_integrity(valid_file_path)
            
            sys.stdout = original_stdout
            self.assertTrue(result, "Valid file should pass integrity check")
        finally:
            if os.path.exists(valid_file_path):
                os.remove(valid_file_path)

    def test_results_include_checkui_import_keys(self):
        """Test that exported results contain keys CheckUI import requires."""
        for result in self.export_record["results"]:
            self.assertIn("session_id", result)
            self.assertIn("task_id", result)
            self.assertTrue(result["session_id"])
            self.assertTrue(result["task_id"])
            self.assertIn("session_name", result)
            self.assertIn("error", result)
            
    def test_modified_file_verification(self):
        """Test that a modified file fails verification."""
        modified_record = copy.deepcopy(self.export_record)
        modified_record['tool'] = "malicious_actor"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tf:
            json.dump(modified_record, tf, indent=2, ensure_ascii=False)
            modified_file_path = tf.name
            
        try:
            from io import StringIO
            original_stdout = sys.stdout
            sys.stdout = StringIO()

            result = verify_export_file_integrity(modified_file_path)

            sys.stdout = original_stdout
            self.assertFalse(result, "Modified file should fail integrity check")
        finally:
            if os.path.exists(modified_file_path):
                os.remove(modified_file_path)

    def test_export_id_validation_rejects_changed_payload(self):
        """Test that CheckUI import can reject a payload whose id no longer matches."""
        changed_record = copy.deepcopy(self.export_record)
        changed_record['results'][0]['status'] = 'failed'

        self.assertFalse(is_export_id_valid(changed_record))

    def test_export_id_validation_rejects_missing_id(self):
        """Test that CheckUI import can reject a payload without an id."""
        missing_id_record = copy.deepcopy(self.export_record)
        missing_id_record.pop('id')

        self.assertFalse(is_export_id_valid(missing_id_record))

    def test_invalid_statistics(self):
        """Test that a file with hash match but invalid stats fails verification."""
        # Create data with incorrect stats
        bad_stats_data = copy.deepcopy(self.sample_data)
        # Modify stats so they are wrong (claimed 100% pass but 0 passed)
        bad_stats_data['statistics']['passed_tasks_count'] = 100 
        
        # Recalculate hash so the integrity check passes, forcing the stats check to run
        bad_stats_data['id'] = calculate_export_id(bad_stats_data)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tf:
            json.dump(bad_stats_data, tf, indent=2, ensure_ascii=False)
            file_path = tf.name
            
        try:
            from io import StringIO
            original_stdout = sys.stdout
            sys.stdout = StringIO()

            result = verify_export_file_integrity(file_path)

            sys.stdout = original_stdout
            self.assertFalse(result, "File with invalid stats should fail verification despite valid hash")
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)


    def test_unicode_handling(self):
        """Test that unicode characters are handled correctly."""
        # Add unicode to sample data
        unicode_sample = copy.deepcopy(self.sample_data)
        unicode_sample['results'][0]['session_name'] = "测试会话"
        unicode_sample['results'][0]['task_name'] = "测试任务"
        
        # Recalculate hash
        unicode_sample['id'] = calculate_export_id(unicode_sample)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tf:
            # Write unescaped unicode to file
            json.dump(unicode_sample, tf, indent=2, ensure_ascii=False)
            file_path = tf.name
            
        try:
            # Capture stdout
            from io import StringIO
            original_stdout = sys.stdout
            sys.stdout = StringIO()

            result = verify_export_file_integrity(file_path)

            sys.stdout = original_stdout
            self.assertTrue(result, "Unicode file should pass integrity check")
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

if __name__ == '__main__':
    # Check if a file path argument was provided
    if len(sys.argv) > 1:
        # Run in "utility tool" mode
        input_path = sys.argv[1]
        
        if os.path.isdir(input_path):
            print(f"Checking directory: {input_path}")
            # Get all JSON files in the directory
            files = glob.glob(os.path.join(input_path, "*.json"))
            if not files:
                print("No JSON files found in the directory.")
                sys.exit(0)
            
            failed_files = []
            for file_path in files:
                print(f"\nChecking: {file_path}")
                if not verify_export_file_integrity(file_path):
                    failed_files.append(file_path)
            
            print("\n" + "="*30)
            if failed_files:
                print(f"Summary: {len(failed_files)} out of {len(files)} files FAILED verification.")
                for f in failed_files:
                    print(f" - {f}")
                sys.exit(1)
            else:
                print(f"Summary: All {len(files)} files PASSED verification.")
                sys.exit(0)
        else:
            # Single file check
            if verify_export_file_integrity(input_path):
                sys.exit(0)
            else:
                sys.exit(1)
    else:
        # Run in "test" mode
        unittest.main()
