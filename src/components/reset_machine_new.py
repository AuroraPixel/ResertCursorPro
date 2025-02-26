import hashlib
import requests
import os
import re


# 本地支持版本的 MD5 映射
local_md5_map = {
    "1f53d40367d0ac76f3f123c83b901497": ["0.45.2~0.45.8[-5]", "0.45.11[-5]"],
    "1650464dc26313c87c789da60c0495d0": ["0.45.10[-5]"],
    "723d492726d0cfa5ac2ad0649f499ef5": ["0.45.15[-5]"],
    "2df7e08131902951452d37fe946b8b8c": ["0.46.0[-5]"],
    "44fd6c68052686e67c0402f69ae3f1bb": ["0.46.2[-5]"]
    # 添加其他 MD5
}

def fetch_md5_map():
    '''
    获取远程的 MD5 映射
    '''
    url = "https://gist.githubusercontent.com/Angels-Ray/11a0c8990750f4f563292a55c42465f1/raw"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as error:
        print(f"获取MD5列表失败 {url}: {error}")
    return local_md5_map

def calculate_md5_without_last_lines(file_path, lines_to_remove=5):
    '''
    计算文件的 MD5，去掉最后几行
    '''
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        if len(lines) < lines_to_remove:
            content = ''.join(lines)
        else:
            content = ''.join(lines[:-lines_to_remove])
        
        md5_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
        return md5_hash
    except Exception as e:
        raise Exception(f"计算 main.js md5失败: {str(e)}")
    
def update_main_js_content(file_path):
    md5 = calculate_md5_without_last_lines(file_path)
    md5_map = fetch_md5_map()

    if md5 not in md5_map:
        versions = ', '.join([' '.join(versions) for versions in md5_map.values()])
        message = f"当前 main.js 的版本可能未被支持, 或已修补过\n\n已支持的版本: {versions}\n\n是否仍要继续修补？"
        
        choice = input(message + " (y/n): ")
        if choice.lower() != 'y':
            raise Exception("操作已取消")

    try:
        # 创建备份文件
        backup_path = file_path + '.backup'
        if not os.path.exists(backup_path):
            with open(file_path, 'r', encoding='utf-8') as file:
                original_content = file.read()
            with open(backup_path, 'w', encoding='utf-8') as backup_file:
                backup_file.write(original_content)
        
        # 更新文件内容
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # 使用正则表达式替换内容
        patterns = [
            (r'async\s+(\w+)\s*\(\)\s*{\s*return\s+this\.[\w.]+\?\?\s*this\.([\w.]+)\.machineId\s*}', 
             r'async \1() { return this.\2.machineId }'),
            (r'async\s+(\w+)\s*\(\)\s*{\s*return\s+this\.[\w.]+\?\?\s*this\.([\w.]+)\.macMachineId\s*}', 
             r'async \1() { return this.\2.macMachineId }')
        ]

        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content)
        
        # 写入修改后的内容
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)

    except Exception as e:
        print(f"文件操作出错: {e}")