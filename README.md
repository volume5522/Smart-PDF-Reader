# PDF EBOOK Reader

Python, PySide6, PyMuPDF로 만든 Windows 데스크톱 PDF EBOOK 리더입니다.
PDF 원본은 수정하지 않고, PDF를 이미지로 렌더링한 뒤 그 위에 필기 레이어를 그립니다.
필기 데이터는 PDF 옆에 `book.pdf.notes.json` 형식으로 저장됩니다.

## 실행 방법

```powershell
cd C:\Users\Kim\Desktop\Project\pdf_ebook_reader
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## 주요 기능

- PDF 파일 열기
- 이전 페이지 / 다음 페이지 이동
- 현재 페이지와 전체 페이지 수 표시
- 확대 / 축소
- PDF 위에 마우스 왼쪽 버튼 드래그로 빨간색 필기
- 저장 버튼으로 페이지별 필기, 마지막 페이지, 확대 비율 저장
- 같은 PDF를 다시 열면 필기와 마지막으로 읽은 페이지 복원

## 저장 파일 예시

`book.pdf`를 열고 저장하면 같은 폴더에 아래 파일이 만들어집니다.

```text
book.pdf.notes.json
```

JSON에는 원본 PDF 경로, 마지막 페이지, 확대 비율, 페이지별 필기 좌표가 저장됩니다.
