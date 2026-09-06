"""
FnGuide Data Scraper & API Client
Fetches financial indicators, consensus timeseries, and target prices from https://wcomp.fnguide.com/
"""

import re
import json
import requests
from bs4 import BeautifulSoup
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://wcomp.fnguide.com/'
}

BASE_URL = 'https://wcomp.fnguide.com'


def _extract_embedded_json(html: str, key: str) -> Optional[Dict[str, Any]]:
    """Extracts a JSON object assigned to a specific key in JavaScript block."""
    pattern = rf'{key}\s*:\s*\{{'
    m = re.search(pattern, html)
    if not m:
        return None

    brace_start = m.end() - 1
    brace_count = 0
    in_str = False
    escape = False
    brace_end = -1

    for i in range(brace_start, len(html)):
        c = html[i]
        if c == '"' and not escape:
            in_str = not in_str
        elif c == '\\':
            escape = not escape
            continue
        elif not in_str:
            if c == '{':
                brace_count += 1
            elif c == '}':
                brace_count -= 1
                if brace_count == 0:
                    brace_end = i + 1
                    break
        escape = False

    if brace_end != -1:
        try:
            return json.loads(html[brace_start:brace_end])
        except Exception:
            return None
    return None


def get_company_basic_info(cmp_cd: str) -> Dict[str, Any]:
    """Fetches company name, market type, current price, and basic info from Snapshot."""
    url = f"{BASE_URL}/CompanyInfo/Snapshot?cmp_cd={cmp_cd}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')

        # Company Name
        gi_name = soup.find(id='giName')
        cmp_nm = gi_name.get_text(strip=True) if gi_name else ""
        if not cmp_nm and soup.title:
            title_text = soup.title.get_text()
            if '(' in title_text:
                cmp_nm = title_text.split('(')[0].strip()

        # Market type
        mkt_nm = "KOSPI"
        mkt_span = soup.find('span', class_='corp_group')
        if mkt_span:
            mkt_nm = mkt_span.get_text(strip=True)

        # Price info
        price_elem = soup.find('strong', class_='txt_price')
        current_price = price_elem.get_text(strip=True) if price_elem else "-"

        # Sector / Industry
        sector_elem = soup.find(id='biz_top_0_1')
        sector_nm = sector_elem.get_text(strip=True) if sector_elem else ""

        return {
            'cmp_cd': cmp_cd,
            'cmp_nm': cmp_nm or cmp_cd,
            'mkt_nm': mkt_nm,
            'current_price': current_price,
            'sector_nm': sector_nm
        }
    except Exception as e:
        return {
            'cmp_cd': cmp_cd,
            'cmp_nm': cmp_cd,
            'mkt_nm': '',
            'current_price': '-',
            'sector_nm': '',
            'error': str(e)
        }


def _fetch_snp_financial_api(cmp_cd: str, freq_typ: str) -> Optional[Dict[str, Any]]:
    """Fetches full 8-period Financial Highlight for Annual (Y) or Quarterly (Q)."""
    url = f"{BASE_URL}/CompanyInfo/getSnpFinancial?cmp_cd={cmp_cd}&consol_typ=C&freq_typ={freq_typ}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        res = r.json()
        dataset = res.get('dataset')
        if dataset and 'header' in dataset and 'data' in dataset and len(dataset['header']) > 0:
            return dataset
    except Exception:
        pass
    return None


