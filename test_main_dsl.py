#!/usr/bin/env python3
"""
Test the main.py DSL logic with the user's actual log data
"""

import sys
import os

# Add the backend directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'app'))

# Import the DSL logic from main.py
from main import evaluate_rule_matches

def test_user_rule_with_actual_data():
    """Test the user's rule with log data that actually contains the keywords"""
    
    print("🧪 Testing main.py DSL with actual log data containing keywords")
    print("=" * 60)
    
    # The user's rule
    rule = {
        "id": 8,
        "name": "万兆网卡崩溃",
        "description": "检测万兆网卡相关崩溃",
        "enabled": True,
        "dsl": "\"aq_ring_rx_clean\" & \"atlantic\"",
        "patterns": [],
        "operator": "OR",
        "is_regex": True,
        "folder_id": 1
    }
    
    # Log content that actually contains both keywords (from user's grep output)
    test_log = """
aq_ring_rx_clean+0x175/0xe60 [atlantic]  
aq_ring_rx_clean+0x14d/0xe60 [atlantic]
aq_ring_update_queue_state+0xd0/0x60 [atlantic]
kernel: some other log entry
"""
    
    print(f"Rule: {rule['dsl']}")
    print(f"Log contains 'aq_ring_rx_clean': {'aq_ring_rx_clean' in test_log.lower()}")
    print(f"Log contains 'atlantic': {'atlantic' in test_log.lower()}")
    print()
    
    # Test the rule
    try:
        matches = evaluate_rule_matches(test_log, rule)
        print(f"✅ DSL evaluation completed successfully!")
        print(f"Number of matches: {len(matches)}")
        
        if matches:
            print("Match details:")
            for i, match in enumerate(matches[:3]):  # Show first 3 matches
                if hasattr(match, 'group'):
                    print(f"  {i+1}. Text: '{match.group()}'")
                    print(f"     Position: {match.start()}-{match.end()}")
                else:
                    print(f"  {i+1}. Match object: {match}")
        else:
            print("❌ No matches found - this indicates a problem")
            
    except Exception as e:
        print(f"❌ Error during DSL evaluation: {e}")
        import traceback
        traceback.print_exc()
        
    print()
    
    # Test with a rule that should definitely match
    simple_rule = {
        "id": 9,
        "name": "Test rule",
        "enabled": True,
        "dsl": "\"aq_ring_rx_clean\"",
        "patterns": [],
        "operator": "OR",
        "is_regex": True
    }
    
    print("Testing simpler rule that should definitely match:")
    print(f"Rule: {simple_rule['dsl']}")
    
    try:
        matches2 = evaluate_rule_matches(test_log, simple_rule)
        print(f"Matches: {len(matches2)}")
        if matches2:
            print("✅ Simple rule works correctly!")
        else:
            print("❌ Even simple rule failed - DSL logic has issues")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_user_rule_with_actual_data()