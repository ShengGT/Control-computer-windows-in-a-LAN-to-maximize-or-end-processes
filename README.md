# 使用源代码运行程序或打包
# 安装依赖：打开命令提示符，执行以下命令安装Windows窗口操作库
pip install pywin32 pillow pystray psutil
# 先安装打包工具
pip install pyinstaller
# 打包被控端
pyinstaller -F -w 被控端.py
# 打包控制端
pyinstaller -F -w 控制端.py
