"""
Plotly Chart Generators for Financial Indicators & Consensus Dashboard
Creates interactive, publication-quality financial charts with sleek gray theme.
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import Optional, Dict, Any

# Professional high-contrast palette for sleek gray background
THEME = {
    'paper_bgcolor': '#1E2430',    # Elegant slate dark-gray paper
    'plot_bgcolor': '#161B24',     # Deep slate-gray plot area
    'text_main': '#F8FAFC',        # Crisp white for titles
    'text_body': '#E2E8F0',        # Off-white for general text
    'text_muted': '#94A3B8',       # Slate for muted labels
    'grid_color': '#2A3342',       # Subtle dark slate grid lines
    'border_color': '#3E4C5E',     # Axis lines & legend border
    'legend_bg': 'rgba(30, 36, 48, 0.9)',
    'consensus_line': '#F87171',   # Coral red for consensus
    'primary_bar': '#3B82F6',      # Vibrant blue
    'profit_bar': '#10B981',       # Vibrant green
    'net_profit_bar': '#F59E0B'    # Vibrant amber
}

COMMON_LAYOUT = dict(
    font=dict(family="Pretendard, Malgun Gothic, -apple-system, sans-serif", size=12, color=THEME['text_body']),
    margin=dict(l=55, r=55, t=55, b=45),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        bgcolor=THEME['legend_bg'],
        bordercolor=THEME['border_color'],
        borderwidth=1,
        font=dict(color=THEME['text_body'], size=11)
    ),
    hoverlabel=dict(
        bgcolor="#0F172A",
        font_color="#FFFFFF",
        font_size=12,
        font_family="Pretendard, Malgun Gothic, sans-serif",
        bordercolor=THEME['border_color']
    ),
    plot_bgcolor=THEME['plot_bgcolor'],
    paper_bgcolor=THEME['paper_bgcolor']
)


def plot_eps_chart(df_eps: pd.DataFrame) -> go.Figure:
    """
    1. EPS 차트:
    'Financial Highlight'의 'EPS'('연결' '연간' 기준) 데이터를 연도별 막대 그래프로 표시,
    전년도 대비 증가율을 계산하여 꺾은선 그래프로 표시 (이중축).
    범례: 'EPS(원)', 'EPS증가율(%)'
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1. Bar: EPS (원)
    fig.add_trace(
        go.Bar(
            x=df_eps['Period'],
            y=df_eps['EPS(원)'],
            name="EPS(원)",
            marker=dict(
                color='#3B82F6',
                line=dict(color='#60A5FA', width=1),
                cornerradius=4
            ),
            hovertemplate="<b>%{x}</b><br>EPS: %{y:,.1f}원<extra></extra>"
        ),
        secondary_y=False
    )

    # 2. Line: EPS증가율 (%)
    fig.add_trace(
        go.Scatter(
            x=df_eps['Period'],
            y=df_eps['EPS증가율(%)'],
            name="EPS증가율(%)",
            mode='lines+markers+text',
            line=dict(color='#F87171', width=2.5),
            marker=dict(size=8, color='#EF4444', line=dict(color='#F8FAFC', width=1.5)),
            text=[f"{val:+.1f}%" if pd.notnull(val) else "" for val in df_eps['EPS증가율(%)']],
            textposition="top center",
            textfont=dict(size=11, color='#FCA5A5'),
            hovertemplate="<b>%{x}</b><br>EPS증가율: %{y:+.2f}%<extra></extra>"
        ),
        secondary_y=True
    )

    fig.update_layout(
        COMMON_LAYOUT,
        title=dict(text="<b>1. EPS 및 YoY 증가율 (연결 연간)</b>", font=dict(size=16, color=THEME['text_main'])),
        xaxis=dict(
            title=None,
            showgrid=False,
            linecolor=THEME['border_color'],
            tickfont=dict(color=THEME['text_body'], size=11)
        ),
        yaxis=dict(
            title="EPS (원)",
            title_font=dict(size=12, color='#60A5FA'),
            tickformat=",d",
            showgrid=True,
            gridcolor=THEME['grid_color'],
            linecolor=THEME['border_color'],
            tickfont=dict(color=THEME['text_body'], size=11)
        ),
        yaxis2=dict(
            title="EPS 증가율 (%)",
            title_font=dict(size=12, color='#F87171'),
            ticksuffix="%",
            showgrid=False,
            zeroline=True,
            zerolinecolor=THEME['border_color'],
            zerolinewidth=1,
            tickfont=dict(color=THEME['text_body'], size=11)
        ),
        height=420
    )
    return fig


