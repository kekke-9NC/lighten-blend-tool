import os
import sys
import shutil
import subprocess
import requests
import zipfile
import threading
from pathlib import Path

# Windows用のFFmpegダウンロードURL (Gyan.dev mirror)
# 安定性のために特定のバージョンまたはrelease-essentialsを使用
FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
INSTALL_DIR_NAME = "ffmpeg_bin"

def get_base_path():
    """アプリケーションの実行ベースパスを取得（PyInstaller対応）"""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def get_install_dir():
    """FFmpegのインストール（配置）先ディレクトリ"""
    # ユーザーのAppData等に保存するのが行儀が良いが、
    # 簡易化のためにexeと同じ場所、または指定場所にする
    # ここでは exe のあるフォルダ/ffmpeg_bin にする
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base, INSTALL_DIR_NAME)

def get_ffmpeg_path():
    """
    FFmpegの実行ファイルパスを取得する。
    1. インストールディレクトリ内
    2. システムパス
    の順で探す。
    """
    # 1. ローカルインストール（配置）場所をチェック
    install_dir = get_install_dir()
    
    # 展開後の構造は ffmpeg-release-essentials/bin/ffmpeg.exe かもしれないので再帰的に探すか、固定パスを狙う
    # 通常は zip直下 -> フォルダ -> bin -> ffmpeg.exe
    
    if os.path.exists(install_dir):
        for root, dirs, files in os.walk(install_dir):
            if "ffmpeg.exe" in files:
                return os.path.join(root, "ffmpeg.exe")
    
    # 2. システムパスをチェック
    return shutil.which("ffmpeg")

def is_installed():
    """FFmpegが利用可能かチェック"""
    path = get_ffmpeg_path()
    if path and os.path.exists(path):
        # 実行テスト
        try:
            subprocess.run([path, "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return True
        except:
            return False
    return False

def download_and_setup(progress_callback=None):
    """
    FFmpegをダウンロードしてセットアップする
    """
    if is_installed():
        if progress_callback: progress_callback("FFmpegは既にインストールされています。")
        return True

    install_dir = get_install_dir()
    os.makedirs(install_dir, exist_ok=True)
    
    zip_path = os.path.join(install_dir, "ffmpeg.zip")
    
    try:
        if progress_callback: progress_callback("FFmpegをダウンロード中...")
        
        # ダウンロード
        response = requests.get(FFMPEG_URL, stream=True)
        response.raise_for_status()
        
        total_length = response.headers.get('content-length')
        dl = 0
        total_length = int(total_length) if total_length else 0
        
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    dl += len(chunk)
                    f.write(chunk)
                    if progress_callback and total_length > 0:
                        percent = int(dl / total_length * 100)
                        # 頻繁すぎる更新を避ける（適当に間引くか、UI側で制御）
                        # ここでは簡易的にメッセージ更新
                        # progress_callback(f"ダウンロード中: {percent}%") 
                        # 注: UI更新が重くなるのでパーセントは別途渡す設計が良いが、今回はメッセージのみ
        
        if progress_callback: progress_callback("FFmpegを展開中...")
        
        # 解凍
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(install_dir)
            
        # zip削除
        os.remove(zip_path)
        
        if is_installed():
            if progress_callback: progress_callback("セットアップ完了！")
            return True
        else:
            if progress_callback: progress_callback("エラー: 展開後のファイルが見つかりません。")
            return False
            
    except Exception as e:
        if progress_callback: progress_callback(f"エラーが発生しました: {str(e)}")
        # 失敗したら掃除
        if os.path.exists(zip_path):
            os.remove(zip_path)
        return False

