# 创建时间：2024-12-06 17：00
# 功能：dd测试，数据块4, 8, 16, 32, 64, 128, 256, 512, 1024，测试完成生成HTML报告
# 使用方法：python3 dd_test_generate_report.py <测试选项> <测试文件大小>
import re
import subprocess
import time
from datetime import datetime
import os
import sys
import html # 用于生成HTML
import shutil  # 用于文件操作
import signal

# 全局变量，用于控制程序是否应该退出
should_exit = False

# 信号处理函数
def signal_handler(sig, frame):
    global should_exit
    print("\n\n收到终止信号，正在优雅退出...")
    should_exit = True
    
# 命令行显示说明
def show_usage():
    print("""
    使用方法：python3 dd_test_generate_report.py <测试选项> <测试文件大小> [测试轮数]

    测试选项:
    all - 测试所有SATA硬盘
    allmd - 测试所有MD阵列设备
    allvol - 测试所有挂载点文件系统
    <具体设备名> - 测试指定的单个设备(如sda或md1)
    <挂载点路径> - 测试指定的单个挂载点(如/volume1)
    
    测试文件大小:
    数字 - 以G为单位的测试文件大小
    test - 快速测试模式，只运行最小化测试以验证功能

    测试轮数(可选):
    数字 - 每个测试项重复测试的次数，默认为5次
    
    示例：

    正常测试所有SATA硬盘:
    python3 dd_test_generate_report.py all 5

    测试所有MD设备，每个测试项重复3次:
    python3 dd_test_generate_report.py allmd 5 3

    测试所有挂载点:
    python3 dd_test_generate_report.py allvol 5
    
    测试指定设备:
    python3 dd_test_generate_report.py sda 5
    python3 dd_test_generate_report.py md1 5 2
    
    测试指定挂载点:
    python3 dd_test_generate_report.py /volume1 5
    
    快速验证功能是否正常:
    python3 dd_test_generate_report.py all test

注：正常文件大小默认以G为单位，填写数字即可5即5G
    快速测试模式只做最少量的测试，用于验证流程是否工作正常
    Ctrl+C可以随时中断测试，已测试的数据会被保存

""")

# 邮件配置 - 已移除

# 获取设备型号，用于邮件的名称区分
def get_model():
    try:
        # 先尝试从fw_printenv获取ugmodel（针对ARM设备）
        cmd = "which fw_printenv >/dev/null 2>&1 && fw_printenv ugmodel 2>/dev/null | head -n 1"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        # 检查命令是否成功执行且有输出
        if result.returncode == 0 and result.stdout.strip():
            # 从输出中提取ugmodel值
            output = result.stdout.strip()
            
            # 分割字符串并获取型号，去除可能的ugsn后缀
            if '=' in output:
                model_name = output.split('=')[1].strip()
            else:
                model_name = output.strip()
                
            # 去除可能出现的ugsn后缀
            if "ugsn" in model_name.lower():
                model_name = model_name.lower().split("ugsn")[0].strip()
                
            print(f"从fw_printenv获取到设备型号: {model_name}")
            return model_name
        
        # 如果没有找到ugmodel，使用原始的dmidecode方法（针对x86设备）
        print("未找到ugmodel或非ARM设备，尝试使用dmidecode获取型号...")
        cmd = "dmidecode -t 1 | grep 'Product Name'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        # 检查命令是否成功执行
        if result.returncode == 0:
            # 从输出中提取Product Name
            output = result.stdout.strip()
            # 分割字符串并获取产品名称
            product_name = output.split(':')[1].strip() if ':' in output else "Unknown"
            return product_name
        else:
            return "Unknown"
    except Exception as e:
        print(f"获取设备型号出错: {str(e)}")
        return "Unknown"

# 获取系统固件版本
def get_system_version():
    try:
        cmd = "cat /etc/os-release | grep 'OS_VERSION'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            # 提取OS_VERSION后的内容
            output = result.stdout.strip()
            if '=' in output:
                version = output.split('=')[1].strip()
                return version
        # 如果没有OS_VERSION，尝试获取VERSION_ID
        cmd = "cat /etc/os-release | grep 'VERSION_ID'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            output = result.stdout.strip()
            if '=' in output:
                version = output.split('=')[1].strip().replace('"', '')
                return version
        return "Unknown"
    except Exception as e:
        print(f"Error: {str(e)}")
        return "Unknown"

# 获取系统内存信息
def get_memory_info():
    try:
        cmd = "free -h | grep 'Mem:'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            output = result.stdout.strip()
            parts = output.split()
            if len(parts) >= 2:
                return parts[1]  # 获取总内存大小
        return "Unknown"
    except Exception as e:
        print(f"Error: {str(e)}")
        return "Unknown"

# 获取系统中所有的SATA硬盘
def get_all_sata_disks():
    try:
        # 使用lsblk命令获取所有硬盘信息
        cmd = "lsblk -d -o NAME,TYPE | grep disk | awk '{print $1}'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            # 提取硬盘名称
            disks = result.stdout.strip().split('\n')
            # 过滤掉空行
            disks = [disk for disk in disks if disk]
            # 只保留sd开头的设备（真正的SATA硬盘），过滤掉mmcblk、zram等设备
            sata_disks = [disk for disk in disks if disk.startswith('sd')]
            return sata_disks
        return []
    except Exception as e:
        print(f"获取SATA硬盘列表出错: {str(e)}")
        return []

# 获取系统中所有的MD阵列设备
def get_all_md_devices():
    try:
        # 使用ls命令获取所有md设备
        cmd = "ls -1 /dev/md* 2>/dev/null | grep -E 'md[0-9]+$' | sed 's|/dev/||'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            # 提取md设备名称
            md_devices = result.stdout.strip().split('\n')
            # 过滤掉空行
            md_devices = [md for md in md_devices if md]
            return md_devices
        return []
    except Exception as e:
        print(f"获取MD阵列设备列表出错: {str(e)}")
        return []

# 获取系统中所有的挂载点
def get_all_mount_points():
    try:
        # 使用df命令获取所有挂载点信息
        cmd = "df -hT | grep -v Filesystem | grep -v tmpfs | grep -v devtmpfs | grep -v overlay"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            # 提取挂载点信息
            lines = result.stdout.strip().split('\n')
            mount_points = []
            for line in lines:
                parts = line.split()
                if len(parts) >= 7:  # df输出格式：文件系统 类型 大小 已用 可用 已用% 挂载点
                    mount_point = parts[6]
                    # 只收集 /volume 开头的挂载点，这些是MD阵列相关的数据卷
                    if mount_point.startswith('/volume'):
                        mount_points.append(mount_point)
            return mount_points
        return []
    except Exception as e:
        print(f"获取挂载点列表出错: {str(e)}")
        return []

# 获取挂载点的详细信息
def get_mount_point_info(mount_point):
    mount_info = {}
    try:
        # 使用df -T命令获取更详细的文件系统信息
        cmd = f"df -T {mount_point} | grep -v Filesystem"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            line = result.stdout.strip().split('\n')[0]
            parts = line.split()
            if len(parts) >= 7:
                mount_info['filesystem'] = parts[0]  # 文件系统设备
                mount_info['type'] = parts[1]       # 文件系统类型
                mount_info['size'] = parts[2]       # 总大小
                mount_info['used'] = parts[3]       # 已用空间
                mount_info['avail'] = parts[4]      # 可用空间
                mount_info['used_percent'] = parts[5]  # 已用百分比
                
                # 如果是mapper设备，尝试获取对应的MD设备信息
                if 'mapper' in parts[0]:
                    try:
                        # 尝试获取底层设备信息
                        cmd = f"lsblk -no PKNAME {parts[0]}"
                        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                        if result.returncode == 0 and result.stdout.strip():
                            parent_dev = result.stdout.strip()
                            mount_info['parent_device'] = parent_dev
                            
                            # 检查是否为MD设备
                            if parent_dev.startswith('md'):
                                mount_info['is_md'] = True
                                
                                # 使用mdadm -D获取更详细信息
                                cmd = f"mdadm -D /dev/{parent_dev}"
                                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                                if result.returncode == 0 and result.stdout.strip():
                                    md_detail = result.stdout.strip()
                                    mount_info['md_raw_info'] = md_detail
                                    
                                    # 解析阵列级别
                                    raid_level_match = re.search(r'Raid Level : ([\w\d-]+)', md_detail)
                                    if raid_level_match:
                                        raid_level = raid_level_match.group(1)
                                        mount_info['raid_level_raw'] = raid_level
                                        
                                        # 格式化阵列类型名称
                                        if raid_level.lower() == 'raid1':
                                            raid_level = 'RAID1'
                                        elif raid_level.lower() == 'raid0':
                                            raid_level = 'RAID0'
                                        elif raid_level.lower() == 'raid5':
                                            raid_level = 'RAID5'
                                        elif raid_level.lower() == 'raid6':
                                            raid_level = 'RAID6'
                                        elif raid_level.lower() == 'raid10':
                                            raid_level = 'RAID10'
                                        elif raid_level.lower() == 'linear':
                                            raid_level = 'JBOD'
                                        mount_info['raid_level'] = raid_level
                                    
                                    # 解析Chunk Size
                                    chunk_match = re.search(r'Chunk Size : (\d+[KMG])', md_detail)
                                    if chunk_match:
                                        mount_info['chunk_size'] = chunk_match.group(1)
                                    
                                    # 解析设备数量
                                    device_count_match = re.search(r'Total Devices : (\d+)', md_detail)
                                    if device_count_match:
                                        mount_info['device_count'] = device_count_match.group(1)
                                    
                                    # 解析Bitmap信息
                                    bitmap_match = re.search(r'Bitmap : (Internal|External|None)', md_detail)
                                    if bitmap_match:
                                        bitmap_type = bitmap_match.group(1)
                                        if bitmap_type != 'None':
                                            mount_info['bitmap'] = True
                                            mount_info['bitmap_info'] = bitmap_type
                                    
                                    # 解析阵列成员
                                    members = []
                                    member_matches = re.finditer(r'\s+\d+\s+\d+\s+\d+\s+\d+\s+\w+\s+/dev/([\w\d]+)', md_detail)
                                    for m in member_matches:
                                        members.append(m.group(1))
                                    mount_info['members'] = members
                                
                                # 也获取MD设备信息
                                md_info = get_md_info()
                                if parent_dev in md_info:
                                    mount_info['md_info'] = md_info[parent_dev]
                    except Exception as e:
                        print(f"获取底层设备信息出错: {str(e)}")
        else:
            mount_info['filesystem'] = "未知"
            mount_info['type'] = "未知"
            mount_info['size'] = "未知"
    except Exception as e:
        print(f"获取挂载点信息出错: {str(e)}")
        mount_info['error'] = str(e)
    
    return mount_info

# 获取硬盘的详细信息，包括容量和转速
def get_disk_detail_info(disk_name):
    disk_info = {}
    
    # 获取硬盘型号、大小和转速
    try:
        # 获取型号信息
        cmd = f"smartctl -i /dev/{disk_name} | grep -E 'Device Model|Product|Model Family|Vendor|Model Number'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            model_output = result.stdout.strip()
            disk_info['model'] = model_output
        else:
            disk_info['model'] = "无法获取型号信息"
        
        # 获取容量信息
        cmd = f"smartctl -i /dev/{disk_name} | grep 'User Capacity'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            capacity_line = result.stdout.strip()
            # 尝试提取容量数据，通常格式为：User Capacity: 2,000,398,934,016 bytes [2.00 TB]
            capacity_match = re.search(r'\[([\d\.\s]+[KMGTP]B)\]', capacity_line)
            if capacity_match:
                disk_info['capacity'] = capacity_match.group(1)
            else:
                disk_info['capacity'] = "未知容量"
        else:
            try:
                # 如果smartctl不能获取容量,尝试使用fdisk
                cmd = f"fdisk -l /dev/{disk_name} | grep -i 'Disk /dev/{disk_name}:'"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    fdisk_line = result.stdout.strip()
                    # 提取容量信息,格式通常为：Disk /dev/sda: 1.8 TiB, 2000398934016 bytes, 3907029168 sectors
                    capacity_match = re.search(r':\s*([\d\.\s]+[KMGTP]iB)', fdisk_line)
                    if capacity_match:
                        disk_info['capacity'] = capacity_match.group(1)
                    else:
                        disk_info['capacity'] = "未知容量"
                else:
                    disk_info['capacity'] = "未知容量"
            except:
                disk_info['capacity'] = "未知容量"
        
        # 获取转速信息
        cmd = f"smartctl -i /dev/{disk_name} | grep -E 'Rotation Rate'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            rpm_line = result.stdout.strip()
            disk_info['rpm'] = rpm_line.split(':')[1].strip() if ':' in rpm_line else "未知转速"
        else:
            disk_info['rpm'] = "未知转速"
            
    except Exception as e:
        disk_info['model'] = f"获取硬盘信息出错: {str(e)}"
        disk_info['capacity'] = "未知容量"
        disk_info['rpm'] = "未知转速"
    
    # 获取硬盘连接方式
    try:
        cmd = f"ls -la /sys/block/{disk_name}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            output = result.stdout.strip()
            disk_info['connection'] = output
            # 判断硬盘连接类型
            if "pci" in output:
                if "usb" in output:
                    disk_info['type'] = "USB桥接"
                else:
                    disk_info['type'] = "PCIe直连"
            elif "ahci" in output: # 尝试增加对原生SATA的判断
                disk_info['type'] = "原生SATA"
            else:
                disk_info['type'] = "其他连接方式"
        else:
            disk_info['connection'] = "无法获取硬盘连接信息"
            disk_info['type'] = "未知"
    except Exception as e:
        disk_info['connection'] = f"获取硬盘连接方式出错: {str(e)}"
        disk_info['type'] = "未知"
    
    return disk_info

# 发送邮件 - 已移除

