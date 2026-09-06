# 한국 증시 종목별 실적 및 컨센서스 추이 대시보드

FnGuide(`https://wcomp.fnguide.com/`)의 실시간 재무 데이터와 컨센서스 시계열 API를 연동하여 종목별 핵심 재무 지표, 현금흐름, 컨센서스 시계열 및 적정주가를 분석/시각화하는 Streamlit 기반 대시보드입니다.

---

## 📊 주요 기능 및 12대 차트

1. **EPS & YoY 증가율**: 연결 연간 EPS 막대 그래프 + YoY 증가율(%) 꺾은선 (이중 Y축)
2. **Earnings(Q)**: 분기 실적 (매출액, 영업이익, 당기순이익 그룹 막대)
3. **Earnings(Y)**: 연간 실적 (매출액, 영업이익, 당기순이익 그룹 막대)
4. **OPM(Q)**: 분기 영업이익률(%) 막대 그래프
5. **OPM(Y)**: 연간 영업이익률(%) 막대 그래프
6. **PER**: 연간 주가수익비율(배) 8개년(추정치 3개년 포함) 꺾은선 그래프
7. **PBR**: 연간 주가순자산비율(배) 8개년(추정치 3개년 포함) 꺾은선 그래프
8. **ROE**: 연간 자기자본이익률(%) 8개년(추정치 3개년 포함) 막대 그래프
9. **Free Cash Flow**: FnGuide 고유 양식을 복제한 3대 현금흐름(영업활동, 투자활동, 재무활동) 그룹 막대 그래프 (연간/분기 전환 지원)
10. **컨센서스 시계열 추이(Q)**: 분기 기준 컨센서스(최고, 최저, 평균) 꺾은선 그래프 (매출액, 영업이익, 당기순이익, EPS, PER, PER(Fwd,12M) 지표 선택 지원)
11. **컨센서스 시계열 추이(Y)**: 연간 기준 컨센서스(최고, 최저, 평균) 꺾은선 그래프 (지표 선택 지원)
12. **적정주가 추이**: 증권사별 목표주가 리포트 시계열 + Consensus 평균 목표주가 수평 기준선

---

## 🛠️ 기술 스택

- **Frontend / UI**: [Streamlit](https://streamlit.io/)
- **Charts**: [Plotly](https://plotly.com/)
- **Data Collection**: `requests`, `BeautifulSoup4` (FnGuide Company Guide 웹 스크래핑 및 내부 REST API 연동)
- **Stock Ticker Source**: `pykrx`, `FinanceDataReader`

---

## 🚀 실행 방법

### 1. 필수 패키지 설치
```bash
pip install -r requirements.txt
```

### 2. 대시보드 실행
```bash
streamlit run app.py
```

브라우저에서 `http://localhost:8501`로 접속하여 이용하실 수 있습니다.
