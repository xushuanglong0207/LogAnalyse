#!/usr/bin/env python3
"""
DSL规则测试脚本
测试 DSL 规则引擎是否能正确解析和匹配规则
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.app.services.dsl_parser import DSLRuleEngine

def test_basic_dsl_rules():
    """测试基本的DSL规则"""
    
    print("🧪 测试DSL规则引擎")
    print("=" * 50)
    
    test_cases = [
        {
            "name": "万兆网卡规则测试",
            "rule": '"aq_ring_rx_clean" & "atlantic"',
            "test_texts": [
                "aq_ring_rx_clean atlantic network error occurred",  # 应该匹配
                "atlantic network driver aq_ring_rx_clean failed",   # 应该匹配  
                "aq_ring_rx_clean error in network",                 # 不应该匹配
                "atlantic network driver error",                     # 不应该匹配
                "some other network error"                           # 不应该匹配
            ],
            "expected": [True, True, False, False, False]
        },
        {
            "name": "内核错误规则测试", 
            "rule": '"kernel panic" | "oops"',
            "test_texts": [
                "kernel panic - not syncing",      # 应该匹配
                "Oops: 0000 [#1] SMP",            # 应该匹配
                "kernel error occurred",           # 不应该匹配
            ],
            "expected": [True, True, False]
        },
        {
            "name": "复合规则测试",
            "rule": '("disk full" | "no space") & !"write"',
            "test_texts": [
                "Error: disk full on /tmp",                    # 应该匹配
                "no space left on device",                     # 应该匹配
                "disk full during write operation",            # 不应该匹配
                "write failed: no space left",                 # 不应该匹配
            ],
            "expected": [True, True, False, False]
        },
        {
            "name": "NOT操作测试",
            "rule": '"error" & !"warning"',
            "test_texts": [
                "fatal error occurred",           # 应该匹配
                "error: file not found",          # 应该匹配  
                "warning: error in config",       # 不应该匹配
            ],
            "expected": [True, True, False]
        }
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for test_case in test_cases:
        print(f"\n📋 测试用例: {test_case['name']}")
        print(f"   规则: {test_case['rule']}")
        
        # 编译规则
        compiled = DSLRuleEngine.compile_rule(test_case['rule'])
        if not compiled["compiled"]:
            print(f"   ❌ 规则编译失败: {compiled['error']}")
            continue
            
        print(f"   ✅ 规则编译成功")
        
        # 测试每个文本
        for i, (text, expected) in enumerate(zip(test_case['test_texts'], test_case['expected'])):
            total_tests += 1
            result = DSLRuleEngine.test_rule(test_case['rule'], text)
            
            if result["matched"] == expected:
                passed_tests += 1
                status = "✅"
            else:
                status = "❌"
            
            print(f"   {status} 文本 {i+1}: '{text[:50]}{'...' if len(text) > 50 else ''}'")
            print(f"      预期: {expected}, 实际: {result['matched']}")
            
            if result.get("error"):
                print(f"      错误: {result['error']}")
    
    print(f"\n📊 测试结果统计")
    print(f"总测试数: {total_tests}")
    print(f"通过数: {passed_tests}")
    print(f"成功率: {passed_tests/total_tests*100:.1f}%")
    
    if passed_tests == total_tests:
        print("🎉 所有测试通过!")
        return True
    else:
        print("⚠️  有测试失败，请检查DSL规则引擎")
        return False


def test_kernel_panic_log():
    """测试实际的内核崩溃日志"""
    
    print(f"\n🔍 测试实际日志匹配")
    print("=" * 30)
    
    # 从您的截图中的日志内容
    kernel_log = """<4>[ 6127.437389] CR2: ffff9a5bac8ae2f0 CR3: 0000000105890003 CR4: 00000000f72ef0
<4>[ 6127.437392] PKRU: 55555554
<0>[ 6127.437395] Kernel panic - not syncing: Fatal exception in interrupt
<0>[ 6127.437458] Kernel Offset: 0x14600000 from 0xffffffff81000000 (relocation range: 0xffffffff80000000-0xffffffffbfffffff)
dmesg-efi_pstore-17561731560100l:"""
    
    # 测试您的规则
    your_rule = '"aq_ring_rx_clean" & "atlantic"'
    
    print(f"规则: {your_rule}")
    print(f"日志内容预览: {kernel_log[:100]}...")
    
    result = DSLRuleEngine.test_rule(your_rule, kernel_log)
    
    print(f"匹配结果: {result['matched']}")
    if result.get("error"):
        print(f"错误: {result['error']}")
    
    # 测试一个应该匹配的规则
    kernel_panic_rule = '"kernel panic" | "fatal exception"'
    print(f"\n测试应该匹配的规则: {kernel_panic_rule}")
    
    result2 = DSLRuleEngine.test_rule(kernel_panic_rule, kernel_log)
    print(f"匹配结果: {result2['matched']}")
    
    if result2['matched']:
        print("✅ 内核崩溃检测规则工作正常!")
    else:
        print("❌ 内核崩溃检测规则有问题")


if __name__ == "__main__":
    print("🚀 DSL规则引擎测试开始")
    
    # 基本功能测试
    basic_success = test_basic_dsl_rules()
    
    # 实际日志测试
    test_kernel_panic_log()
    
    print(f"\n🏁 测试完成")
    if basic_success:
        print("✨ DSL规则引擎工作正常，可以处理您的规则了!")
    else:
        print("⚠️  DSL规则引擎需要进一步调试")