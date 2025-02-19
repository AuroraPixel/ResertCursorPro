# ResertCursorPro

这是一个跨平台的桌面应用程序，支持 macOS 和 Windows 系统。

## 开发环境要求

- Python 3.8+
- pip

## 环境设置

1. 创建虚拟环境：
```bash
python3 -m venv venv
```

2. 激活虚拟环境：
```bash
# macOS/Linux
source venv/bin/activate

# Windows
.\venv\Scripts\activate
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

## 开发

确保虚拟环境已激活，然后运行：
```bash
python src/main.py
```

## 打包

确保虚拟环境已激活，然后根据你的操作系统运行相应的命令：

### macOS
```bash
pyinstaller --windowed --name ResertCursorPro src/main.py
```

### Windows
```bash
pyinstaller --windowed --name ResertCursorPro src/main.py
```

打包后的可执行文件将在 `dist` 目录中生成。

## 退出虚拟环境

当你完成开发工作后，可以使用以下命令退出虚拟环境：
```bash
deactivate
``` 