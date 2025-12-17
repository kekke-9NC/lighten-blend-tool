"""
比較明合成ツール - メインGUIアプリケーション (Modern UI)

CustomTkinterを使用したモダンなGUIで、
ドラッグ＆ドロップで動画や静止画を追加し、
比較明合成画像・動画を作成するアプリケーション。
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD
from pathlib import Path
from datetime import datetime

import lighten_blend_image
import lighten_blend_video
import ffmpeg_manager

# テーマ設定
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")  # "blue", "green", "dark-blue"


class DnDApp(ctk.CTk, TkinterDnD.DnDWrapper):
    """CustomTkinterとTkinterDnDを組み合わせた基底クラス"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.TkdndVersion = TkinterDnD._require(self)


class App(DnDApp):
    def __init__(self):
        super().__init__()
        
        self.title("比較明合成ツール")
        self.geometry("900x700")
        
        self.file_paths = []
        self.setup_ui()
        self.update_button_state()
        
        # 起動時に依存関係チェック
        self.after(500, self.check_dependencies)
    
    def setup_ui(self):
        """UIコンポーネントの設定"""
        # メイングッドレイアウト (左右または上下)
        # 上部: ファイルリストと操作
        # 下部: ログ
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)  # Main content
        self.grid_rowconfigure(1, weight=0)  # Log area
        
        # --- メインコンテンツフレーム ---
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1) # File list grows
        
        # ヘッダー / ドロップエリア
        self.drop_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent", border_width=2, border_color=("gray70", "gray30"))
        self.drop_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        self.drop_label = ctk.CTkLabel(
            self.drop_frame,
            text="ここにファイルをドラッグ＆ドロップ\n(動画: mp4, mov... / 画像: png, jpg...)",
            font=("Meiryo UI", 16),
            text_color=("gray10", "gray90")
        )
        self.drop_label.pack(pady=30, padx=20, fill="x")
        
        # DnD登録 (FrameとLabel両方にバインドして反応範囲を広げる)
        self.drop_frame.drop_target_register(DND_FILES)
        self.drop_frame.dnd_bind('<<Drop>>', self.on_drop)
        self.drop_label.drop_target_register(DND_FILES)
        self.drop_label.dnd_bind('<<Drop>>', self.on_drop)
        
        # --- ファイルリストエリア ---
        list_header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        list_header_frame.grid(row=1, column=0, padx=10, pady=(0,5), sticky="new")
        
        self.list_label = ctk.CTkLabel(list_header_frame, text="ファイル一覧", font=("Meiryo UI", 14, "bold"))
        self.list_label.pack(side="left")
        
        self.file_count_label = ctk.CTkLabel(list_header_frame, text="0 件", font=("Meiryo UI", 12))
        self.file_count_label.pack(side="left", padx=10)
        
        # スクロール可能なファイルリスト
        self.scrollable_list = ctk.CTkScrollableFrame(self.main_frame, label_text="追加されたファイル")
        self.scrollable_list.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="nsew")
        # グリッド内のアイテム管理用
        self.list_item_frames = {} 
        
        # --- ボタンエリア ---
        self.btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.btn_frame.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="ew")
        
        self.btn_add = ctk.CTkButton(self.btn_frame, text="ファイルを追加...", command=self.add_files_dialog, width=120)
        self.btn_add.pack(side="left", padx=(0, 10))
        
        self.btn_clear = ctk.CTkButton(self.btn_frame, text="すべて削除", command=self.remove_all, fg_color="transparent", border_width=1, width=100)
        self.btn_clear.pack(side="left")
        
        # 右寄せのアクションボタン
        self.btn_create_video = ctk.CTkButton(self.btn_frame, text="比較明合成動画を作成", command=self.create_video, font=("Meiryo UI", 13, "bold"), height=36)
        self.btn_create_video.pack(side="right", padx=(10, 0))
        
        self.btn_create_image = ctk.CTkButton(self.btn_frame, text="比較明合成画像を作成", command=self.create_image, font=("Meiryo UI", 13, "bold"), height=36)
        self.btn_create_image.pack(side="right")

        # プログレスバー
        self.progress = ctk.CTkProgressBar(self.main_frame, mode='indeterminate')
        self.progress.grid(row=4, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.progress.set(0)
        
        # --- ログエリア ---
        self.log_frame = ctk.CTkFrame(self, height=150)
        self.log_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.log_frame.grid_propagate(False) # 固定高さ
        
        self.log_label = ctk.CTkLabel(self.log_frame, text="ログ", font=("Meiryo UI", 12, "bold"))
        self.log_label.pack(anchor="w", padx=10, pady=(5,0))
        
        self.log_text = ctk.CTkTextbox(self.log_frame, font=("Consolas", 12), activate_scrollbars=True)
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.log_text.configure(state="disabled")

    def _refresh_file_list(self):
        """ファイルリストのUIを再描画"""
        # 既存のアイテムを削除
        for widget in self.scrollable_list.winfo_children():
            widget.destroy()
        self.list_item_frames.clear()
        
        for i, path in enumerate(self.file_paths):
            item_frame = ctk.CTkFrame(self.scrollable_list, fg_color=("gray85", "gray25"))
            item_frame.pack(fill="x", pady=2)
            
            # ファイル名
            name_lbl = ctk.CTkLabel(item_frame, text=os.path.basename(path), anchor="w")
            name_lbl.pack(side="left", padx=10, pady=5, fill="x", expand=True)
            
            # 削除ボタン (×)
            del_btn = ctk.CTkButton(
                item_frame, text="✕", width=30, height=24, 
                fg_color="transparent", hover_color=("red", "darkred"), text_color=("gray10", "gray90"),
                command=lambda idx=i: self.remove_at(idx)
            )
            del_btn.pack(side="right", padx=5)
    
    def on_drop(self, event):
        """ドラッグ＆ドロップ処理"""
        paths = self.splitlist(event.data)
        image_ext, video_ext = lighten_blend_image.get_supported_extensions()
        all_ext = image_ext + video_ext
        
        added_count = 0
        for path in paths:
            path = path.strip('{}')
            
            if os.path.isfile(path):
                if Path(path).suffix.lower() in all_ext:
                    if path not in self.file_paths:
                        self.file_paths.append(path)
                        added_count += 1
                        
            elif os.path.isdir(path):
                # フォルダの場合は中のファイルを収集
                files = lighten_blend_image.collect_files_from_folder(path)
                for f in files:
                    if f not in self.file_paths:
                        self.file_paths.append(f)
                        added_count += 1
        
        if added_count > 0:
            self.append_log(f"{added_count} 個のファイルを追加しました")
            self._refresh_file_list()
        else:
            messagebox.showinfo("情報", "有効なファイルがドロップされませんでした")
        
        self.update_button_state()
    
    def add_files_dialog(self):
        """ファイル選択ダイアログ"""
        file_paths = filedialog.askopenfilenames(
            title="ファイルを選択",
            filetypes=[
                ("画像・動画ファイル", "*.jpg *.jpeg *.png *.bmp *.tiff *.tif *.mp4 *.avi *.mov *.mkv *.wmv *.webm *.flv *.m4v *.3gp"),
                ("画像ファイル", "*.jpg *.jpeg *.png *.bmp *.tiff *.tif"),
                ("動画ファイル", "*.mp4 *.avi *.mov *.mkv *.wmv *.webm *.flv *.m4v *.3gp"),
                ("すべてのファイル", "*.*")
            ]
        )
        
        added_count = 0
        for path in file_paths:
            if path not in self.file_paths:
                self.file_paths.append(path)
                added_count += 1
        
        if added_count > 0:
            self.append_log(f"{added_count} 個のファイルを追加しました")
            self._refresh_file_list()
        
        self.update_button_state()
    
    def remove_at(self, index):
        """指定したインデックスのファイルを削除"""
        if 0 <= index < len(self.file_paths):
            del self.file_paths[index]
            self._refresh_file_list()
            self.update_button_state()

    def remove_all(self):
        """すべて削除"""
        if not self.file_paths:
            return
        
        if messagebox.askyesno("確認", "リストからすべてのファイルを削除しますか？"):
            self.file_paths.clear()
            self._refresh_file_list()
            self.update_button_state()
    
    def update_button_state(self):
        """ボタンの状態を更新（ファイルタイプに応じて）"""
        count = len(self.file_paths)
        self.file_count_label.configure(text=f"{count} 件")
        
        # 動画ファイルと画像ファイルをカウント
        _, video_ext = lighten_blend_image.get_supported_extensions()
        video_count = sum(1 for f in self.file_paths if Path(f).suffix.lower() in video_ext)
        
        # 画像ボタン: 2つ以上のファイル（動画・画像問わず）があれば有効
        image_state = "normal" if count >= 2 else "disabled"
        self.btn_create_image.configure(state=image_state)
        
        # 動画ボタン: 2つ以上の動画ファイルがあれば有効
        video_state = "normal" if video_count >= 2 else "disabled"
        self.btn_create_video.configure(state=video_state)
    
    def append_log(self, message: str):
        """ログにメッセージを追加"""
        self.log_text.configure(state='normal')
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state='disabled')
    
    def create_image(self):
        """比較明合成画像を作成"""
        if len(self.file_paths) < 2:
            messagebox.showwarning("警告", "2つ以上のファイルを追加してください")
            return
        
        # デフォルトの保存パスを取得
        default_output = lighten_blend_image.get_default_output_path()
        
        output_path = filedialog.asksaveasfilename(
            title="比較明合成画像の保存先",
            initialdir=os.path.dirname(default_output),
            initialfile=os.path.basename(default_output),
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("JPEG Image", "*.jpg"), ("All Files", "*")]
        )
        
        if not output_path:
            return
        
        self.append_log(f"比較明合成画像の作成を開始します... ({len(self.file_paths)}個のファイル)")
        self.progress.start()
        self.btn_create_image.configure(state="disabled")
        self.btn_create_video.configure(state="disabled")
        
        def run_task():
            success = lighten_blend_image.create_lighten_blend_image(
                list(self.file_paths),
                output_path,
                progress_callback=lambda msg: self.after(0, lambda: self.append_log(msg))
            )
            
            def on_complete():
                self.progress.stop()
                self.update_button_state()
                if success:
                    messagebox.showinfo("完了", f"比較明合成画像の作成が完了しました。\n保存先: {output_path}")
                    self.append_log(f"比較明合成画像の作成が完了しました: {output_path}")
                else:
                    messagebox.showerror("エラー", "比較明合成画像の作成に失敗しました。ログを確認してください。")
                    self.append_log("比較明合成画像の作成に失敗しました。")
            
            self.after(0, on_complete)
        
        threading.Thread(target=run_task, daemon=True).start()
    
    def create_video(self):
        """比較明合成動画を作成"""
        # 動画ファイルのみをフィルタ
        _, video_ext = lighten_blend_image.get_supported_extensions()
        video_files = [f for f in self.file_paths if Path(f).suffix.lower() in video_ext]
        
        if len(video_files) < 2:
            messagebox.showwarning("警告", "2つ以上の動画ファイルを追加してください")
            return
        
        # デフォルトの保存パスを取得
        default_output = lighten_blend_video.get_default_output_path()
        
        output_path = filedialog.asksaveasfilename(
            title="比較明合成動画の保存先",
            initialdir=os.path.dirname(default_output),
            initialfile=os.path.basename(default_output),
            defaultextension=".mp4",
            filetypes=[("MP4 Video", "*.mp4"), ("AVI Video", "*.avi"), ("All Files", "*")]
        )
        
        if not output_path:
            return
        
        self.append_log(f"比較明合成動画の作成を開始します... ({len(video_files)}個の動画)")
        self.progress.start()
        self.btn_create_image.configure(state="disabled")
        self.btn_create_video.configure(state="disabled")
        
        def run_task():
            success = lighten_blend_video.create_lighten_blend_video(
                video_files,
                output_path,
                progress_callback=lambda msg: self.after(0, lambda: self.append_log(msg))
            )
            
            def on_complete():
                self.progress.stop()
                self.update_button_state()
                if success:
                    messagebox.showinfo("完了", f"比較明合成動画の作成が完了しました。\n保存先: {output_path}")
                    self.append_log(f"比較明合成動画の作成が完了しました: {output_path}")
                else:
                    messagebox.showerror("エラー", "比較明合成動画の作成に失敗しました。ログを確認してください。")
                    self.append_log("比較明合成動画の作成に失敗しました。")
            
            self.after(0, on_complete)
        
        threading.Thread(target=run_task, daemon=True).start()

    def check_dependencies(self):
        """依存関係（FFmpeg）のチェックとセットアップ"""
        if not ffmpeg_manager.is_installed():
            # インストール確認ダイアログ
            if messagebox.askyesno("セットアップ", "動画機能を使用するにはFFmpegが必要です。\n自動的にダウンロードしてセットアップしますか？\n(サイズ: 約100MB)"):
                self.show_setup_dialog()
            else:
                self.append_log("警告: FFmpegがセットアップされていないため、動画作成機能は制限されます。")
                
    def show_setup_dialog(self):
        """セットアップ進捗ダイアログを表示"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("セットアップ中")
        dialog.geometry("400x150")
        dialog.transient(self)  # メインウィンドウの手前に表示
        dialog.grab_set()       # モーダル化
        
        label = ctk.CTkLabel(dialog, text="FFmpegをダウンロードしてセットアップしています...\nしばらくお待ちください。", font=("Meiryo UI", 12))
        label.pack(pady=20)
        
        progress = ctk.CTkProgressBar(dialog, mode='indeterminate')
        progress.pack(fill="x", padx=30, pady=10)
        progress.start()
        
        status_label = ctk.CTkLabel(dialog, text="準備中...", font=("Meiryo UI", 10))
        status_label.pack(pady=5)
        
        def run_setup():
            def update_msg(msg):
                self.after(0, lambda: status_label.configure(text=msg))
                self.after(0, lambda: self.append_log(msg))
            
            success = ffmpeg_manager.download_and_setup(progress_callback=update_msg)
            
            def on_complete():
                progress.stop()
                dialog.destroy()
                if success:
                    messagebox.showinfo("完了", "セットアップが完了しました！\n動画作成機能が利用可能です。")
                else:
                    messagebox.showerror("エラー", "セットアップに失敗しました。\nネットワーク接続を確認してください。")
            
            self.after(0, on_complete)
        
        threading.Thread(target=run_setup, daemon=True).start()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
