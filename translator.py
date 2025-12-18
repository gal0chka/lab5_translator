#!/usr/bin/env python3
"""
Транслятор для языка выражений с операциями pow, +, * над INT
Галкин Артемий, КМБО-02-23, Вариант 6

Грамматика (используемая в парсере):
<Expr>      ::= <Sum>
<Sum>       ::= <Prod> <SumTail>
<SumTail>   ::= "+" <Prod> <SumTail> | ε
<Prod>      ::= <Atom> <ProdTail>
<ProdTail>  ::= "*" <Atom> <ProdTail> | ε
<Atom>      ::= INT | "pow" "(" <Expr> "," <Expr> ")"
"""

import sys
import os

# =============================================
# 1. СКАНЕР (Лексический анализатор)
# =============================================

class Token:
    """Класс для представления токена"""
    def __init__(self, type, value=None, line=None, col=None):
        self.type = type      # тип токена: INT, POW, LPAREN, RPAREN, COMMA, PLUS, MULT, EOF, ERROR
        self.value = value    # значение (для чисел)
        self.line = line      # номер строки
        self.col = col        # номер колонки
    
    def __repr__(self):
        if self.value is not None:
            return f"Token({self.type}, {self.value}, line={self.line}, col={self.col})"
        return f"Token({self.type}, line={self.line}, col={self.col})"

class Scanner:
    """Сканер для преобразования потока символов в поток токенов"""
    
    # Определение типов токенов
    INT = 'INT'
    POW = 'POW'
    LPAREN = '('
    RPAREN = ')'
    COMMA = ','
    PLUS = '+'
    MULT = '*'
    EOF = 'EOF'
    ERROR = 'ERROR'
    
    def __init__(self, source):
        self.source = source      # исходный текст
        self.tokens = []          # список токенов
        self.pos = 0              # текущая позиция в строке
        self.line = 1             # текущая строка
        self.col = 1              # текущая колонка
        self.errors = []          # список ошибок сканера
    
    def scan(self):
        """Основной метод сканирования"""
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            
            # Пропускаем пробельные символы
            if ch in ' \t':
                self.pos += 1
                self.col += 1
                continue
            
            # Обработка новой строки
            if ch == '\n':
                self.pos += 1
                self.line += 1
                self.col = 1
                continue
            
            # Распознавание чисел
            if ch.isdigit():
                start_col = self.col
                num_str = ''
                while self.pos < len(self.source) and self.source[self.pos].isdigit():
                    num_str += self.source[self.pos]
                    self.pos += 1
                    self.col += 1
                try:
                    value = int(num_str)
                    if value < 0:
                        self._add_error(f"Отрицательное число: {value}", self.line, start_col)
                        self.tokens.append(Token(self.ERROR, value, self.line, start_col))
                    else:
                        self.tokens.append(Token(self.INT, value, self.line, start_col))
                except ValueError:
                    self._add_error(f"Некорректное число: {num_str}", self.line, start_col)
                    self.tokens.append(Token(self.ERROR, num_str, self.line, start_col))
                continue
            
            # Распознавание ключевого слова pow
            if ch == 'p':
                if self.pos + 2 < len(self.source) and self.source[self.pos:self.pos+3] == 'pow':
                    self.tokens.append(Token(self.POW, None, self.line, self.col))
                    self.pos += 3
                    self.col += 3
                    continue
                else:
                    self._add_error(f"Неизвестный идентификатор: {ch}", self.line, self.col)
                    self.tokens.append(Token(self.ERROR, ch, self.line, self.col))
                    self.pos += 1
                    self.col += 1
                    continue
            
            # Распознавание одиночных символов
            if ch == '(':
                self.tokens.append(Token(self.LPAREN, None, self.line, self.col))
                self.pos += 1
                self.col += 1
                continue
            
            if ch == ')':
                self.tokens.append(Token(self.RPAREN, None, self.line, self.col))
                self.pos += 1
                self.col += 1
                continue
            
            if ch == ',':
                self.tokens.append(Token(self.COMMA, None, self.line, self.col))
                self.pos += 1
                self.col += 1
                continue
            
            if ch == '+':
                self.tokens.append(Token(self.PLUS, None, self.line, self.col))
                self.pos += 1
                self.col += 1
                continue
            
            if ch == '*':
                self.tokens.append(Token(self.MULT, None, self.line, self.col))
                self.pos += 1
                self.col += 1
                continue
            
            # Неизвестный символ
            self._add_error(f"Неизвестный символ: '{ch}'", self.line, self.col)
            self.tokens.append(Token(self.ERROR, ch, self.line, self.col))
            self.pos += 1
            self.col += 1
        
        # Добавляем токен конца файла
        self.tokens.append(Token(self.EOF, None, self.line, self.col))
        return self.tokens
    
    def _add_error(self, message, line, col):
        """Добавление ошибки сканера"""
        self.errors.append(f"[СКАНЕР] Строка {line}, позиция {col}: {message}")
    
    def print_errors(self):
        """Вывод ошибок сканера"""
        for error in self.errors:
            print(error)

