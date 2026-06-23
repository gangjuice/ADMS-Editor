# ADMS-EDITOR

배전 설비계통도 PNG 편집 툴

## 기능

- PNG 계통도 불러오기 + OpenCV 개폐기 자동인식
- 단자 클릭 → 투개방 상태 토글 (빨강=투입 / 초록=개방)
- 선로 클릭 → 개폐기 N대 삽입
- 편집 결과를 PNG + JSON 사이드카로 저장
- JSON 사이드카가 있으면 재불러오기 시 편집 상태 복원

## 실행

```bash
pip install -r requirements.txt
python main.py
```

## 조작법

| 동작 | 설명 |
|---|---|
| 좌클릭 (단자) | 투개방 토글 |
| 좌클릭 (선로) | 개폐기 삽입 수 입력 후 삽입 |
| 휠 | 확대/축소 |
| 중클릭 드래그 | 화면 이동 |
| Ctrl+O | PNG 열기 |
| Ctrl+S | 저장 |
| Ctrl+Shift+S | 다른 이름으로 저장 |

## 심볼 자동인식 설정

`assets/symbols/` 폴더에 개폐기 심볼 PNG 템플릿을 넣으면
자동인식 정확도가 높아집니다.
파일명이 심볼 라벨이 됩니다 (예: `switch_normal.png`).

## 빌드 (Windows exe)

```bash
pyinstaller --onefile --windowed --name ADMS-EDITOR main.py
```
