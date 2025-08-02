#!/usr/bin/env python3
"""
Chạy tất cả các test của dự án SED
"""

import os
import sys
import unittest
import importlib
import argparse

def main():
    """Hàm chính để chạy các test"""
    parser = argparse.ArgumentParser(description='Run SED Tests')
    parser.add_argument('--test', '-t', help='Tên của test cụ thể để chạy (không bao gồm .py)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Hiển thị thông tin chi tiết')
    
    args = parser.parse_args()
    
    # Đường dẫn đến thư mục tests
    test_dir = os.path.join('utils', 'tests')
    
    # Thêm thư mục gốc vào sys.path
    if '.' not in sys.path:
        sys.path.insert(0, '.')
    
    # Chạy một test cụ thể nếu được chỉ định
    if args.test:
        test_module = f'utils.tests.{args.test}'
        try:
            module = importlib.import_module(test_module)
            if hasattr(module, 'main'):
                module.main()
            else:
                print(f"Module {test_module} không có hàm main().")
        except ImportError as e:
            print(f"Không thể import module {test_module}: {e}")
        return
    
    # Nếu không có test cụ thể, chạy tất cả các test
    test_loader = unittest.TestLoader()
    
    try:
        # Tìm tất cả các test trong thư mục tests
        test_suite = test_loader.discover(test_dir)
        
        # Chạy các test
        runner = unittest.TextTestRunner(verbosity=2 if args.verbose else 1)
        result = runner.run(test_suite)
        
        # Thoát với mã trạng thái phù hợp
        sys.exit(not result.wasSuccessful())
        
    except Exception as e:
        print(f"Lỗi khi chạy test: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
