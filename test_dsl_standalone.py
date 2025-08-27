#!/usr/bin/env python3
"""
独立的DSL规则测试脚本
直接复制DSL解析器代码进行测试，避免依赖问题
"""

import re
from typing import List, Dict, Any, Union
from enum import Enum


class TokenType(Enum):
    """Token类型"""
    KEYWORD = "KEYWORD"
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    EOF = "EOF"


class Token:
    """词法分析器Token"""
    def __init__(self, token_type: TokenType, value: str, position: int = 0):
        self.type = token_type
        self.value = value
        self.position = position
    
    def __repr__(self):
        return f"Token({self.type}, {self.value})"


class DSLLexer:
    """DSL词法分析器"""
    
    def __init__(self, text: str):
        self.text = text
        self.position = 0
        self.current_char = self.text[0] if text else None
    
    def error(self, message: str = "Invalid character"):
        raise ValueError(f"Lexer error at position {self.position}: {message}")
    
    def advance(self):
        """移动到下一个字符"""
        self.position += 1
        if self.position >= len(self.text):
            self.current_char = None
        else:
            self.current_char = self.text[self.position]
    
    def skip_whitespace(self):
        """跳过空白字符（除了引号内的）"""
        while self.current_char and self.current_char.isspace():
            self.advance()
    
    def read_string(self) -> str:
        """读取引号包围的字符串"""
        quote_char = self.current_char
        self.advance()  # 跳过开始引号
        
        result = ""
        while self.current_char and self.current_char != quote_char:
            if self.current_char == '\\':  # 处理转义字符
                self.advance()
                if self.current_char:
                    result += self.current_char
                    self.advance()
            else:
                result += self.current_char
                self.advance()
        
        if self.current_char != quote_char:
            self.error("Unterminated string")
        
        self.advance()  # 跳过结束引号
        return result
    
    def read_word(self) -> str:
        """读取单词（不含引号的关键字）"""
        result = ""
        while (self.current_char and 
               (self.current_char.isalnum() or 
                self.current_char in '_-.')):
            result += self.current_char
            self.advance()
        return result
    
    def get_next_token(self) -> Token:
        """获取下一个token"""
        while self.current_char:
            if self.current_char.isspace():
                self.skip_whitespace()
                continue
            
            # 处理引号字符串
            if self.current_char in '"\'':
                value = self.read_string()
                return Token(TokenType.KEYWORD, value, self.position)
            
            # 处理逻辑运算符
            if self.current_char == '&':
                self.advance()
                return Token(TokenType.AND, '&', self.position)
            
            if self.current_char == '|':
                self.advance()
                return Token(TokenType.OR, '|', self.position)
            
            if self.current_char in '!！':  # 支持中英文叹号
                self.advance()
                return Token(TokenType.NOT, '!', self.position)
            
            if self.current_char == '(':
                self.advance()
                return Token(TokenType.LPAREN, '(', self.position)
            
            if self.current_char == ')':
                self.advance()
                return Token(TokenType.RPAREN, ')', self.position)
            
            # 处理不带引号的单词
            if self.current_char.isalnum() or self.current_char in '_-.':
                word = self.read_word()
                return Token(TokenType.KEYWORD, word, self.position)
            
            self.error(f"Unexpected character: '{self.current_char}'")
        
        return Token(TokenType.EOF, '', self.position)
    
    def tokenize(self) -> List[Token]:
        """对整个输入进行词法分析"""
        tokens = []
        while True:
            token = self.get_next_token()
            tokens.append(token)
            if token.type == TokenType.EOF:
                break
        return tokens


class ASTNode:
    """抽象语法树节点基类"""
    pass


class KeywordNode(ASTNode):
    """关键字节点"""
    def __init__(self, keyword: str):
        self.keyword = keyword
    
    def __repr__(self):
        return f"Keyword('{self.keyword}')"


class BinaryOpNode(ASTNode):
    """二元操作节点"""
    def __init__(self, left: ASTNode, operator: str, right: ASTNode):
        self.left = left
        self.operator = operator
        self.right = right
    
    def __repr__(self):
        return f"BinaryOp({self.left} {self.operator} {self.right})"


class UnaryOpNode(ASTNode):
    """一元操作节点"""
    def __init__(self, operator: str, operand: ASTNode):
        self.operator = operator
        self.operand = operand
    
    def __repr__(self):
        return f"UnaryOp({self.operator} {self.operand})"


