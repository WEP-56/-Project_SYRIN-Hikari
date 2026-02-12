#!/usr/bin/env python3
"""
斐波那契数列计算器
支持多种计算方法和输出格式
"""

def fibonacci_iterative(n: int) -> int:
    """
    迭代法计算斐波那契数列第n项
    时间复杂度: O(n)
    空间复杂度: O(1)
    """
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


def fibonacci_recursive(n: int) -> int:
    """
    递归法计算斐波那契数列第n项
    时间复杂度: O(2^n) - 不推荐用于大数
    空间复杂度: O(n) - 递归栈深度
    """
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fibonacci_recursive(n - 1) + fibonacci_recursive(n - 2)


def fibonacci_memoization(n: int, memo: dict = None) -> int:
    """
    带记忆化的递归法计算斐波那契数列第n项
    时间复杂度: O(n)
    空间复杂度: O(n)
    """
    if memo is None:
        memo = {0: 0, 1: 1}
    
    if n in memo:
        return memo[n]
    
    memo[n] = fibonacci_memoization(n - 1, memo) + fibonacci_memoization(n - 2, memo)
    return memo[n]


def fibonacci_generator(n: int):
    """
    生成器方式生成斐波那契数列前n项
    """
    a, b = 0, 1
    for _ in range(n):
        yield a
        a, b = b, a + b


def fibonacci_matrix(n: int) -> int:
    """
    矩阵快速幂法计算斐波那契数列第n项
    时间复杂度: O(log n)
    空间复杂度: O(1)
    """
    if n <= 0:
        return 0
    
    def matrix_multiply(a, b):
        return [
            [a[0][0]*b[0][0] + a[0][1]*b[1][0], a[0][0]*b[0][1] + a[0][1]*b[1][1]],
            [a[1][0]*b[0][0] + a[1][1]*b[1][0], a[1][0]*b[0][1] + a[1][1]*b[1][1]]
        ]
    
    def matrix_power(matrix, power):
        result = [[1, 0], [0, 1]]  # 单位矩阵
        while power > 0:
            if power % 2 == 1:
                result = matrix_multiply(result, matrix)
            matrix = matrix_multiply(matrix, matrix)
            power //= 2
        return result
    
    base_matrix = [[1, 1], [1, 0]]
    powered_matrix = matrix_power(base_matrix, n - 1)
    return powered_matrix[0][0]


def print_fibonacci_sequence(n: int, method: str = 'iterative'):
    """
    打印斐波那契数列前n项
    
    Args:
        n: 要计算的项数
        method: 计算方法，可选 'iterative', 'recursive', 'memoization', 'matrix'
    """
    if n <= 0:
        print("请输入大于0的整数")
        return
    
    print(f"斐波那契数列前{n}项:")
    
    if method == 'iterative':
        # 使用迭代法
        a, b = 0, 1
        sequence = []
        for i in range(n):
            sequence.append(a)
            a, b = b, a + b
        print(" ".join(str(x) for x in sequence))
        
    elif method == 'recursive':
        # 使用递归法（仅适用于小n）
        if n > 35:
            print(f"警告：递归法计算{n}项可能非常慢，建议使用其他方法")
        sequence = [fibonacci_recursive(i) for i in range(n)]
        print(" ".join(str(x) for x in sequence))
        
    elif method == 'memoization':
        # 使用记忆化递归
        sequence = [fibonacci_memoization(i) for i in range(n)]
        print(" ".join(str(x) for x in sequence))
        
    elif method == 'matrix':
        # 使用矩阵快速幂法
        sequence = [fibonacci_matrix(i) for i in range(n)]
        print(" ".join(str(x) for x in sequence))
        
    elif method == 'generator':
        # 使用生成器
        sequence = list(fibonacci_generator(n))
        print(" ".join(str(x) for x in sequence))
        
    else:
        print(f"未知的计算方法: {method}")
        print("可用的方法: iterative, recursive, memoization, matrix, generator")


def benchmark_methods(n: int = 30):
    """
    比较不同方法的性能
    """
    import time
    
    methods = [
        ('迭代法', fibonacci_iterative),
        ('记忆化递归', lambda x: fibonacci_memoization(x)),
        ('矩阵快速幂', fibonacci_matrix),
    ]
    
    print(f"\n性能测试 (计算第{n}项斐波那契数):")
    print("-" * 50)
    
    for method_name, method_func in methods:
        start_time = time.time()
        result = method_func(n)
        elapsed_time = time.time() - start_time
        
        print(f"{method_name}:")
        print(f"  结果: {result}")
        print(f"  耗时: {elapsed_time:.6f}秒")
        print()


def main():
    """
    主函数：提供交互式界面
    """
    print("斐波那契数列计算器")
    print("=" * 50)
    
    while True:
        print("\n选项:")
        print("1. 计算斐波那契数列前n项")
        print("2. 计算第n项斐波那契数")
        print("3. 性能比较测试")
        print("4. 退出")
        
        choice = input("\n请选择 (1-4): ").strip()
        
        if choice == '1':
            try:
                n = int(input("请输入项数 n: "))
                if n <= 0:
                    print("项数必须大于0")
                    continue
                    
                print("\n可用的计算方法:")
                print("1. iterative - 迭代法 (推荐)")
                print("2. recursive - 递归法 (仅适用于小n)")
                print("3. memoization - 记忆化递归")
                print("4. matrix - 矩阵快速幂法")
                print("5. generator - 生成器")
                
                method_choice = input("请选择计算方法 (1-5, 默认1): ").strip()
                method_map = {
                    '1': 'iterative',
                    '2': 'recursive',
                    '3': 'memoization',
                    '4': 'matrix',
                    '5': 'generator'
                }
                
                method = method_map.get(method_choice, 'iterative')
                print_fibonacci_sequence(n, method)
                
            except ValueError:
                print("请输入有效的整数")
                
        elif choice == '2':
            try:
                n = int(input("请输入项数 n (从0开始): "))
                if n < 0:
                    print("项数不能为负数")
                    continue
                    
                print(f"\n第{n}项斐波那契数:")
                print(f"迭代法: {fibonacci_iterative(n)}")
                print(f"记忆化递归: {fibonacci_memoization(n)}")
                print(f"矩阵快速幂: {fibonacci_matrix(n)}")
                
            except ValueError:
                print("请输入有效的整数")
                
        elif choice == '3':
            try:
                n = int(input("请输入测试的项数 (默认30): ") or "30")
                benchmark_methods(n)
            except ValueError:
                print("请输入有效的整数")
                
        elif choice == '4':
            print("再见！")
            break
            
        else:
            print("无效的选择，请重新输入")


if __name__ == "__main__":
    # 示例用法
    print("示例输出:")
    print_fibonacci_sequence(10, 'iterative')
    print()
    
    # 运行交互式界面
    main()