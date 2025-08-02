"""
Tiện ích cung cấp hỗ trợ cho các test
"""
import os
import sys

def setup_test_path():
    """
    Thêm thư mục gốc của dự án vào sys.path để các import hoạt động đúng từ các test
    """
    # Lấy đường dẫn hiện tại của file này
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Lấy thư mục gốc của dự án (lên 2 cấp từ thư mục hiện tại)
    project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
    
    # Thêm thư mục gốc vào sys.path nếu chưa có
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        print(f"Added project root to sys.path: {project_root}")