def get_financial_highlight_data(cmp_cd: str) -> Optional[Dict[str, Any]]:
    """
    Fetches and parses 'Financial Highlight' from FnGuide.
    Fetches full annual data (including 2026/12(E), 2027/12(E), 2028/12(E)) and
    full quarterly data (including 2026/09(E), 2026/12(E), 2027/03(E)).
    """
    dataset_y = _fetch_snp_financial_api(cmp_cd, 'Y')
    dataset_q = _fetch_snp_financial_api(cmp_cd, 'Q')

    # Fallback to embedded snpFinancial from Snapshot page if API is unavailable
    if not dataset_y or not dataset_q:
        url = f"{BASE_URL}/CompanyInfo/Snapshot?cmp_cd={cmp_cd}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            r.encoding = 'utf-8'
            data_embedded = _extract_embedded_json(r.text, 'snpFinancial')
        except Exception:
            data_embedded = None
    else:
        data_embedded = None

    def _to_float(val: Any) -> Optional[float]:
        if val is None or val == '' or val == '-':
            return None
        try:
            return float(str(val).replace(',', ''))
        except (ValueError, TypeError):
            return None

    # 1. Process Annual (Y) Data (for Chart 1 EPS, Chart 3 Earnings(Y), Chart 5 OPM(Y))
    if dataset_y:
        y_headers = dataset_y['header']
        y_rows = {row.get('NAME', '').strip(): row for row in dataset_y.get('data', [])}
        annual_cols = [h['CD'] for h in y_headers]
        annual_labels = [h['YYMM'] + ('(E)' if (h.get('EP_CHK') or '').strip() == 'E' else '') for h in y_headers]
    elif data_embedded and 'header' in data_embedded:
        y_headers = data_embedded['header'][:4]
        y_rows = {row.get('NAME', '').strip(): row for row in data_embedded.get('data', [])}
        annual_cols = [h['CD'] for h in y_headers]
        annual_labels = [h['YYMM'] + ('(E)' if (h.get('EP_CHK') or '').strip() == 'E' else '') for h in y_headers]
    else:
        return None

    # 2. Process Quarterly (Q) Data (for Chart 2 Earnings(Q), Chart 4 OPM(Q))
    if dataset_q:
        q_headers = dataset_q['header']
        q_rows = {row.get('NAME', '').strip(): row for row in dataset_q.get('data', [])}
        quarter_cols = [h['CD'] for h in q_headers]
        quarter_labels = [h['YYMM'] + ('(E)' if (h.get('EP_CHK') or '').strip() == 'E' else '') for h in q_headers]
    elif data_embedded and 'header' in data_embedded:
        q_headers = data_embedded['header'][4:]
        q_rows = {row.get('NAME', '').strip(): row for row in data_embedded.get('data', [])}
        quarter_cols = [h['CD'] for h in q_headers]
        quarter_labels = [h['YYMM'] + ('(E)' if (h.get('EP_CHK') or '').strip() == 'E' else '') for h in q_headers]
    else:
        return None

    # Helper for Net Income with fallback rule:
    # "만일 다가올 분기/연도의 당기순이익 추정치가 '당기순이익(지배)'에는 없고 '당기순이익'에만 표시되어 있는 경우에는
    #  '당기순이익(지배)'를 버리고, '당기순이익'의 데이터를 가져옵니다."
    def _resolve_net_income(rows_dict: Dict[str, Dict[str, Any]], cols: List[str], headers_slice: List[Dict[str, Any]]) -> Tuple[str, List[Optional[float]]]:
        net_ctrl = rows_dict.get('당기순이익(지배)')
        net_total = rows_dict.get('당기순이익')

        use_total = False
        if net_ctrl and net_total:
            # Check all estimate column(s) where EP_CHK == 'E'
            for idx, h in enumerate(headers_slice):
                c = cols[idx]
                is_estimate = (h.get('EP_CHK') or '').strip() == 'E'
                if is_estimate:
                    ctrl_val = _to_float(net_ctrl.get(c))
                    total_val = _to_float(net_total.get(c))
                    if ctrl_val is None and total_val is not None:
                        use_total = True
                        break

        chosen_row = net_total if use_total else (net_ctrl or net_total)
        chosen_name = '당기순이익' if use_total else ('당기순이익(지배)' if net_ctrl else '당기순이익')
        vals = [_to_float(chosen_row.get(c)) if chosen_row else None for c in cols]
        return chosen_name, vals

    # 1. EPS Data (연간) - includes 2026/12(E), 2027/12(E), 2028/12(E)
    eps_row = y_rows.get('EPS')
    eps_vals: List[Optional[float]] = []
    eps_growth: List[Optional[float]] = []

    if eps_row:
        eps_vals = [_to_float(eps_row.get(c)) for c in annual_cols]
        # Calculate YoY growth rate (%)
        eps_growth.append(None)
        for i in range(1, len(eps_vals)):
            prev, curr = eps_vals[i - 1], eps_vals[i]
            if prev is not None and curr is not None and prev != 0:
                growth = ((curr - prev) / abs(prev)) * 100.0
                eps_growth.append(round(growth, 2))
            else:
                eps_growth.append(None)
    else:
        eps_vals = [None] * len(annual_cols)
        eps_growth = [None] * len(annual_cols)

    df_eps = pd.DataFrame({
        'Period': annual_labels,
        'EPS(원)': eps_vals,
        'EPS증가율(%)': eps_growth
    })

    # 2. Earnings (Q) (분기) - includes all upcoming quarters
    q_rev_row = q_rows.get('매출액')
    q_op_row = q_rows.get('영업이익(발표기준)') or q_rows.get('영업이익')
    q_rev_vals = [_to_float(q_rev_row.get(c)) if q_rev_row else None for c in quarter_cols]
    q_op_vals = [_to_float(q_op_row.get(c)) if q_op_row else None for c in quarter_cols]
    q_net_name, q_net_vals = _resolve_net_income(q_rows, quarter_cols, q_headers)

    df_earnings_q = pd.DataFrame({
        'Period': quarter_labels,
        '매출액': q_rev_vals,
        '영업이익(발표기준)': q_op_vals,
        q_net_name: q_net_vals
    })

    # 3. Earnings (Y) (연간) - includes all upcoming years
    y_rev_row = y_rows.get('매출액')
    y_op_row = y_rows.get('영업이익(발표기준)') or y_rows.get('영업이익')
    y_rev_vals = [_to_float(y_rev_row.get(c)) if y_rev_row else None for c in annual_cols]
    y_op_vals = [_to_float(y_op_row.get(c)) if y_op_row else None for c in annual_cols]
    y_net_name, y_net_vals = _resolve_net_income(y_rows, annual_cols, y_headers)

    df_earnings_y = pd.DataFrame({
        'Period': annual_labels,
        '매출액': y_rev_vals,
        '영업이익(발표기준)': y_op_vals,
        y_net_name: y_net_vals
    })

    # 4. OPM (Q) (분기)
    q_opm_row = q_rows.get('영업이익률')
    q_opm_vals = [_to_float(q_opm_row.get(c)) if q_opm_row else None for c in quarter_cols]
    df_opm_q = pd.DataFrame({
        'Period': quarter_labels,
        '영업이익률(%)': q_opm_vals
    })

    # 5. OPM (Y) (연간)
    y_opm_row = y_rows.get('영업이익률')
    y_opm_vals = [_to_float(y_opm_row.get(c)) if y_opm_row else None for c in annual_cols]
    df_opm_y = pd.DataFrame({
        'Period': annual_labels,
        '영업이익률(%)': y_opm_vals
    })

    # 6. ROE (Y) (연간) - 8개년 (추정치 3개년 포함)
    y_roe_row = y_rows.get('ROE')
    y_roe_vals = [_to_float(y_roe_row.get(c)) if y_roe_row else None for c in annual_cols]
    df_roe_y = pd.DataFrame({
        'Period': annual_labels,
        'ROE(%)': y_roe_vals
    })

    # PER (Y) (연간) - 8개년 (추정치 3개년 포함)
    y_per_row = y_rows.get('PER') or y_rows.get('PER(배)')
    y_per_vals = [_to_float(y_per_row.get(c)) if y_per_row else None for c in annual_cols]
    df_per_y = pd.DataFrame({
        'Period': annual_labels,
        'PER(배)': y_per_vals
    })

    # PBR (Y) (연간) - 8개년 (추정치 3개년 포함)
    y_pbr_row = y_rows.get('PBR') or y_rows.get('PBR(배)')
    y_pbr_vals = [_to_float(y_pbr_row.get(c)) if y_pbr_row else None for c in annual_cols]
    df_pbr_y = pd.DataFrame({
        'Period': annual_labels,
        'PBR(배)': y_pbr_vals
    })

    return {
        'annual_labels': annual_labels,
        'quarter_labels': quarter_labels,
        'df_eps': df_eps,
        'df_earnings_q': df_earnings_q,
        'df_earnings_y': df_earnings_y,
        'q_net_name': q_net_name,
        'y_net_name': y_net_name,
        'df_opm_q': df_opm_q,
        'df_opm_y': df_opm_y,
        'df_roe_y': df_roe_y,
        'df_per_y': df_per_y,
        'df_pbr_y': df_pbr_y
    }


