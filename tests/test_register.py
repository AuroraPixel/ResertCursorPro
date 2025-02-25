#!/usr/bin/env python3
import os
import sys
import asyncio
from pathlib import Path

# 获取项目根目录
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent

# 将项目根目录添加到 Python 路径
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.components.register_account import AccountRegister

async def test_register():
    register = AccountRegister()
    # 测试单个账号注册
    # await register.register_single_account()
    
    # 测试批量注册
    await register.batch_register(1)

if __name__ == "__main__":
    asyncio.run(test_register()) 