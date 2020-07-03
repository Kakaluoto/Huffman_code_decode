import sys
from PyQt5.QtCore import QThread, pyqtSignal, QObject

sys.setrecursionlimit(1000000)  # 压缩大文件实时会出现超出递归深度，故修改限制
import time


# 节点类定义
class node(object):
    def __init__(self, value=None, left=None, right=None, father=None):
        self.value = value  # 节点的权值
        self.left = left  # 左节点
        self.right = right  # 右节点
        self.father = father  # 父节点

    def build_father(left, right):  # 构造父节点
        n = node(value=left.value + right.value, left=left, right=right)  # 子节点权值相加
        left.father = right.father = n
        return n

    def encode(n):  # huffman编码，从下往上递归遍历
        if n.father == None:
            return b''
        if n.father.left == n:
            return node.encode(n.father) + b'0'  # 左节点编码0
        else:
            return node.encode(n.father) + b'1'  # 右节点编码为1


# 只有继承了QObject类才可以使用信号
class HuffmanEncoder(QObject, object):
    progress = pyqtSignal(int)  # 发送进度信号，这个类可以向外发送当前进度值

    def __init__(self, node_dict=None, count_dict=None, ec_dict=None, nodes=None, inverse_dict=None):
        super(HuffmanEncoder, self).__init__()
        if node_dict is None:
            node_dict = {}
            # 存储节点的字典，key为读入的字节，value为对应的节点对象
        if count_dict is None:
            count_dict = {}
            # 字符频率对应字典，key为读入的字节(字符)，value为该字节出现次数，为了解码重构哈夫曼树
        if ec_dict is None:
            ec_dict = {}
            # 符号编码表 key:字节(符号),value:编码如b'1001000'，都是字符串
        if nodes is None:
            nodes = []
            # 存放节点的列表
        if inverse_dict is None:
            inverse_dict = {}
            # 反向字典，key:编码 value:编码对应的字符
        self.node_dict = node_dict
        self.count_dict = count_dict
        self.ec_dict = ec_dict
        self.nodes = nodes
        self.inverse_dict = inverse_dict
        self.temp = 0  # 当前进度，用于向外发送信号

    # 构造哈夫曼树
    def build_tree(self, l):
        if len(l) == 1:
            return l
            # 节点列表只剩一个根节点的时候，返回
            # 此时根节点连接了两个子节点，子节点又连接了孙节点，可以通过叶子节点递归遍历
        sorts = sorted(l, key=lambda x: x.value, reverse=False)  # 根据节点的权值进行排序
        n = node.build_father(sorts[0], sorts[1])  # 权值最小的两个节点，生成父节点
        sorts.pop(0)  # 将节点列表里面节点权值最小的丢掉
        sorts.pop(0)  # 继续把参与合并的第二个节点丢掉
        sorts.append(n)  # 把合并之后得到新权值的父节点，加入节点列表
        return self.build_tree(sorts)  # 递归构造

    # 可以看出，因为每次都是选择最小的两个节点，其中较小的那个节点做左节点，较大的做右节点
    # 所以编码结果是唯一的，与手工编码随机选取左右节点不同

    # 当树构建好之后调用，根据每个叶子结点，从下往上编码
    def encode(self, echo):
        # node_dict存储节点的字典，key为读入的字节，value为对应的节点对象
        for x in self.node_dict.keys():
            # ec_dict[x]符号编码表 key:字节(符号),value:编码如b'1001000'
            self.ec_dict[x] = node.encode(self.node_dict[x])
            if echo:  # 输出编码表（用于调试）
                print(x)
                print(self.ec_dict[x])

    # 编码函数
    def encodefile(self, inputfile, outputfile):
        node_dict = self.node_dict
        # node_dict存储节点的字典，key为读入的字节，value为对应的节点对象
        count_dict = self.count_dict
        # 字符频率对应字典，key为读入的字节(字符)，value为该字节出现次数，为了解码重构哈夫曼树
        ec_dict = self.ec_dict
        # ec_dict[x]符号编码表 key:字节(符号),value:编码如b'1001000'
        print("Starting encode...")
        f = open(inputfile, "rb")
        bytes_width = 1  # 每次读取的字节宽度
        i = 0

        f.seek(0, 2)
        count = f.tell() / bytes_width  # 一共有多少个符号数
        print(count)
        nodes = []  # 结点列表，用于构建哈夫曼树
        buff = [b''] * int(count)  # 初始化字节存储列表buff
        f.seek(0)

        # 计算字符频率,并将单个字符构建成单一节点
        while i < count:
            buff[i] = f.read(bytes_width)  # 每次读取bytes_width个字节
            if count_dict.get(buff[i], -1) == -1:
                count_dict[buff[i]] = 0  # key:buff[i] ，value:0
            count_dict[buff[i]] = count_dict[buff[i]] + 1
            i = i + 1
        print("Read OK")
        print(count_dict)  # 输出权值字典,可注释掉
        for x in count_dict.keys():
            node_dict[x] = node(count_dict[x])
            # 生成一个频率为count_dict[x]的节点，存入字典 node_dict[x]
            nodes.append(node_dict[x])
            # 把这个节点加入节点列表

        f.close()
        tree = self.build_tree(nodes)  # 哈夫曼树构建
        self.encode(False)  # 构建编码表
        print("Encode OK")
        # sorted_nodes是被排过序的节点列表[(key1,value1),(key2,value2)...]
        # 每个元素是一个元组(key,value)，其中key是对应的字符(字节),value是该字符出现的频率
        sorted_nodes = sorted(count_dict.items(), key=lambda x: x[1], reverse=True)
        # 对所有根节点进行排序，找出频率最高的节点
        bit_width = 1
        print("head:", sorted_nodes[0][1])
        # 动态调整编码表的字节长度，优化文件头大小，sorted_nodes[0][1]即value1，最大的频率值
        # 计算存储最大频率值需要的字节数
        if sorted_nodes[0][1] > 255:
            bit_width = 2
            if sorted_nodes[0][1] > 65535:
                bit_width = 3
                if sorted_nodes[0][1] > 16777215:
                    bit_width = 4
        print("bit_width:", bit_width)
        i = 0  # 计数变量，用于遍历所有字节
        byte_written = 0b1
        # 初始化为1占位，移位运算调用bit_length判断当前长度，这个变量是要被写入硬盘的

        o = open(outputfile, 'wb')
        name = inputfile.split('/')
        o.write((name[len(name) - 1] + '\n').encode(encoding="utf-8"))  # 写出原文件名
        o.write(int.to_bytes(len(ec_dict), 2, byteorder='big'))  # 写出不同符号种类数，即叶子结点总数
        o.write(int.to_bytes(bit_width, 1, byteorder='big'))  # 写出编码表字节宽度
        for x in ec_dict.keys():  # 编码文件头
            o.write(x)  # 写入符号
            o.write(int.to_bytes(count_dict[x], bit_width, byteorder='big'))  # 写入符号对应频率

        print('head OK')
        # 注意是按字节写入
        while i < count:  # 开始压缩数据,一个一个字节遍历，将编码结果写入
            for x in ec_dict[buff[i]]:
                # buff[i]是一个符号(字节)，作为key从编码字典ec_dict[buff[i]]取出一个编码b'1100...111000..'，类型是字符串
                byte_written = byte_written << 1  # 右移腾出空位
                if x == 49:  # 如果，x当前是'1'，那就将byte_written最后一位置1
                    byte_written = byte_written | 1
                if byte_written.bit_length() == 9:
                    # 一个字节有8位，9位包含了第一位是1的那个占位符,因为bit_length只从第一个非0位算起
                    byte_written = byte_written & (~(1 << 8))  # 取出一个字节，即低8位
                    o.write(int.to_bytes(byte_written, 1, byteorder='big'))
                    o.flush()  # 立即写入，更新缓冲区
                    byte_written = 0b1  # 置1复位
            tem = int(i / len(buff) * 100)
            if tem > 0:
                if tem - self.temp >= 1:  # 防止频繁发送信号阻塞主线程UI
                    print("encode:", tem, '%')  # 输出压缩进度
                    if tem > 95:
                        self.temp = 100
                    else:
                        self.temp = tem
                    self.progress.emit(self.temp)  # 发送当前进度
            i = i + 1

        if byte_written.bit_length() > 1:  # 处理文件尾部不足一个字节的数据
            byte_written = byte_written << (8 - (byte_written.bit_length() - 1))
            byte_written = byte_written & (~(1 << byte_written.bit_length() - 1))
            o.write(int.to_bytes(byte_written, 1, byteorder='big'))
        o.close()
        self.node_dict = node_dict
        self.count_dict = count_dict
        self.ec_dict = ec_dict
        self.nodes = nodes
        print("File encode successful.")

    def decodefile(self, inputfile, outputfile):
        node_dict = self.node_dict
        # node_dict存储节点的字典，key为读入的字节，value为对应的节点对象
        ec_dict = self.ec_dict
        # 字符频率对应字典，key为读入的字节(字符)，value为该字节出现次数，为了解码重构哈夫曼树
        inverse_dict = self.inverse_dict
        # 反向字典，key:编码 value:编码对应的字符
        nodes = self.nodes  # 存放节点的列表
        print("Starting decode...")
        count = 0
        byte_written = 0
        f = open(inputfile, 'rb')
        f.seek(0, 2)
        eof = f.tell()  # 获取文件末尾位置
        f.seek(0)
        outputfile = (outputfile + f.readline().decode(encoding="utf-8")).replace('\n', '')
        # 文件保存路径和文件名结合生成文件指针
        o = open(outputfile, 'wb')
        count = int.from_bytes(f.read(2), byteorder='big')  # 取出叶子结点数量，也就是不同符号种类数
        bit_width = int.from_bytes(f.read(1), byteorder='big')  # 取出编码表字宽
        i = 0
        de_dict = {}
        while i < count:  # 解析文件头
            key = f.read(1)  # 取出符号
            value = int.from_bytes(f.read(bit_width), byteorder='big')  # 取出符号对应频率
            de_dict[key] = value  # 建立符号频率表 key:符号 value:该符号出现次数
            i = i + 1
        for x in de_dict.keys():
            node_dict[x] = node(de_dict[x])
            nodes.append(node_dict[x])
        tree = self.build_tree(nodes)  # 重建哈夫曼树
        self.encode(False)  # 建立编码表，此时产生 self.ec_dict编码字典，key:符号，value:b'010101....1010..'
        for x in ec_dict.keys():  # 反向字典构建
            inverse_dict[ec_dict[x]] = x  # key和value对调,key:是编码b'010101....1010..',value:是x即符号，8位
        i = f.tell()  # 获取当前指针位置
        data = b''
        while i < eof:  # 开始解压数据
            byte_written = int.from_bytes(f.read(1), byteorder='big')
            # print("byte_written:",byte_written)
            i = i + 1
            j = 8  # 一个字节八位
            while j > 0:
                if (byte_written >> (j - 1)) & 1 == 1:  # 取最高位判断
                    data = data + b'1'
                    byte_written = byte_written & (~(1 << (j - 1)))  # 去掉最高位，保留剩下几位
                else:
                    data = data + b'0'
                    byte_written = byte_written & (~(1 << (j - 1)))
                if inverse_dict.get(data, 0) != 0:  # key:是编码b'010101....1010..',value:是x即符号，8位
                    o.write(inverse_dict[data])
                    o.flush()
                    # print("decode",data,":",inverse_dict[data])
                    data = b''  # 如果匹配到了就清零，如果没有就不清零，比如码长大于8，不会清零会继续变长直到匹配
                j = j - 1
            tem = int(i / eof * 100)
            if tem > 0:
                if tem - self.temp >= 1:
                    print("decode:", tem, '%')  # 输出解压进度
                    if tem > 95:
                        self.temp = 100
                    else:
                        self.temp = tem
                    self.progress.emit(self.temp)
            byte_written = 0

        f.close()
        o.close()
        print("File decode successful.")
