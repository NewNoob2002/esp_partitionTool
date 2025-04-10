import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv
import json
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

ALIGNMENT = 0x1000  # 4KB对齐
KB = 1024
COMMON_SUBTYPES = ["nvs", "ota", "ota_0", "ota_1", "littlefs", "phy", "factory"]

class EnhancedPartitionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("分区表设计工具 v2.0")
        
        self.partitions = []
        self.flash_size = 0x400000  # 默认4MB
        self.create_widgets()
        self.setup_status_bar()
        
    def create_widgets(self):
        # 工具栏
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="导入CSV", command=self.import_csv).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="导出CSV", command=self.export_csv).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="添加分区", command=self.add_partition).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="删除选中", command=self.delete_partition).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="显示图表", command=self.show_chart).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="生成代码", command=self.generate_code).pack(side=tk.LEFT)
        
        # Flash大小设置
        flash_frame = ttk.Frame(self.root)
        flash_frame.pack(fill=tk.X, padx=5)
        ttk.Label(flash_frame, text="Flash总大小:").pack(side=tk.LEFT)
        self.flash_entry = ttk.Entry(flash_frame, width=10)
        self.flash_entry.pack(side=tk.LEFT, padx=5)
        self.flash_entry.insert(0, "0x400000")
        ttk.Button(flash_frame, text="更新", command=self.update_flash_size).pack(side=tk.LEFT)
        
        # 分区表格
        self.tree = ttk.Treeview(self.root, columns=("Name", "Type", "SubType", "Offset", "Size", "KB", "Flags"), 
                                show="headings", selectmode="browse")
        
        # 设置列宽和标题
        columns = [
            ("Name", 100), ("Type", 80), ("SubType", 100),
            ("Offset", 120), ("Size", 120), ("KB", 80), ("Flags", 80)
        ]
        for col, width in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor=tk.W)
        
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.tree.bind("<Double-1>", self.on_double_click)
        
    def setup_status_bar(self):
        # 状态栏
        self.status_var = tk.StringVar()
        status_bar = ttk.Label(self.root, textvariable=self.status_var, 
                              relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.update_status()
    
    def update_status(self):
        total = self.flash_size
        used = sum(p["size"] for p in self.partitions)
        free = total - used
        status_color = "red" if used > total else "black"
        
        status_text = (f"总空间: {total/KB:.1f}KB ({hex(total)}) | "
                      f"已用: {used/KB:.1f}KB ({hex(used)}) | "
                      f"剩余: {free/KB:.1f}KB ({hex(free)})")
        
        self.status_var.set(status_text)
        self.root.after(500, self.update_status)  # 实时更新
        
    def add_partition(self):
        new_partition = {
            "name": "new_part",
            "type": "data",
            "subtype": "nvs",
            "offset": None,
            "size": 0x1000,
            "flags": ""
        }
        self.partitions.append(new_partition)
        self.refresh_table()
        
    def delete_partition(self):
        selected = self.tree.selection()
        if selected:
            index = int(selected[0][1:]) - 1
            del self.partitions[index]
            self.refresh_table()
        
    def import_csv(self):
        filepath = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if filepath:
            try:
                self.partitions = []
                with open(filepath, 'r') as f:
                    lines = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
                    # ESP32分区表CSV格式特殊处理
                    for line in lines:
                        parts = [part.strip() for part in line.split(',')]
                        if len(parts) < 5:  # 至少需要5列
                            continue
                            
                        partition = {
                            "name": parts[0],
                            "type": parts[1],
                            "subtype": parts[2],
                            "offset": int(parts[3], 16) if parts[3].strip() else None,
                            "size": int(parts[4], 16) if parts[4].strip() else 0,
                            "flags": parts[5] if len(parts) > 5 else ""
                        }
                        self.partitions.append(partition)
                self.refresh_table()
                messagebox.showinfo("导入成功", f"成功导入 {len(self.partitions)} 个分区")
            except Exception as e:
                messagebox.showerror("导入错误", f"CSV文件格式错误: {str(e)}")
        
    def export_csv(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".csv")
        if filepath:
            try:
                with open(filepath, 'w', newline='') as f:
                    # 写入ESP32分区表格式头部
                    f.write("# Name,   Type, SubType,  Offset,   Size,  Flags\n")
                    
                    for p in self.partitions:
                        offset_str = f"0x{p['offset']:x}" if p['offset'] is not None else ""
                        size_str = f"0x{p['size']:x}" if p['size'] else ""
                        
                        line = f"{p['name']}, {p['type']}, {p['subtype']}, {offset_str}, {size_str}"
                        if p['flags']:
                            line += f", {p['flags']}"
                        f.write(line + "\n")
                        
                messagebox.showinfo("导出成功", "CSV文件已保存")
            except Exception as e:
                messagebox.showerror("导出错误", f"保存失败: {str(e)}")
        
    def update_flash_size(self):
        try:
            self.flash_size = int(self.flash_entry.get(), 16)
            self.refresh_table()
        except ValueError:
            messagebox.showerror("错误", "无效的Flash大小格式")
        
    def refresh_table(self):
        self.tree.delete(*self.tree.get_children())
        self.calculate_offsets()
        
        for idx, p in enumerate(self.partitions):
            kb_size = p["size"] / KB
            values = (
                p["name"], p["type"], p["subtype"],
                f"0x{p['offset']:x}", f"0x{p['size']:x}",
                f"{kb_size:.1f} KB", p["flags"]
            )
            self.tree.insert("", "end", iid=f"i{idx+1}", values=values)
        
    def calculate_offsets(self):
        current_end = 0
        for p in self.partitions:
            if p["offset"] is not None:
                if p["offset"] < current_end:
                    messagebox.showerror("偏移冲突", f"{p['name']} 偏移重叠")
                    return
                current_end = p["offset"] + p["size"]
            else:
                next_offset = ((current_end + ALIGNMENT - 1) // ALIGNMENT) * ALIGNMENT
                p["offset"] = next_offset
                current_end = next_offset + p["size"]
                
            if p["size"] % ALIGNMENT != 0:
                suggest = ((p["size"] // ALIGNMENT) + 1) * ALIGNMENT
                if messagebox.askyesno("对齐建议",
                    f"{p['name']} 大小未对齐(0x{p['size']:x})\n调整为0x{suggest:x}?"):
                    p["size"] = suggest
                    current_end = p["offset"] + p["size"]
        
        if current_end > self.flash_size:
            over = current_end - self.flash_size
            messagebox.showerror("容量超限", 
                f"超出 {over/KB:.1f}KB (0x{over:x})\n"
                f"请调整分区大小或Flash容量")
        
    def on_double_click(self, event):
        row_id = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        
        if not row_id or col == "#0":
            return
        
        col_idx = int(col[1:]) - 1
        cell_rect = self.tree.bbox(row_id, col)
        
        # 处理Subtype列的下拉框
        if col_idx == 2:  # SubType列
            current = self.tree.set(row_id, col)
            combo = ttk.Combobox(self.tree, values=COMMON_SUBTYPES)
            combo.place(x=cell_rect[0], y=cell_rect[1], 
                       width=cell_rect[2], height=cell_rect[3])
            combo.set(current)
            
            def save_subtype(event):
                new_value = combo.get()
                combo.destroy()
                self.update_partition(row_id, col_idx, new_value)
            
            combo.bind("<<ComboboxSelected>>", save_subtype)
            combo.bind("<FocusOut>", save_subtype)
            combo.focus_set()
        else:
            # 其他列的文本编辑
            old_value = self.tree.set(row_id, col)
            entry = ttk.Entry(self.tree)
            entry.place(x=cell_rect[0], y=cell_rect[1],
                       width=cell_rect[2], height=cell_rect[3])
            entry.insert(0, old_value)
            
            def save_edit(event):
                new_value = entry.get()
                entry.destroy()
                self.update_partition(row_id, col_idx, new_value)
            
            entry.bind("<FocusOut>", save_edit)
            entry.bind("<Return>", save_edit)
            entry.focus_set()
        
    def update_partition(self, row_id, col_idx, new_value):
        index = int(row_id[1:]) - 1
        fields = ["name", "type", "subtype", "offset", "size", "flags"]
        field = fields[col_idx]
        
        try:
            if field in ["offset", "size"]:
                value = int(new_value, 16)
                if field == "offset" and value % ALIGNMENT != 0:
                    raise ValueError("偏移必须4KB对齐")
                self.partitions[index][field] = value
            else:
                self.partitions[index][field] = new_value
            
            self.refresh_table()
        except Exception as e:
            messagebox.showerror("输入错误", str(e))
            self.refresh_table()
    
 # 新增功能方法 ----------------------------------------
    def show_chart(self):
        fig = plt.Figure(figsize=(8, 4), dpi=100)
        ax = fig.add_subplot(111)
        
        total = self.flash_size
        used = sum(p['size'] for p in self.partitions)
        free = total - used
        
        labels = ['UsedSpace', 'FreeSapce']
        sizes = [used, free]
        colors = ['#ff9999','#66b3ff']
        
        ax.pie(sizes, colors=colors, labels=labels, autopct='%1.1f%%',
               startangle=90, wedgeprops=dict(width=0.3))
        ax.axis('equal')
        
        chart_window = tk.Toplevel(self.root)
        chart_window.title("存储空间分布图")
        canvas = FigureCanvasTkAgg(fig, master=chart_window)
        canvas.draw()
        canvas.get_tk_widget().pack()

    def generate_code(self):
        code = "typedef struct {\n"
        code += "    const char* name;\n    uint32_t offset;\n    uint32_t size;\n} partition_entry_t;\n\n"
        code += "static const partition_entry_t partitions[] = {\n"
        
        for p in self.partitions:
            code += f'    {{"{p["name"]}", 0x{p["offset"]:X}, 0x{p["size"]:X}}},\n'
        
        code += "    {NULL, 0, 0} // 结束标记\n};\n"
        
        code_window = tk.Toplevel(self.root)
        text = tk.Text(code_window, wrap=tk.WORD)
        text.insert(tk.END, code)
        text.pack(fill=tk.BOTH, expand=True)

if __name__ == "__main__":
    root = tk.Tk()
    app = EnhancedPartitionApp(root)
    root.geometry("1000x600")
    root.mainloop()