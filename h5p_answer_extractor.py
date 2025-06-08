#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
H5P Answer Extractor
Trích xuất và hiển thị tất cả đáp án từ file H5P content.json
"""

import json
import re
import os
from pathlib import Path
from typing import Dict, List, Any, Optional


class H5PAnswerExtractor:
    def __init__(self, file_path: str):
        """
        Khởi tạo H5P Answer Extractor

        Args:
            file_path (str): Đường dẫn đến file content.json
        """
        self.file_path = Path(file_path)
        self.content = self._load_content()

    def _load_content(self) -> Dict[str, Any]:
        """Đọc và parse file JSON"""
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                content = f.read()
                # Loại bỏ comment đầu file nếu có
                if content.startswith("//"):
                    lines = content.split("\n")
                    content = "\n".join(lines[1:])
                return json.loads(content)
        except FileNotFoundError:
            raise FileNotFoundError(f"Không tìm thấy file: {self.file_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Lỗi parse JSON: {e}")

    def _clean_html_text(self, text: str) -> str:
        """Làm sạch HTML tags và format text"""
        if not text:
            return ""
        # Loại bỏ HTML tags
        clean_text = re.sub(r"<[^>]+>", "", text)
        # Loại bỏ &nbsp; và các entity khác
        clean_text = re.sub(r"&nbsp;", " ", clean_text)
        clean_text = re.sub(r"&[a-zA-Z]+;", "", clean_text)
        # Loại bỏ khoảng trắng thừa
        clean_text = re.sub(r"\s+", " ", clean_text).strip()
        return clean_text

    def _extract_multiple_choice_answers(
        self, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Trích xuất đáp án từ Multiple Choice questions"""
        question_text = self._clean_html_text(params.get("question", ""))
        answers = params.get("answers", [])

        answer_options = []
        correct_answer = None

        for i, answer in enumerate(answers):
            answer_text = self._clean_html_text(answer.get("text", ""))
            is_correct = answer.get("correct", False)

            answer_options.append(
                {
                    "option": chr(65 + i),  # A, B, C, D...
                    "text": answer_text,
                    "is_correct": is_correct,
                }
            )

            if is_correct:
                correct_answer = chr(65 + i)

        return {
            "question": question_text,
            "answers": answer_options,
            "correct_answer": correct_answer,
        }

    def _extract_drag_drop_answers(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Trích xuất đáp án từ Drag and Drop questions"""
        question_data = params.get("question", {})
        task = question_data.get("task", {})

        # Lấy các elements có thể drag (drag items)
        elements = task.get("elements", [])
        # Lấy các drop zones
        drop_zones = task.get("dropZones", [])

        drag_items = []
        drop_areas = []
        correct_matches = {}

        # Trích xuất drag items (elements)
        for idx, element in enumerate(elements):
            element_type = element.get("type", {})
            if element_type.get("library") == "H5P.AdvancedText 1.1":
                text = self._clean_html_text(
                    element_type.get("params", {}).get("text", "")
                )
                drag_items.append(text)

        # Trích xuất drop zones và correct elements
        for idx, zone in enumerate(drop_zones):
            zone_label = self._clean_html_text(zone.get("label", ""))
            if zone_label:
                drop_areas.append(zone_label)

            # Lấy các elements đúng cho drop zone này
            correct_elements = zone.get("correctElements", [])
            for element_idx in correct_elements:
                try:
                    element_idx = int(element_idx)
                    if element_idx < len(drag_items):
                        drag_item_text = drag_items[element_idx]
                        if drag_item_text not in correct_matches:
                            correct_matches[drag_item_text] = []
                        correct_matches[drag_item_text].append(idx)
                except (ValueError, IndexError):
                    continue

        return {
            "type": "Drag and Drop",
            "drag_items": drag_items,
            "drop_areas": drop_areas,
            "correct_matches": correct_matches,
        }

    def _extract_true_false_answers(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Trích xuất đáp án từ True/False questions"""
        question_text = self._clean_html_text(params.get("question", ""))
        correct = params.get("correct", "")
        if isinstance(correct, bool):
            correct_answer = "True" if correct else "False"
        else:
            correct_answer = str(correct).capitalize()
        return {
            "question": question_text,
            "correct_answer": correct_answer,
        }

    def _extract_fill_in_blanks_answers(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Trích xuất đáp án từ Fill in the Blanks questions"""
        # Đáp án thường nằm trong trường 'questions' hoặc 'text'
        questions = params.get("questions")
        if questions:
            # Nếu là list, nối lại thành chuỗi
            if isinstance(questions, list):
                text = "\n".join(questions)
            else:
                text = str(questions)
        else:
            text = params.get("text", "")
        text = self._clean_html_text(text)
        # Tìm các đáp án nằm trong dấu *Đáp án*
        answers = re.findall(r"\*(.*?)\*", text)
        return {
            "question": text,
            "answers": answers,
        }

    def _extract_drag_text_answers(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Trích xuất đáp án từ Drag Text questions (H5P.DragText)"""
        # Lấy mô tả câu hỏi
        question_text = self._clean_html_text(params.get("taskDescription", ""))
        # Lấy đoạn văn bản chứa đáp án
        text_field = params.get("textField", "")
        # SỬA: Regex đúng để lấy cụm từ giữa dấu *
        answers = re.findall(r"\*(.*?)\*", text_field)
        answers = [self._clean_html_text(ans) for ans in answers]
        return {
            "question": question_text,
            "answers": answers,
            "text_field": text_field,
        }

    def extract_all_answers(self) -> List[Dict[str, Any]]:
        """Trích xuất tất cả đáp án từ file H5P"""
        answers = []

        # Lấy interactions từ interactive video
        interactions = (
            self.content.get("interactiveVideo", {})
            .get("assets", {})
            .get("interactions", [])
        )

        question_number = 1

        for interaction in interactions:
            action = interaction.get("action", {})
            library = action.get("library", "")
            params = action.get("params", {})

            # Lấy thời gian xuất hiện
            duration = interaction.get("duration", {})
            time_from = duration.get("from", 0)
            time_to = duration.get("to", 0)

            answer_data = {
                "question_number": question_number,
                "library_type": library,
                "time_range": f"{time_from:.2f}s - {time_to:.2f}s",
                "subcontent_id": action.get("subContentId", ""),
            }

            if "MultiChoice" in library:
                # Multiple Choice questions
                mc_data = self._extract_multiple_choice_answers(params)
                answer_data.update(mc_data)
                answer_data["type"] = "Multiple Choice"

            elif "DragQuestion" in library:
                # Drag and Drop questions
                dd_data = self._extract_drag_drop_answers(params)
                answer_data.update(dd_data)

            elif "TrueFalse" in library:
                # True/False questions
                tf_data = self._extract_true_false_answers(params)
                answer_data.update(tf_data)
                answer_data["type"] = "True/False"

            elif "Blanks" in library:
                # Fill in the Blanks questions
                blanks_data = self._extract_fill_in_blanks_answers(params)
                answer_data.update(blanks_data)
                answer_data["type"] = "Fill in the Blanks"

            elif "Image" in library:
                # Skip image interactions
                continue

            elif "DragText" in library:
                # Drag Text questions
                dragtext_data = self._extract_drag_text_answers(params)
                answer_data.update(dragtext_data)
                answer_data["type"] = "Drag Text"

            else:
                # Các loại câu hỏi khác
                answer_data["type"] = "Other"
                answer_data["raw_params"] = params

            if answer_data.get("question") or answer_data.get("type") in [
                "Drag and Drop",
                "Fill in the Blanks",
                "True/False",
                "Drag Text",
            ]:
                answers.append(answer_data)
                question_number += 1

        return answers

    def display_answers(self) -> None:
        """Hiển thị tất cả đáp án ra console"""
        answers = self.extract_all_answers()

        print("=" * 80)
        print("H5P ANSWER EXTRACTOR - TRÍCH XUẤT ĐÁP ÁN")
        print("=" * 80)
        print(f"File: {self.file_path}")
        print(f"Tổng số câu hỏi: {len(answers)}")
        print("=" * 80)

        for answer in answers:
            print(f"\nCÂU HỎI {answer['question_number']}")
            print(f"Loại: {answer['type']}")
            print(f"Thời gian: {answer['time_range']}")
            print(f"ID: {answer['subcontent_id']}")
            print("-" * 50)

            if answer["type"] == "Multiple Choice":
                print(f"Câu hỏi: {answer['question']}")
                print("\nCác lựa chọn:")
                for option in answer["answers"]:
                    status = "✓ ĐÚNG" if option["is_correct"] else "✗ SAI"
                    print(f"  {option['option']}. {option['text']} [{status}]")
                print(f"\nĐÁP ÁN ĐÚNG: {answer['correct_answer']}")

            elif answer["type"] == "Drag and Drop":
                print("Loại: Kéo thả")
                print(f"Số items để kéo: {len(answer['drag_items'])}")
                print(f"Số vùng thả: {len(answer['drop_areas'])}")

                if answer["drag_items"]:
                    print("\nCác item để kéo:")
                    for i, item in enumerate(answer["drag_items"], 1):
                        print(f"  {i}. {item}")

                if answer["drop_areas"]:
                    print("\nCác vùng thả:")
                    for i, area in enumerate(answer["drop_areas"], 1):
                        print(f"  {i}. {area}")

                if answer["correct_matches"]:
                    print("\nCác kết nối đúng:")
                    for item, zones in answer["correct_matches"].items():
                        zone_numbers = [str(int(z) + 1) for z in zones]
                        print(f"  '{item}' → Vùng {', '.join(zone_numbers)}")

            elif answer["type"] == "True/False":
                print(f"Câu hỏi: {answer['question']}")
                print(f"ĐÁP ÁN ĐÚNG: {answer['correct_answer']}")

            elif answer["type"] == "Fill in the Blanks":
                print(f"Câu hỏi: {answer['question']}")
                print(
                    f"ĐÁP ÁN: {', '.join(answer['answers']) if answer['answers'] else 'Không xác định được đáp án'}"
                )

            elif answer["type"] == "Drag Text":
                print(f"Câu hỏi: {answer['question']}")
                print(f"Đoạn văn: {answer['text_field']}")
                print(
                    f"ĐÁP ÁN: {', '.join(answer['answers']) if answer['answers'] else 'Không xác định được đáp án'}"
                )

            print("\n" + "=" * 50)

    def save_answers_to_file(
        self, output_path: str = None, original_input: str = None
    ) -> None:
        """Lưu đáp án ra file text với tên file theo tên file h5p truyền vào"""
        if output_path is None:
            # Nếu có original_input là file .h5p thì lấy tên file đó
            if original_input and original_input.lower().endswith(".h5p"):
                base_name = os.path.splitext(os.path.basename(original_input))[0]
                output_path = os.path.join(os.getcwd(), f"{base_name}_answer.txt")
            else:
                # Nếu là content.json thì lấy tên thư mục hiện tại
                output_path = os.path.join(os.getcwd(), "extracted_answers.txt")

        answers = self.extract_all_answers()

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("H5P ANSWER EXTRACTOR - TRÍCH XUẤT ĐÁP ÁN\n")
            f.write("=" * 80 + "\n")
            f.write(f"File: {self.file_path}\n")
            f.write(f"Tổng số câu hỏi: {len(answers)}\n")
            f.write("=" * 80 + "\n")

            for answer in answers:
                f.write(f"\nCÂU HỎI {answer['question_number']}\n")
                f.write(f"Loại: {answer['type']}\n")
                f.write(f"Thời gian: {answer['time_range']}\n")
                f.write(f"ID: {answer['subcontent_id']}\n")
                f.write("-" * 50 + "\n")

                if answer["type"] == "Multiple Choice":
                    f.write(f"Câu hỏi: {answer['question']}\n")
                    f.write("\nCác lựa chọn:\n")
                    for option in answer["answers"]:
                        status = "✓ ĐÚNG" if option["is_correct"] else "✗ SAI"
                        f.write(f"  {option['option']}. {option['text']} [{status}]\n")
                    f.write(f"\nĐÁP ÁN ĐÚNG: {answer['correct_answer']}\n")

                elif answer["type"] == "Drag and Drop":
                    f.write("Loại: Kéo thả\n")
                    f.write(f"Số items để kéo: {len(answer['drag_items'])}\n")
                    f.write(f"Số vùng thả: {len(answer['drop_areas'])}\n")

                    if answer["drag_items"]:
                        f.write("\nCác item để kéo:\n")
                        for i, item in enumerate(answer["drag_items"], 1):
                            f.write(f"  {i}. {item}\n")

                    if answer["drop_areas"]:
                        f.write("\nCác vùng thả:\n")
                        for i, area in enumerate(answer["drop_areas"], 1):
                            f.write(f"  {i}. {area}\n")

                    if answer["correct_matches"]:
                        f.write("\nCác kết nối đúng:\n")
                        for item, zones in answer["correct_matches"].items():
                            zone_numbers = [str(int(z) + 1) for z in zones]
                            f.write(f"  '{item}' → Vùng {', '.join(zone_numbers)}\n")

                elif answer["type"] == "True/False":
                    f.write(f"Câu hỏi: {answer['question']}\n")
                    f.write(f"ĐÁP ÁN ĐÚNG: {answer['correct_answer']}\n")

                elif answer["type"] == "Fill in the Blanks":
                    f.write(f"Câu hỏi: {answer['question']}\n")
                    f.write(
                        f"ĐÁP ÁN: {', '.join(answer['answers']) if answer['answers'] else 'Không xác định được đáp án'}\n"
                    )

                elif answer["type"] == "Drag Text":
                    f.write(f"Câu hỏi: {answer['question']}\n")
                    f.write(f"Đoạn văn: {answer['text_field']}\n")
                    f.write(
                        f"ĐÁP ÁN: {', '.join(answer['answers']) if answer['answers'] else 'Không xác định được đáp án'}\n"
                    )

                f.write("\n" + "=" * 50 + "\n")

        print(f"\nĐã lưu đáp án vào file: {output_path}")


def main():
    """Hàm main để chạy script"""
    import sys

    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        # Mặc định sử dụng file trong thư mục hiện tại
        file_path = "content.json"

    try:
        extractor = H5PAnswerExtractor(file_path)

        # Hiển thị đáp án ra console
        extractor.display_answers()

        # Lưu đáp án ra file
        extractor.save_answers_to_file(file_path)

    except Exception as e:
        print(f"Lỗi: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