# =============================================
# 2. ПАРСЕР (Синтаксический анализатор)
# =============================================

class Parser:
    """Рекурсивный нисходящий предикативный распознаватель"""
    
    def __init__(self, tokens):
        self.tokens = tokens          # поток токенов
        self.pos = 0                  # текущая позиция в потоке токенов
        self.current_token = None     # текущий токен
        self.errors = []              # список синтаксических ошибок
        self.ast = None               # AST дерево
        self._advance()               # инициализация первого токена
    
    def _advance(self):
        """Переход к следующему токену"""
        if self.pos < len(self.tokens):
            self.current_token = self.tokens[self.pos]
            self.pos += 1
        return self.current_token
    
    def _match(self, expected_type):
        """Проверка соответствия текущего токена ожидаемому типу"""
        if self.current_token.type == expected_type:
            token = self.current_token
            self._advance()
            return token
        else:
            self._add_error(f"Ожидается {expected_type}, получен {self.current_token.type}", 
                          self.current_token.line, self.current_token.col)
            return None
    
    def _peek(self):
        """Просмотр следующего токена без продвижения"""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None
    
    def _add_error(self, message, line, col):
        """Добавление синтаксической ошибки"""
        self.errors.append(f"[СИНТАКСИС] Строка {line}, позиция {col}: {message}")
    
    # ================= НЕТЕРМИНАЛЫ ГРАММАТИКИ =================
    
    def parse_expr(self):
        """
        <Expr> ::= <Sum>
        """
        return self.parse_sum()
    
    def parse_sum(self):
        """
        <Sum> ::= <Prod> <SumTail>
        """
        node = self.parse_prod()
        if node is None:
            return None
        
        sum_tail_node = self.parse_sum_tail()
        if sum_tail_node is None:
            return node
        
        # Если есть SumTail, создаем узел для цепочки сложений
        while sum_tail_node:
            if sum_tail_node[0] == '+':
                right = self.parse_prod()
                if right is None:
                    return None
                node = ('+', node, right)
                sum_tail_node = self.parse_sum_tail()
            else:
                break
        
        return node
    
    def parse_sum_tail(self):
        """
        <SumTail> ::= "+" <Prod> <SumTail> | ε
        Возвращает кортеж ('+',) если найден '+', иначе None
        """
        if self.current_token.type == Scanner.PLUS:
            token = self._match(Scanner.PLUS)
            if token is None:
                return None
            return ('+',)
        return None
    
    def parse_prod(self):
        """
        <Prod> ::= <Atom> <ProdTail>
        """
        node = self.parse_atom()
        if node is None:
            return None
        
        prod_tail_node = self.parse_prod_tail()
        if prod_tail_node is None:
            return node
        
        # Если есть ProdTail, создаем узел для цепочки умножений
        while prod_tail_node:
            if prod_tail_node[0] == '*':
                right = self.parse_atom()
                if right is None:
                    return None
                node = ('*', node, right)
                prod_tail_node = self.parse_prod_tail()
            else:
                break
        
        return node
    
    def parse_prod_tail(self):
        """
        <ProdTail> ::= "*" <Atom> <ProdTail> | ε
        Возвращает кортеж ('*',) если найден '*', иначе None
        """
        if self.current_token.type == Scanner.MULT:
            token = self._match(Scanner.MULT)
            if token is None:
                return None
            return ('*',)
        return None
    
    def parse_atom(self):
        """
        <Atom> ::= INT | "pow" "(" <Expr> "," <Expr> ")"
        """
        # Вариант 1: INT
        if self.current_token.type == Scanner.INT:
            token = self._match(Scanner.INT)
            if token is None:
                return None
            return ('INT', token.value)
        
        # Вариант 2: "pow" "(" <Expr> "," <Expr> ")"
        elif self.current_token.type == Scanner.POW:
            pow_token = self._match(Scanner.POW)
            if pow_token is None:
                return None
            
            if not self._match(Scanner.LPAREN):
                return None
            
            # Первый аргумент
            arg1 = self.parse_expr()
            if arg1 is None:
                return None
            
            if not self._match(Scanner.COMMA):
                self._add_error("Ожидается запятая между аргументами pow", 
                              self.current_token.line, self.current_token.col)
                return None
            
            # Второй аргумент
            arg2 = self.parse_expr()
            if arg2 is None:
                return None
            
            if not self._match(Scanner.RPAREN):
                self._add_error("Ожидается закрывающая скобка ')'", 
                              self.current_token.line, self.current_token.col)
                return None
            
            return ('pow', arg1, arg2)
        
        else:
            self._add_error(f"Ожидается INT или pow, получен {self.current_token.type}", 
                          self.current_token.line, self.current_token.col)
            return None
    
    def parse(self):
        """
        Основной метод парсинга
        """
        self.ast = self.parse_expr()
        
        # Проверяем, что достигли конца файла
        if self.current_token.type != Scanner.EOF:
            self._add_error(f"Неожиданный токен в конце: {self.current_token.type}", 
                          self.current_token.line, self.current_token.col)
        
        return self.ast
    
    def print_errors(self):
        """Вывод синтаксических ошибок"""
        for error in self.errors:
            print(error)

