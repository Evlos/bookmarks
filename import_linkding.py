import json
import re
import requests
from bs4 import BeautifulSoup

# 配置项
BOOKMARK_FILE = 'bookmarks.html'  # 替换为你的书签文件实际路径
API_URL = 'http://192.168.233.107:30808/api/bookmarks'
HEADERS = {'Content-Type': 'application/json'}

def clean_url(raw_url):
    """
    清理可能出现的 Markdown 格式包裹，例如: [http://...](http://...)
    如果是正常的 URL 则直接返回。
    """
    match = re.search(r'\]\((.*?)\)', raw_url)
    if match:
        return match.group(1)
    return raw_url.strip()

def import_bookmarks():
    print(f"正在读取文件: {BOOKMARK_FILE} ...")
    with open(BOOKMARK_FILE, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    # Netscape 书签标准中，每一项由 <DT> 包含 <A> 组成
    # 描述（如果有）通常紧跟在 <DT> 后面，作为 <DD> 标签存在
    dts = soup.find_all('dt')
    print(f"共找到 {len(dts)} 个书签，开始导入...\n")

    success_count = 0
    fail_count = 0

    for dt in dts:
        a_tag = dt.find('a')
        if not a_tag:
            continue

        raw_url = a_tag.get('href', '')
        url = clean_url(raw_url)
        title = a_tag.get_text(strip=True)

        # 查找紧跟在 dt 后面的兄弟节点，看是否是 dd（忽略空白字符）
        next_tag = dt.find_next_sibling(['dd', 'dt'])
        if next_tag and next_tag.name == 'dd':
            description = next_tag.get_text(strip=True)
            # 将描述拼接到标题后面
            if description:
                title = f"{title} | {description}"

        # 构造发往新系统的 payload
        payload = {
            "url": url,
            "title": title,
            "icon": "",
            "tags": []
        }
        print(f"{title}: {url}")

        try:
            # verify=False 对应 curl 中的 --insecure 参数
            response = requests.post(API_URL, headers=HEADERS, json=payload, verify=False, timeout=10)

            if response.status_code in [200, 201]:
                print(f"✅ [成功] {title}")
                success_count += 1
            else:
                print(f"❌ [失败] HTTP {response.status_code} - {title}\n    返回内容: {response.text}")
                fail_count += 1

        except requests.exceptions.RequestException as e:
            print(f"⚠️ [异常] 请求失败 - {title}\n    错误信息: {e}")
            fail_count += 1

    print(f"\n导入完成！成功: {success_count} 条，失败: {fail_count} 条。")

if __name__ == "__main__":
    # 如果有 HTTPS 警告可以取消下方注释来屏蔽
    # requests.packages.urllib3.disable_warnings()
    import_bookmarks()
