#!/usr/bin/env python3
import os
import sys
import asyncio

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_root)

from src.components.register_account import AccountRegister

async def main():
    register = AccountRegister()
    # 测试单个账号注册
    # await register.register_single_account()
    
    # 测试批量注册
    await register.batch_register(1)

if __name__ == "__main__":
    asyncio.run(main()) 