# =============================================
# 3. СЕМАНТИЧЕСКИЙ АНАЛИЗАТОР (Вычисление значения)
# =============================================

class SemanticAnalyzer:
    """Семантический анализатор для вычисления значения выражения"""
    
    def __init__(self, ast):
        self.ast = ast
        self.errors = []
    
    def evaluate(self, node=None):
        """
        Рекурсивное вычисление значения AST
        """
        if node is None:
            node = self.ast
        
        if node is None:
            self.errors.append("[СЕМАНТИКА] Пустое AST дерево")
            return None
        
        node_type = node[0]
        
        # Целое число
        if node_type == 'INT':
            return node[1]
        
        # Операция сложения
        elif node_type == '+':
            left_val = self.evaluate(node[1])
            right_val = self.evaluate(node[2])
            
            if left_val is None or right_val is None:
                return None
            
            # Проверка переполнения
            try:
                result = left_val + right_val
                if result < 0:  # В нашем языке только положительные числа
                    self.errors.append(f"[СЕМАНТИКА] Отрицательный результат сложения: {left_val} + {right_val}")
                    return None
                return result
            except OverflowError:
                self.errors.append(f"[СЕМАНТИКА] Переполнение при сложении: {left_val} + {right_val}")
                return None
        
        # Операция умножения
        elif node_type == '*':
            left_val = self.evaluate(node[1])
            right_val = self.evaluate(node[2])
            
            if left_val is None or right_val is None:
                return None
            
            # Проверка переполнения
            try:
                result = left_val * right_val
                if result < 0:  # В нашем языке только положительные числа
                    self.errors.append(f"[СЕМАНТИКА] Отрицательный результат умножения: {left_val} * {right_val}")
                    return None
                return result
            except OverflowError:
                self.errors.append(f"[СЕМАНТИКА] Переполнение при умножении: {left_val} * {right_val}")
                return None
        
        # Функция pow (возведение в степень)
        elif node_type == 'pow':
            base = self.evaluate(node[1])
            exponent = self.evaluate(node[2])
            
            if base is None or exponent is None:
                return None
            
            # Проверка на отрицательные значения
            if base < 0 or exponent < 0:
                self.errors.append(f"[СЕМАНТИКА] Отрицательные аргументы в pow: pow({base}, {exponent})")
                return None
            
            # Проверка на слишком большие значения
            if exponent > 1000:  # Практическое ограничение
                self.errors.append(f"[СЕМАНТИКА] Слишком большая степень: {exponent}")
                return None
            
            try:
                result = pow(base, exponent)
                if result < 0:
                    self.errors.append(f"[СЕМАНТИКА] Отрицательный результат pow: pow({base}, {exponent})")
                    return None
                return result
            except OverflowError:
                self.errors.append(f"[СЕМАНТИКА] Переполнение при возведении в степень: pow({base}, {exponent})")
                return None
        
        else:
            self.errors.append(f"[СЕМАНТИКА] Неизвестный тип узла: {node_type}")
            return None
    
    def print_ast(self, node=None, indent=0):
        """
        Красивый вывод AST дерева
        """
        if node is None:
            node = self.ast
        
        if node is None:
            return
        
        node_type = node[0]
        
        if node_type == 'INT':
            print("  " * indent + f"INT: {node[1]}")
        elif node_type == '+':
            print("  " * indent + "ADD (+)")
            self.print_ast(node[1], indent + 1)
            self.print_ast(node[2], indent + 1)
        elif node_type == '*':
            print("  " * indent + "MULT (*)")
            self.print_ast(node[1], indent + 1)
            self.print_ast(node[2], indent + 1)
        elif node_type == 'pow':
            print("  " * indent + "POW")
            self.print_ast(node[1], indent + 1)
            self.print_ast(node[2], indent + 1)
    
    def print_errors(self):
        """Вывод семантических ошибок"""
        for error in self.errors:
            print(error)

