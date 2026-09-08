"""
한국 증시 종목별 주요 재무 지표 및 컨센서스 대시보드
Data Source: https://wcomp.fnguide.com/
"""

import os
import streamlit as st
import pandas as pd
import fnguide_api
import charts
import importlib
importlib.reload(charts)
importlib.reload(fnguide_api)

# Page Configuration
FAVICON_PATH = os.path.join(os.path.dirname(__file__), "favicon.png")

st.set_page_config(
    page_title="한국 증시 종목별 실적 및 컨센서스 추이",
    page_icon=FAVICON_PATH if os.path.exists(FAVICON_PATH) else None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    html, body, [class*="css"] {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif;
    }
    .block-container {
        padding-top: 4.5rem !important;
        padding-bottom: 3rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 1. 종목 리스트 로드 (33 NetBuyerChart 방식 + 로컬 CSV & 다중 폴백)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=86400)
def load_stock_tickers():
    """상장 종목 전체 리스트 가져오기 (로컬 CSV -> pykrx StockTicker -> FDR -> 내장 대표주)"""
    csv_path = os.path.join(os.path.dirname(__file__), "krx_tickers.csv")

    # 1. 로컬 krx_tickers.csv 최우선 로드 (해외 IP 차단/네트워크 지연 원천 차단)
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path, dtype={'티커': str}, index_col='티커')
            if not df.empty and '종목' in df.columns:
                return df
        except Exception:
            pass

    # 2. pykrx StockTicker 시도
    try:
        from pykrx.website.krx.market.ticker import StockTicker
        st_ticker = StockTicker()
        df = st_ticker.listed
        if not df.empty and '종목' in df.columns:
            try:
                df.to_csv(csv_path, encoding='utf-8-sig')
            except Exception:
                pass
            return df
    except Exception:
        pass

    # 3. Fallback to FinanceDataReader
    try:
        import FinanceDataReader as fdr
        df = fdr.StockListing('KRX')
        df = df.set_index('Code')
        df['종목'] = df['Name']
        return df
    except Exception:
        pass

    # 4. 내장 대표 30개 우량주 fallback (최악의 오프라인/네트워크 차단 환경 대비)
    fallback_data = {
        '005930': '삼성전자', '000660': 'SK하이닉스', '373220': 'LG에너지솔루션',
        '207940': '삼성바이오로직스', '005380': '현대차', '000270': '기아',
        '068270': '셀트리온', '105560': 'KB금융', '055550': '신한지주',
        '035420': 'NAVER', '005490': 'POSCO홀딩스', '012330': '현대모비스',
        '035720': '카카오', '028260': '삼성물산', '051910': 'LG화학',
        '086520': '에코프로비엠', '247540': '에코프로', '006400': '삼성SDI',
        '032830': '삼성생명', '015760': '한국전력', '329180': 'HD현대중공업',
        '010130': '고려아연', '033780': 'KT&G', '003550': 'LG',
        '018260': '삼성에스디에스', '017670': 'SK텔레콤', '030200': 'KT',
        '034730': 'SK', '323410': '카카오뱅크', '259960': '크래프톤'
    }
    return pd.DataFrame(list(fallback_data.items()), columns=['티커', '종목']).set_index('티커')


CNS_METRIC_OPTIONS = {
    "0": "매출액",
    "1": "영업이익",
    "2": "당기순이익",
    "3": "EPS",
    "4": "PER",
    "5": "PER(Fwd,12M)"
}


# Cached Data Fetching
@st.cache_data(ttl=300)
def load_company_info(code: str):
    return fnguide_api.get_company_basic_info(code)

@st.cache_data(ttl=300)
def load_financial_highlights(code: str):
    return fnguide_api.get_financial_highlight_data(code)

@st.cache_data(ttl=300)
def load_consensus_ts(code: str, freq: str, data_typ: str = '0', period: str = None):
    return fnguide_api.get_consensus_timeseries_data(code, freq_typ=freq, data_typ=data_typ, select_gsym=period)

@st.cache_data(ttl=300)
def load_target_prices(code: str):
    return fnguide_api.get_target_prices_data(code)

@st.cache_data(ttl=300)
def load_free_cash_flow(code: str, freq: str = 'Y'):
    return fnguide_api.get_free_cash_flow_data(code, freq_typ=freq)


# State initialization
if "selected_code" not in st.session_state:
    st.session_state.selected_code = "005930"  # Default: 삼성전자


# Layout: Left Panel (Input Form & Query Button) | Right Panel (Header & 10 Charts)
col_left, col_right = st.columns([1, 3.2], gap="large")