def plot_earnings_chart(df_earnings: pd.DataFrame, is_quarter: bool = True, net_col_name: str = "당기순이익(지배)") -> go.Figure:
    """
    2. Earnings(Q) & 3. Earnings(Y) 차트:
    'Financial Highlight'의 '매출액', '영업이익(발표기준)', '당기순이익' 데이터를 막대 그래프로 표시.
    """
    chart_num = "2" if is_quarter else "3"
    freq_label = "분기" if is_quarter else "연간"
    title_text = f"<b>{chart_num}. Earnings({('Q' if is_quarter else 'Y')}) - 실적 추이 (연결 {freq_label})</b>"

    fig = go.Figure()

    # 1. 매출액
    fig.add_trace(
        go.Bar(
            x=df_earnings['Period'],
            y=df_earnings['매출액'],
            name="매출액",
            marker=dict(color=THEME['primary_bar'], cornerradius=3),
            hovertemplate="<b>%{x}</b><br>매출액: %{y:,.0f} 억원<extra></extra>"
        )
    )

    # 2. 영업이익(발표기준)
    fig.add_trace(
        go.Bar(
            x=df_earnings['Period'],
            y=df_earnings['영업이익(발표기준)'],
            name="영업이익(발표기준)",
            marker=dict(color=THEME['profit_bar'], cornerradius=3),
            hovertemplate="<b>%{x}</b><br>영업이익(발표기준): %{y:,.0f} 억원<extra></extra>"
        )
    )

    # 3. 당기순이익(지배) or 당기순이익
    fig.add_trace(
        go.Bar(
            x=df_earnings['Period'],
            y=df_earnings[net_col_name],
            name=net_col_name,
            marker=dict(color=THEME['net_profit_bar'], cornerradius=3),
            hovertemplate=f"<b>%{{x}}</b><br>{net_col_name}: %{{y:,.0f}} 억원<extra></extra>"
        )
    )

    fig.update_layout(
        COMMON_LAYOUT,
        barmode='group',
        title=dict(text=title_text, font=dict(size=16, color=THEME['text_main'])),
        xaxis=dict(
            title=None,
            showgrid=False,
            linecolor=THEME['border_color'],
            tickfont=dict(color=THEME['text_body'], size=11)
        ),
        yaxis=dict(
            title="금액 (억원)",
            title_font=dict(size=12, color=THEME['text_muted']),
            tickformat=",d",
            showgrid=True,
            gridcolor=THEME['grid_color'],
            linecolor=THEME['border_color'],
            tickfont=dict(color=THEME['text_body'], size=11)
        ),
        height=420
    )
    return fig


