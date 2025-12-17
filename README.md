# Lighten Blend Tool

![Downloads](https://img.shields.io/github/downloads/kekke-9NC/lighten-blend-tool/total?color=blue&style=flat-square)

比較明合成画像・動画を作成するデスクトップアプリケーションです。
複数の画像や動画ファイルから、明るい部分を合成して出力します。星空の軌跡（スタートレイル）や光跡写真の作成に適しています。

## 概要

- 複数の画像・動画に対する比較明合成処理
- ドラッグ&ドロップによるファイル追加
- CustomTkinterを使用したGUI
- FFmpegを使用した動画処理（初回実行時に自動セットアップ）

## インストールと実行

### 実行ファイルを使用する場合 (Windows)

Releasesページから `LightenBlendTool.exe` をダウンロードして実行してください。
Python環境の構築は不要です。

### ソースコードから実行する場合

Python 3.8以上が必要です。

1. リポジトリをクローンします。
    ```bash
    git clone https://github.com/kekke-9NC/lighten-blend-tool.git
    cd lighten-blend-tool
    ```

2. 依存ライブラリをインストールします。
    ```bash
    pip install -r requirements.txt
    ```

3. アプリケーションを実行します。
    ```bash
    python main.py
    ```

## 使い方

1. アプリケーションを起動します。
2. 画像または動画ファイルをウィンドウにドラッグ&ドロップして追加します。フォルダをドロップするとフォルダ内の対応ファイルが全て追加されます。
3. 実行したい処理に合わせてボタンをクリックします。
    - **比較明合成画像を作成**: 追加された全ファイルから1枚の合成画像を作成します。
    - **比較明合成動画を作成**: 追加された動画ファイルから合成動画を作成します。
4. 保存時のファイル名と場所を指定すると処理が開始されます。

## システム要件

- Windows 10/11
- FFmpeg (動画作成機能を使用する場合。アプリケーションが自動的にダウンロード・設定します)

## ライセンス

本ソフトウェアは [MIT License](LICENSE) の下で公開されています。
