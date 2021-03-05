import os
import urllib.request

def download_gaiku(version = '18.0a'):
    """
    街区レベル位置参照情報をダウンロード
    """
    target_dir = os.path.abspath(os.path.join(
        os.path.dirname(__file__), 'gaiku'))
    if not os.path.exists(target_dir):
        os.mkdir(target_dir, mode=0o755)

    urlbase = 'https://nlftp.mlit.go.jp/isj/dls/data'
    for pref_code in range(1, 48):
        url = "{0}/{1}/{2:02d}000-{1}.zip".format(
            urlbase, version, pref_code)
        filepath = os.path.join(target_dir, "{:02d}000.zip".format(pref_code))
        if not os.path.exists(filepath):
            urllib.request.urlretrieve(url, filepath)
            
        # print("wget {}".format(url))
        
def download_oaza(version = '13.0b'):
    """
    大字レベル位置参照情報をダウンロード
    """
    target_dir = os.path.abspath(os.path.join(
        os.path.dirname(__file__), 'oaza'))
    if not os.path.exists(target_dir):
        os.mkdir(target_dir, mode=0o755)

    urlbase = 'https://nlftp.mlit.go.jp/isj/dls/data'
    for pref_code in range(1, 48):
        url = "{0}/{1}/{2:02d}000-{1}.zip".format(
            urlbase, version, pref_code)
        filepath = os.path.join(target_dir, "{:02d}000.zip".format(pref_code))
        if not os.path.exists(filepath):
            urllib.request.urlretrieve(url, filepath)
            
        # print("wget {}".format(url))
        
if __name__ == '__main__':
    download_gaiku('18.0a')
    download_oaza('13.0b')