def plot_opm_chart(df_opm: pd.DataFrame, is_quarter: bool = True) -> go.Figure:
    """
    4. OPM(Q) & 5. OPM(Y) 차트:
    'Financial Highlight'의 '영업이익률' 데이터를 분기/연간별 막대 그래프로 표시.
    """
    chart_num = "4" if is_quarter else "5"
    freq_label = "분기" if is_quarter else "연간"
    title_text = f"<b>{chart_num}. OPM({('Q' if is_quarter else 'Y')}) - 영업이익률 추이 (연결 {freq_label})</b>"

    colors = [THEME['profit_bar'] if (val is not None and val >= 0) else '#F87171' for val in df_opm['영업이익률(%)']]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df_opm['Period'],
            y=df_opm['영업이익률(%)'],
            name="영업이익률(%)",
            marker=dict(color=colors, cornerradius=4),
            text=[f"{val:.2f}%" if pd.notnull(val) else "" for val in df_opm['영업이익률(%)']],
            textposition="auto",
            textfont=dict(color='#FFFFFF', size=11),
            hovertemplate="<b>%{x}</b><br>영업이익률: %{y:.2f}%<extra></extra>"
        )
    )

    fig.update_layout(
        COMMON_LAYOUT,
        title=dict(text=title_text, font=dict(size=16, color=THEME['text_main'])),
        xaxis=dict(
            title=None,
            showgrid=False,
            linecolor=THEME['border_color'],
            tickfont=dict(color=THEME['text_body'], size=11)
        ),
        yaxis=dict(
            title="영업이익률 (%)",
            title_font=dict(size=12, color=THEME['text_muted']),
            ticksuffix="%",
            showgrid=True,
            gridcolor=THEME['grid_color'],
            linecolor=THEME['border_color'],
            zeroline=True,
            zerolinecolor=THEME['border_color'],
            zerolinewidth=1.5,
            tickfont=dict(color=THEME['text_body'], size=11)
        ),
        height=400
    )
    return fig


def plot_roe_chart(df_roe: pd.DataFrame) -> go.Figure:
    """
    6. ROE - 자기자본이익률 추이 (연결 연간):
    'Financial Highlight'의 'ROE' 데이터(8개년, 추정치 3개년 포함)를 막대 그래프로 표시.
    """
    title_text = "<b>6. ROE - 자기자본이익률 추이 (연결 연간)</b>"
    fig = go.Figure()

    if df_roe.empty or 'ROE(%)' not in df_roe.columns:
        fig.add_annotation(
            text="ROE 데이터가 존재하지 않습니다.",
            showarrow=False,
            font=dict(size=14, color=THEME['text_muted']),
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5
        )
        fig.update_layout(COMMON_LAYOUT, title=dict(text=title_text, font=dict(color=THEME['text_main'])), height=400)
        return fig

    colors = [THEME['profit_bar'] if (val is not None and val >= 0) else '#F87171' for val in df_roe['ROE(%)']]

    fig.add_trace(
        go.Bar(
            x=df_roe['Period'],
            y=df_roe['ROE(%)'],
            name="ROE(%)",
            marker=dict(color=colors, cornerradius=4),
            text=[f"{val:.2f}%" if pd.notnull(val) else "" for val in df_roe['ROE(%)']],
            textposition="auto",
            textfont=dict(color='#FFFFFF', size=11),
            hovertemplate="<b>%{x}</b><br>ROE: %{y:.2f}%<extra></extra>"
        )
    )

    fig.update_layout(
        COMMON_LAYOUT,
        title=dict(text=title_text, font=dict(size=16, color=THEME['text_main'])),
        xaxis=dict(
            title=None,
            showgrid=False,
            linecolor=THEME['border_color'],
            tickfont=dict(color=THEME['text_body'], size=11)
        ),
        yaxis=dict(
            title="ROE (%)",
            title_font=dict(size=12, color=THEME['text_muted']),
            ticksuffix="%",
            showgrid=True,
            gridcolor=THEME['grid_color'],
            linecolor=THEME['border_color'],
            zeroline=True,
            zerolinecolor=THEME['border_color'],
            zerolinewidth=1.5,
            tickfont=dict(color=THEME['text_body'], size=11)
        ),
        height=400
    )
    return fig