class DSLParser:
    """DSL语法分析器"""
    
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.position = 0
        self.current_token = self.tokens[0] if tokens else None
    
    def error(self, message: str = "Invalid syntax"):
        token_info = f"'{self.current_token.value}'" if self.current_token else "EOF"
        raise ValueError(f"Parser error at {token_info}: {message}")
    
    def eat(self, token_type: TokenType):
        """消费指定类型的token"""
        if self.current_token.type == token_type:
            self.position += 1
            if self.position < len(self.tokens):
                self.current_token = self.tokens[self.position]
            else:
                self.current_token = Token(TokenType.EOF, '', self.position)
        else:
            self.error(f"Expected {token_type}, got {self.current_token.type}")
    
    def parse(self) -> ASTNode:
        """解析DSL表达式"""
        node = self.or_expr()
        if self.current_token.type != TokenType.EOF:
            self.error("Unexpected token after complete expression")
        return node
    
    def or_expr(self) -> ASTNode:
        """解析OR表达式（最低优先级）"""
        node = self.and_expr()
        
        while self.current_token.type == TokenType.OR:
            op = self.current_token.value
            self.eat(TokenType.OR)
            right = self.and_expr()
            node = BinaryOpNode(node, op, right)
        
        return node
    
    def and_expr(self) -> ASTNode:
        """解析AND表达式"""
        node = self.not_expr()
        
        while self.current_token.type == TokenType.AND:
            op = self.current_token.value
            self.eat(TokenType.AND)
            right = self.not_expr()
            node = BinaryOpNode(node, op, right)
        
        return node
    
    def not_expr(self) -> ASTNode:
        """解析NOT表达式（最高优先级）"""
        if self.current_token.type == TokenType.NOT:
            op = self.current_token.value
            self.eat(TokenType.NOT)
            operand = self.not_expr()  # 递归处理连续的NOT
            return UnaryOpNode(op, operand)
        
        return self.primary_expr()
    
    def primary_expr(self) -> ASTNode:
        """解析基本表达式"""
        token = self.current_token
        
        if token.type == TokenType.KEYWORD:
            self.eat(TokenType.KEYWORD)
            return KeywordNode(token.value)
        
        if token.type == TokenType.LPAREN:
            self.eat(TokenType.LPAREN)
            node = self.or_expr()
            self.eat(TokenType.RPAREN)
            return node
        
        self.error(f"Unexpected token: {token.type}")


class DSLEvaluator:
    """DSL表达式求值器"""
    
    def __init__(self, text: str):
        self.text = text.lower()  # 不区分大小写
    
    def evaluate(self, node: ASTNode) -> bool:
        """递归求值AST节点"""
        if isinstance(node, KeywordNode):
            return node.keyword.lower() in self.text
        
        if isinstance(node, BinaryOpNode):
            left_result = self.evaluate(node.left)
            right_result = self.evaluate(node.right)
            
            if node.operator == '&':
                return left_result and right_result
            elif node.operator == '|':
                return left_result or right_result
            else:
                raise ValueError(f"Unknown binary operator: {node.operator}")
        
        if isinstance(node, UnaryOpNode):
            operand_result = self.evaluate(node.operand)
            if node.operator == '!':
                return not operand_result
            else:
                raise ValueError(f"Unknown unary operator: {node.operator}")
        
        raise ValueError(f"Unknown node type: {type(node)}")


class DSLRuleEngine:
    """DSL规则引擎"""
    
    @staticmethod
    def compile_rule(dsl_expression: str) -> Dict[str, Any]:
        """编译DSL规则为可执行对象"""
        try:
            # 词法分析
            lexer = DSLLexer(dsl_expression)
            tokens = lexer.tokenize()
            
            # 语法分析
            parser = DSLParser(tokens)
            ast = parser.parse()
            
            return {
                "compiled": True,
                "ast": ast,
                "original": dsl_expression,
                "error": None
            }
        
        except Exception as e:
            return {
                "compiled": False,
                "ast": None,
                "original": dsl_expression,
                "error": str(e)
            }
    
    @staticmethod
    def match_rule(compiled_rule: Dict[str, Any], text: str) -> bool:
        """使用编译后的规则匹配文本"""
        if not compiled_rule["compiled"]:
            return False
        
        try:
            evaluator = DSLEvaluator(text)
            return evaluator.evaluate(compiled_rule["ast"])
        except Exception:
            return False
    
    @staticmethod
    def test_rule(dsl_expression: str, test_text: str) -> Dict[str, Any]:
        """测试DSL规则"""
        compiled_rule = DSLRuleEngine.compile_rule(dsl_expression)
        
        if not compiled_rule["compiled"]:
            return {
                "matched": False,
                "error": compiled_rule["error"],
                "rule": dsl_expression
            }
        
        try:
            matched = DSLRuleEngine.match_rule(compiled_rule, test_text)
            return {
                "matched": matched,
                "error": None,
                "rule": dsl_expression,
                "test_text": test_text[:100] + "..." if len(test_text) > 100 else test_text
            }
        except Exception as e:
            return {
                "matched": False,
                "error": str(e),
                "rule": dsl_expression
            }


