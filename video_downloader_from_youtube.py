import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import yt_dlp
import threading
import browser_cookie3
import os
from pathlib import Path
import tempfile
from yt_dlp import YoutubeDL
import platform
import subprocess
import json


def save_cookies_to_file(cj):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.txt')
    with open(tmp.name, 'w') as f:
        for cookie in cj:
            f.write(f"{cookie.domain}\t{'TRUE' if cookie.domain.startswith('.') else 'FALSE'}\t{cookie.path}\t"
                    f"{'TRUE' if cookie.secure else 'FALSE'}\t{int(cookie.expires) if cookie.expires else 0}\t"
                    f"{cookie.name}\t{cookie.value}\n")
    return tmp.name

def playlist_logic(pl_url):
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True
    }

    with YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(pl_url, download=False)
        entries = info_dict.get('entries', [])

        urls = []
        for entry in entries:
            if 'url' in entry:
                video_id = entry['url']
                full_url = f"{video_id}"
                urls.append(full_url)

        return urls

def update_label():
    app.download_queue_label.config(
        text=f"Download Queue ({app.queue_listbox.size()}):"
    )
    root.after(100, update_label)

class YouTubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader")
        self.root.geometry("800x600")
        self.root.resizable(False, False)
        self.queue = []
        self.history_file = os.path.join(str(Path.home()), "youtube_download_history.json")
        self.history = self.load_history()

        style = ttk.Style()
        style.configure("TButton", font=("Segoe UI", 16))

        ttk.Label(root, text="Video or Playlist URL:", font=("Segoe UI", 18)).pack(pady=(20, 5))
        self.url_entry = ttk.Entry(root, width=100, font=("Segoe UI", 20))
        self.url_entry.pack(pady=5, padx=10)

        self.download_queue_label = ttk.Label(root, text="Download Queue", font=("Segoe UI", 16))
        self.download_queue_label.pack(pady=5)

        queue_frame = ttk.Frame(root)
        queue_frame.pack(pady=5)
        ttk.Button(queue_frame, text="➕ Add", command=self.add_to_queue).pack(side=tk.LEFT, padx=5)
        ttk.Button(queue_frame, text="❌ Remove", command=self.remove_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(queue_frame, text="⬆️ Up", command=self.move_up).pack(side=tk.LEFT, padx=5)
        ttk.Button(queue_frame, text="⬇️ Down", command=self.move_down).pack(side=tk.LEFT, padx=5)
        ttk.Button(queue_frame, text="📜 Show History", command=self.show_history).pack(side=tk.LEFT, padx=5)

        self.queue_listbox = tk.Listbox(root, width=100, height=6, font=("Segoe UI", 16), borderwidth=0)
        self.queue_listbox.pack(pady=5, padx=10)

        self.quality_var = tk.StringVar(value='🎥 Best Quality')
        self.quality_menu = tk.OptionMenu(root, self.quality_var, '🎥 Best Quality', '📉 Lowest Quality', '🎧 Audio Only')
        self.quality_menu.config(
            font=("Segoe UI", 16),
            width=28,
            bg="SystemButtonFace",
            fg="black",
            activebackground="#e0e0e0",
            activeforeground="black",
            highlightthickness=0,
            bd=0
        )
        self.quality_menu['menu'].config(font=("Segoe UI", 14))

        self.quality_menu.pack(pady=3)

        self.select_folder_btn = ttk.Button(root, text="Select Save Folder", command=self.choose_directory , width=30)
        self.select_folder_btn.pack(pady=3)


        style = ttk.Style()
        style.configure("Custom.TCheckbutton", font=("Segoe UI", 16)) 

        self.sort_var = tk.BooleanVar(value=False)
        self.sort_checkbox = ttk.Checkbutton(
            root,
            text="Folders Autosorting",
            variable=self.sort_var,
            width=28,
            style="Custom.TCheckbutton"
        )
        self.sort_checkbox.pack(pady=3)

        self.output_path = ttk.Label(root, text="Default folder: Downloads", foreground="grey", font=("Segoe UI", 15))
        self.output_path.pack()

        self.download_btn = ttk.Button(root, text="⬇️ Start Download", command=self.start_download_thread, width=30)
        self.download_btn.pack(pady=3)

        self.progress = ttk.Progressbar(root, orient='horizontal', length=500, mode='determinate')
        self.progress.pack(pady=5)

        self.status = ttk.Label(root, text="Don't forget to open YouTube in Firefox", font=("Segoe UI", 8, "italic"))
        self.status.pack(pady=5)

        self.download_dir = str(Path.home() / "Downloads")

    def choose_directory(self):
        path = filedialog.askdirectory()
        if path:
            self.download_dir = path
            self.output_path.config(text=path, foreground="black")
        else:
            self.output_path.config(text=f"Default folder: Downloads", foreground="grey")

    def add_to_queue(self, video_url=None):
        if video_url:
            url = video_url
            threading.Thread(target=self.fetch_title_and_add, args=(url,)).start()
            return

        url_input = self.url_entry.get().strip()
        if "playlist?list=" in url_input:
            urls = playlist_logic(url_input)
            for url in urls:
                threading.Thread(target=self.fetch_title_and_add, args=(url,)).start()
        else:
            if url_input:
                threading.Thread(target=self.fetch_title_and_add, args=(url_input,)).start()

    def fetch_title_and_add(self, url):
        self.queue.append(url)
        self.queue_listbox.insert(tk.END, url)
        self.url_entry.delete(0, tk.END)

    def remove_selected(self):
        selected_indices = self.queue_listbox.curselection()
        for index in reversed(selected_indices):
            self.queue_listbox.delete(index)
            del self.queue[index]

    def move_up(self):
        selected = self.queue_listbox.curselection()
        if not selected or selected[0] == 0:
            return
        index = selected[0]
        self.queue[index - 1], self.queue[index] = self.queue[index], self.queue[index - 1]
        self.refresh_listbox()
        self.queue_listbox.select_set(index - 1)

    def move_down(self):
        selected = self.queue_listbox.curselection()
        if not selected or selected[0] == len(self.queue) - 1:
            return
        index = selected[0]
        self.queue[index + 1], self.queue[index] = self.queue[index], self.queue[index + 1]
        self.refresh_listbox()
        self.queue_listbox.select_set(index + 1)

    def refresh_listbox(self):
        self.queue_listbox.delete(0, tk.END)
        for url in self.queue:
            self.queue_listbox.insert(tk.END, url)

    def start_download_thread(self):
        threading.Thread(target=self.download_videos).start()

    def download_videos(self):
        if not self.queue:
            messagebox.showerror("Error", "The download queue is empty!")
            return

        cookies = browser_cookie3.firefox(domain_name='youtube.com')
        quality_label = self.quality_var.get()
        quality_map = {
            '🎥 Best Quality': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
            '📉 Lowest Quality': 'worst',
            '🎧 Audio Only': 'bestaudio',
        }
        quality = quality_map.get(quality_label, 'best')

        while self.queue:
            url = self.queue.pop(0)
            self.queue_listbox.delete(0)
            self.status.config(text=f"Downloading: {url}")
            self.progress['value'] = 0

            ydl_opts = {
                'format': quality,
                'merge_output_format': 'mp4',
                'outtmpl': os.path.join(self.download_dir,'%(uploader)s' if self.sort_var.get() else '','%(title)s.%(ext)s'),
                'ffmpeg_location': '.',
                'cookies': cookies,
                'noplaylist': False,
                'quiet': False,
                'progress_hooks': [self.hook],
                'outtmpl_na_placeholder': 'unknown'
            }

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    title = info.get('title', url)
                    self.save_to_history(title=title, url=url)
            except Exception as e:
                self.status.config(text=f"Error: {str(e)}")

        self.status.config(text="All downloads completed.")
        self.play_notification_sound()

    def hook(self, d):
        def update():
            if d['status'] == 'downloading':
                filename = d.get('filename', 'Video')
                downloaded_bytes = d.get('downloaded_bytes', 0)
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')

                if total_bytes:
                    progress_percent = downloaded_bytes / total_bytes * 100
                    size_mb = total_bytes / (1024 * 1024)
                    downloaded_mb = downloaded_bytes / (1024 * 1024)
                    self.progress['value'] = progress_percent
                    self.status.config(
                        text=f"{downloaded_mb:.1f}MB / {size_mb:.1f}MB"
                    )
                else:
                    self.progress['value'] = 0
                    self.status.config(text=f"{filename}: calculating size...")

            elif d['status'] == 'finished':
                self.progress['value'] = 100
                self.status.config(text="Download finished. Merging...")
                self.root.after(1000, lambda: self.progress.config(value=0))

        self.root.after(0, update)

    def play_notification_sound(self):
        system = platform.system()
        try:
            if system == 'Windows':
                import winsound
                winsound.MessageBeep()
            elif system == 'Darwin':
                subprocess.run(['afplay', '/System/Library/Sounds/Glass.aiff'])
            else:
                subprocess.run(['paplay', '/usr/share/sounds/freedesktop/stereo/complete.oga'])
        except Exception as e:
            print(f"Sound notification failed: {e}")

    def load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def clear_history(self, listbox=None):
        self.history = []
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f)
        except Exception as e:
            print(f"Failed to clear history: {e}")
        if listbox:
            listbox.delete(0, tk.END)


    def save_to_history(self, title, url):
        self.history.append({'title': title, 'url': url})
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save history: {e}")

    def show_history(self):
        history_win = tk.Toplevel(self.root)
        history_win.title("Download History")
        history_win.geometry("700x550")

        listbox = tk.Listbox(history_win, font=("Segoe UI", 14), width=100, height=18)
        listbox.pack(padx=10, pady=(10, 0), fill=tk.BOTH, expand=True)

        clear_btn = ttk.Button(history_win, text="🗑 Clear History", command=lambda: self.clear_history(listbox))
        clear_btn.pack(pady=(5, 10))

        for item in self.history:
            title = item.get('title', 'Unknown Title')
            listbox.insert(tk.END, f"{title}")

if __name__ == '__main__':
    if platform.system() == "Windows":
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    root = tk.Tk()
    root.call('tk', 'scaling', 1.2)
    app = YouTubeDownloader(root)
    update_label()
    root.mainloop()