def plot_free_cash_flow_chart(fcf_data: Dict[str, Any], is_quarter: bool = False) -> go.Figure:
    """
    7. Free Cash Flow 차트:
    FnGuide 사이트의 'Free Cash Flow' 차트 양식을 그대로 복제하여 그룹 막대 그래프로 표시.
    (영업활동현금흐름, 투자활동현금흐름, 재무활동현금흐름)
    """
    freq_label = "분기" if is_quarter else "연간"
    title_text = f"<b>7. Free Cash Flow (연결 {freq_label})</b>"
    df = fcf_data.get('df', pd.DataFrame())

    fig = go.Figure()

    if df.empty or 'Period' not in df.columns:
        fig.add_annotation(
            text="Free Cash Flow 데이터가 존재하지 않습니다.",
            showarrow=False,
            font=dict(size=14, color=THEME['text_muted']),
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5
        )
        fig.update_layout(COMMON_LAYOUT, title=dict(text=title_text, font=dict(color=THEME['text_main'])), height=420)
        return fig

    # Map standard series colors: 영업활동: Royal Blue (#3B82F6), 투자활동: Amber (#F59E0B), 재무활동: Emerald Green (#10B981)
    series_colors = {
        '영업활동현금흐름': '#3B82F6',
        '투자활동현금흐름': '#F59E0B',
        '재무활동현금흐름': '#10B981'
    }
    fallback_colors = ['#3B82F6', '#F59E0B', '#10B981', '#A855F7']

    val_cols = fcf_data.get('val_cols', [c for c in df.columns if c != 'Period'])
    for idx, col in enumerate(val_cols):
        color = series_colors.get(col, fallback_colors[idx % len(fallback_colors)])
        fig.add_trace(
            go.Bar(
                x=df['Period'],
                y=df[col],
                name=col,
                marker=dict(color=color, cornerradius=3),
                hovertemplate=f"<b>%{{x}}</b><br>{col}: %{{y:,.0f}} 억원<extra></extra>"
            )
        )

    fig.update_layout(
        COMMON_LAYOUT,
        barmode='group',
        title=dict(text=title_text, font=dict(size=16, color=THEME['text_main'])),
        xaxis=dict(
            title=None,
            showgrid=False,
            linecolor=THEME['border_color'],
            tickfont=dict(color=THEME['text_body'], size=11)
        ),
        yaxis=dict(
            title="금액 (억원)",
            title_font=dict(size=12, color=THEME['text_muted']),
            tickformat=",d",
            showgrid=True,
            gridcolor=THEME['grid_color'],
            linecolor=THEME['border_color'],
            zeroline=True,
            zerolinecolor=THEME['border_color'],
            zerolinewidth=1.5,
            tickfont=dict(color=THEME['text_body'], size=11)
        ),
        height=420
    )
    return fig


