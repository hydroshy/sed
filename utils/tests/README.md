# Tests for SED Project

Thư mục này chứa tất cả các test cho dự án SED.

## Cấu trúc

- `test_utils.py`: Tiện ích hỗ trợ chạy test từ thư mục utils/tests
- `test_*.py`: Các file test cụ thể cho từng chức năng

## Cách chạy test

Có hai cách để chạy test:

### 1. Sử dụng file run_tests.py ở thư mục gốc

```bash
python run_tests.py                # Chạy tất cả các test
python run_tests.py -t test_yuv420 # Chạy test cụ thể
python run_tests.py -v             # Chạy với chế độ verbose
```

### 2. Chạy trực tiếp các file test cụ thể

```bash
python utils/tests/test_yuv420.py
```

## Viết test mới

Khi viết test mới, hãy import test_utils để thiết lập đường dẫn:

```python
from utils.tests.test_utils import setup_test_path
setup_test_path()
```