# =============================================
# 4. ОСНОВНАЯ ПРОГРАММА
# =============================================

def main():
    """Основная функция программы"""
    
    print("=" * 60)
    print("ТРАНСЛЯТОР ДЛЯ ЯЗЫКА ВЫРАЖЕНИЙ С pow, +, *")
    print("Галкин Артемий, КМБО-02-23, Вариант 6")
    print("=" * 60)
    
    # Чтение входных данных
    if len(sys.argv) > 1:
        # Чтение из файла
        filename = sys.argv[1]
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                source = f.read()
            print(f"Чтение из файла: {filename}")
        except FileNotFoundError:
            print(f"Ошибка: Файл '{filename}' не найден")
            return
        except Exception as e:
            print(f"Ошибка при чтении файла: {e}")
            return
    else:
        # Чтение из stdin
        print("Введите выражение (Ctrl+D для завершения ввода):")
        try:
            source = sys.stdin.read()
        except KeyboardInterrupt:
            print("\nВвод прерван")
            return
    
    if not source.strip():
        print("Ошибка: Пустой ввод")
        return
    
    print(f"\nВходное выражение: {source.strip()}")
    
    # ================= 1. ЛЕКСИЧЕСКИЙ АНАЛИЗ =================
    print("\n" + "=" * 60)
    print("1. ЛЕКСИЧЕСКИЙ АНАЛИЗ (СКАНЕР)")
    print("=" * 60)
    
    scanner = Scanner(source)
    tokens = scanner.scan()
    
    if scanner.errors:
        print("Обнаружены ошибки сканера:")
        scanner.print_errors()
        print("\nТокены (включая ошибки):")
    else:
        print("Лексический анализ завершен успешно!")
        print("\nРаспознанные токены:")
    
    for i, token in enumerate(tokens):
        if token.type != Scanner.EOF:
            print(f"  {i:3d}: {token}")
    
    # ================= 2. СИНТАКСИЧЕСКИЙ АНАЛИЗ =================
    print("\n" + "=" * 60)
    print("2. СИНТАКСИЧЕСКИЙ АНАЛИЗ (ПАРСЕР)")
    print("=" * 60)
    
    parser = Parser(tokens)
    ast = parser.parse()
    
    if parser.errors:
        print("Обнаружены синтаксические ошибки:")
        parser.print_errors()
        return
    
    print("Синтаксический анализ завершен успешно!")
    print("\nАбстрактное синтаксическое дерево (AST):")
    
    # ================= 3. СЕМАНТИЧЕСКИЙ АНАЛИЗ =================
    print("\n" + "=" * 60)
    print("3. СЕМАНТИЧЕСКИЙ АНАЛИЗ И ВЫЧИСЛЕНИЕ")
    print("=" * 60)
    
    semantic = SemanticAnalyzer(ast)
    
    # Вывод AST
    semantic.print_ast()
    
    # Вычисление значения
    print("\nВычисление значения выражения:")
    result = semantic.evaluate()
    
    if semantic.errors:
        print("Обнаружены семантические ошибки:")
        semantic.print_errors()
    elif result is not None:
        print(f"\n✓ РЕЗУЛЬТАТ: {result}")
        
        # Дополнительная проверка
        print("\nПроверка корректности результата:")
        try:
            # Безопасная проверка через eval (только для демонстрации)
            # ВНИМАНИЕ: eval используется только для демонстрации!
            # В реальном трансляторе это было бы небезопасно
            safe_source = source.strip().replace('pow', '**')
            eval_result = eval(safe_source, {"__builtins__": {}}, {})
            print(f"  Результат вычисления Python: {eval_result}")
            if result == eval_result:
                print("  ✓ Результаты совпадают!")
            else:
                print(f"  ⚠ Результаты различаются (возможно переполнение)")
        except:
            print("  ⚠ Невозможно выполнить проверку через eval")
    else:
        print("\n✗ Не удалось вычислить значение")
    
    print("\n" + "=" * 60)
    print("РАБОТА ЗАВЕРШЕНА")
    print("=" * 60)

