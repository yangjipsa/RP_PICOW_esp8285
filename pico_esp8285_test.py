from machine import UART
import time, struct

uart = UART(0, 115200, timeout=2000, timeout_char=100)
SSID = "YOUR SSID"
PASSWORD = "YOUR PASSWORD"

def flush_uart():
    while uart.any():
        uart.read()

def send(cmd, wait=1.0):
    flush_uart()
    uart.write(cmd + "\r\n")
    time.sleep(wait)
    data = b""
    while uart.any():
        data += uart.read()
#     if data:
#         try:
#             print(data.decode(), end="")
#         except:
#             print(data)
    return data

def ntp_request():
    """NTP 요청 및 시간 출력"""
    flush_uart()
    ntp_query = b'\x1b' + 47 * b'\0'
    uart.write(f"AT+CIPSEND={len(ntp_query)}\r\n")
    time.sleep(0.5)
    uart.write(ntp_query)
    time.sleep(1.2)

    raw = b""
    t0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t0) < 2000:
        if uart.any():
            raw += uart.read()
        time.sleep(0.05)

    if b'+IPD' in raw:
        try:
            i = raw.find(b':') + 1
            pkt = raw[i:i+48]
            if len(pkt) == 48:
                t = struct.unpack("!12I", pkt)[10] - 2208988800
                kst = time.localtime(t + 9*3600)
                print("🕐 %04d-%02d-%02d %02d:%02d:%02d" %
                      (kst[0], kst[1], kst[2], kst[3], kst[4], kst[5]))
                return True
        except Exception as e:
            print("⚠️ NTP 파싱 실패:", e)
    else:
        print("⚠️ NTP 응답 없음")
    return False


print("\n🔌 ESP8285 NTP Clock (안정형 단일모드)\n")

send("AT+RST", wait=5)
send("ATE0")
send("AT+CWMODE=1")
send(f'AT+CWJAP="{SSID}","{PASSWORD}"', wait=8)
send("AT+CIPMUX=0")  # ✅ 단일 연결 모드
send("AT+CIPCLOSE", wait=1)  # 🔧 혹시 남아있던 연결 닫기

print("\n🌐 UDP 세션 연결 중...\n")
send('AT+CIPSTART="UDP","pool.ntp.org",123', wait=3)

print("\n⏱️ 1초마다 NTP 요청 반복 (Ctrl+C로 중지)\n")

while True:
    ok = ntp_request()
    if not ok:
        print("🔁 UDP 세션 재연결...\n")
        send("AT+CIPCLOSE", wait=1)
        send('AT+CIPSTART="UDP","pool.ntp.org",123', wait=3)
    time.sleep(10)


