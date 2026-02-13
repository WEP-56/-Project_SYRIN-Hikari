#!/usr/bin/env python3
# 打印10到1的数字倒计时脚本

def main():
    """打印10到1的数字"""
    print("开始倒计时：")
    
    # 方法1: 使用range函数倒序
    for i in range(10, 0, -1):
        print(i)
    
    print("倒计时结束！")

if __name__ == "__main__":
    main()