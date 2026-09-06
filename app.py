"""
한국 증시 종목별 주요 재무 지표 및 컨센서스 대시보드
Data Source: https://wcomp.fnguide.com/
"""

import streamlit as st
import pandas as pd
import fnguide_api
import charts
import importlib
importlib.reload(charts)
importlib.reload(fnguide_api)

# Page Configuration
st.set_page_config(
    page_title="한국 증시 종목별 실적 및 컨센서스 추이",
    page_icon="📈",
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
# 1. 종목 리스트 로드 (35 ShortSelling 방식 적용)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=86400)
def load_stock_tickers():
    """상장 종목 전체 리스트 가져오기 (pykrx StockTicker 및 FDR 폴백)"""
    try:
        from pykrx.website.krx.market.ticker import StockTicker
        st_ticker = StockTicker()
        df = st_ticker.listed
        if not df.empty and '종목' in df.columns:
            return df
    except Exception:
        pass
    
    # Fallback to FinanceDataReader
    try:
        import FinanceDataReader as fdr
        df = fdr.StockListing('KRX')
        df = df.set_index('Code')
        df['종목'] = df['Name']
        return df
    except Exception:
        return pd.DataFrame()


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
# LEFT PANEL: 종목 선택 입력 폼 & 조회 버튼 (35 ShortSelling 방식)
# ==============================================================================
with col_left:
    st.subheader("🔍 종목 선택")

    tickers_df = load_stock_tickers()
    if not tickers_df.empty:
        # selectbox 표시용 포맷팅: 종목명 (티커) - 35 ShortSelling 방식
        tickers_df['display_name'] = tickers_df['종목'] + " (" + tickers_df.index + ")"
        default_index = 0
        if st.session_state.selected_code in tickers_df.index:
            default_index = int(tickers_df.index.get_loc(st.session_state.selected_code))

        with st.form(key="stock_search_form"):
            selected_display = st.selectbox(
                "종목명(코드) 입력 / 선택",
                options=tickers_df['display_name'].tolist(),
                index=default_index,
                help="키보드로 종목명(예: 삼성전자) 또는 종목코드(예: 005930)를 입력하여 검색할 수 있습니다."
            )
            submitted = st.form_submit_button("조회", use_container_width=True, type="primary")

            if submitted and selected_display:
                code_from_display = selected_display.split("(")[-1].replace(")", "").strip()
                if st.session_state.selected_code != code_from_display:
                    st.session_state.selected_code = code_from_display
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
        1. <b>EPS</b> (연결 연간 및 YoY 증가율)<br>
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
# RIGHT PANEL: 제목 및 10개 차트 순차적 표시
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
                        key="select_cns_q_period"
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
                        key="select_cns_y_period"
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