# ==============================================================================
# LEFT PANEL: 종목 선택 입력 폼 & 조회 버튼 (33 NetBuyerChart 방식 적용)
# ==============================================================================
with col_left:
    st.subheader("🔍 종목 선택")

    tickers_df = load_stock_tickers()
    curr_code = st.session_state.get("selected_code", "005930")

    with st.form(key="stock_selection_form"):
        selected_ticker = None

        if not tickers_df.empty and '종목' in tickers_df.columns:
            # 33 NetBuyerChart 방식: 종목명 (티커) 포맷팅 및 sorted() 가나다순 정렬
            tickers_df['display_name'] = tickers_df['종목'].astype(str) + " (" + tickers_df.index.astype(str) + ")"
            display_names = sorted(tickers_df['display_name'].tolist())

            # 현재 선택된 종목 코드에 해당하는 인덱스 탐색 (기본: 삼성전자 005930)
            default_idx = 0
            for idx, name in enumerate(display_names):
                if f"({curr_code})" in name:
                    default_idx = idx
                    break

            selected_display = st.selectbox(
                "종목 검색 및 선택",
                options=display_names,
                index=default_idx,
                help="키보드로 종목명(예: 삼성전자, 카카오) 또는 종목코드(예: 005930)를 입력하여 검색할 수 있습니다."
            )
            if selected_display:
                selected_ticker = selected_display.split("(")[-1].replace(")", "").strip()
        else:
            st.warning("⚠️ 종목 목록을 불러오지 못했습니다. 아래에 종목코드를 직접 입력해 주세요.")

        # 종목코드 또는 종목명 직접 입력란
        manual_input = st.text_input(
            "또는 종목명 / 종목코드 직접 입력",
            value="",
            placeholder=f"예: 005930 또는 삼성전자",
            help="종목코드 6자리(예: 005930) 또는 종목명(예: 현대차, 카카오)을 직접 입력하여 빠르게 조회할 수 있습니다."
        ).strip()

        submitted = st.form_submit_button("📊 조회하기", use_container_width=True, type="primary")

        if submitted:
            new_code = None
            if manual_input:
                # 1) 6자리 코드 직접 입력인 경우 (예: 005930)
                if len(manual_input) == 6 and manual_input.isalnum():
                    new_code = manual_input
                # 2) 종목명을 입력한 경우 (예: 카카오, 현대차)
                elif not tickers_df.empty and '종목' in tickers_df.columns:
                    matched = tickers_df[tickers_df['종목'].str.strip() == manual_input]
                    if not matched.empty:
                        new_code = str(matched.index[0]).strip()
                    else:
                        # 부분 일치 검색
                        partial = tickers_df[tickers_df['종목'].str.contains(manual_input, regex=False)]
                        if not partial.empty:
                            new_code = str(partial.index[0]).strip()
                        else:
                            st.warning(f"입력하신 '{manual_input}'에 해당하는 종목을 찾을 수 없습니다.")
            elif selected_ticker:
                new_code = selected_ticker

            if new_code and new_code != st.session_state.selected_code:
                st.session_state.selected_code = new_code
                st.rerun()

    active_code = st.session_state.selected_code

    # Company Info Meta Card
    info = load_company_info(active_code)
    with st.container(border=True):
        st.caption(f"선택 종목 코드: `{active_code}`")
        st.markdown(f"### {info.get('cmp_nm', active_code)}")
        badges = [f"`{active_code}`", f"`{info.get('mkt_nm', 'KOSPI')}`"]
        if info.get('sector_nm'):
            badges.append(f"`{info.get('sector_nm')}`")
        st.markdown(" · ".join(badges))
        st.divider()
        st.caption("데이터 출처: [FnGuide Company Guide](https://wcomp.fnguide.com/)")

    with st.container(border=True):
        st.markdown("**💡 대시보드 안내**")
        st.markdown("""
        <p style="font-size: 13px; margin-bottom: 12px; color: inherit;">FnGuide에서 수집한 재무 및 컨센서스 지표를 12개의 차트로 표시합니다.</p>
        <div style="font-size: 13px; line-height: 1.65;">
        1. <b>EPS & YoY 증가율</b> (연결 연간)<br>
        2. <b>Earnings(Q)</b> (분기 실적)<br>
        3. <b>Earnings(Y)</b> (연간 실적)<br>
        4. <b>OPM(Q)</b> (분기 영업이익률)<br>
        5. <b>OPM(Y)</b> (연간 영업이익률)<br>
        6. <b>PER</b> (연간 주가수익비율)<br>
        7. <b>PBR</b> (연간 주가순자산비율)<br>
        8. <b>ROE</b> (연간 자기자본이익률)<br>
        9. <b>Free Cash Flow</b> (현금흐름)<br>
        10. <b>컨센서스 시계열 추이(Q)</b><br>
        11. <b>컨센서스 시계열 추이(Y)</b><br>
        12. <b>적정주가 추이</b> (증권사별)
        </div>
        """, unsafe_allow_html=True)


