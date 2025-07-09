from PyQt5.QtWidgets import QMessageBox, QFileDialog
import time
import json
from detection.edge_detection import detect_edges

def add_job(self):
    from PyQt5.QtGui import QStandardItem
    job_name = f"Job {self.job_model.rowCount()+1}"
    job_item = QStandardItem(job_name)
    job_item.setEditable(False)
    roi_item = QStandardItem("")
    self.job_model.appendRow([job_item, roi_item])
    self.jobs.append({"name": job_name, "tools": []})

def edit_job(self):
    # Có thể mở rộng để sửa tên job/tool hoặc ROI
    pass

def remove_job(self):
    selected_indexes = self.ui.jobView.selectedIndexes()
    if not selected_indexes:
        return
    index = selected_indexes[0]
    if not index.parent().isValid():
        self.job_model.removeRow(index.row())
        del self.jobs[index.row()]
    else:
        parent = index.parent()
        self.job_model.item(parent.row(), 0).removeRow(index.row())
        del self.jobs[parent.row()]["tools"][index.row()]

def run_job(self):
    from PyQt5.QtGui import QStandardItem
    selected_indexes = self.ui.jobView.selectedIndexes()
    if not selected_indexes:
        QMessageBox.warning(self, "Chọn Job", "Hãy chọn một job để chạy.")
        return
    job_index = selected_indexes[0]
    if job_index.parent().isValid():
        job_index = job_index.parent()
    job_row = job_index.row()
    job = self.jobs[job_row]
    tools = job["tools"]
    if not tools:
        QMessageBox.warning(self, "Không có tool", "Job này chưa có tool nào.")
        return

    total_time = 0.0
    tool_times = []
    for idx, tool in enumerate(tools):
        start = time.time()
        if tool["name"] == "Phát hiện biên":
            frame = self.region_selector.current_frame
            if frame is not None:
                _ = detect_edges(frame)
        # Có thể mở rộng thêm các tool khác ở đây
        elapsed = time.time() - start
        tool_times.append(elapsed)
        total_time += elapsed

        tool_item = self.job_model.item(job_row, 0).child(idx, 0)
        if tool_item:
            arrow = "→" if idx < len(tools) - 1 else ""
            tool_item.setText(f"{tool['name']} {arrow}")

    self.ui.executionTime.display(f"{total_time:.3f}")

def save_job_file(self):
    path, _ = QFileDialog.getSaveFileName(self, "Save Job File", "", "SED Job Files (*.sedjob)")
    if not path:
        return
    if not path.endswith(".sedjob"):
        path += ".sedjob"
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.jobs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        QMessageBox.critical(self, "Lỗi", f"Không thể lưu file: {e}")

def load_job_file(self):
    path, _ = QFileDialog.getOpenFileName(self, "Load Job File", "", "SED Job Files (*.sedjob)")
    if not path:
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            jobs = json.load(f)
        self.jobs = jobs
        reload_job_tree(self)
    except Exception as e:
        QMessageBox.critical(self, "Lỗi", f"Không thể tải file: {e}")

def reload_job_tree(self):
    self.job_model.removeRows(0, self.job_model.rowCount())
    from PyQt5.QtGui import QStandardItem
    for job in self.jobs:
        job_item = QStandardItem(job["name"])
        job_item.setEditable(False)
        roi_item = QStandardItem("")
        self.job_model.appendRow([job_item, roi_item])
        for tool in job.get("tools", []):
            tool_item = QStandardItem(tool["name"])
            tool_item.setEditable(False)
            roi_item = QStandardItem(str(tool.get("roi", "")))
            job_item.appendRow([tool_item, roi_item])
