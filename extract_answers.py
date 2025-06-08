#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple H5P Answer Extractor - Version đơn giản
Sử dụng: python extract_answers.py [đường_dẫn_file]
"""

from h5p_answer_extractor import H5PAnswerExtractor
import sys
import zipfile
import tempfile
import shutil
import os


def extract_answers(file_path):
    """
    Trích xuất và hiển thị đáp án từ file H5P hoặc content.json

    Args:
        file_path (str): Đường dẫn đến file content.json hoặc .h5p/.zip
    """
    temp_dir = None
    try:
        original_input = file_path
        # Nếu là file .h5p hoặc .zip thì giải nén và tìm content.json
        if file_path.lower().endswith((".h5p", ".zip")):
            print("🗜️ Đang giải nén file H5P...")
            temp_dir = tempfile.mkdtemp()
            with zipfile.ZipFile(file_path, "r") as zip_ref:
                zip_ref.extractall(temp_dir)  # Tìm file content.json trong thư mục tạm
            content_json_path = None
            for root, dirs, files in os.walk(temp_dir):
                if "content.json" in files:
                    content_json_path = os.path.join(root, "content.json")
                    break
            if not content_json_path:
                raise FileNotFoundError("Không tìm thấy content.json trong file H5P.")
            file_path = content_json_path

        print("🔍 Đang phân tích file H5P...")
        extractor = H5PAnswerExtractor(file_path)

        print("📋 Hiển thị đáp án:")
        extractor.display_answers()

        print("\n💾 Lưu đáp án ra file...")
        extractor.save_answers_to_file(original_input=original_input)

        print("✅ Hoàn thành!")

    except FileNotFoundError:
        print(f"❌ Lỗi: Không tìm thấy file '{file_path}'")
        print("💡 Đảm bảo đường dẫn file đúng và file tồn tại.")

    except Exception as e:
        print(f"❌ Lỗi: {e}")
    finally:
        # Xóa thư mục tạm nếu có (phòng trường hợp lỗi xảy ra trước khi xóa)
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    print("=" * 60)
    print("🎯 H5P ANSWER EXTRACTOR - TRÍCH XUẤT ĐÁP ÁN H5P")
    print("=" * 60)

    # Lấy đường dẫn file từ command line hoặc nhập từ người dùng
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        print(f"📁 File đầu vào: {file_path}")
    else:
        print("📁 Nhập đường dẫn đến file H5P (.h5p) hoặc content.json:")
        print("💡 Bạn có thể kéo thả file vào đây hoặc gõ đường dẫn")
        print("💡 Để dùng file mặc định 'content.json', chỉ cần nhấn Enter")
        print("-" * 60)

        user_input = input("🔍 Đường dẫn file: ").strip()

        # Loại bỏ dấu ngoặc kép nếu có (từ việc kéo thả file)
        if user_input.startswith('"') and user_input.endswith('"'):
            user_input = user_input[1:-1]
        elif user_input.startswith("'") and user_input.endswith("'"):
            user_input = user_input[1:-1]

        # Sử dụng file mặc định nếu không nhập gì
        file_path = user_input if user_input else "content.json"
        print(f"📁 Sử dụng file: {file_path}")

    print("=" * 60)
    extract_answers(file_path)
    input("Nhấn Enter để thoát...")