# ==============================================================================
# RIGHT PANEL: 제목 및 12개 차트 순차적 표시
# ==============================================================================
with col_right:
    # 1. Right Panel Title Header (35 ShortSelling style #8AB4F8)
    st.markdown("<h1 style='color: #8AB4F8; margin-bottom: 8px; font-weight: 700;'>한국 증시 종목별 실적 및 컨센서스 추이</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color: #BDC1C6; font-size: 1.0rem; margin-bottom: 16px;'>📌 <b>{info.get('cmp_nm', active_code)}</b> ({active_code}) 실적 및 컨센서스 분석 대시보드</p>", unsafe_allow_html=True)
    st.divider()

    # Fetch Data with spinner
    with st.spinner("FnGuide 데이터를 불러오는 중입니다..."):
        fin_data = load_financial_highlights(active_code)
        cns_q_data = load_consensus_ts(active_code, freq='Q')
        cns_y_data = load_consensus_ts(active_code, freq='Y')
        target_data = load_target_prices(active_code)
        fcf_y_data = load_free_cash_flow(active_code, freq='Y')

    if not fin_data:
        st.error(f"종목 [{active_code}]의 재무 하이라이트 데이터를 가져올 수 없습니다. ETF/ETN이거나 데이터가 없는 종목일 수 있습니다.")
    else:
        # ----------------------------------------------------------------------
        # Chart 1: EPS (연결 연간 막대 + 전년도 대비 증가율 꺾은선)
        # ----------------------------------------------------------------------
        with st.container(border=True):
            fig_eps = charts.plot_eps_chart(fin_data['df_eps'])
            st.plotly_chart(fig_eps, use_container_width=True)
            with st.expander("📊 EPS 원본 데이터 확인"):
                st.dataframe(fin_data['df_eps'], use_container_width=True)

        # ----------------------------------------------------------------------
        # Chart 2: Earnings(Q) (Financial Highlight 연결 분기 기준)
        # ----------------------------------------------------------------------
        with st.container(border=True):
            fig_eq = charts.plot_earnings_chart(
                fin_data['df_earnings_q'],
                is_quarter=True,
                net_col_name=fin_data['q_net_name']
            )
            st.plotly_chart(fig_eq, use_container_width=True)
            with st.expander("📊 Earnings(Q) 원본 데이터 확인"):
                st.dataframe(fin_data['df_earnings_q'], use_container_width=True)

        # ----------------------------------------------------------------------
        # Chart 3: Earnings(Y) (Financial Highlight 연결 연간 기준)
        # ----------------------------------------------------------------------
        with st.container(border=True):
            fig_ey = charts.plot_earnings_chart(
                fin_data['df_earnings_y'],
                is_quarter=False,
                net_col_name=fin_data['y_net_name']
            )
            st.plotly_chart(fig_ey, use_container_width=True)
            with st.expander("📊 Earnings(Y) 원본 데이터 확인"):
                st.dataframe(fin_data['df_earnings_y'], use_container_width=True)

        # ----------------------------------------------------------------------
        # Chart 4: OPM(Q) (영업이익률 연결 분기 기준)
        # ----------------------------------------------------------------------
        with st.container(border=True):
            fig_opmq = charts.plot_opm_chart(fin_data['df_opm_q'], is_quarter=True)
            st.plotly_chart(fig_opmq, use_container_width=True)
            with st.expander("📊 OPM(Q) 원본 데이터 확인"):
                st.dataframe(fin_data['df_opm_q'], use_container_width=True)

        # ----------------------------------------------------------------------
        # Chart 5: OPM(Y) (영업이익률 연결 연간 기준)
        # ----------------------------------------------------------------------
        with st.container(border=True):
            fig_opmy = charts.plot_opm_chart(fin_data['df_opm_y'], is_quarter=False)
            st.plotly_chart(fig_opmy, use_container_width=True)
            with st.expander("📊 OPM(Y) 원본 데이터 확인"):
                st.dataframe(fin_data['df_opm_y'], use_container_width=True)

        # ----------------------------------------------------------------------
        # Chart 6: PER - 주가수익비율 추이 (연결 연간, 8개년)
        # ----------------------------------------------------------------------
        with st.container(border=True):
            if 'df_per_y' in fin_data and not fin_data['df_per_y'].empty:
                fig_per = charts.plot_per_chart(fin_data['df_per_y'])
                st.plotly_chart(fig_per, use_container_width=True)
                with st.expander("📊 PER 원본 데이터 확인"):
                    st.dataframe(fin_data['df_per_y'], use_container_width=True)
            else:
                st.info("6. PER: 해당 종목의 PER 데이터가 제공되지 않습니다.")

        # ----------------------------------------------------------------------
        # Chart 7: PBR - 주가순자산비율 추이 (연결 연간, 8개년)
        # ----------------------------------------------------------------------
        with st.container(border=True):
            if 'df_pbr_y' in fin_data and not fin_data['df_pbr_y'].empty:
                fig_pbr = charts.plot_pbr_chart(fin_data['df_pbr_y'])
                st.plotly_chart(fig_pbr, use_container_width=True)
                with st.expander("📊 PBR 원본 데이터 확인"):
                    st.dataframe(fin_data['df_pbr_y'], use_container_width=True)
            else:
                st.info("7. PBR: 해당 종목의 PBR 데이터가 제공되지 않습니다.")

        # ----------------------------------------------------------------------
        # Chart 8: ROE - 자기자본이익률 추이 (연결 연간, 8개년)
        # ----------------------------------------------------------------------
        with st.container(border=True):
            if 'df_roe_y' in fin_data and not fin_data['df_roe_y'].empty:
                fig_roe = charts.plot_roe_chart(fin_data['df_roe_y'])
                st.plotly_chart(fig_roe, use_container_width=True)
                with st.expander("📊 ROE 원본 데이터 확인"):
                    st.dataframe(fin_data['df_roe_y'], use_container_width=True)
            else:
                st.info("8. ROE: 해당 종목의 ROE 데이터가 제공되지 않습니다.")

        # ----------------------------------------------------------------------
        # Chart 9: Free Cash Flow (연간/분기 그룹 막대)
        # ----------------------------------------------------------------------
        with st.container(border=True):
            col_fcf_t, col_fcf_s = st.columns([3, 1])
            with col_fcf_s:
                selected_fcf_freq = st.selectbox(
                    "주기 선택",
                    options=["Y", "Q"],
                    format_func=lambda x: "연간" if x == "Y" else "분기",
                    index=0,
                    key="select_fcf_freq"
                )

            if selected_fcf_freq == "Y":
                fcf_active_data = fcf_y_data
            else:
                fcf_active_data = load_free_cash_flow(active_code, freq="Q")

            fig_fcf = charts.plot_free_cash_flow_chart(
                fcf_active_data,
                is_quarter=(selected_fcf_freq == "Q")
            )
            st.plotly_chart(fig_fcf, use_container_width=True)

            with st.expander("📊 Free Cash Flow 원본 데이터 확인"):
                if fcf_active_data and not fcf_active_data['df'].empty:
                    st.dataframe(fcf_active_data['df'], use_container_width=True)
                else:
                    st.info("해당 주기의 Free Cash Flow 데이터가 없습니다.")

        # ----------------------------------------------------------------------
        # Chart 10: 컨센서스 시계열 추이(Q) (연결 분기 기준)
        # ----------------------------------------------------------------------
        with st.container(border=True):
            if cns_q_data and cns_q_data.get('periods'):
                q_periods = cns_q_data['periods']
                q_period_options = [p['YYMM'] for p in q_periods]
                q_period_labels = {p['YYMM']: p.get('YYMM_F', p['YYMM']) for p in q_periods}

                # Metric & Period selectors ("추정 대상 지표" comes before "추정 대상 분기")
                col_m10, col_p10 = st.columns([1, 1])
                with col_m10:
                    selected_q_metric = st.selectbox(
                        "추정 대상 지표",
                        options=list(CNS_METRIC_OPTIONS.keys()),
                        format_func=lambda x: CNS_METRIC_OPTIONS[x],
                        index=0,
                        key="select_cns_q_metric"
                    )
                with col_p10:
                    selected_q_period = st.selectbox(
                        "추정 대상 분기",
                        options=q_period_options,
                        format_func=lambda x: f"{q_period_labels[x]} 기준",
                        index=0,
                        key=f"select_cns_q_period_{active_code}"
                    )
                
                # Reload data if metric or period differs from default
                if selected_q_metric != '0' or selected_q_period != cns_q_data.get('selected_period'):
                    cns_q_data_active = load_consensus_ts(
                        active_code,
                        freq='Q',
                        data_typ=selected_q_metric,
                        period=selected_q_period
                    )
                else:
                    cns_q_data_active = cns_q_data

                fig_cns_q = charts.plot_consensus_timeseries_chart(
                    cns_q_data_active,
                    is_quarter=True,
                    metric_code=selected_q_metric,
                    metric_label=CNS_METRIC_OPTIONS[selected_q_metric]
                )
                st.plotly_chart(fig_cns_q, use_container_width=True)

                with st.expander("📊 컨센서스 시계열 추이(Q) 원본 데이터 확인"):
                    if cns_q_data_active and not cns_q_data_active['df'].empty:
                        st.dataframe(cns_q_data_active['df'], use_container_width=True)
                    else:
                        st.info("해당 지표 및 분기의 컨센서스 시계열 데이터가 없습니다.")
            else:
                st.info("10. 컨센서스 시계열 추이(Q): 해당 종목의 분기 컨센서스 추이 데이터가 제공되지 않습니다.")

        # ----------------------------------------------------------------------
        # Chart 11: 컨센서스 시계열 추이(Y) (연결 연간 기준)
        # ----------------------------------------------------------------------
        with st.container(border=True):
            if cns_y_data and cns_y_data.get('periods'):
                y_periods = cns_y_data['periods']
                y_period_options = [p['YYMM'] for p in y_periods]
                y_period_labels = {p['YYMM']: p.get('YYMM_F', p['YYMM']) for p in y_periods}

                # Metric & Period selectors ("추정 대상 지표" comes before "추정 대상 연도")
                col_m11, col_p11 = st.columns([1, 1])
                with col_m11:
                    selected_y_metric = st.selectbox(
                        "추정 대상 지표",
                        options=list(CNS_METRIC_OPTIONS.keys()),
                        format_func=lambda x: CNS_METRIC_OPTIONS[x],
                        index=0,
                        key="select_cns_y_metric"
                    )
                with col_p11:
                    selected_y_period = st.selectbox(
                        "추정 대상 연도",
                        options=y_period_options,
                        format_func=lambda x: f"{y_period_labels[x]} 기준",
                        index=0,
                        key=f"select_cns_y_period_{active_code}"
                    )

                if selected_y_metric != '0' or selected_y_period != cns_y_data.get('selected_period'):
                    cns_y_data_active = load_consensus_ts(
                        active_code,
                        freq='Y',
                        data_typ=selected_y_metric,
                        period=selected_y_period
                    )
                else:
                    cns_y_data_active = cns_y_data

                fig_cns_y = charts.plot_consensus_timeseries_chart(
                    cns_y_data_active,
                    is_quarter=False,
                    metric_code=selected_y_metric,
                    metric_label=CNS_METRIC_OPTIONS[selected_y_metric]
                )
                st.plotly_chart(fig_cns_y, use_container_width=True)

                with st.expander("📊 컨센서스 시계열 추이(Y) 원본 데이터 확인"):
                    if cns_y_data_active and not cns_y_data_active['df'].empty:
                        st.dataframe(cns_y_data_active['df'], use_container_width=True)
                    else:
                        st.info("해당 지표 및 연도의 컨센서스 시계열 데이터가 없습니다.")
            else:
                st.info("11. 컨센서스 시계열 추이(Y): 해당 종목의 연간 컨센서스 추이 데이터가 제공되지 않습니다.")

        # ----------------------------------------------------------------------
        # Chart 12: 적정 주가 추이 (증권사별 적정주가 & Consensus 직선)
        # ----------------------------------------------------------------------
        with st.container(border=True):
            fig_target = charts.plot_target_price_chart(target_data)
            st.plotly_chart(fig_target, use_container_width=True)

            with st.expander("📋 증권사별 적정주가 & 투자의견 상세 리포트 목록"):
                if not target_data['df'].empty:
                    display_df = target_data['df'][['추정기관', '일자_str', '적정주가', '투자의견']].rename(
                        columns={'일자_str': '추정일자'}
                    )
                    if target_data.get('consensus_price'):
                        st.markdown(f"**현재 Consensus 평균 적정주가**: `{target_data['consensus_price']:,.0f}원`")
                    st.dataframe(display_df, use_container_width=True)
                else:
                    st.info("증권사 적정주가 리포트 데이터가 없습니다.")