def plot_consensus_timeseries_chart(
    cns_data: Dict[str, Any],
    is_quarter: bool = True,
    metric_code: str = "0",
    metric_label: str = "매출액"
) -> go.Figure:
    """
    8. 컨센서스 시계열 추이(Q) & 9. 컨센서스 시계열 추이(Y):
    FnGuide의 '컨센서스 시계열 추이' 차트를 복제하여 최고, 최저, 평균 컨센서스를 꺾은선으로 표시.
    지표별(매출액, 영업이익, 당기순이익, EPS, PER, PER(Fwd,12M)) 단위 및 축 포맷 동적 적용.
    """
    chart_num = "8" if is_quarter else "9"
    freq_label = "분기" if is_quarter else "연간"
    period_label = cns_data.get('period_label', '')
    title_text = f"<b>{chart_num}. 컨센서스 시계열 추이({('Q' if is_quarter else 'Y')}) - {metric_label} | {period_label} 기준 (연결 {freq_label})</b>"

    df = cns_data.get('df', pd.DataFrame())
    fig = go.Figure()

    if df.empty:
        fig.add_annotation(
            text=f"'{metric_label}' 컨센서스 시계열 데이터가 존재하지 않습니다.",
            showarrow=False,
            font=dict(size=14, color=THEME['text_muted']),
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5
        )
        fig.update_layout(COMMON_LAYOUT, title=dict(text=title_text, font=dict(color=THEME['text_main'])), height=400)
        return fig

    # Determine unit and formatting based on metric_code
    if metric_code in ['0', '1', '2']:  # 매출액, 영업이익, 당기순이익
        unit_label = "금액 (억원)"
        hover_unit = " 억원"
        tick_format = ",d"
    elif metric_code == '3':             # EPS
        unit_label = "EPS (원)"
        hover_unit = " 원"
        tick_format = ",.1f"
    elif metric_code in ['4', '5']:      # PER, PER(Fwd,12M)
        unit_label = "PER (배)"
        hover_unit = " 배"
        tick_format = ",.2f"
    else:
        unit_label = ""
        hover_unit = ""
        tick_format = ",.2f"

    # PER(Fwd,12M) typically only has VAL_AVG
    if metric_code == '5':
        if 'VAL_AVG' in df.columns and df['VAL_AVG'].dropna().any():
            fig.add_trace(
                go.Scatter(
                    x=df['TRD_DT'],
                    y=df['VAL_AVG'],
                    name="PER(Fwd 12M)",
                    mode='lines+markers',
                    line=dict(color='#60A5FA', width=2.5),
                    marker=dict(size=6, color='#60A5FA'),
                    hovertemplate=f"<b>%{{x}}</b><br>PER(Fwd 12M): %{{y:,.2f}}{hover_unit}<extra></extra>"
                )
            )
    else:
        # VAL_MAX: 컨센서스(최고) - 주황색 (Warm Orange)
        if 'VAL_MAX' in df.columns and df['VAL_MAX'].dropna().any():
            fig.add_trace(
                go.Scatter(
                    x=df['TRD_DT'],
                    y=df['VAL_MAX'],
                    name="컨센서스(최고)",
                    mode='lines+markers',
                    line=dict(color='#FB923C', width=2),
                    marker=dict(size=5, color='#FB923C', symbol='circle'),
                    hovertemplate=f"<b>%{{x}}</b><br>최고: %{{y:{tick_format}}}{hover_unit}<extra></extra>"
                )
            )

        # VAL_MIN: 컨센서스(최저) - 선명한 블루 (Vibrant Royal Blue)
        if 'VAL_MIN' in df.columns and df['VAL_MIN'].dropna().any():
            fig.add_trace(
                go.Scatter(
                    x=df['TRD_DT'],
                    y=df['VAL_MIN'],
                    name="컨센서스(최저)",
                    mode='lines+markers',
                    line=dict(color='#3B82F6', width=2),
                    marker=dict(size=5, color='#3B82F6', symbol='circle'),
                    hovertemplate=f"<b>%{{x}}</b><br>최저: %{{y:{tick_format}}}{hover_unit}<extra></extra>"
                )
            )

        # VAL_AVG: 컨센서스(평균) - 선명한 에메랄드 그린 (Vibrant Emerald Green)
        # 최저(블루), 최고(주황)와 뚜렷하게 구별되도록 그린 색상 및 다이아몬드 마커, 두께 2.5 적용
        if 'VAL_AVG' in df.columns and df['VAL_AVG'].dropna().any():
            fig.add_trace(
                go.Scatter(
                    x=df['TRD_DT'],
                    y=df['VAL_AVG'],
                    name="컨센서스",
                    mode='lines+markers',
                    line=dict(color='#10B981', width=2.5),
                    marker=dict(size=6, color='#10B981', symbol='diamond'),
                    hovertemplate=f"<b>%{{x}}</b><br>평균: %{{y:{tick_format}}}{hover_unit}<extra></extra>"
                )
            )

    fig.update_layout(
        COMMON_LAYOUT,
        title=dict(text=title_text, font=dict(size=16, color=THEME['text_main'])),
        xaxis=dict(
            title=None,
            showgrid=True,
            gridcolor=THEME['grid_color'],
            linecolor=THEME['border_color'],
            tickangle=-25,
            tickfont=dict(color=THEME['text_body'], size=11)
        ),
        yaxis=dict(
            title=unit_label,
            title_font=dict(size=12, color=THEME['text_muted']),
            tickformat=tick_format,
            showgrid=True,
            gridcolor=THEME['grid_color'],
            linecolor=THEME['border_color'],
            tickfont=dict(color=THEME['text_body'], size=11)
        ),
        height=420
    )
    return fig