# dd命令封装，返回传输速度
def dd_cmd(cmd):
    print(f"\n指令: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stderr:
        print(result.stderr)  
        # 正则匹配速度
        match = re.search(r'(\d+\.?\d*) s, (\d+\.?\d*) ([MG]B)/s', result.stderr)
        if match:
            # 传输速度值转换
            speed = float(match.group(2))
            # 传输速度单位（MB或GB）
            unit = match.group(3)
            if unit == 'GB':
                # 转换为MB/s
                speed = speed * 1024
            print(f"传输速度: {speed:.2f} MB/s")
            return speed
    return 0

# 清除缓存
def clear_cache():
    print("\n清理缓存....")
    subprocess.run("sync; echo 3 > /proc/sys/vm/drop_caches", shell=True)

# 删除测试文件(没调用，之后可以加入)
#def clear_files(volume):
#    print("\n删除dd测试文件...\n")
#    subprocess.run("rm -f ./{volume}/test*.bak", shell=True)


def test_disk(device, file_size, is_md_device=True):
    """
    功能：测试不同块大小文件,带缓存和不带缓存读写测试
    参数：
        device 设备名称 例：md1或sda
        file_size 文件大小，单位为G 例：5
        is_md_device 是否为md设备，True为阵列设备，False为裸盘

    返回:
        包含测试结果的字典
    """
    # 测试不同块大小
    bs_list = [4, 8, 16, 32, 64, 128, 256, 512, 1024]
    # xGB文件大小转化为kb
    total_size_kb = (file_size * 1024) * 1024
    # 获取设备的型号
    model = get_model()
    # 保存数据到日志文件
    device_type = "md" if is_md_device else "disk"
    log_file = f"{model}_{device}_{device_type}_test_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.log"
    
    # 存储测试结果的字典
    results_data = {}
    # 用于存储测试摘要
    test_summary = []
    # 用于存储测试命令
    test_commands = []
    
    print(f"开始进行dd测试，结果保存在： {log_file}")
    
    # 收集系统信息
    system_info = {
        'model': model,
        'system_version': get_system_version(),
        'memory': get_memory_info()
    }
    
    # 如果是裸盘，获取硬盘信息
    if not is_md_device:
        disk_info = get_disk_detail_info(device)
        system_info['disk_info'] = f"硬盘型号: {disk_info.get('model', '未知')}\n连接方式: {disk_info.get('type', '未知')}\n连接详情: {disk_info.get('connection', '未知')}"
    else:
        # 如果是MD设备，获取MD设备信息
        md_info = get_md_info()
        md_detail = md_info.get(device, {})
        raid_level = md_detail.get('raid_level', '未知')
        chunk_size = md_detail.get('chunk_size', '未知')
        bitmap = md_detail.get('bitmap', False)
        bitmap_info = md_detail.get('bitmap_info', '无') if bitmap else '未开启'
        members = md_detail.get('members', [])
        
        md_info_str = f"阵列类型: {raid_level}\nChunk Size: {chunk_size}\nBitmap: "
        if bitmap:
            md_info_str += f"已开启 ({bitmap_info})"
        else:
            md_info_str += "未开启"
        
        if members:
            md_info_str += f"\n成员盘: {', '.join(members)}"
            
        system_info['disk_info'] = md_info_str
    
    with open(log_file, 'w') as f:
        start_time = datetime.now()
        f.write(f"开始测试时间： {start_time}\n\n")
        f.write(f"系统信息:\n")
        f.write(f"设备型号: {system_info['model']}\n")
        f.write(f"系统版本: {system_info['system_version']}\n")
        f.write(f"内存大小: {system_info['memory']}\n\n")
        f.write(f"硬盘信息:\n{system_info['disk_info']}\n\n")
        
        tests = []
        if is_md_device:
            tests = [
                ("阵列读写测试-不经过缓存顺序写", f"if=/dev/zero of=/dev/{device} oflag=direct", range(1, 2)),
                ("阵列读写测试-不经过缓存顺序读", f"if=/dev/{device} of=/dev/null iflag=direct", range(3, 4)),
                ("阵列读写测试-经过缓存顺序写", f"if=/dev/zero of=/dev/{device}", range(5, 6)),
                ("阵列读写测试-经过缓存顺序读", f"if=/dev/{device} of=/dev/null", range(7, 8)),
            ]
        else:
            tests = [
                ("硬盘裸盘测试-不经过缓存顺序写", f"if=/dev/zero of=/dev/{device} oflag=direct", range(1, 2)),
                ("硬盘裸盘测试-不经过缓存顺序读", f"if=/dev/{device} of=/dev/null iflag=direct", range(3, 4)),
                ("硬盘裸盘测试-经过缓存顺序写", f"if=/dev/zero of=/dev/{device}", range(5, 6)),
                ("硬盘裸盘测试-经过缓存顺序读", f"if=/dev/{device} of=/dev/null", range(7, 8)),
            ]

        for test_name, cmd_template, test_range in tests:
            print(f"\n{'='*50}")
            print(f"开始{model}-{device}-{test_name}测试")
            print(f"{'='*50}")
            f.write(f"\n{model}-{device}-{test_name}测试:\n")
            
            # 记录测试命令
            base_cmd = f"dd {cmd_template} bs=<块大小>k count=<计数>"
            test_commands.append(f"{test_name}: {base_cmd}")
            
            # 用于存储当前测试类型下各块大小的结果
            current_test_results = {}
            
            for i, bs in enumerate(bs_list):
                test_num = i + test_range.start
                # 根据文件大小和块大小计算count值
                count = total_size_kb // bs
                # 统计传输速度
                speeds = []
                
                print(f"\n测试项目 {test_num}: 块大小 = {bs}k, Count = {count}")
                f.write(f"\n测试项目(bs={bs}k):\n")
                
                # 完整的dd命令
                full_cmd = f"dd {cmd_template} bs={bs}k count={count}"
                f.write(f"测试命令: {full_cmd}\n")
                
                # 循环执行5次计算传输速度的平均值
                for run in range(5):
                    print(f"\n测试数据{run + 1}/5:")
                    # 经过缓存的测试会进行清除缓存前置操作，不经过缓存则跳过处理
                    if "不经过" in test_name:
                        pass
                    else:
                        clear_cache()
                        time.sleep(5)
                        
                    # dd测试，同时记录速度
                    speed = dd_cmd(full_cmd)
                    if speed > 0:  # 只记录有效的速度值
                        speeds.append(speed)
                        f.write(f"测试数据 {run + 1}: {speed:.2f} MB/s\n")
                    
                    if run < 4:  
                        print("\n等待5s进行下一个dd测试...")
                        time.sleep(5)
                
                if speeds:
                    avg_speed = sum(speeds) / len(speeds)
                    current_test_results[bs] = f"{avg_speed:.2f}" # 记录平均速度
                    print(f"\n平均速度: {avg_speed:.2f} MB/s")
                    f.write(f"\n平均速度: {avg_speed:.2f} MB/s\n")
                    
                    # 记录该类型测试的摘要
                    test_summary.append(f"{device} - {test_name}(bs={bs}k): 平均速度: {avg_speed:.2f} MB/s")
                else:
                    current_test_results[bs] = "N/A" # 记录无有效数据
                    print("\n没有有效的速度数据")
                    f.write("\n没有有效的速度数据\n")
                f.write("-" * 50 + "\n")
            
            # 将当前测试类型的结果存入总结果字典
            results_data[test_name] = current_test_results

    # 返回包含日志文件路径、结果数据、系统信息和命令的元组
    return log_file, results_data, system_info, "\n".join(test_commands)

# 测试所有SATA硬盘或MD设备 - 直接写入指定日志文件
def test_all_devices_direct(devices, file_size, is_md_devices=False, log_file=None, fast_test=False, test_rounds=5):
    """
    功能：测试所有SATA硬盘或MD设备，直接写入指定日志文件
    参数：
        devices 设备列表
        file_size 文件大小，单位为G
        is_md_devices 是否为MD设备
        log_file 指定的日志文件路径
        fast_test 是否为快速测试模式
        test_rounds 测试轮数，默认为5
    返回:
        测试结果数据字典、系统信息、测试命令和设备详情
    """
    # 全局变量，用于检查是否应该退出
    global should_exit
    
    # 获取设备的型号
    model = get_model()
    # 设备类型描述
    device_type = "md阵列" if is_md_devices else "SATA硬盘"
    
    # 存储所有设备的测试结果
    all_results_data = {}
    # 用于存储所有设备的测试摘要
    all_test_summary = []
    # 用于存储所有测试命令
    all_test_commands = []
    
    # 收集系统信息
    system_info = {
        'model': model,
        'system_version': get_system_version(),
        'memory': get_memory_info(),
        'disk_info': f"测试对象: 所有{device_type}\n测试设备列表: {', '.join(devices)}" # 初始信息
    }
    
    device_details = {} # 用于存储每个设备的详细信息
    
    # 如果是MD设备，获取所有MD设备的详细信息
    md_info = {}
    if is_md_devices:
        md_info = get_md_info()
    
    with open(log_file, 'w') as f:
        start_time = datetime.now()
        f.write(f"开始测试时间： {start_time}\n\n")
        f.write(f"系统信息:\n")
        f.write(f"设备型号: {system_info['model']}\n")
        f.write(f"系统版本: {system_info['system_version']}\n")
        f.write(f"内存大小: {system_info['memory']}\n\n")
        f.write(f"测试对象: 所有{device_type}\n")
        f.write(f"测试设备列表: {', '.join(devices)}\n\n")
        f.write(f"测试轮数: {test_rounds}\n\n")
        
        # 依次测试每个设备
        for device in devices:
            # 检查是否应该退出程序
            if should_exit:
                f.write("\n因用户中断，测试提前停止\n")
                break
                
            device_start_time = datetime.now()
            f.write(f"\n{'='*50}\n")
            f.write(f"开始测试 {device}\n")
            f.write(f"{'='*50}\n")
            
            device_info_str = ""
            if not is_md_devices:  # 如果是硬盘，获取硬盘详细信息
                disk_info = get_disk_detail_info(device)
                device_info_str = f"硬盘型号: {disk_info.get('model', '未知')}\n连接方式: {disk_info.get('type', '未知')}\n连接详情: {disk_info.get('connection', '未知')}"
                device_details[device] = disk_info # 存储详细信息
                f.write(f"{device_info_str}\n\n")
            else:
                # 获取MD设备详细信息
                md_detail = md_info.get(device, {})
                raid_level = md_detail.get('raid_level', '未知')
                chunk_size = md_detail.get('chunk_size', '未知')
                bitmap = md_detail.get('bitmap', False)
                bitmap_info = md_detail.get('bitmap_info', '无')
                
                device_info_str = f"阵列类型: {raid_level}\nChunk Size: {chunk_size}\n"
                if bitmap:
                    device_info_str += f"Bitmap: 已开启 ({bitmap_info})\n"
                else:
                    device_info_str += "Bitmap: 未开启\n"
                
                members = md_detail.get('members', [])
                if members:
                    device_info_str += f"成员盘: {', '.join(members)}\n"
                
                device_details[device] = md_detail # 存储详细信息
                f.write(f"{device_info_str}\n")

            
            print(f"\n\n{'='*80}")
            print(f"开始测试设备: {device}")
            print(f"{'='*80}")
            
            # 测试不同块大小 - 快速测试模式只测试两种大小
            bs_list = [4, 1024] if fast_test else [4, 8, 16, 32, 64, 128, 256, 512, 1024]
            # xGB文件大小转化为kb - 快速测试模式使用较小文件大小
            fast_size = 1 # 快速测试使用1G
            total_size_kb = (fast_size if fast_test else file_size) * 1024 * 1024
            
            # 存储当前设备测试结果的字典
            current_device_results = {}
            
            # 快速测试模式只测试一种场景
            if fast_test:
                tests = []
                if is_md_devices:
                    tests = [("阵列读写测试-经过缓存顺序读", f"if=/dev/{device} of=/dev/null", range(1, 2))]
                else:
                    tests = [("硬盘裸盘测试-经过缓存顺序读", f"if=/dev/{device} of=/dev/null", range(1, 2))]
            else:
                tests = []
                if is_md_devices:
                    tests = [
                        ("阵列读写测试-不经过缓存顺序写", f"if=/dev/zero of=/dev/{device} oflag=direct", range(1, 2)),
                        ("阵列读写测试-不经过缓存顺序读", f"if=/dev/{device} of=/dev/null iflag=direct", range(3, 4)),
                        ("阵列读写测试-经过缓存顺序写", f"if=/dev/zero of=/dev/{device}", range(5, 6)),
                        ("阵列读写测试-经过缓存顺序读", f"if=/dev/{device} of=/dev/null", range(7, 8)),
                    ]
                else:
                    tests = [
                        ("硬盘裸盘测试-不经过缓存顺序写", f"if=/dev/zero of=/dev/{device} oflag=direct", range(1, 2)),
                        ("硬盘裸盘测试-不经过缓存顺序读", f"if=/dev/{device} of=/dev/null iflag=direct", range(3, 4)),
                        ("硬盘裸盘测试-经过缓存顺序写", f"if=/dev/zero of=/dev/{device}", range(5, 6)),
                        ("硬盘裸盘测试-经过缓存顺序读", f"if=/dev/{device} of=/dev/null", range(7, 8)),
                    ]

            for test_name, cmd_template, test_range in tests:
                # 检查是否应该退出程序
                if should_exit:
                    f.write("\n因用户中断，测试提前停止\n")
                    break
                    
                print(f"\n{'='*50}")
                print(f"开始{model}-{device}-{test_name}测试")
                print(f"{'='*50}")
                f.write(f"\n{model}-{device}-{test_name}测试:\n")
                
                # 记录测试命令
                base_cmd = f"dd {cmd_template} bs=<块大小>k count=<计数>"
                all_test_commands.append(f"{device} - {test_name}: {base_cmd}")
                
                # 存储当前测试类型下各块大小的结果
                current_test_type_results = {}
                
                for i, bs in enumerate(bs_list):
                    # 检查是否应该退出程序
                    if should_exit:
                        f.write("\n因用户中断，测试提前停止\n")
                        break
                        
                    test_num = i + test_range.start
                    # 根据文件大小和块大小计算count值
                    count = total_size_kb // bs
                    # 统计传输速度
                    speeds = []
                    
                    print(f"\n测试项目 {test_num}: 块大小 = {bs}k, Count = {count}")
                    f.write(f"\n测试项目(bs={bs}k):\n")
                    
                    # 完整的dd命令
                    full_cmd = f"dd {cmd_template} bs={bs}k count={count}"
                    f.write(f"测试命令: {full_cmd}\n")
                    
                    # 循环执行test_rounds次计算传输速度的平均值
                    test_runs = 1 if fast_test else test_rounds
                    for run in range(test_runs):
                        # 检查是否应该退出程序
                        if should_exit:
                            f.write("\n因用户中断，测试提前停止\n")
                            break
                            
                        print(f"\n测试数据{run + 1}/{test_runs}:")
                        # 经过缓存的测试会进行清除缓存前置操作，不经过缓存则跳过处理
                        if "不经过" in test_name:
                            pass
                        else:
                            clear_cache()
                            if not fast_test:
                                time.sleep(5)
                            
                        # dd测试，同时记录速度
                        speed = dd_cmd(full_cmd)
                        if speed > 0:  # 只记录有效的速度值
                            speeds.append(speed)
                            f.write(f"测试数据 {run + 1}: {speed:.2f} MB/s\n")
                        
                        if run < test_runs - 1:  
                            wait_time = 1 if fast_test else 5
                            print(f"\n等待{wait_time}s进行下一个dd测试...")
                            time.sleep(wait_time)
                    
                    if speeds:
                        avg_speed = sum(speeds) / len(speeds)
                        current_test_type_results[bs] = f"{avg_speed:.2f}" # 记录平均速度
                        print(f"\n平均速度: {avg_speed:.2f} MB/s")
                        f.write(f"\n平均速度: {avg_speed:.2f} MB/s\n")
                
                        # 记录该类型测试的摘要
                        all_test_summary.append(f"{device} - {test_name}(bs={bs}k): 平均速度: {avg_speed:.2f} MB/s")
                    else:
                        current_test_type_results[bs] = "N/A" # 记录无有效数据
                        print("\n没有有效的速度数据")
                        f.write("\n没有有效的速度数据\n")
                    f.write("-" * 50 + "\n")

                # 将当前测试类型结果存入当前设备的结果字典
                current_device_results[test_name] = current_test_type_results
            
            # 将当前设备的结果存入总结果字典
            all_results_data[device] = current_device_results
            
            # 如果测试被中断，提前跳出设备循环
            if should_exit:
                break
                
            device_end_time = datetime.now()
            device_duration = device_end_time - device_start_time
            f.write(f"\n设备 {device} 测试完成时间: {device_end_time}\n")
            f.write(f"设备 {device} 测试用时: {device_duration}\n\n")
    
    # 返回所有设备结果、系统信息、所有命令和设备详细信息
    return all_results_data, system_info, "\n".join(all_test_commands), device_details

# -- 新增函数 --
# 获取磁盘接口映射 (比如 sda 对应 ata1, sdb 对应 ata3 等等，你懂的哈~) 和连接类型
def get_disk_interface_mapping():
    mapping = {}
    try:
        # 获取所有sd*设备
        cmd = "ls -al /sys/block/sd*"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print("无法获取/sys/block/sd* 信息")
            return mapping

        lines = result.stdout.strip().split('\n')
        for line in lines:
            if "->" not in line:
                continue
            
            parts = line.split()
            # 提取设备名 (如 /sys/block/sda)
            dev_path = parts[8]
            dev_name = dev_path.split('/')[-1]
            
            # 提取链接目标 (如 ../devices/pci.../ata1/...)
            link_target = parts[10]
            
            interface = "未知接口"
            connection_type = "未知连接"

            # 查找ataX接口
            ata_match = re.search(r'/ata(\d+)/', link_target)
            if ata_match:
                interface = f"ata{ata_match.group(1)}"
            
            # 判断连接类型
            if "pci" in link_target:
                if "usb" in link_target:
                    connection_type = "USB桥接"
                else:
                    connection_type = "PCIe直连"
            elif "ahci" in link_target or "ata" in link_target: # 简化判断
                 connection_type = "原生SATA"
            elif "platform" in link_target and "sdhci" in link_target: # 常见于ARM平台的SD/eMMC控制器
                 connection_type = "SD/eMMC"

            mapping[dev_name] = {'interface': interface, 'connection': connection_type}

    except Exception as e:
        print(f"获取磁盘接口映射出错: {str(e)}")
    return mapping

# 解析 /proc/mdstat 获取MD阵列信息
def get_md_info():
    md_details = {}
    try:
        # 首先读取/proc/mdstat文件
        with open('/proc/mdstat', 'r') as f:
            content = f.read()
        
        # 使用更宽松的正则表达式匹配每个MD设备的信息，兼容多种格式
        # 匹配md设备名、状态、RAID级别、成员盘
        pattern = re.compile(
            r'^(md\d+)\s*:\s*(active|inactive)\s*(?:(raid\d+|linear|multipath))?\s*([\w\d\[\]\(\) ]+)(?:\n\s+(\d+)\s+blocks)?', 
            re.MULTILINE
        )
        
        matches = pattern.finditer(content)
        
        for match in matches:
            md_name = match.group(1)
            status = match.group(2)
            raid_level_raw = match.group(3) if match.group(3) else 'unknown' # 有时候吧，它就不告诉你level是啥 (比如那个linear，就挺秃然的)
            members_raw = match.group(4)
            
            # 提取成员盘名称 (如 sda2[0], sdb2[1])
            member_pattern = re.compile(r'(\w+)(\[\d+\])?(?:\(\w\))?')
            members = [m.group(1) for m in member_pattern.finditer(members_raw)]
            
            raid_level = raid_level_raw
            num_members = len(members)

            # 判断 Basic 和 JBOD
            if raid_level_raw == 'raid1' and num_members == 1:
                raid_level = 'Basic'
            elif raid_level_raw == 'linear' and num_members >= 1: # JBOD这小老弟啊，一般都装成linear的样子
                raid_level = 'JBOD'
            elif raid_level_raw == 'raid1' and num_members > 1:
                 raid_level = 'RAID1' # 明确是RAID1
            elif raid_level_raw == 'raid0':
                 raid_level = 'RAID0'
            elif raid_level_raw == 'raid5':
                 raid_level = 'RAID5'
            elif raid_level_raw == 'raid6':
                 raid_level = 'RAID6'
            elif raid_level_raw == 'raid10':
                 raid_level = 'RAID10'
                 
            md_details[md_name] = {
                'status': status,
                'raid_level': raid_level,
                'members': members,
                'num_members': num_members,
                'chunk_size': 'Unknown',
                'bitmap': False
            }
            
            # 检查chunk size信息
            chunk_pattern = re.compile(r'%s.*?(\d+[kmg]).*?chunk' % md_name, re.DOTALL | re.IGNORECASE)
            chunk_match = chunk_pattern.search(content)
            if chunk_match:
                md_details[md_name]['chunk_size'] = chunk_match.group(1)
            
            # 检查bitmap信息
            bitmap_pattern = re.compile(r'%s.*?bitmap:.*?(\d+/\d+\s+pages)' % md_name, re.DOTALL | re.IGNORECASE)
            bitmap_match = bitmap_pattern.search(content)
            if bitmap_match:
                md_details[md_name]['bitmap'] = True
                md_details[md_name]['bitmap_info'] = bitmap_match.group(1)
            
        # 如果没有找到任何MD设备，尝试使用mdadm命令获取更多信息
        if not md_details:
            print("未从/proc/mdstat找到MD设备信息，尝试使用mdadm命令...")
            # 首先获取所有MD设备列表
            cmd = "ls -1 /dev/md* 2>/dev/null | grep -E 'md[0-9]+'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout.strip():
                md_devices = result.stdout.strip().split('\n')
                
                for md_dev_path in md_devices:
                    # 提取md设备名 (例如: /dev/md1 -> md1)
                    md_name = os.path.basename(md_dev_path)
                    
                    # 使用mdadm命令获取详细信息
                    cmd = f"mdadm -D {md_dev_path}"
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        md_info = result.stdout.strip()
                        
                        # 提取RAID级别
                        raid_level_match = re.search(r'Raid Level : ([\w\d]+)', md_info)
                        raid_level_raw = raid_level_match.group(1).lower() if raid_level_match else 'unknown'
                        raid_level = raid_level_raw
                        
                        # 转换raid level名称为一致的格式
                        if raid_level_raw == 'raid1':
                            raid_level = 'RAID1'
                        elif raid_level_raw == 'raid0':
                            raid_level = 'RAID0'
                        elif raid_level_raw == 'raid5':
                            raid_level = 'RAID5'
                        elif raid_level_raw == 'raid6':
                            raid_level = 'RAID6'
                        elif raid_level_raw == 'raid10':
                            raid_level = 'RAID10'
                        
                        # 提取状态
                        state_match = re.search(r'State : (\w+)', md_info)
                        status = state_match.group(1) if state_match else 'unknown'
                        
                        # 提取成员盘
                        members = []
                        member_matches = re.finditer(r'\s+\d+\s+\d+\s+\d+\s+\d+\s+\w+\s+/dev/([\w\d]+)', md_info)
                        for m in member_matches:
                            members.append(m.group(1))
                        
                        md_details[md_name] = {
                            'status': status,
                            'raid_level': raid_level,
                            'members': members,
                            'num_members': len(members),
                            'chunk_size': 'Unknown',
                            'bitmap': False
                        }
                        
                        # 提取chunk size信息
                        chunk_match = re.search(r'Chunk Size : (\d+[KMG])', md_info)
                        if chunk_match:
                            md_details[md_name]['chunk_size'] = chunk_match.group(1)
                        
                        # 提取bitmap信息
                        bitmap_match = re.search(r'Intent Bitmap : (Internal|External|None)', md_info)
                        if bitmap_match and bitmap_match.group(1) != 'None':
                            md_details[md_name]['bitmap'] = True
                            md_details[md_name]['bitmap_info'] = bitmap_match.group(1)
                
                print(f"通过mdadm获取到MD设备信息: {list(md_details.keys())}")
                
    except FileNotFoundError:
        print("错误：无法读取 /proc/mdstat")
    except Exception as e:
        print(f"解析 /proc/mdstat 出错: {str(e)}")
        import traceback
        traceback.print_exc() # 打印详细错误堆栈
    
    return md_details

# 创建整合了RAID类型的目录名
def create_test_dir(system_info, md_info=None):
    """
    创建测试目录,包含RAID类型信息
    """
    model = system_info.get('model', 'Unknown').replace(' ', '_')
    raid_types = []
    
    # 如果有MD信息,提取RAID类型
    if md_info:
        for md_device, info in md_info.items():
            raid_type = info.get('raid_level', '').lower()
            if raid_type and raid_type not in raid_types:
                raid_types.append(raid_type)
    
    # 创建目录名
    dir_name = model
    if raid_types:
        dir_name += "_" + "_".join(raid_types)
    
    dir_name += f"_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # 确保目录不存在
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    
    return dir_name

# 生成HTML报告 - 直接输出到指定路径
def generate_html_report_direct(report_filename, results_data, system_info, test_commands, device_details):
    """
    直接在指定路径生成HTML报告，不进行路径处理
    """
    # 获取磁盘接口映射信息
    disk_mapping = get_disk_interface_mapping()
    # 获取MD阵列详细信息
    md_info = get_md_info()
    
    # CSS样式改进
    css_style = """
    <style>
        body { font-family: sans-serif; margin: 20px; }
        h1, h2, h3 { color: #333; }
        h4 { color: #2c3e50; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: center; vertical-align: middle; }
        th { background-color: #f2f2f2; color: #333; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        .info-box { background-color: #eef; padding: 15px; border-left: 5px solid #aaf; margin-bottom: 20px; }
        .device-section { margin-bottom: 30px; padding: 15px; border: 1px solid #ccc; border-radius: 5px; }
        .raid-info { background-color: #f8f9fa; padding: 10px; border-left: 4px solid #2980b9; margin-top: 10px; }
        .fs-type { color: #2980b9; font-weight: bold; }
        pre { background-color: #f5f5f5; padding: 10px; border: 1px solid #eee; overflow-x: auto; }
        .test-cmd { font-family: monospace; padding: 5px; background-color: #f5f5f5; overflow: hidden; }
        .cache { color: #2c7873; }
        .no-cache { color: #1985a1; }
        .cmd-column { text-align: left; width: 45%; font-family: monospace; font-size: 0.9em; }
        .bs-column { text-align: center; width: 10%; }
        .speed-column { text-align: center; width: 10%; }
        .highlight { color: #e74c3c; font-weight: bold; }
        .speed-header { text-align: center; background-color: #daedf5; }
    </style>
    """
    
    html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>磁盘性能测试报告 - {system_info.get('model', 'Unknown')}</title>
    {css_style}
</head>
<body>
    <h1>磁盘性能测试报告</h1>
    <p>生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>

    <div class="info-box">
        <h2>系统信息</h2>
        <p><strong>设备型号:</strong> {html.escape(system_info.get('model', 'Unknown'))}</p>
        <p><strong>系统版本:</strong> {html.escape(system_info.get('system_version', 'Unknown'))}</p>
        <p><strong>内存大小:</strong> {html.escape(system_info.get('memory', 'Unknown'))}</p>
    </div>

    <h2>测试结果汇总</h2>
"""

    # 区分SATA盘、MD阵列和文件系统
    sata_devices = {dev: data for dev, data in results_data.items() if dev.startswith('sd')}
    md_devices = {dev: data for dev, data in results_data.items() if dev.startswith('md')}
    fs_devices = {dev: data for dev, data in results_data.items() if dev.startswith('/')}
    
    # --- SATA硬盘报告 ---
    if sata_devices:
        html_content += "<h3>SATA 硬盘测试</h3>"
        for device, tests in sata_devices.items():
            disk_map_info = disk_mapping.get(device, {'interface': '未知', 'connection': '未知'})
            disk_num_match = re.search(r'ata(\d+)', disk_map_info['interface'])
            disk_label = f"硬盘{disk_num_match.group(1)}" if disk_num_match else device
            
            detail = device_details.get(device, {})
            disk_capacity = detail.get('capacity', '未知容量')
            disk_rpm = detail.get('rpm', '未知转速')
            
            html_content += f"""
            <div class="device-section">
                <h4>设备: {device} ({disk_label})</h4>
                <p><strong>接口:</strong> {html.escape(disk_map_info['interface'])}</p>
                <p><strong>连接类型:</strong> {html.escape(disk_map_info['connection'])}</p>
                <p><strong>容量:</strong> {html.escape(disk_capacity)}</p>
                <p><strong>转速:</strong> {html.escape(disk_rpm)}</p>
                <p><strong>型号信息:</strong><pre>{html.escape(detail.get('model', '无法获取'))}</pre></p>
                
                <table>
                    <thead>
                        <tr>
                            <th class="bs-column" rowspan="2">块大小</th>
                            <th class="cmd-column" rowspan="2">测试指令</th>
                            <th class="speed-header" colspan="4">硬盘-读写速度</th>
                        </tr>
                        <tr>
                            <th class="speed-column">经过缓存-读(MB/s)</th>
                            <th class="speed-column">经过缓存-写(MB/s)</th>
                            <th class="speed-column">不经过缓存-读(MB/s)</th>
                            <th class="speed-column">不经过缓存-写(MB/s)</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            # 按照块大小分组生成行
            bs_list = [4, 8, 16, 32, 64, 128, 256, 512, 1024]
            for bs in bs_list:
                # 生成读写命令
                cached_read_cmd = f"dd if=/dev/{device} of=/dev/null bs={bs}k count={int(5*1024*1024/bs)}"
                cached_write_cmd = f"dd if=/dev/zero of=/dev/{device} bs={bs}k count={int(5*1024*1024/bs)}"
                direct_read_cmd = f"dd if=/dev/{device} of=/dev/null bs={bs}k count={int(5*1024*1024/bs)} iflag=direct"
                direct_write_cmd = f"dd if=/dev/zero of=/dev/{device} bs={bs}k count={int(5*1024*1024/bs)} oflag=direct"
                
                # 命令集合
                cmds = f"硬盘裸盘：<br/>{cached_read_cmd}<br/>{cached_write_cmd}<br/>{direct_read_cmd}<br/>{direct_write_cmd}"
                
                # 查找对应的性能数据
                cached_read_speed = "N/A"
                cached_write_speed = "N/A"
                direct_read_speed = "N/A"
                direct_write_speed = "N/A"
                
                for test_name, test_results in tests.items():
                    if "硬盘裸盘测试-经过缓存顺序读" in test_name:
                        cached_read_speed = test_results.get(bs, "N/A")
                    elif "硬盘裸盘测试-经过缓存顺序写" in test_name:
                        cached_write_speed = test_results.get(bs, "N/A")
                    elif "硬盘裸盘测试-不经过缓存顺序读" in test_name:
                        direct_read_speed = test_results.get(bs, "N/A")
                    elif "硬盘裸盘测试-不经过缓存顺序写" in test_name:
                        direct_write_speed = test_results.get(bs, "N/A")
                
                html_content += f"""
                <tr>
                    <td class="bs-column">{bs}k</td>
                    <td class="cmd-column">{cmds}</td>
                    <td class="speed-column cache">{cached_read_speed}</td>
                    <td class="speed-column cache">{cached_write_speed}</td>
                    <td class="speed-column no-cache">{direct_read_speed}</td>
                    <td class="speed-column no-cache">{direct_write_speed}</td>
                </tr>
                """
                
            html_content += """
                    </tbody>
                </table>
            </div>
            """

    # --- MD阵列报告 ---
    if md_devices:
        html_content += "<h3>MD 阵列测试</h3>"
        for device, tests in md_devices.items():
            md_detail = md_info.get(device, {'raid_level': '未知', 'members': [], 'status': '未知'})
             
            member_info_list = []
            for member in md_detail['members']:
                # 提取盘符 (如 sda2 -> sda)
                member_disk = re.match(r'([a-z]+)', member)
                if member_disk:
                    member_disk_name = member_disk.group(1)
                    disk_map_info = disk_mapping.get(member_disk_name, {'interface': '未知', 'connection': '未知'})
                    member_info_list.append(f"{member} ({disk_map_info['interface']}, {disk_map_info['connection']})")
                else:
                    member_info_list.append(f"{member} (接口信息未知)")
            members_str = ', '.join(member_info_list)
            
            # 获取更多阵列详细信息
            chunk_size = md_detail.get('chunk_size', '未知')
            has_bitmap = md_detail.get('bitmap', False)
            bitmap_info = md_detail.get('bitmap_info', '无')
            
            html_content += f"""
            <div class="device-section">
                <h4>阵列: {device}</h4>
                <p><strong>阵列类型:</strong> {html.escape(md_detail['raid_level'])}</p>
                <p><strong>状态:</strong> {html.escape(md_detail['status'])}</p>
                <p><strong>Chunk Size:</strong> <span style="color:#e74c3c;font-weight:bold">{html.escape(chunk_size)}</span></p>
                <p><strong>Bitmap:</strong> {html.escape('已开启 - ' + bitmap_info) if has_bitmap else '未开启'}</p>
                <p><strong>成员盘数量:</strong> {len(md_detail.get('members', []))}</p>
                <p><strong>成员盘详情:</strong> {html.escape(members_str)}</p>
                
                <table>
                    <thead>
                        <tr>
                            <th class="bs-column" rowspan="2">块大小</th>
                            <th class="cmd-column" rowspan="2">测试指令</th>
                            <th class="speed-header" colspan="4">阵列-读写速度</th>
                        </tr>
                        <tr>
                            <th class="speed-column">经过缓存-读(MB/s)</th>
                            <th class="speed-column">经过缓存-写(MB/s)</th>
                            <th class="speed-column">不经过缓存-读(MB/s)</th>
                            <th class="speed-column">不经过缓存-写(MB/s)</th>
                        </tr>
                    </thead>
                    <tbody>
            """

            # 按照块大小分组生成行
            bs_list = [4, 8, 16, 32, 64, 128, 256, 512, 1024]
            for bs in bs_list:
                # 生成读写命令
                cached_read_cmd = f"dd if=/dev/{device} of=/dev/null bs={bs}k count={int(5*1024*1024/bs)}"
                cached_write_cmd = f"dd if=/dev/zero of=/dev/{device} bs={bs}k count={int(5*1024*1024/bs)}"
                direct_read_cmd = f"dd if=/dev/{device} of=/dev/null bs={bs}k count={int(5*1024*1024/bs)} iflag=direct"
                direct_write_cmd = f"dd if=/dev/zero of=/dev/{device} bs={bs}k count={int(5*1024*1024/bs)} oflag=direct"
                
                # 命令集合
                cmds = f"阵列：<br/>{cached_read_cmd}<br/>{cached_write_cmd}<br/>{direct_read_cmd}<br/>{direct_write_cmd}"
                
                # 查找对应的性能数据
                cached_read_speed = "N/A"
                cached_write_speed = "N/A"
                direct_read_speed = "N/A"
                direct_write_speed = "N/A"
                
                for test_name, test_results in tests.items():
                    if "阵列读写测试-经过缓存顺序读" in test_name:
                        cached_read_speed = test_results.get(bs, "N/A")
                    elif "阵列读写测试-经过缓存顺序写" in test_name:
                        cached_write_speed = test_results.get(bs, "N/A")
                    elif "阵列读写测试-不经过缓存顺序读" in test_name:
                        direct_read_speed = test_results.get(bs, "N/A")
                    elif "阵列读写测试-不经过缓存顺序写" in test_name:
                        direct_write_speed = test_results.get(bs, "N/A")
                
                html_content += f"""
                <tr>
                    <td class="bs-column">{bs}k</td>
                    <td class="cmd-column">{cmds}</td>
                    <td class="speed-column cache">{cached_read_speed}</td>
                    <td class="speed-column cache">{cached_write_speed}</td>
                    <td class="speed-column no-cache">{direct_read_speed}</td>
                    <td class="speed-column no-cache">{direct_write_speed}</td>
                </tr>
                """
                
            html_content += """
                    </tbody>
                </table>
            </div>
            """
    
    # --- 文件系统报告 ---
    if fs_devices:
        html_content += "<h3>文件系统测试</h3>"
        for mount_point, tests in fs_devices.items():
            detail = device_details.get(mount_point, {})
            fs_type = detail.get('type', '未知')
            fs_size = detail.get('size', '未知容量')
            fs_used = detail.get('used', '未知')
            fs_avail = detail.get('avail', '未知')
            fs_dev = detail.get('filesystem', '未知')
            
            # 判断是否关联MD设备
            is_md_related = detail.get('is_md', False)
            parent_md = detail.get('parent_device', '')
            md_detail = detail.get('md_info', {})
            
            html_content += f"""
            <div class="device-section">
                <h4>挂载点: {mount_point}</h4>
                <p><strong>文件系统:</strong> {html.escape(fs_dev)}</p>
                <p><strong>类型:</strong> <span class="fs-type">{html.escape(fs_type)}</span></p>
                <p><strong>总大小:</strong> {html.escape(fs_size)}</p>
                <p><strong>已用空间:</strong> {html.escape(fs_used)}</p>
                <p><strong>可用空间:</strong> {html.escape(fs_avail)}</p>"""
            
            # 如果是MD相关的挂载点，添加MD设备信息
            if is_md_related and parent_md:
                html_content += """
                <div class="raid-info">"""
                
                html_content += f"""
                    <p><strong>底层MD设备:</strong> {html.escape(parent_md)}</p>"""
                
                if md_detail:
                    raid_level = md_detail.get('raid_level', '未知')
                    members = md_detail.get('members', [])
                    chunk_size = md_detail.get('chunk_size', '未知')
                    has_bitmap = md_detail.get('bitmap', False)
                    bitmap_info = md_detail.get('bitmap_info', '无') if has_bitmap else '未开启'
                    
                    html_content += f"""
                    <p><strong>阵列类型:</strong> <span class="highlight">{html.escape(raid_level)}</span></p>
                    <p><strong>Chunk Size:</strong> <span class="highlight">{html.escape(chunk_size)}</span></p>
                    <p><strong>Bitmap:</strong> {html.escape('已开启 - ' + bitmap_info) if has_bitmap else '未开启'}</p>
                    <p><strong>成员盘:</strong> {html.escape(', '.join(members))}</p>"""
                
                html_content += """
                </div>"""
            
            html_content += f"""
                <table>
                    <thead>
                        <tr>
                            <th class="bs-column" rowspan="2">块大小</th>
                            <th class="cmd-column" rowspan="2">测试指令</th>
                            <th class="speed-header" colspan="4">文件系统-读写速度</th>
                        </tr>
                        <tr>
                            <th class="speed-column">经过缓存-读(MB/s)</th>
                            <th class="speed-column">经过缓存-写(MB/s)</th>
                            <th class="speed-column">不经过缓存-读(MB/s)</th>
                            <th class="speed-column">不经过缓存-写(MB/s)</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            # 按照块大小分组生成行
            bs_list = [4, 8, 16, 32, 64, 128, 256, 512, 1024]
            test_file = f"{mount_point}/dd_test_file.dat"
            
            for bs in bs_list:
                # 生成读写命令
                cached_read_cmd = f"dd if={test_file} of=/dev/null bs={bs}k count={int(5*1024*1024/bs)}"
                cached_write_cmd = f"dd if=/dev/zero of={test_file} bs={bs}k count={int(5*1024*1024/bs)}"
                direct_read_cmd = f"dd if={test_file} of=/dev/null bs={bs}k count={int(5*1024*1024/bs)} iflag=direct"
                direct_write_cmd = f"dd if=/dev/zero of={test_file} bs={bs}k count={int(5*1024*1024/bs)} oflag=direct"
                
                # 命令集合
                cmds = f"文件系统：<br/>{cached_read_cmd}<br/>{cached_write_cmd}<br/>{direct_read_cmd}<br/>{direct_write_cmd}"
                
                # 查找对应的性能数据
                cached_read_speed = "N/A"
                cached_write_speed = "N/A"
                direct_read_speed = "N/A"
                direct_write_speed = "N/A"
                
                for test_name, test_results in tests.items():
                    if "文件系统测试-经过缓存顺序读" in test_name:
                        cached_read_speed = test_results.get(bs, "N/A")
                    elif "文件系统测试-经过缓存顺序写" in test_name:
                        cached_write_speed = test_results.get(bs, "N/A")
                    elif "文件系统测试-不经过缓存顺序读" in test_name:
                        direct_read_speed = test_results.get(bs, "N/A")
                    elif "文件系统测试-不经过缓存顺序写" in test_name:
                        direct_write_speed = test_results.get(bs, "N/A")
                
                html_content += f"""
                <tr>
                    <td class="bs-column">{bs}k</td>
                    <td class="cmd-column">{cmds}</td>
                    <td class="speed-column cache">{cached_read_speed}</td>
                    <td class="speed-column cache">{cached_write_speed}</td>
                    <td class="speed-column no-cache">{direct_read_speed}</td>
                    <td class="speed-column no-cache">{direct_write_speed}</td>
                </tr>
                """
                
            html_content += """
                    </tbody>
                </table>
            </div>
            """

    html_content += """
</body>
</html>
"""

    try:
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"\nHTML报告已生成: {report_filename}")
        return report_filename
    except Exception as e:
        print(f"生成HTML报告失败: {str(e)}")
        return None

# 测试挂载点的文件系统性能
def test_filesystem(mount_point, file_size):
    """
    功能：测试挂载点的文件系统读写性能
    参数：
        mount_point 挂载点路径，如/volume1
        file_size 测试文件大小，单位为G
    返回:
        包含测试结果的字典
    """
    # 测试不同块大小
    bs_list = [4, 8, 16, 32, 64, 128, 256, 512, 1024]
    # xGB文件大小转化为kb
    total_size_kb = (file_size * 1024) * 1024
    # 获取设备的型号
    model = get_model()
    # 保存数据到日志文件
    log_file = f"{model}_{mount_point.replace('/', '_')}_fs_test_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.log"
    
    # 存储测试结果的字典
    results_data = {}
    # 用于存储测试摘要
    test_summary = []
    # 用于存储测试命令
    test_commands = []
    
    print(f"开始进行文件系统dd测试，结果保存在： {log_file}")
    
    # 收集系统信息
    system_info = {
        'model': model,
        'system_version': get_system_version(),
        'memory': get_memory_info()
    }
    
    # 获取挂载点信息
    fs_info = get_mount_point_info(mount_point)
    system_info['fs_info'] = f"挂载点: {mount_point}\n" \
                            f"文件系统: {fs_info.get('filesystem', '未知')}\n" \
                            f"类型: {fs_info.get('type', '未知')}\n" \
                            f"总大小: {fs_info.get('size', '未知')}\n" \
                            f"已用空间: {fs_info.get('used', '未知')}\n" \
                            f"可用空间: {fs_info.get('avail', '未知')}"
    
    # 测试文件路径
    test_file = f"{mount_point}/dd_test_file_{datetime.now().strftime('%Y%m%d_%H%M%S')}.dat"
    
    with open(log_file, 'w') as f:
        start_time = datetime.now()
        f.write(f"开始测试时间： {start_time}\n\n")
        f.write(f"系统信息:\n")
        f.write(f"设备型号: {system_info['model']}\n")
        f.write(f"系统版本: {system_info['system_version']}\n")
        f.write(f"内存大小: {system_info['memory']}\n\n")
        f.write(f"文件系统信息:\n{system_info['fs_info']}\n\n")
        
        tests = [
            ("文件系统测试-不经过缓存顺序写", f"if=/dev/zero of={test_file} oflag=direct", range(1, 2)),
            ("文件系统测试-不经过缓存顺序读", f"if={test_file} of=/dev/null iflag=direct", range(3, 4)),
            ("文件系统测试-经过缓存顺序写", f"if=/dev/zero of={test_file}", range(5, 6)),
            ("文件系统测试-经过缓存顺序读", f"if={test_file} of=/dev/null", range(7, 8)),
        ]

        for test_name, cmd_template, test_range in tests:
            print(f"\n{'='*50}")
            print(f"开始{model}-{mount_point}-{test_name}测试")
            print(f"{'='*50}")
            f.write(f"\n{model}-{mount_point}-{test_name}测试:\n")
            
            # 记录测试命令
            base_cmd = f"dd {cmd_template} bs=<块大小>k count=<计数>"
            test_commands.append(f"{test_name}: {base_cmd}")
            
            # 用于存储当前测试类型下各块大小的结果
            current_test_results = {}
            
            for i, bs in enumerate(bs_list):
                test_num = i + test_range.start
                # 根据文件大小和块大小计算count值
                count = total_size_kb // bs
                # 统计传输速度
                speeds = []
                
                print(f"\n测试项目 {test_num}: 块大小 = {bs}k, Count = {count}")
                f.write(f"\n测试项目(bs={bs}k):\n")
                
                # 完整的dd命令
                full_cmd = f"dd {cmd_template} bs={bs}k count={count}"
                f.write(f"测试命令: {full_cmd}\n")
                
                # 循环执行5次计算传输速度的平均值
                for run in range(5):
                    print(f"\n测试数据{run + 1}/5:")
                    # 经过缓存的测试会进行清除缓存前置操作，不经过缓存则跳过处理
                    if "不经过" in test_name:
                        pass
                    else:
                        clear_cache()
                        time.sleep(5)
                        
                    # dd测试，同时记录速度
                    speed = dd_cmd(full_cmd)
                    if speed > 0:  # 只记录有效的速度值
                        speeds.append(speed)
                        f.write(f"测试数据 {run + 1}: {speed:.2f} MB/s\n")
                    
                    if run < 4:  
                        print("\n等待5s进行下一个dd测试...")
                        time.sleep(5)
                
                if speeds:
                    avg_speed = sum(speeds) / len(speeds)
                    current_test_results[bs] = f"{avg_speed:.2f}" # 记录平均速度
                    print(f"\n平均速度: {avg_speed:.2f} MB/s")
                    f.write(f"\n平均速度: {avg_speed:.2f} MB/s\n")
                    
                    # 记录该类型测试的摘要
                    test_summary.append(f"{mount_point} - {test_name}(bs={bs}k): 平均速度: {avg_speed:.2f} MB/s")
                else:
                    current_test_results[bs] = "N/A" # 记录无有效数据
                    print("\n没有有效的速度数据")
                    f.write("\n没有有效的速度数据\n")
                f.write("-" * 50 + "\n")
            
            # 将当前测试类型的结果存入总结果字典
            results_data[test_name] = current_test_results
        
        # 测试完成后删除测试文件
        try:
            subprocess.run(f"rm -f {test_file}", shell=True)
            f.write("\n清理测试文件\n")
        except Exception as e:
            f.write(f"\n清理测试文件失败: {str(e)}\n")

    # 返回包含日志文件路径、结果数据、系统信息和命令的元组
    return log_file, results_data, system_info, "\n".join(test_commands)

# 测试所有挂载点的文件系统性能
def test_all_filesystems(file_size):
    """
    功能：测试所有挂载点的文件系统性能
    参数：
        file_size 测试文件大小，单位为G
    返回:
        包含所有挂载点测试结果的字典
    """
    # 获取设备的型号
    model = get_model()
    # 保存数据到日志文件
    log_file = f"{model}_ALL_Filesystems_test_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.log"
    
    # 获取所有挂载点
    mount_points = get_all_mount_points()
    if not mount_points:
        print("没有找到有效的挂载点")
        return None, {}, {}, "", {}
    
    # 存储所有挂载点的测试结果
    all_results_data = {}
    # 用于存储所有挂载点的测试摘要
    all_test_summary = []
    # 用于存储所有测试命令
    all_test_commands = []
    
    # 收集系统信息
    system_info = {
        'model': model,
        'system_version': get_system_version(),
        'memory': get_memory_info(),
        'fs_info': f"测试对象: 所有挂载点\n测试挂载点列表: {', '.join(mount_points)}" # 初始信息
    }
    
    mount_point_details = {} # 用于存储每个挂载点的详细信息
    
    with open(log_file, 'w') as f:
        start_time = datetime.now()
        f.write(f"开始测试时间： {start_time}\n\n")
        f.write(f"系统信息:\n")
        f.write(f"设备型号: {system_info['model']}\n")
        f.write(f"系统版本: {system_info['system_version']}\n")
        f.write(f"内存大小: {system_info['memory']}\n\n")
        f.write(f"测试对象: 所有挂载点\n")
        f.write(f"测试挂载点列表: {', '.join(mount_points)}\n\n")
        
        # 依次测试每个挂载点
        for mount_point in mount_points:
            # 获取挂载点详情
            fs_info = get_mount_point_info(mount_point)
            mount_point_details[mount_point] = fs_info
            
            # 记录挂载点信息
            fs_info_str = f"挂载点: {mount_point}\n" \
                         f"文件系统: {fs_info.get('filesystem', '未知')}\n" \
                         f"类型: {fs_info.get('type', '未知')}\n" \
                         f"总大小: {fs_info.get('size', '未知')}\n" \
                         f"已用空间: {fs_info.get('used', '未知')}\n" \
                         f"可用空间: {fs_info.get('avail', '未知')}"
            
            device_start_time = datetime.now()
            f.write(f"\n{'='*50}\n")
            f.write(f"开始测试挂载点: {mount_point}\n")
            f.write(f"{'='*50}\n")
            f.write(f"{fs_info_str}\n\n")
            
            print(f"\n\n{'='*80}")
            print(f"开始测试挂载点: {mount_point}")
            print(f"{'='*80}")
            
            # 测试文件路径
            test_file = f"{mount_point}/dd_test_file_{datetime.now().strftime('%Y%m%d_%H%M%S')}.dat"
            
            # 测试不同块大小
            bs_list = [4, 8, 16, 32, 64, 128, 256, 512, 1024]
            # xGB文件大小转化为kb
            total_size_kb = (file_size * 1024) * 1024
            
            # 存储当前挂载点测试结果的字典
            current_mount_point_results = {}
            
            tests = [
                ("文件系统测试-不经过缓存顺序写", f"if=/dev/zero of={test_file} oflag=direct", range(1, 2)),
                ("文件系统测试-不经过缓存顺序读", f"if={test_file} of=/dev/null iflag=direct", range(3, 4)),
                ("文件系统测试-经过缓存顺序写", f"if=/dev/zero of={test_file}", range(5, 6)),
                ("文件系统测试-经过缓存顺序读", f"if={test_file} of=/dev/null", range(7, 8)),
            ]

            for test_name, cmd_template, test_range in tests:
                print(f"\n{'='*50}")
                print(f"开始{model}-{mount_point}-{test_name}测试")
                print(f"{'='*50}")
                f.write(f"\n{model}-{mount_point}-{test_name}测试:\n")
                
                # 记录测试命令
                base_cmd = f"dd {cmd_template} bs=<块大小>k count=<计数>"
                all_test_commands.append(f"{mount_point} - {test_name}: {base_cmd}")
                
                # 存储当前测试类型下各块大小的结果
                current_test_type_results = {}
                
                for i, bs in enumerate(bs_list):
                    test_num = i + test_range.start
                    # 根据文件大小和块大小计算count值
                    count = total_size_kb // bs
                    # 统计传输速度
                    speeds = []
                    
                    print(f"\n测试项目 {test_num}: 块大小 = {bs}k, Count = {count}")
                    f.write(f"\n测试项目(bs={bs}k):\n")
                    
                    # 完整的dd命令
                    full_cmd = f"dd {cmd_template} bs={bs}k count={count}"
                    f.write(f"测试命令: {full_cmd}\n")
                    
                    # 循环执行5次计算传输速度的平均值
                    for run in range(5):
                        print(f"\n测试数据{run + 1}/5:")
                        # 经过缓存的测试会进行清除缓存前置操作，不经过缓存则跳过处理
                        if "不经过" in test_name:
                            pass
                        else:
                            clear_cache()
                            time.sleep(5)
                            
                        # dd测试，同时记录速度
                        speed = dd_cmd(full_cmd)
                        if speed > 0:  # 只记录有效的速度值
                            speeds.append(speed)
                            f.write(f"测试数据 {run + 1}: {speed:.2f} MB/s\n")
                        
                        if run < 4:  
                            print("\n等待5s进行下一个dd测试...")
                            time.sleep(5)
                    
                    if speeds:
                        avg_speed = sum(speeds) / len(speeds)
                        current_test_type_results[bs] = f"{avg_speed:.2f}" # 记录平均速度
                        print(f"\n平均速度: {avg_speed:.2f} MB/s")
                        f.write(f"\n平均速度: {avg_speed:.2f} MB/s\n")
                    
                        # 记录该类型测试的摘要
                        all_test_summary.append(f"{mount_point} - {test_name}(bs={bs}k): 平均速度: {avg_speed:.2f} MB/s")
                    else:
                        current_test_type_results[bs] = "N/A" # 记录无有效数据
                        print("\n没有有效的速度数据")
                        f.write("\n没有有效的速度数据\n")
                    f.write("-" * 50 + "\n")

                # 将当前测试类型结果存入当前挂载点的结果字典
                current_mount_point_results[test_name] = current_test_type_results
            
            # 将当前挂载点的结果存入总结果字典
            all_results_data[mount_point] = current_mount_point_results
            
            # 测试完成后删除测试文件
            try:
                subprocess.run(f"rm -f {test_file}", shell=True)
                f.write("\n清理测试文件\n")
            except Exception as e:
                f.write(f"\n清理测试文件失败: {str(e)}\n")
            
            device_end_time = datetime.now()
            device_duration = device_end_time - device_start_time
            f.write(f"\n挂载点 {mount_point} 测试完成时间: {device_end_time}\n")
            f.write(f"挂载点 {mount_point} 测试用时: {device_duration}\n\n")
    
    # 返回日志文件路径、所有挂载点结果、系统信息、所有命令和挂载点详细信息
    return log_file, all_results_data, system_info, "\n".join(all_test_commands), mount_point_details

# 测试挂载点的文件系统性能 - 直接写入指定日志文件
def test_filesystem_direct(mount_point, file_size, log_file=None, fast_test=False):
    """
    功能：测试挂载点的文件系统读写性能，直接写入指定日志文件
    参数：
        mount_point 挂载点路径，如/volume1
        file_size 测试文件大小，单位为G
        log_file 指定的日志文件路径
        fast_test 是否为快速测试模式
    返回:
        包含测试结果的字典
    """
    # 测试不同块大小 - 快速测试模式只测试两种大小
    bs_list = [4, 1024] if fast_test else [4, 8, 16, 32, 64, 128, 256, 512, 1024]
    # xGB文件大小转化为kb - 快速测试模式使用较小文件大小
    fast_size = 1 # 快速测试使用1G
    total_size_kb = (fast_size if fast_test else file_size) * 1024 * 1024
    # 获取设备的型号
    model = get_model()
    
    # 存储测试结果的字典
    results_data = {}
    # 用于存储测试摘要
    test_summary = []
    # 用于存储测试命令
    test_commands = []
    
    print(f"开始进行文件系统dd测试，结果保存在： {log_file}")
    
    # 收集系统信息
    system_info = {
        'model': model,
        'system_version': get_system_version(),
        'memory': get_memory_info()
    }
    
    # 获取挂载点信息
    fs_info = get_mount_point_info(mount_point)
    
    # 打印详细的文件系统信息
    print(f"\n挂载点: {mount_point}")
    print(f"文件系统: {fs_info.get('filesystem', '未知')}")
    print(f"文件系统类型: {fs_info.get('type', '未知')}")
    print(f"总大小: {fs_info.get('size', '未知')}")
    print(f"已用空间: {fs_info.get('used', '未知')}")
    print(f"可用空间: {fs_info.get('avail', '未知')}")
    
    # 如果是MD设备关联的卷，打印MD设备信息
    if fs_info.get('is_md', False):
        parent_dev = fs_info.get('parent_device', '未知')
        print(f"\n【底层阵列信息】")
        print(f"底层MD设备: {parent_dev}")
        
        # 使用从mdadm -D获取的详细信息
        if 'raid_level' in fs_info:
            print(f"阵列类型: {fs_info['raid_level']}")
        elif 'md_info' in fs_info and 'raid_level' in fs_info['md_info']:
            print(f"阵列类型: {fs_info['md_info']['raid_level']}")
        else:
            print(f"阵列类型: 未知")
            
        if 'chunk_size' in fs_info:
            print(f"块大小: {fs_info['chunk_size']}")
        elif 'md_info' in fs_info and 'chunk_size' in fs_info['md_info']:
            print(f"块大小: {fs_info['md_info']['chunk_size']}")
            
        if 'device_count' in fs_info:
            print(f"设备数: {fs_info['device_count']}")
            
        # 显示成员盘
        if 'members' in fs_info and fs_info['members']:
            print(f"成员盘: {', '.join(fs_info['members'])}")
        elif 'md_info' in fs_info and 'members' in fs_info['md_info']:
            print(f"成员盘: {', '.join(fs_info['md_info']['members'])}")
            
        # 获取每个成员盘的详细信息
        members = fs_info.get('members', [])
        if not members and 'md_info' in fs_info:
            members = fs_info['md_info'].get('members', [])
            
        if members:
            print("\n成员盘详情:")
            for member in members:
                try:
                    disk_info = get_disk_detail_info(member.rstrip('0123456789'))  # 去除分区号
                    model = disk_info.get('model', '未知型号').split('\n')[0] if isinstance(disk_info.get('model'), str) else '未知型号'
                    capacity = disk_info.get('capacity', '未知容量')
                    print(f"  • {member}: {model}, {capacity}")
                except:
                    print(f"  • {member}: 无法获取详情")
    
    # 更新系统信息字符串
    system_info['fs_info'] = f"挂载点: {mount_point}\n" \
                            f"文件系统: {fs_info.get('filesystem', '未知')}\n" \
                            f"类型: {fs_info.get('type', '未知')}\n" \
                            f"总大小: {fs_info.get('size', '未知')}\n" \
                            f"已用空间: {fs_info.get('used', '未知')}\n" \
                            f"可用空间: {fs_info.get('avail', '未知')}"
    
    # 如果是MD设备关联的卷，添加MD信息
    if fs_info.get('is_md', False):
        parent_dev = fs_info.get('parent_device', '未知')
        
        # 获取阵列类型信息
        raid_level = "未知"
        if 'raid_level' in fs_info:
            raid_level = fs_info['raid_level']
        elif 'md_info' in fs_info and 'raid_level' in fs_info['md_info']:
            raid_level = fs_info['md_info']['raid_level']
            
        # 获取块大小信息
        chunk_size = "未知"
        if 'chunk_size' in fs_info:
            chunk_size = fs_info['chunk_size']
        elif 'md_info' in fs_info and 'chunk_size' in fs_info['md_info']:
            chunk_size = fs_info['md_info']['chunk_size']
            
        # 获取成员盘
        members = []
        if 'members' in fs_info:
            members = fs_info['members']
        elif 'md_info' in fs_info and 'members' in fs_info['md_info']:
            members = fs_info['md_info']['members']
            
        # 格式化信息
        system_info['fs_info'] += f"\n\n【底层阵列信息】\n" \
                                f"底层MD设备: {parent_dev}\n" \
                                f"阵列类型: {raid_level}\n" \
                                f"块大小: {chunk_size}\n"
                                
        if 'device_count' in fs_info:
            system_info['fs_info'] += f"设备数: {fs_info['device_count']}\n"
            
        if members:
            system_info['fs_info'] += f"成员盘: {', '.join(members)}\n\n"
            
            # 添加成员盘详情
            system_info['fs_info'] += "成员盘详情:\n"
            for member in members:
                try:
                    disk_info = get_disk_detail_info(member.rstrip('0123456789'))  # 去除分区号
                    model = disk_info.get('model', '未知型号').split('\n')[0] if isinstance(disk_info.get('model'), str) else '未知型号'
                    capacity = disk_info.get('capacity', '未知容量')
                    system_info['fs_info'] += f"  • {member}: {model}, {capacity}\n"
                except:
                    system_info['fs_info'] += f"  • {member}: 无法获取详情\n"
    
    # 测试文件路径
    test_file = f"{mount_point}/dd_test_file_{datetime.now().strftime('%Y%m%d_%H%M%S')}.dat"
    
    with open(log_file, 'w') as f:
        start_time = datetime.now()
        f.write(f"开始测试时间： {start_time}\n\n")
        f.write(f"系统信息:\n")
        f.write(f"设备型号: {system_info['model']}\n")
        f.write(f"系统版本: {system_info['system_version']}\n")
        f.write(f"内存大小: {system_info['memory']}\n\n")
        f.write(f"文件系统信息:\n{system_info['fs_info']}\n\n")
        
        # 快速测试模式只测试一种场景
        if fast_test:
            tests = [("文件系统测试-经过缓存顺序读", f"if={test_file} of=/dev/null", range(1, 2))]
            # 先创建测试文件
            print(f"创建测试文件: {test_file}")
            f.write(f"创建测试文件: {test_file}\n")
            create_cmd = f"dd if=/dev/zero of={test_file} bs=1M count={fast_size*1024}"
            subprocess.run(create_cmd, shell=True)
        else:
            tests = [
                ("文件系统测试-不经过缓存顺序写", f"if=/dev/zero of={test_file} oflag=direct", range(1, 2)),
                ("文件系统测试-不经过缓存顺序读", f"if={test_file} of=/dev/null iflag=direct", range(3, 4)),
                ("文件系统测试-经过缓存顺序写", f"if=/dev/zero of={test_file}", range(5, 6)),
                ("文件系统测试-经过缓存顺序读", f"if={test_file} of=/dev/null", range(7, 8)),
            ]

        for test_name, cmd_template, test_range in tests:
            print(f"\n{'='*50}")
            print(f"开始{model}-{mount_point}-{test_name}测试")
            print(f"{'='*50}")
            f.write(f"\n{model}-{mount_point}-{test_name}测试:\n")
            
            # 记录测试命令
            base_cmd = f"dd {cmd_template} bs=<块大小>k count=<计数>"
            test_commands.append(f"{test_name}: {base_cmd}")
            
            # 用于存储当前测试类型下各块大小的结果
            current_test_results = {}
            
            for i, bs in enumerate(bs_list):
                test_num = i + test_range.start
                # 根据文件大小和块大小计算count值
                count = total_size_kb // bs
                # 统计传输速度
                speeds = []
                
                print(f"\n测试项目 {test_num}: 块大小 = {bs}k, Count = {count}")
                f.write(f"\n测试项目(bs={bs}k):\n")
                
                # 完整的dd命令
                full_cmd = f"dd {cmd_template} bs={bs}k count={count}"
                f.write(f"测试命令: {full_cmd}\n")
                
                # 循环执行test_rounds次计算传输速度的平均值
                test_runs = 1 if fast_test else test_rounds
                for run in range(test_runs):
                    print(f"\n测试数据{run + 1}/{test_runs}:")
                    # 经过缓存的测试会进行清除缓存前置操作，不经过缓存则跳过处理
                    if "不经过" in test_name:
                        pass
                    else:
                        clear_cache()
                        if not fast_test:
                            time.sleep(5)
                        
                    # dd测试，同时记录速度
                    speed = dd_cmd(full_cmd)
                    if speed > 0:  # 只记录有效的速度值
                        speeds.append(speed)
                        f.write(f"测试数据 {run + 1}: {speed:.2f} MB/s\n")
                    
                    if run < test_runs - 1:  
                        wait_time = 1 if fast_test else 5
                        print(f"\n等待{wait_time}s进行下一个dd测试...")
                        time.sleep(wait_time)
                
                if speeds:
                    avg_speed = sum(speeds) / len(speeds)
                    current_test_results[bs] = f"{avg_speed:.2f}" # 记录平均速度
                    print(f"\n平均速度: {avg_speed:.2f} MB/s")
                    f.write(f"\n平均速度: {avg_speed:.2f} MB/s\n")
                    
                    # 记录该类型测试的摘要
                    test_summary.append(f"{mount_point} - {test_name}(bs={bs}k): 平均速度: {avg_speed:.2f} MB/s")
                else:
                    current_test_results[bs] = "N/A" # 记录无有效数据
                    print("\n没有有效的速度数据")
                    f.write("\n没有有效的速度数据\n")
                f.write("-" * 50 + "\n")
            
            # 将当前测试类型的结果存入总结果字典
            results_data[test_name] = current_test_results
        
        # 测试完成后删除测试文件
        try:
            subprocess.run(f"rm -f {test_file}", shell=True)
            f.write("\n清理测试文件\n")
        except Exception as e:
            f.write(f"\n清理测试文件失败: {str(e)}\n")

    # 返回测试结果数据、系统信息和测试命令
    return results_data, system_info, "\n".join(test_commands)

# 测试所有挂载点的文件系统性能 - 直接写入指定日志文件
def test_all_filesystems_direct(file_size, log_file=None, fast_test=False, test_rounds=5):
    """
    功能：测试所有挂载点的文件系统性能，直接写入指定日志文件
    参数：
        file_size 测试文件大小，单位为G
        log_file 指定的日志文件路径
        fast_test 是否为快速测试模式
        test_rounds 测试轮数，默认为5
    返回:
        包含所有挂载点测试结果的字典
    """
    # 全局变量，用于检查是否应该退出
    global should_exit
    
    # 获取设备的型号
    model = get_model()
    
    # 获取所有挂载点 - 只获取/volume开头的
    mount_points = get_all_mount_points()
    if not mount_points:
        print("没有找到有效的挂载点 (/volume开头的挂载点)")
        return {}, {}, "", {}
    else:
        print(f"找到以下有效挂载点: {', '.join(mount_points)}")
    
    # 存储所有挂载点的测试结果
    all_results_data = {}
    # 用于存储所有挂载点的测试摘要
    all_test_summary = []
    # 用于存储所有测试命令
    all_test_commands = []
    
    # 收集系统信息
    system_info = {
        'model': model,
        'system_version': get_system_version(),
        'memory': get_memory_info(),
        'fs_info': f"测试对象: 所有/volume挂载点\n测试挂载点列表: {', '.join(mount_points)}" # 初始信息
    }
    
    mount_point_details = {} # 用于存储每个挂载点的详细信息
    
    with open(log_file, 'w') as f:
        start_time = datetime.now()
        f.write(f"开始测试时间： {start_time}\n\n")
        f.write(f"系统信息:\n")
        f.write(f"设备型号: {system_info['model']}\n")
        f.write(f"系统版本: {system_info['system_version']}\n")
        f.write(f"内存大小: {system_info['memory']}\n\n")
        f.write(f"测试对象: 所有/volume挂载点\n")
        f.write(f"测试挂载点列表: {', '.join(mount_points)}\n\n")
        f.write(f"测试轮数: {test_rounds}\n\n")
        
        # 依次测试每个挂载点
        for mount_point in mount_points:
            # 检查是否应该退出程序
            if should_exit:
                f.write("\n因用户中断，测试提前停止\n")
                break
                
            # 获取挂载点详情
            fs_info = get_mount_point_info(mount_point)
            mount_point_details[mount_point] = fs_info
            
            # 打印详细的文件系统信息
            print(f"\n挂载点: {mount_point}")
            print(f"文件系统: {fs_info.get('filesystem', '未知')}")
            print(f"文件系统类型: {fs_info.get('type', '未知')}")
            print(f"总大小: {fs_info.get('size', '未知')}")
            print(f"已用空间: {fs_info.get('used', '未知')}")
            print(f"可用空间: {fs_info.get('avail', '未知')}")
            
            # 如果是MD设备关联的卷，打印MD设备信息
            if fs_info.get('is_md', False):
                parent_dev = fs_info.get('parent_device', '未知')
                print(f"\n【底层阵列信息】")
                print(f"底层MD设备: {parent_dev}")
                
                # 使用从mdadm -D获取的详细信息
                if 'raid_level' in fs_info:
                    print(f"阵列类型: {fs_info['raid_level']}")
                elif 'md_info' in fs_info and 'raid_level' in fs_info['md_info']:
                    print(f"阵列类型: {fs_info['md_info']['raid_level']}")
                else:
                    print(f"阵列类型: 未知")
                    
                if 'chunk_size' in fs_info:
                    print(f"块大小: {fs_info['chunk_size']}")
                elif 'md_info' in fs_info and 'chunk_size' in fs_info['md_info']:
                    print(f"块大小: {fs_info['md_info']['chunk_size']}")
                    
                if 'device_count' in fs_info:
                    print(f"设备数: {fs_info['device_count']}")
                    
                # 显示成员盘
                if 'members' in fs_info and fs_info['members']:
                    print(f"成员盘: {', '.join(fs_info['members'])}")
                elif 'md_info' in fs_info and 'members' in fs_info['md_info']:
                    print(f"成员盘: {', '.join(fs_info['md_info']['members'])}")
                    
                # 获取每个成员盘的详细信息
                members = fs_info.get('members', [])
                if not members and 'md_info' in fs_info:
                    members = fs_info['md_info'].get('members', [])
                    
                if members:
                    print("\n成员盘详情:")
                    for member in members:
                        try:
                            disk_info = get_disk_detail_info(member.rstrip('0123456789'))  # 去除分区号
                            model = disk_info.get('model', '未知型号').split('\n')[0] if isinstance(disk_info.get('model'), str) else '未知型号'
                            capacity = disk_info.get('capacity', '未知容量')
                            print(f"  • {member}: {model}, {capacity}")
                        except:
                            print(f"  • {member}: 无法获取详情")
            
            # 记录挂载点信息
            fs_info_str = f"挂载点: {mount_point}\n" \
                         f"文件系统: {fs_info.get('filesystem', '未知')}\n" \
                         f"类型: {fs_info.get('type', '未知')}\n" \
                         f"总大小: {fs_info.get('size', '未知')}\n" \
                         f"已用空间: {fs_info.get('used', '未知')}\n" \
                         f"可用空间: {fs_info.get('avail', '未知')}"
            
            # 如果是MD设备关联的卷，添加MD信息
            if fs_info.get('is_md', False):
                parent_dev = fs_info.get('parent_device', '未知')
                
                # 获取阵列类型信息
                raid_level = "未知"
                if 'raid_level' in fs_info:
                    raid_level = fs_info['raid_level']
                elif 'md_info' in fs_info and 'raid_level' in fs_info['md_info']:
                    raid_level = fs_info['md_info']['raid_level']
                    
                # 获取块大小信息
                chunk_size = "未知"
                if 'chunk_size' in fs_info:
                    chunk_size = fs_info['chunk_size']
                elif 'md_info' in fs_info and 'chunk_size' in fs_info['md_info']:
                    chunk_size = fs_info['md_info']['chunk_size']
                    
                # 获取成员盘
                members = []
                if 'members' in fs_info:
                    members = fs_info['members']
                elif 'md_info' in fs_info and 'members' in fs_info['md_info']:
                    members = fs_info['md_info']['members']
                    
                # 格式化信息
                fs_info_str += f"\n\n【底层阵列信息】\n" \
                             f"底层MD设备: {parent_dev}\n" \
                             f"阵列类型: {raid_level}\n" \
                             f"块大小: {chunk_size}\n"
                            
                if 'device_count' in fs_info:
                    fs_info_str += f"设备数: {fs_info['device_count']}\n"
                    
                if members:
                    fs_info_str += f"成员盘: {', '.join(members)}\n\n"
                    
                    # 添加成员盘详情
                    fs_info_str += "成员盘详情:\n"
                    for member in members:
                        try:
                            disk_info = get_disk_detail_info(member.rstrip('0123456789'))  # 去除分区号
                            model = disk_info.get('model', '未知型号').split('\n')[0] if isinstance(disk_info.get('model'), str) else '未知型号'
                            capacity = disk_info.get('capacity', '未知容量')
                            fs_info_str += f"  • {member}: {model}, {capacity}\n"
                        except:
                            fs_info_str += f"  • {member}: 无法获取详情\n"
            
            device_start_time = datetime.now()
            f.write(f"\n{'='*50}\n")
            f.write(f"开始测试挂载点: {mount_point}\n")
            f.write(f"{'='*50}\n")
            f.write(f"{fs_info_str}\n\n")
            
            print(f"\n\n{'='*80}")
            print(f"开始测试挂载点: {mount_point}")
            print(f"{'='*80}")
            
            # 测试文件路径
            test_file = f"{mount_point}/dd_test_file_{datetime.now().strftime('%Y%m%d_%H%M%S')}.dat"
            
            # 测试不同块大小 - 快速测试模式只测试两种大小
            bs_list = [4, 1024] if fast_test else [4, 8, 16, 32, 64, 128, 256, 512, 1024]
            # xGB文件大小转化为kb - 快速测试模式使用较小文件大小
            fast_size = 1 # 快速测试使用1G
            total_size_kb = (fast_size if fast_test else file_size) * 1024 * 1024
            
            # 存储当前挂载点测试结果的字典
            current_mount_point_results = {}
            
            # 快速测试模式只测试一种场景
            if fast_test:
                tests = [("文件系统测试-经过缓存顺序读", f"if={test_file} of=/dev/null", range(1, 2))]
                # 先创建测试文件
                print(f"创建测试文件: {test_file}")
                f.write(f"创建测试文件: {test_file}\n")
                create_cmd = f"dd if=/dev/zero of={test_file} bs=1M count={fast_size*1024}"
                subprocess.run(create_cmd, shell=True)
            else:
                tests = [
                    ("文件系统测试-不经过缓存顺序写", f"if=/dev/zero of={test_file} oflag=direct", range(1, 2)),
                    ("文件系统测试-不经过缓存顺序读", f"if={test_file} of=/dev/null iflag=direct", range(3, 4)),
                    ("文件系统测试-经过缓存顺序写", f"if=/dev/zero of={test_file}", range(5, 6)),
                    ("文件系统测试-经过缓存顺序读", f"if={test_file} of=/dev/null", range(7, 8)),
                ]

            for test_name, cmd_template, test_range in tests:
                # 检查是否应该退出程序
                if should_exit:
                    f.write("\n因用户中断，测试提前停止\n")
                    break
                    
                print(f"\n{'='*50}")
                print(f"开始{model}-{mount_point}-{test_name}测试")
                print(f"{'='*50}")
                f.write(f"\n{model}-{mount_point}-{test_name}测试:\n")
                
                # 记录测试命令
                base_cmd = f"dd {cmd_template} bs=<块大小>k count=<计数>"
                all_test_commands.append(f"{mount_point} - {test_name}: {base_cmd}")
                
                # 存储当前测试类型下各块大小的结果
                current_test_type_results = {}
                
                for i, bs in enumerate(bs_list):
                    # 检查是否应该退出程序
                    if should_exit:
                        f.write("\n因用户中断，测试提前停止\n")
                    test_num = i + test_range.start
                    # 根据文件大小和块大小计算count值
                    count = total_size_kb // bs
                    # 统计传输速度
                    speeds = []
                    
                    print(f"\n测试项目 {test_num}: 块大小 = {bs}k, Count = {count}")
                    f.write(f"\n测试项目(bs={bs}k):\n")
                    
                    # 完整的dd命令
                    full_cmd = f"dd {cmd_template} bs={bs}k count={count}"
                    f.write(f"测试命令: {full_cmd}\n")
                    
                    # 循环执行test_rounds次计算传输速度的平均值
                    test_runs = 1 if fast_test else test_rounds
                    for run in range(test_runs):
                        print(f"\n测试数据{run + 1}/{test_runs}:")
                        # 经过缓存的测试会进行清除缓存前置操作，不经过缓存则跳过处理
                        if "不经过" in test_name:
                            pass
                        else:
                            clear_cache()
                            if not fast_test:
                                time.sleep(5)
                            
                        # dd测试，同时记录速度
                        speed = dd_cmd(full_cmd)
                        if speed > 0:  # 只记录有效的速度值
                            speeds.append(speed)
                            f.write(f"测试数据 {run + 1}: {speed:.2f} MB/s\n")
                        
                        if run < test_runs - 1:  
                            wait_time = 1 if fast_test else 5
                            print(f"\n等待{wait_time}s进行下一个dd测试...")
                            time.sleep(wait_time)
                    
                    if speeds:
                        avg_speed = sum(speeds) / len(speeds)
                        current_test_type_results[bs] = f"{avg_speed:.2f}" # 记录平均速度
                        print(f"\n平均速度: {avg_speed:.2f} MB/s")
                        f.write(f"\n平均速度: {avg_speed:.2f} MB/s\n")
                    
                        # 记录该类型测试的摘要
                        all_test_summary.append(f"{mount_point} - {test_name}(bs={bs}k): 平均速度: {avg_speed:.2f} MB/s")
                    else:
                        current_test_type_results[bs] = "N/A" # 记录无有效数据
                        print("\n没有有效的速度数据")
                        f.write("\n没有有效的速度数据\n")
                    f.write("-" * 50 + "\n")

                # 将当前测试类型结果存入当前挂载点的结果字典
                current_mount_point_results[test_name] = current_test_type_results
            
            # 将当前挂载点的结果存入总结果字典
            all_results_data[mount_point] = current_mount_point_results
            
            # 测试完成后删除测试文件
            try:
                subprocess.run(f"rm -f {test_file}", shell=True)
                f.write("\n清理测试文件\n")
            except Exception as e:
                f.write(f"\n清理测试文件失败: {str(e)}\n")
            
            device_end_time = datetime.now()
            device_duration = device_end_time - device_start_time
            f.write(f"\n挂载点 {mount_point} 测试完成时间: {device_end_time}\n")
            f.write(f"挂载点 {mount_point} 测试用时: {device_duration}\n\n")
    
    # 返回所有挂载点结果、系统信息、所有命令和挂载点详细信息
    return all_results_data, system_info, "\n".join(all_test_commands), mount_point_details

# 直接版本的硬盘测试函数，直接写入指定日志文件 - 增加快速测试模式
def test_disk_direct(device, file_size, is_md_device=True, log_file=None, fast_test=False, test_rounds=5):
    """
    功能：测试不同块大小文件,带缓存和不带缓存读写测试
    参数：
        device 设备名称 例：md1或sda
        file_size 文件大小，单位为G
        is_md_device 是否为md设备，True为阵列设备，False为裸盘
        log_file 指定的日志文件路径
        fast_test 是否为快速测试模式
        test_rounds 测试轮数，默认为5

    返回:
        包含测试结果的字典
    """
    # 全局变量，用于检查是否应该退出
    global should_exit
    
    # 测试不同块大小 - 快速测试模式只测试两种大小
    bs_list = [4, 1024] if fast_test else [4, 8, 16, 32, 64, 128, 256, 512, 1024]
    # xGB文件大小转化为kb - 快速测试模式使用较小文件大小
    fast_size = 1 # 快速测试使用1G
    total_size_kb = (fast_size if fast_test else file_size) * 1024 * 1024
    # 获取设备的型号
    model = get_model()
    
    # 存储测试结果的字典
    results_data = {}
    # 用于存储测试摘要
    test_summary = []
    # 用于存储测试命令
    test_commands = []
    
    print(f"开始进行dd测试，结果保存在： {log_file}")
    
    # 收集系统信息
    system_info = {
        'model': model,
        'system_version': get_system_version(),
        'memory': get_memory_info()
    }
    
    # 如果是裸盘，获取硬盘信息
    if not is_md_device:
        disk_info = get_disk_detail_info(device)
        system_info['disk_info'] = f"硬盘型号: {disk_info.get('model', '未知')}\n连接方式: {disk_info.get('type', '未知')}\n连接详情: {disk_info.get('connection', '未知')}"
    else:
        # 如果是MD设备，获取MD设备信息
        md_info = get_md_info()
        md_detail = md_info.get(device, {})
        raid_level = md_detail.get('raid_level', '未知')
        chunk_size = md_detail.get('chunk_size', '未知')
        bitmap = md_detail.get('bitmap', False)
        bitmap_info = md_detail.get('bitmap_info', '无') if bitmap else '未开启'
        members = md_detail.get('members', [])
        
        md_info_str = f"阵列类型: {raid_level}\nChunk Size: {chunk_size}\nBitmap: "
        if bitmap:
            md_info_str += f"已开启 ({bitmap_info})"
        else:
            md_info_str += "未开启"
        
        if members:
            md_info_str += f"\n成员盘: {', '.join(members)}"
            
        system_info['disk_info'] = md_info_str
    
    with open(log_file, 'w') as f:
        start_time = datetime.now()
        f.write(f"开始测试时间： {start_time}\n\n")
        f.write(f"系统信息:\n")
        f.write(f"设备型号: {system_info['model']}\n")
        f.write(f"系统版本: {system_info['system_version']}\n")
        f.write(f"内存大小: {system_info['memory']}\n\n")
        f.write(f"硬盘信息:\n{system_info['disk_info']}\n\n")
        f.write(f"测试轮数: {test_rounds}\n\n")
        
        # 快速测试模式只测试一种场景
        if fast_test:
            tests = []
            if is_md_device:
                tests = [("阵列读写测试-经过缓存顺序读", f"if=/dev/{device} of=/dev/null", range(1, 2))]
            else:
                tests = [("硬盘裸盘测试-经过缓存顺序读", f"if=/dev/{device} of=/dev/null", range(1, 2))]
        else:
            tests = []
            if is_md_device:
                tests = [
                    ("阵列读写测试-不经过缓存顺序写", f"if=/dev/zero of=/dev/{device} oflag=direct", range(1, 2)),
                    ("阵列读写测试-不经过缓存顺序读", f"if=/dev/{device} of=/dev/null iflag=direct", range(3, 4)),
                    ("阵列读写测试-经过缓存顺序写", f"if=/dev/zero of=/dev/{device}", range(5, 6)),
                    ("阵列读写测试-经过缓存顺序读", f"if=/dev/{device} of=/dev/null", range(7, 8)),
                ]
            else:
                tests = [
                    ("硬盘裸盘测试-不经过缓存顺序写", f"if=/dev/zero of=/dev/{device} oflag=direct", range(1, 2)),
                    ("硬盘裸盘测试-不经过缓存顺序读", f"if=/dev/{device} of=/dev/null iflag=direct", range(3, 4)),
                    ("硬盘裸盘测试-经过缓存顺序写", f"if=/dev/zero of=/dev/{device}", range(5, 6)),
                    ("硬盘裸盘测试-经过缓存顺序读", f"if=/dev/{device} of=/dev/null", range(7, 8)),
                ]

        for test_name, cmd_template, test_range in tests:
            # 检查是否应该退出程序
            if should_exit:
                f.write("\n因用户中断，测试提前停止\n")
                break
                
            print(f"\n{'='*50}")
            print(f"开始{model}-{device}-{test_name}测试")
            print(f"{'='*50}")
            f.write(f"\n{model}-{device}-{test_name}测试:\n")
            
            # 记录测试命令
            base_cmd = f"dd {cmd_template} bs=<块大小>k count=<计数>"
            test_commands.append(f"{test_name}: {base_cmd}")
            
            # 用于存储当前测试类型下各块大小的结果
            current_test_results = {}
            
            for i, bs in enumerate(bs_list):
                # 检查是否应该退出程序
                if should_exit:
                    f.write("\n因用户中断，测试提前停止\n")
                    break
                    
                test_num = i + test_range.start
                # 根据文件大小和块大小计算count值
                count = total_size_kb // bs
                # 统计传输速度
                speeds = []
                
                print(f"\n测试项目 {test_num}: 块大小 = {bs}k, Count = {count}")
                f.write(f"\n测试项目(bs={bs}k):\n")
                
                # 完整的dd命令
                full_cmd = f"dd {cmd_template} bs={bs}k count={count}"
                f.write(f"测试命令: {full_cmd}\n")
                
                # 循环执行test_rounds次计算传输速度的平均值
                test_runs = 1 if fast_test else test_rounds
                for run in range(test_runs):
                    # 检查是否应该退出程序
                    if should_exit:
                        f.write("\n因用户中断，测试提前停止\n")
                        break
                        
                    print(f"\n测试数据{run + 1}/{test_runs}:")
                    # 经过缓存的测试会进行清除缓存前置操作，不经过缓存则跳过处理
                    if "不经过" in test_name:
                        pass
                    else:
                        clear_cache()
                        if not fast_test:
                            time.sleep(5)
                        
                    # dd测试，同时记录速度
                    speed = dd_cmd(full_cmd)
                    if speed > 0:  # 只记录有效的速度值
                        speeds.append(speed)
                        f.write(f"测试数据 {run + 1}: {speed:.2f} MB/s\n")
                    
                    if run < test_runs - 1 and not should_exit:  
                        wait_time = 1 if fast_test else 5
                        print(f"\n等待{wait_time}s进行下一个dd测试...")
                        time.sleep(wait_time)
                
                if speeds:
                    avg_speed = sum(speeds) / len(speeds)
                    current_test_results[bs] = f"{avg_speed:.2f}" # 记录平均速度
                    print(f"\n平均速度: {avg_speed:.2f} MB/s")
                    f.write(f"\n平均速度: {avg_speed:.2f} MB/s\n")
                    
                    # 记录该类型测试的摘要
                    test_summary.append(f"{device} - {test_name}(bs={bs}k): 平均速度: {avg_speed:.2f} MB/s")
                else:
                    current_test_results[bs] = "N/A" # 记录无有效数据
                    print("\n没有有效的速度数据")
                    f.write("\n没有有效的速度数据\n")
                f.write("-" * 50 + "\n")
            
            # 将当前测试类型的结果存入总结果字典
            results_data[test_name] = current_test_results

    # 返回测试结果数据、系统信息和测试命令
    return results_data, system_info, "\n".join(test_commands)

# 修改主函数
if __name__ == "__main__":
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 参数检查
    if len(sys.argv) != 3 and len(sys.argv) != 4:
        show_usage()
        sys.exit(1)

    # 参数1: 测试选项 (比如 all/allmd/allvol/具体设备名/挂载点路径，选你所爱)
    test_option = sys.argv[1]
    # 参数2：测试文件大小,单位为G 或 "test" 表示快速测试模式
    file_size_str = sys.argv[2]
    # 参数3（可选）：测试轮数，默认为5
    test_rounds = 5
    if len(sys.argv) == 4:
        try:
            test_rounds = int(sys.argv[3])
            if test_rounds <= 0:
                print("测试轮数必须大于0，将使用默认值5")
                test_rounds = 5
        except ValueError:
            print(f"无效的测试轮数 '{sys.argv[3]}'，将使用默认值5")
            test_rounds = 5
    
    # 检查是否为快速测试模式
    fast_test = False
    file_size = 5 # 默认大小，快速测试时会被忽略
    
    if file_size_str.lower() == 'test':
        fast_test = True
        print("启用快速测试模式，将只进行最小量的测试以验证功能是否正常")
        test_rounds = 1  # 快速测试模式下强制设为1轮
    else:
        try:
            file_size = int(file_size_str)
            if file_size <= 0:
                 raise ValueError("文件大小必须是正整数")
        except ValueError as e:
            print(f"错误：无效的文件大小 '{file_size_str}'. {e}")
            show_usage()
            sys.exit(1)
            
    print(f"测试轮数设置为: {test_rounds}")
    
    start_time = datetime.now()
    timestamp = start_time.strftime('%Y%m%d_%H%M%S')
    print(f"测试开始时间: {start_time}")
    
    results_data = {}
    system_info = {}
    test_commands = ""
    device_details = {} # 用于存储测试设备的详细信息

    try:
        # 获取系统信息
        system_info = {
            'model': get_model(),
            'system_version': get_system_version(),
            'memory': get_memory_info(),
        }
        
        # 获取MD信息,用于创建目录
        md_info = get_md_info()
        
        # 收集可能的文件系统类型和RAID类型，用于文件名
        fs_types = []
        raid_types = []
        
        # 从MD信息中获取RAID类型
        if md_info:
            for md_device, info in md_info.items():
                raid_type = info.get('raid_level', '')
                if raid_type and raid_type not in raid_types:
                    raid_types.append(raid_type)
        
        # 如果是测试单个挂载点，获取其文件系统类型
        if test_option.startswith('/'):
            try:
                fs_info = get_mount_point_info(test_option)
                fs_type = fs_info.get('type', '')
                if fs_type and fs_type not in fs_types:
                    fs_types.append(fs_type)
                # 如果挂载点基于MD设备，获取其RAID类型
                if fs_info.get('is_md', False):
                    raid_type = ""
                    if 'raid_level' in fs_info:
                        raid_type = fs_info['raid_level']
                    elif 'md_info' in fs_info and 'raid_level' in fs_info['md_info']:
                        raid_type = fs_info['md_info']['raid_level']
                    if raid_type and raid_type not in raid_types:
                        raid_types.append(raid_type)
            except:
                pass
        # 如果是测试所有挂载点，预先获取所有挂载点的文件系统类型
        elif test_option.lower() == 'allvol':
            mount_points = get_all_mount_points()
            for mount in mount_points:
                try:
                    fs_info = get_mount_point_info(mount)
                    fs_type = fs_info.get('type', '')
                    if fs_type and fs_type not in fs_types:
                        fs_types.append(fs_type)
                    # 如果挂载点基于MD设备，获取其RAID类型
                    if fs_info.get('is_md', False):
                        raid_type = ""
                        if 'raid_level' in fs_info:
                            raid_type = fs_info['raid_level']
                        elif 'md_info' in fs_info and 'raid_level' in fs_info['md_info']:
                            raid_type = fs_info['md_info']['raid_level']
                        if raid_type and raid_type not in raid_types:
                            raid_types.append(raid_type)
                except:
                    pass
        
        # 创建测试目录，使用统一的时间戳
        test_dir = create_test_dir(system_info, md_info)
        print(f"创建测试目录: {test_dir}")
        
        # 构建文件名后缀，包含文件系统类型和RAID类型
        name_suffix = ""
        if fs_types:
            name_suffix += "_" + "_".join(fs_types)
        if raid_types:
            name_suffix += "_" + "_".join(raid_types)
        
        # 根据测试选项确定日志文件名前缀
        if test_option.lower() == 'all':
            # 测试所有SATA硬盘
            sata_disks = get_all_sata_disks()
            if not sata_disks:
                print("未找到可测试的SATA硬盘设备")
                sys.exit(1)
            print(f"找到以下SATA硬盘设备: {', '.join(sata_disks)}")
            
            # 在快速测试模式下只测试第一个磁盘
            if fast_test and sata_disks:
                test_disk = sata_disks[0]
                print(f"快速测试模式：仅测试第一个磁盘 {test_disk}")
                sata_disks = [test_disk]
                
            # 获取硬盘详细信息
            for disk in sata_disks:
                device_details[disk] = get_disk_detail_info(disk)
                
            # 修改：使用所有硬盘名称替代"ALL_SATA"
            log_prefix = f"{system_info['model']}_{'_'.join(sata_disks)}"
                
            # 修改函数调用，直接传入log_file参数，避免在当前目录创建日志
            results_data, system_info, test_commands, device_details = test_all_devices_direct(
                sata_disks, file_size=file_size, is_md_devices=False, log_file=os.path.join(test_dir, f"{log_prefix}_test_{timestamp}.log"), fast_test=fast_test, test_rounds=test_rounds)
            
        elif test_option.lower() == 'allmd':
            # 测试所有MD阵列设备
            md_devices = get_all_md_devices()
            if not md_devices:
                print("未找到可测试的MD阵列设备")
                sys.exit(1)
            print(f"找到以下MD阵列设备: {', '.join(md_devices)}")
            
            # 在快速测试模式下只测试第一个MD设备
            if fast_test and md_devices:
                test_md = md_devices[0]
                print(f"快速测试模式：仅测试第一个MD阵列 {test_md}")
                md_devices = [test_md]
                
            # 修改：使用所有MD设备名称替代"ALL_MD"
            log_prefix = f"{system_info['model']}_{'_'.join(md_devices)}{name_suffix}"
                
            # 修改函数调用，直接传入log_file参数
            results_data, system_info, test_commands, device_details = test_all_devices_direct(
                md_devices, file_size=file_size, is_md_devices=True, log_file=os.path.join(test_dir, f"{log_prefix}_test_{timestamp}.log"), fast_test=fast_test, test_rounds=test_rounds)
            
        elif test_option.lower() == 'allvol':
            # 测试所有挂载点文件系统
            mount_points = get_all_mount_points()
            if not mount_points:
                print("未找到可测试的挂载点")
                sys.exit(1)
            print(f"找到以下挂载点: {', '.join(mount_points)}")
            
            # 在快速测试模式下只测试第一个挂载点
            if fast_test and mount_points:
                test_mount = mount_points[0]
                print(f"快速测试模式：仅测试第一个挂载点 {test_mount}")
                mount_points = [test_mount]
            
            # 修改：使用所有挂载点名称（替换'/'为'_'）替代"ALL_FS"
            mount_points_names = [mp.replace('/', '_') for mp in mount_points]
            log_prefix = f"{system_info['model']}_{'_'.join(mount_points_names)}{name_suffix}"
                
            # 修改函数调用，直接传入log_file参数
            results_data, system_info, test_commands, device_details = test_all_filesystems_direct(
                file_size=file_size, log_file=os.path.join(test_dir, f"{log_prefix}_test_{timestamp}.log"), fast_test=fast_test, test_rounds=test_rounds)
            
        elif test_option.startswith('/'):
            # 测试单个挂载点
            # 首先检查挂载点是否存在
            if not os.path.ismount(test_option):
                print(f"错误: {test_option} 不是有效的挂载点")
                sys.exit(1)
                
            log_prefix = f"{system_info['model']}_{test_option.replace('/', '_')}{name_suffix}"
                
            # 修改函数调用，直接传入log_file参数
            fs_results, system_info, test_commands = test_filesystem_direct(
                test_option, file_size=file_size, log_file=os.path.join(test_dir, f"{log_prefix}_test_{timestamp}.log"), fast_test=fast_test, test_rounds=test_rounds)
                
            # 将单个挂载点结果包装成多个挂载点结果的格式
            results_data = {test_option: fs_results}
            # 获取单个挂载点的详细信息
            device_details = {test_option: get_mount_point_info(test_option)}
            
        else:
            # 测试单个设备
            is_md_device = test_option.startswith('md')
            
            # 检查设备是否存在
            if not os.path.exists(f"/dev/{test_option}"):
                print(f"错误: /dev/{test_option} 设备不存在")
                sys.exit(1)
                
            log_prefix = f"{system_info['model']}_{test_option}{name_suffix}"
                
            # 获取硬盘详细信息
            if not is_md_device:
                device_details[test_option] = get_disk_detail_info(test_option)
                
            # 修改函数调用，直接传入log_file参数
            device_results, system_info, test_commands = test_disk_direct(
                test_option, file_size=file_size, is_md_device=is_md_device, log_file=os.path.join(test_dir, f"{log_prefix}_test_{timestamp}.log"), fast_test=fast_test, test_rounds=test_rounds)
                
            # 将单个设备结果包装成多设备结果的格式
            results_data = {test_option: device_results}
            # 获取单个设备的详细信息
            if is_md_device:
                device_details = {test_option: {'type': 'md'}} # MD信息后续从mdstat获取
            else:
                device_details = {test_option: get_disk_detail_info(test_option)}
        
        # 快速测试模式添加标记
        if fast_test:
            log_prefix += "_FAST"
        
        # 直接在测试目录中创建日志文件
        log_file = os.path.join(test_dir, f"{log_prefix}_test_{timestamp}.log")
        
        # 生成HTML报告，使用相同的时间戳，确保文件名与日志文件一致
        report_prefix = log_prefix.replace("_test_", "_perf_report_")
        report_file = os.path.join(test_dir, f"{report_prefix}_{timestamp}.html")
        generate_html_report_direct(report_file, results_data, system_info, test_commands, device_details)
        print(f"\nHTML报告已生成: {report_file}")
        
    except Exception as e:
        print(f"发生严重错误：{str(e)}")
        import traceback
        traceback.print_exc() # 打印详细错误堆栈
        sys.exit(1)
    finally:
        end_time = datetime.now()
        duration = end_time - start_time
        print(f"\n测试完成时间: {end_time}")
        print(f"总用时: {duration}")
        print(f"\n结果保存在目录: {os.path.abspath(test_dir)}")