def get_free_cash_flow_data(cmp_cd: str, freq_typ: str = 'Y') -> Dict[str, Any]:
    """
    Fetches Free Cash Flow chart data from FnGuide internal API:
    /CompanyInfo/getFinCashFlowFreeChart?cmp_cd={cmp_cd}&freq_typ={freq_typ}&consol_typ=C
    freq_typ: 'Y' (연간) or 'Q' (분기)
    Returns dictionary with 'df', 'headers', and metadata.
    """
    url = f"{BASE_URL}/CompanyInfo/getFinCashFlowFreeChart?cmp_cd={cmp_cd}&freq_typ={freq_typ}&consol_typ=C"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r_json = r.json()
        dataset = r_json.get('dataset', {})
        header = dataset.get('header', [])
        data = dataset.get('data', [])
    except Exception as e:
        return {'df': pd.DataFrame(), 'headers': [], 'error': str(e), 'val_cols': []}

    if not data:
        return {'df': pd.DataFrame(), 'headers': header, 'val_cols': []}

    col_map = {}
    for h in header:
        cid = h.get('ID')
        cnm = h.get('NM')
        if cid and cnm:
            col_map[cid] = cnm

    df = pd.DataFrame(data)
    if 'TRD_DT' in df.columns:
        df = df.rename(columns={'TRD_DT': 'Period'})

    for col_id, col_name in col_map.items():
        if col_id in df.columns and col_id != 'TRD_DT':
            df = df.rename(columns={col_id: col_name})

    val_cols = [col_name for cid, col_name in col_map.items() if cid != 'TRD_DT' and col_name in df.columns]
    keep_cols = ['Period'] + val_cols
    df = df[[c for c in keep_cols if c in df.columns]]

    return {
        'df': df,
        'headers': header,
        'freq_typ': freq_typ,
        'val_cols': val_cols
    }


