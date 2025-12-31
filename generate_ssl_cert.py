#!/usr/bin/env python3
"""
生成自签名SSL证书脚本
用于局域网HTTPS访问
"""
import os
import sys
import subprocess
import socket

def get_local_ip():
    """获取本机局域网IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "localhost"

def generate_cert():
    """生成自签名SSL证书"""
    print("🔐 开始生成SSL证书...")
    print("-" * 60)
    
    # 获取本机IP
    local_ip = get_local_ip()
    print(f"📍 检测到局域网IP: {local_ip}")
    
    # 证书文件路径
    cert_dir = os.path.dirname(os.path.abspath(__file__))
    key_file = os.path.join(cert_dir, "ssl", "server.key")
    cert_file = os.path.join(cert_dir, "ssl", "server.crt")
    
    # 创建ssl目录
    ssl_dir = os.path.join(cert_dir, "ssl")
    if not os.path.exists(ssl_dir):
        os.makedirs(ssl_dir)
        print(f"✅ 创建SSL目录: {ssl_dir}")
    
    # 检查是否已存在证书
    if os.path.exists(key_file) and os.path.exists(cert_file):
        print(f"⚠️  证书文件已存在:")
        print(f"   密钥文件: {key_file}")
        print(f"   证书文件: {cert_file}")
        response = input("是否重新生成？(y/N): ").strip().lower()
        if response != 'y':
            print("✅ 使用现有证书")
            return key_file, cert_file
        print()
    
    # 检查OpenSSL是否安装（支持Windows常见安装路径）
    openssl_cmd = None
    try:
        result = subprocess.run(["openssl", "version"], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        if result.returncode == 0:
            openssl_cmd = "openssl"
            print(f"✅ OpenSSL已安装: {result.stdout.strip()}")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # 在Windows上尝试查找常见安装路径
        if sys.platform == "win32":
            print("⚠️  OpenSSL不在系统PATH中，尝试查找常见安装路径...")
            common_paths = [
                r"C:\Program Files\OpenSSL-Win64\bin\openssl.exe",
                r"C:\OpenSSL-Win64\bin\openssl.exe",
                r"C:\Program Files (x86)\OpenSSL-Win32\bin\openssl.exe",
                r"C:\OpenSSL-Win32\bin\openssl.exe",
                r"C:\Program Files\Git\usr\bin\openssl.exe",
                r"C:\Program Files (x86)\Git\usr\bin\openssl.exe",
            ]
            
            for path in common_paths:
                if os.path.exists(path):
                    try:
                        result = subprocess.run([path, "version"],
                                              capture_output=True,
                                              text=True,
                                              timeout=5)
                        if result.returncode == 0:
                            openssl_cmd = path
                            print(f"✅ 找到OpenSSL: {path}")
                            print(f"   版本: {result.stdout.strip()}")
                            break
                    except:
                        continue
            
            if not openssl_cmd:
                print("❌ 错误: 未找到OpenSSL")
                print()
                print("请确保OpenSSL已安装:")
                print("  1. 下载并安装: https://slproweb.com/products/Win32OpenSSL.html")
                print("  2. 安装时选择将OpenSSL添加到系统PATH")
                print("  3. 或者安装Git Bash (通常自带OpenSSL)")
                print()
                print("常见安装路径:")
                for path in common_paths[:4]:
                    print(f"  - {path}")
                sys.exit(1)
        else:
            print("❌ 错误: 未找到OpenSSL")
            print()
            print("请安装OpenSSL:")
            print("  Linux: sudo apt-get install openssl")
            print("  Mac: brew install openssl")
            sys.exit(1)
    
    print()
    print("📝 生成证书配置...")
    
    # 生成证书
    print(f"🔨 正在生成私钥和证书...")
    
    # 生成私钥
    key_cmd = [
        openssl_cmd, "genrsa",
        "-out", key_file,
        "2048"
    ]
    
    try:
        result = subprocess.run(key_cmd, 
                              capture_output=True, 
                              text=True, 
                              timeout=30,
                              check=True)
        print("✅ 私钥生成成功")
    except subprocess.CalledProcessError as e:
        print(f"❌ 私钥生成失败: {e.stderr}")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("❌ 私钥生成超时")
        sys.exit(1)
    
    # 生成证书签名请求和自签名证书
    cert_cmd = [
        openssl_cmd, "req",
        "-new",
        "-x509",
        "-key", key_file,
        "-out", cert_file,
        "-days", "365",
        "-subj", f"/C=CN/ST=Beijing/L=Beijing/O=TrafficSystem/OU=Dev/CN={local_ip}"
    ]
    
    try:
        result = subprocess.run(cert_cmd,
                              capture_output=True,
                              text=True,
                              timeout=30,
                              check=True)
        print("✅ 证书生成成功")
    except subprocess.CalledProcessError as e:
        print(f"❌ 证书生成失败: {e.stderr}")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("❌ 证书生成超时")
        sys.exit(1)
    
    print()
    print("-" * 60)
    print("✅ SSL证书生成完成！")
    print()
    print(f"📁 证书文件位置:")
    print(f"   私钥: {key_file}")
    print(f"   证书: {cert_file}")
    print()
    print("⚠️  注意:")
    print("   1. 这是自签名证书，浏览器会显示'不安全'警告")
    print("   2. 这是正常的，可以点击'高级' -> '继续访问'来接受证书")
    print("   3. 证书有效期为365天，过期后需要重新生成")
    print()
    print(f"🌐 访问地址:")
    print(f"   https://localhost:5000")
    print(f"   https://{local_ip}:5000")
    print()
    
    return key_file, cert_file

if __name__ == '__main__':
    try:
        key_file, cert_file = generate_cert()
        print("✅ 完成！现在可以启动应用使用HTTPS了")
    except KeyboardInterrupt:
        print("\n\n⚠️  操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