def plot_target_price_chart(target_data: Dict[str, Any]) -> go.Figure:
    """
    10. 적정 주가 추이 차트:
    '증권사별 적정주가 & 투자의견'의 '추정기관', '추정일자', '적정주가' 데이터를 가져와서 꺾은선 그래프로 표시.
    가로축: 날짜, 세로축: 주가(원).
    'Consensus'의 '적정주가'는 별도의 직선으로 표시.
    """
    title_text = "<b>10. 적정 주가 추이 (증권사별 목표주가 및 Consensus)</b>"
    df = target_data.get('df', pd.DataFrame())
    consensus_price = target_data.get('consensus_price')

    fig = go.Figure()

    if df.empty and consensus_price is None:
        fig.add_annotation(
            text="증권사별 적정주가 추정 데이터가 존재하지 않습니다.",
            showarrow=False,
            font=dict(size=14, color=THEME['text_muted']),
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5
        )
        fig.update_layout(COMMON_LAYOUT, title=dict(text=title_text, font=dict(color=THEME['text_main'])), height=420)
        return fig

    # 1. Brokerage estimates (Line with markers)
    if not df.empty:
        hover_texts = [
            f"<b>{row['추정기관']}</b><br>일자: {row['일자_str']}<br>적정주가: {row['적정주가']:,.0f}원"
            + (f"<br>투자의견: {row['투자의견']}" if row['투자의견'] else "")
            for _, row in df.iterrows()
        ]

        fig.add_trace(
            go.Scatter(
                x=df['일자_str'],
                y=df['적정주가'],
                name="증권사별 적정주가",
                mode='lines+markers',
                line=dict(color='#818CF8', width=2, shape='linear'),
                marker=dict(size=8, color='#6366F1', line=dict(color='#FFFFFF', width=1.5)),
                text=df['추정기관'],
                hoverinfo="text",
                hovertext=hover_texts
            )
        )

    # 2. Consensus Target Price Line
    if consensus_price is not None and consensus_price > 0:
        if not df.empty:
            x_range = [df['일자_str'].iloc[0], df['일자_str'].iloc[-1]]
        else:
            x_range = ["과거", "현재"]

        fig.add_trace(
            go.Scatter(
                x=x_range,
                y=[consensus_price, consensus_price],
                name=f"Consensus 적정주가 ({consensus_price:,.0f}원)",
                mode='lines',
                line=dict(color=THEME['consensus_line'], width=2.5, dash='dash'),
                hovertemplate=f"<b>Consensus 평균</b><br>적정주가: {consensus_price:,.0f}원<extra></extra>"
            )
        )

        # Add annotation marker on the right side of the consensus line
        fig.add_annotation(
            xref="paper",
            yref="y",
            x=1.01,
            y=consensus_price,
            text=f" <b>Consensus</b><br> {consensus_price:,.0f}원",
            showarrow=False,
            font=dict(size=11, color='#FECACA'),
            align="left",
            bgcolor="rgba(153, 27, 27, 0.85)",
            bordercolor="#F87171",
            borderwidth=1,
            borderpad=4
        )

    fig.update_layout(
        COMMON_LAYOUT,
        title=dict(text=title_text, font=dict(size=16, color=THEME['text_main'])),
        xaxis=dict(
            title="추정 일자",
            title_font=dict(size=12, color=THEME['text_muted']),
            showgrid=True,
            gridcolor=THEME['grid_color'],
            linecolor=THEME['border_color'],
            tickangle=-30,
            tickfont=dict(color=THEME['text_body'], size=11)
        ),
        yaxis=dict(
            title="주가 (원)",
            title_font=dict(size=12, color=THEME['text_muted']),
            tickformat=",d",
            showgrid=True,
            gridcolor=THEME['grid_color'],
            linecolor=THEME['border_color'],
            tickfont=dict(color=THEME['text_body'], size=11)
        ),
        height=450
    )
    return fig