def get_consensus_timeseries_data(
    cmp_cd: str,
    freq_typ: str = 'Q',
    data_typ: str = '0',
    select_gsym: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Fetches consensus time-series data from FnGuide internal API.
    freq_typ: 'Q' (분기) or 'Y' (연간)
    data_typ: '0': 매출액, '1': 영업이익, '2': 당기순이익, '3': EPS, '4': PER, '5': PER(Fwd,12M)
    select_gsym: forecast target period (e.g. '202609' or '202612')
    """
    # 1. Fetch available target periods
    periods_url = f"{BASE_URL}/CompanyInfo/getCnsTrendYYMM?cmp_cd={cmp_cd}&consol_typ=C&freq_typ={freq_typ}"
    try:
        r_p = requests.get(periods_url, headers=HEADERS, timeout=10)
        p_json = r_p.json()
        periods = p_json.get('dataset', [])
    except Exception:
        periods = []

    if not periods:
        return None

    if not select_gsym:
        select_gsym = periods[0]['YYMM']

    # Find matching label for select_gsym
    period_label = select_gsym
    for p in periods:
        if p.get('YYMM') == select_gsym:
            period_label = p.get('YYMM_F', select_gsym)
            break

    # 2. Fetch time series chart data
    chart_url = (
        f"{BASE_URL}/CompanyInfo/getCnsTrendChart?"
        f"cmp_cd={cmp_cd}&consol_typ=C&freq_typ={freq_typ}&data_typ={data_typ}&select_gsym={select_gsym}"
    )
    try:
        r_c = requests.get(chart_url, headers=HEADERS, timeout=10)
        c_json = r_c.json()
    except Exception:
        return None

    dataset = c_json.get('dataset', {})
    data_points = dataset.get('data', [])
    header = dataset.get('header', [])

    if not data_points:
        return {
            'periods': periods,
            'selected_period': select_gsym,
            'period_label': period_label,
            'df': pd.DataFrame(),
            'headers': header
        }

    df = pd.DataFrame(data_points)
    # df has columns: TRD_DT, VAL_MAX, VAL_MIN, VAL_AVG
    return {
        'periods': periods,
        'selected_period': select_gsym,
        'period_label': period_label,
        'df': df,
        'headers': header
    }


def get_target_prices_data(cmp_cd: str) -> Dict[str, Any]:
    """
    Parses '증권사별 적정주가 & 투자의견' table from Consensus page.
    Returns Consensus average target price and DataFrame of brokerage estimates.
    """
    url = f"{BASE_URL}/CompanyInfo/Consensus?cmp_cd={cmp_cd}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')
    except Exception as e:
        return {'consensus_price': None, 'df': pd.DataFrame(), 'error': str(e)}

    # Find the target price table
    target_table = None
    for table in soup.find_all('table'):
        cap = table.find('caption')
        if cap and '증권사별' in cap.get_text():
            target_table = table
            break

    if not target_table:
        return {'consensus_price': None, 'df': pd.DataFrame()}

    tbody = target_table.find('tbody')
    if not tbody:
        return {'consensus_price': None, 'df': pd.DataFrame()}

    rows = tbody.find_all('tr')
    estimates: List[Dict[str, Any]] = []
    consensus_price: Optional[float] = None

    for row in rows:
        cells = [td.get_text(strip=True).replace(',', '') for td in row.find_all(['th', 'td'])]
        if not cells:
            continue

        org = cells[0]
        if org == 'Consensus':
            try:
                # Target price is cells[2]
                val_str = cells[2]
                if val_str and val_str != '-':
                    consensus_price = float(val_str)
            except Exception:
                pass
        else:
            if len(cells) >= 3:
                date_str = cells[1]
                target_str = cells[2]
                opinion = cells[3] if len(cells) > 3 else ''
                try:
                    if target_str and target_str != '-':
                        target_val = float(target_str)
                        if date_str:
                            estimates.append({
                                '추정기관': org,
                                '추정일자': date_str,
                                '적정주가': target_val,
                                '투자의견': opinion
                            })
                except Exception:
                    pass

    df = pd.DataFrame(estimates)
    if not df.empty:
        # Sort chronologically by date
        df['추정일자'] = pd.to_datetime(df['추정일자'])
        df = df.sort_values('추정일자').reset_index(drop=True)
        # Reformat date to YYYY/MM/DD string for chart display
        df['일자_str'] = df['추정일자'].dt.strftime('%Y/%m/%d')

    return {
        'consensus_price': consensus_price,
        'df': df
    }


def search_stocks_fnguide(query: str) -> List[Dict[str, str]]:
    """Searches stock codes and names via FnGuide autocomplete API."""
    if not query:
        return []
    url = f"{BASE_URL}/Common/getCompanySearch?data_typ=0&q={query}&limit=15"
    try:
        r = requests.get(url, headers=HEADERS, timeout=5)
        data = r.json()
        results = []
        for item in data:
            results.append({
                'code': item.get('cmp_cd', ''),
                'name': item.get('cmp_nm', ''),
                'market': item.get('mkt_nm', '')
            })
        return results
    except Exception:
        return []