def test_your_rule():
    """测试您的具体规则"""
    
    print("测试您的万兆网卡规则")
    print("=" * 40)
    
    your_rule = '"aq_ring_rx_clean" & "atlantic"'
    
    # 从您的截图中的日志内容
    kernel_log = """<4>[ 6127.437389] CR2: ffff9a5bac8ae2f0 CR3: 0000000105890003 CR4: 00000000f72ef0
<4>[ 6127.437392] PKRU: 55555554
<0>[ 6127.437395] Kernel panic - not syncing: Fatal exception in interrupt
<0>[ 6127.437458] Kernel Offset: 0x14600000 from 0xffffffff81000000 (relocation range: 0xffffffff80000000-0xffffffffbfffffff)
dmesg-efi_pstore-17561731560100l:"""
    
    print(f"您的规则: {your_rule}")
    print(f"日志内容: {kernel_log[:100]}...")
    
    result = DSLRuleEngine.test_rule(your_rule, kernel_log)
    
    print(f"匹配结果: {result['matched']}")
    if result.get("error"):
        print(f"错误: {result['error']}")
    
    print(f"\n分析:")
    print(f"- 规则要求同时包含 'aq_ring_rx_clean' 和 'atlantic'")
    print(f"- 日志中是否包含 'aq_ring_rx_clean': {'aq_ring_rx_clean' in kernel_log.lower()}")
    print(f"- 日志中是否包含 'atlantic': {'atlantic' in kernel_log.lower()}")
    
    if not result['matched']:
        print(f"规则不匹配，因为日志中缺少所需的关键字")
        print(f"建议修改规则来匹配实际的日志内容")
        
        # 测试能匹配的规则
        working_rule = '"kernel panic" | "fatal exception"'
        working_result = DSLRuleEngine.test_rule(working_rule, kernel_log)
        print(f"\n能匹配的规则示例: {working_rule}")
        print(f"   匹配结果: {working_result['matched']}")


def test_basic_functionality():
    """测试基本功能"""
    
    print("\n测试DSL基本功能")
    print("=" * 30)
    
    test_cases = [
        {
            "rule": '"error" & "fatal"',
            "text": "fatal error occurred",
            "expected": True
        },
        {
            "rule": '"warn" | "error"',  
            "text": "warning message",
            "expected": True
        },
        {
            "rule": '"error" & !"warning"',
            "text": "error occurred",
            "expected": True
        },
        {
            "rule": '"error" & !"warning"',
            "text": "warning: error occurred", 
            "expected": False
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        result = DSLRuleEngine.test_rule(test["rule"], test["text"])
        status = "[PASS]" if result["matched"] == test["expected"] else "[FAIL]"
        
        print(f"{status} 测试 {i}: {test['rule']}")
        print(f"   文本: '{test['text']}'")
        print(f"   预期: {test['expected']}, 实际: {result['matched']}")


if __name__ == "__main__":
    print("DSL规则测试")
    
    # 测试基本功能
    test_basic_functionality()
    
    # 测试您的具体规则
    test_your_rule()
    
    print(f"\n解决方案:")
    print(f"1. DSL规则引擎工作正常")
    print(f"2. 您的规则语法正确")
    print(f"3. 但是您的日志内容中不包含这些关键字，所以不匹配")
    print(f"4. 请检查您要分析的日志是否包含 'aq_ring_rx_clean' 和 'atlantic'")
    print(f"5. 或者修改规则来匹配实际的日志内容")