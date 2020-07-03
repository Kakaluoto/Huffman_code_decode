import subprocess, os
#提取文件夹图片资源自动生成qrc文件
images = os.listdir('./image')
f = open('images.qrc', 'w+')
f.write(u'<!DOCTYPE RCC>\n<RCC version="1.0">\n<qresource>\n')

for item in images:
    f.write(u'<file alias="image/'+ item +'">image/'+ item +'</file>\n')


f.write(u'</qresource>\n</RCC>')
f.close()

pipe = subprocess.Popen(r'pyrcc5 -o images.py images.qrc', stdout = subprocess.PIPE, stdin = subprocess.PIPE, stderr = subprocess.PIPE, creationflags=0x08)