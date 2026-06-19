import os
import zipfile
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import re

class ZipContentCleaner:
    def __init__(self, root):
        self.root = root
        self.root.title("압축파일 내부 특정 이미지 일괄 제거")
        self.root.geometry("950x750")
        
        # 상태 변수
        self.target_dir = tk.StringVar()
        
        # 압축파일 내부 이미지 삭제 범위
        self.start_num = tk.StringVar(value="0")
        self.end_num = tk.StringVar(value="0")
        
        # 숫자 인식 방식 선택 (전체 숫자 vs 특정 단어 기준)
        self.match_mode = tk.StringVar(value="all_numbers") # 'all_numbers' 또는 'custom_word'
        
        # 특정 단어 설정 및 위치 변수
        self.custom_word = tk.StringVar(value="image")
        self.word_position = tk.StringVar(value="after") # 'before' (단어 앞) 또는 'after' (단어 뒤)
        
        # ComicInfo 무조건 삭제 옵션
        self.delete_xml = tk.BooleanVar(value=True)
        
        # 백업 활성화 옵션
        self.use_backup = tk.BooleanVar(value=True)
        
        # 감지된 항목 저장
        self.detected_items = {}
        self.tree_items = {}
        
        self.setup_ui()
        
    def setup_ui(self):
        # 1. 상단: 폴더 선택 및 복구 버튼
        top_frame = tk.LabelFrame(self.root, text="1. 대상 폴더 지정 및 백업 복구")
        top_frame.pack(fill="x", padx=10, pady=5, side="top")
        
        tk.Label(top_frame, text="대상 폴더:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        tk.Entry(top_frame, textvariable=self.target_dir, width=60).grid(row=0, column=1, padx=5, pady=5)
        tk.Button(top_frame, text="찾아보기", command=self.browse_folder).grid(row=0, column=2, padx=5, pady=5)
        
        # 복구 버튼
        tk.Button(top_frame, text="⏪ 원본 파일 복구하기 (Backup 폴더 기준)", bg="#FF9800", fg="white", font=("맑은 고딕", 9, "bold"), command=self.restore_backup).grid(row=0, column=3, padx=5, pady=5)
        
        # 2. 중간 상단: 탐색 및 삭제 조건 세부 설정
        cond_frame = tk.LabelFrame(self.root, text="2. 압축파일 내부 이미지 삭제 범위 및 인식 방식 설정")
        cond_frame.pack(fill="x", padx=10, pady=5)
        
        # 번호 범위 설정 칸
        range_frame = tk.Frame(cond_frame)
        range_frame.pack(fill="x", anchor="w", padx=5, pady=5)
        
        tk.Label(range_frame, text="삭제할 이미지 번호 범위: ").pack(side="left")
        tk.Entry(range_frame, textvariable=self.start_num, width=6).pack(side="left", padx=2)
        tk.Label(range_frame, text=" 번 부터 ").pack(side="left")
        tk.Entry(range_frame, textvariable=self.end_num, width=6).pack(side="left", padx=2)
        # 에러 해결: fg="green" 옵션을 Label 내부로 정상 이동시켰습니다.
        tk.Label(range_frame, text=" 번 까지 삭제  (※ 01, 001, 0001 등 자릿수 상관없이 매칭)", fg="green").pack(side="left")
        
        # 라디오 버튼 1 - 파일명 전체에서 숫자 찾기
        mode1_frame = tk.Frame(cond_frame)
        mode1_frame.pack(fill="x", anchor="w", padx=5, pady=5)
        tk.Radiobutton(mode1_frame, text="파일명 전체에서 최초 발견되는 숫자 기준 (예: 0001.jpg, page_02.png)", 
                       variable=self.match_mode, value="all_numbers").pack(side="left")
                       
        # 라디오 버튼 2 - 특정 단어 기준 설정 구역
        mode2_frame = tk.Frame(cond_frame)
        mode2_frame.pack(fill="x", anchor="w", padx=5, pady=5)
        tk.Radiobutton(mode2_frame, text="특정 단어 주변의 숫자 기준 ➡️ ", variable=self.match_mode, value="custom_word").pack(side="left")
        
        tk.Label(mode2_frame, text="단어 입력:").pack(side="left", padx=2)
        tk.Entry(mode2_frame, textvariable=self.custom_word, width=12).pack(side="left", padx=2)
        
        # 위치 선택 (앞 vs 뒤)
        tk.Label(mode2_frame, text=" 기준 ").pack(side="left", padx=5)
        tk.Radiobutton(mode2_frame, text="단어 앞의 숫자 (예: 001ad.jpg)", variable=self.word_position, value="before").pack(side="left", padx=2)
        tk.Radiobutton(mode2_frame, text="단어 뒤의 숫자 (예: image_001.png)", variable=self.word_position, value="after").pack(side="left", padx=2)
                       
        # 백업 여부 및 XML 옵션
        option_frame = tk.Frame(cond_frame)
        option_frame.pack(fill="x", pady=10, padx=5)
        tk.Checkbutton(option_frame, text="삭제 전 원본 압축파일 자동 백업 생성 (안전 옵션)", variable=self.use_backup).pack(side="left", padx=(0, 20))
        tk.Checkbutton(option_frame, text="ComicInfo.xml 무조건 함께 삭제", variable=self.delete_xml).pack(side="left")
        
        tk.Button(option_frame, text="🔍 조건에 맞는 파일 분석 시작", bg="#4CAF50", fg="white", font=("맑은 고딕", 10, "bold"), command=self.analyze_zip_files).pack(side="right", padx=5)

        # 3. 중간 하단: 미리보기 리스트
        list_frame = tk.LabelFrame(self.root, text="3. 분석 결과 미리보기 (더블클릭/스페이스바로 수동 선택 및 해제 가능)")
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        btn_select_frame = tk.Frame(list_frame)
        btn_select_frame.pack(fill="x", anchor="w", pady=5, padx=5)
        tk.Button(btn_select_frame, text="전체 선택", command=lambda: self.toggle_all_selection(True)).pack(side="left", padx=2)
        tk.Button(btn_select_frame, text="전체 해제", command=lambda: self.toggle_all_selection(False)).pack(side="left", padx=2)
        
        columns = ("file_name", "type", "internal_path", "status")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        self.tree.heading("file_name", text="압축 파일명")
        self.tree.heading("type", text="분류")
        self.tree.heading("internal_path", text="내부 파일 경로")
        self.tree.heading("status", text="삭제 여부")
        
        self.tree.column("file_name", width=180)
        self.tree.column("type", width=180)
        self.tree.column("internal_path", width=330)
        self.tree.column("status", width=100, anchor="center")
        
        self.tree.pack(fill="both", expand=True, side="left", padx=(5, 0), pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(fill="y", side="right", padx=(0, 5), pady=5)
        
        self.tree.bind("<Double-1>", self.on_item_click)
        self.tree.bind("<space>", self.on_item_click)
        
        # 4. 하단: 실행 버튼 및 프로그래스 바
        bottom_frame = tk.Frame(self.root)
        bottom_frame.pack(fill="x", padx=10, pady=10, side="bottom")
        
        self.progress = ttk.Progressbar(bottom_frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", side="top", pady=(0, 5))
        
        tk.Button(bottom_frame, text="🗑️ 선택한 광고/XML 일괄 삭제 실행", bg="#D32F2F", fg="white", font=("맑은 고딕", 11, "bold"), height=2, command=self.execute_cleaning).pack(fill="x")

    def browse_folder(self):
        selected = filedialog.askdirectory()
        if selected:
            self.target_dir.set(selected)
            
    def toggle_all_selection(self, select_all):
        status_text = "[X] 삭제함" if select_all else "[ ] 제외함"
        for item in self.tree.get_children():
            self.tree.set(item, "status", status_text)

    def on_item_click(self, event):
        selected_item = self.tree.focus()
        if not selected_item:
            return
        current_status = self.tree.set(selected_item, "status")
        new_status = "[ ] 제외함" if current_status == "[X] 삭제함" else "[X] 삭제함"
        self.tree.set(selected_item, "status", new_status)

    def get_internal_file_number(self, filename):
        base = os.path.basename(filename).lower()
        mode = self.match_mode.get()
        
        if mode == "all_numbers":
            num_part = re.findall(r'\d+', base)
            if num_part:
                return int(num_part[0])
        else:
            word = self.custom_word.get().strip().lower()
            if not word or word not in base:
                return None
                
            position = self.word_position.get()
            if position == "after":
                idx = base.find(word) + len(word)
                after_text = base[idx:]
                num_part = re.findall(r'\d+', after_text)
                if num_part:
                    return int(num_part[0])
            else:
                idx = base.find(word)
                before_text = base[:idx]
                num_part = re.findall(r'\d+', before_text)
                if num_part:
                    return int(num_part[-1])
                    
        return None

    def analyze_zip_files(self):
        directory = self.target_dir.get()
        if not directory or not os.path.exists(directory):
            messagebox.showerror("에러", "올바른 대상 폴더 경로를 지정해 주세요.")
            return
        
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.detected_items = {}
        self.tree_items = {}
        
        try:
            s_num = int(self.start_num.get().strip())
            e_num = int(self.end_num.get().strip())
        except ValueError:
            messagebox.showerror("에러", "번호 범위에는 숫자만 입력 가능합니다.")
            return
            
        check_xml = self.delete_xml.get()
        
        zip_files = [f for f in os.listdir(directory) if f.lower().endswith(('.zip', '.cbz'))]
        if not zip_files:
            messagebox.showinfo("안내", "해당 폴더에 압축파일(.zip, .cbz)이 없습니다.")
            return
            
        for z_file in zip_files:
            z_path = os.path.join(directory, z_file)
            try:
                with zipfile.ZipFile(z_path, 'r') as z:
                    file_list = z.namelist()
                    
                    detected_images = []
                    has_xml = False
                    
                    for internal_file in file_list:
                        if check_xml and internal_file.lower().endswith('comicinfo.xml'):
                            has_xml = True
                            
                        if internal_file.endswith('/'):
                            continue
                            
                        file_num = self.get_internal_file_number(internal_file)
                        if file_num is not None:
                            if s_num <= file_num <= e_num:
                                detected_images.append(internal_file)
                                
                    if detected_images or has_xml:
                        self.detected_items[z_path] = {"images": detected_images, "xml": has_xml}
                        
                        for img_path in detected_images:
                            node = self.tree.insert("", "end", values=(z_file, "조건 일치 이미지(삭제대상)", img_path, "[X] 삭제함"))
                            self.tree_items[node] = {"zip": z_path, "type": "image", "internal": img_path}
                        if has_xml:
                            xml_internal_path = [f for f in file_list if f.lower().endswith('comicinfo.xml')][0]
                            node = self.tree.insert("", "end", values=(z_file, "ComicInfo.xml", xml_internal_path, "[X] 삭제함"))
                            self.tree_items[node] = {"zip": z_path, "type": "xml", "internal": xml_internal_path}
            except Exception as e:
                print(f"{z_file} 분석 실패: {e}")
                
        if not self.detected_items:
            messagebox.showinfo("완료", "지정한 조건에 일치하는 대상이 발견되지 않았습니다.")
        else:
            messagebox.showinfo("분석 완료", f"총 {len(self.detected_items)}개의 압축파일에서 대상을 찾았습니다.")

    def execute_cleaning(self):
        items_to_remove = {}
        for node in self.tree.get_children():
            status = self.tree.set(node, "status")
            if status == "[X] 삭제함":
                info = self.tree_items[node]
                z_path = info["zip"]
                if z_path not in items_to_remove:
                    items_to_remove[z_path] = {"images": set(), "remove_xml": False}
                if info["type"] == "image":
                    items_to_remove[z_path]["images"].add(info["internal"])
                elif info["type"] == "xml":
                    items_to_remove[z_path]["remove_xml"] = True
                    
        if not items_to_remove:
            messagebox.showwarning("경고", "삭제하도록 선택된 항목이 없습니다.")
            return
            
        if not messagebox.askyesno("최종 확인", f"선택한 항목들을 압축파일에서 정말 삭제하시겠습니까?\n(총 {len(items_to_remove)}개의 압축파일 수정 예정)"):
            return
            
        if self.use_backup.get():
            directory = self.target_dir.get()
            backup_dir = os.path.join(directory, "Backup_Before_Clean")
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
                
            for z_path in items_to_remove.keys():
                shutil.copy2(z_path, backup_dir)
                
        self.progress["maximum"] = len(items_to_remove)
        self.progress["value"] = 0
        success_count = 0
        
        for idx, (z_path, delete_info) in enumerate(items_to_remove.items()):
            temp_z_path = z_path + ".tmp"
            try:
                with zipfile.ZipFile(z_path, 'r') as zin:
                    with zipfile.ZipFile(temp_z_path, 'w', zipfile.ZIP_DEFLATED) as zout:
                        for item in zin.infolist():
                            is_target_image = item.filename in delete_info["images"]
                            is_target_xml = delete_info["remove_xml"] and item.filename.lower().endswith('comicinfo.xml')
                            
                            if not (is_target_image or is_target_xml):
                                zout.writestr(item, zin.read(item.filename))
                                
                os.remove(z_path)
                os.rename(temp_z_path, z_path)
                success_count += 1
            except Exception as e:
                print(f"파일 수정 실패 ({z_path}): {e}")
                if os.path.exists(temp_z_path):
                    os.remove(temp_z_path)
                    
            self.progress["value"] = idx + 1
            self.root.update_idletasks()
            
        msg = f"성공적으로 {success_count}개의 압축파일 수정을 완료했습니다!"
        if self.use_backup.get():
            msg += "\n(수정 전 원본은 'Backup_Before_Clean' 폴더에 안전하게 보관되었습니다.)"
        messagebox.showinfo("작업 완료", msg)
        self.analyze_zip_files()

    def restore_backup(self):
        directory = self.target_dir.get()
        if not directory or not os.path.exists(directory):
            messagebox.showerror("에러", "올바른 대상 폴더 경로를 지정해 주세요.")
            return
            
        backup_dir = os.path.join(directory, "Backup_Before_Clean")
        if not os.path.exists(backup_dir) or not os.listdir(backup_dir):
            messagebox.showinfo("안내", "복구할 수 있는 백업 파일 폴더가 존재하지 않거나 비어 있습니다.")
            return
            
        if not messagebox.askyesno("복구 확인", "백업 폴더 안의 파일들을 원래 위치로 덮어씌워 복구하시겠습니까?\n(현재 수정한 내용이 초기화됩니다)"):
            return
            
        restored_count = 0
        for f in os.listdir(backup_dir):
            if f.lower().endswith(('.zip', '.cbz')):
                shutil.copy2(os.path.join(backup_dir, f), directory)
                restored_count += 1
                
        messagebox.showinfo("복구 완료", f"총 {restored_count}개의 원본 파일이 완벽하게 복구되었습니다!")
        self.analyze_zip_files()

if __name__ == "__main__":
    root = tk.Tk()
    app = ZipContentCleaner(root)
    root.mainloop()