# =============================================
# ТЕСТИРОВАНИЕ
# =============================================

def run_tests():
    """Функция для тестирования транслятора"""
    test_cases = [
        # (выражение, ожидаемый результат)
        ("7", 7),
        ("4+5*6", 34),  # 4 + (5*6) = 34
        ("pow(10,2)", 100),
        ("pow(2,pow(3,4))", 2 ** (3 ** 4)),
        ("pow(1+3,2*5)+9", (1+3) ** (2*5) + 9),
        ("2*3+4*5", 26),  # (2*3) + (4*5) = 6 + 20 = 26
        ("pow(2,3)*4", 32),  # 8 * 4 = 32
    ]
    
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ ТРАНСЛЯТОРА")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for i, (expr, expected) in enumerate(test_cases, 1):
        print(f"\nТест {i}: {expr}")
        print(f"Ожидаемый результат: {expected}")
        
        # Лексический анализ
        scanner = Scanner(expr)
        tokens = scanner.scan()
        
        if scanner.errors:
            print(f"  ✗ Ошибка сканера: {scanner.errors[0]}")
            failed += 1
            continue
        
        # Синтаксический анализ
        parser = Parser(tokens)
        ast = parser.parse()
        
        if parser.errors:
            print(f"  ✗ Ошибка парсера: {parser.errors[0]}")
            failed += 1
            continue
        
        # Семантический анализ
        semantic = SemanticAnalyzer(ast)
        result = semantic.evaluate()
        
        if semantic.errors:
            print(f"  ✗ Семантическая ошибка: {semantic.errors[0]}")
            failed += 1
        elif result == expected:
            print(f"  ✓ Успех: {result}")
            passed += 1
        else:
            print(f"  ✗ Несоответствие: получено {result}, ожидалось {expected}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"ИТОГ: {passed} пройдено, {failed} не пройдено")
    print("=" * 60)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        run_tests()
    else:
        main()