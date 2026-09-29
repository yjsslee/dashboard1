import os
from datetime import date, timedelta

import pandas as pd
import requests
import streamlit as st


# 키움 REST API 모의투자 서버
KIWOOM_HOST = "https://mockapi.kiwoom.com"
STOCK_CODE = "034020"  # 두산에너빌리티
STOCK_NAME = "두산에너빌리티"


st.set_page_config(
    page_title="두산에너빌리티 6개월 차트",
    page_icon="📈",
    layout="wide",
)

st.title("📈 두산에너빌리티 6개월 주가 차트")
st.caption("키움증권 REST API 모의투자 서버 · 수정주가 적용 · 일봉")


def get_secret(name: str) -> str:
    """Streamlit secrets 또는 환경변수에서 인증정보를 읽습니다."""
    try:
        value = st.secrets.get(name, "")
    except Exception:
        value = ""
    return value or os.getenv(name, "")


# GitHub에는 API Key/Secret을 저장하지 않습니다.
app_key = get_secret("KIWOOM_APP_KEY")
secret_key = get_secret("KIWOOM_APP_SECRET")

with st.sidebar:
    st.header("API 설정")
    st.write("GitHub에 인증정보를 저장하지 않도록 구성했습니다.")
    if not app_key:
        app_key = st.text_input("App Key", type="password")
    if not secret_key:
        secret_key = st.text_input("App Secret", type="password")

    period = st.selectbox("조회 기간", ["6개월"], index=0)
    refresh = st.button("🔄 차트 새로고침", use_container_width=True)


@st.cache_data(ttl=60 * 30, show_spinner=False)
def issue_access_token(app_key_value: str, secret_key_value: str) -> str:
    url = f"{KIWOOM_HOST}/oauth2/token"
    headers = {"Content-Type": "application/json;charset=UTF-8"}
    body = {
        "grant_type": "client_credentials",
        "appkey": app_key_value,
        "secretkey": secret_key_value,
    }

    response = requests.post(url, headers=headers, json=body, timeout=20)
    response.raise_for_status()
    data = response.json()
    token = data.get("token")
    if not token:
        raise RuntimeError(data.get("return_msg", "접근토큰을 받지 못했습니다."))
    return token


def fetch_daily_chart(token: str, stock_code: str, base_date: str) -> pd.DataFrame:
    """ka10081 일봉 차트를 연속조회하여 가져옵니다."""
    url = f"{KIWOOM_HOST}/api/dostk/chart"
    rows = []
    cont_yn = "N"
    next_key = ""

    # 6개월이면 통상 한 번의 조회로 충분하지만, 연속조회 응답도 처리합니다.
    for _ in range(5):
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": f"Bearer {token}",
            "cont-yn": cont_yn,
            "next-key": next_key,
            "api-id": "ka10081",
        }
        body = {
            "stk_cd": stock_code,
            "base_dt": base_date,
            "upd_stkpc_tp": "1",  # 수정주가 적용
        }

        response = requests.post(url, headers=headers, json=body, timeout=20)
        response.raise_for_status()
        data = response.json()

        if str(data.get("return_code", "0")) not in ("0", "None"):
            raise RuntimeError(data.get("return_msg", str(data)))

        rows.extend(data.get("stk_dt_pole_chart_qry", []))

        cont_yn = response.headers.get("cont-yn", "N").upper()
        next_key = response.headers.get("next-key", "")
        if cont_yn != "Y" or not next_key:
            break

    if not rows:
        raise RuntimeError("차트 데이터가 없습니다. 키움 API 설정과 종목코드를 확인해 주세요.")

    df = pd.DataFrame(rows)
    required = ["dt", "open_pric", "high_pric", "low_pric", "cur_prc", "trde_qty"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise RuntimeError(f"API 응답에 필요한 항목이 없습니다: {missing}")

    # 키움 API의 가격 필드는 부호가 포함될 수 있으므로 절댓값으로 가격을 정리합니다.
    for col in ["open_pric", "high_pric", "low_pric", "cur_prc", "trde_qty"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").abs()

    df["date"] = pd.to_datetime(df["dt"], format="%Y%m%d", errors="coerce")
    df = df.dropna(subset=["date", "cur_prc"]).copy()
    df = df.sort_values("date").drop_duplicates("date").reset_index(drop=True)

    # 정확히 최근 6개월만 표시
    cutoff = pd.Timestamp(date.today() - timedelta(days=183))
    df = df[df["date"] >= cutoff].copy()
    return df


if not app_key or not secret_key:
    st.info("왼쪽 사이드바에 키움증권 모의투자 App Key와 App Secret을 입력하거나 Streamlit Secrets에 등록해 주세요.")
    st.stop()

try:
    with st.spinner("키움증권에서 두산에너빌리티 6개월 데이터를 가져오는 중입니다..."):
        token = issue_access_token(app_key, secret_key)
        df = fetch_daily_chart(token, STOCK_CODE, date.today().strftime("%Y%m%d"))

    latest = df.iloc[-1]
    previous = df.iloc[-2] if len(df) >= 2 else latest
    change = latest["cur_prc"] - previous["cur_prc"]
    change_pct = (change / previous["cur_prc"] * 100) if previous["cur_prc"] else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("최근 종가", f"{latest['cur_prc']:,.0f}원", f"{change:+,.0f}원")
    col2.metric("등락률", f"{change_pct:+.2f}%")
    col3.metric("조회 시작일", df["date"].min().strftime("%Y-%m-%d"))
    col4.metric("조회 종료일", df["date"].max().strftime("%Y-%m-%d"))

    st.subheader(f"{STOCK_NAME} ({STOCK_CODE})")

    chart_df = df.set_index("date")[["cur_prc"]].rename(columns={"cur_prc": "종가"})
    st.line_chart(chart_df, y="종가", height=520, use_container_width=True)

    with st.expander("최근 거래일 데이터 보기"):
        display_df = df[["date", "open_pric", "high_pric", "low_pric", "cur_prc", "trde_qty"]].copy()
        display_df.columns = ["일자", "시가", "고가", "저가", "종가", "거래량"]
        display_df["일자"] = display_df["일자"].dt.strftime("%Y-%m-%d")
        st.dataframe(display_df.tail(20).sort_values("일자", ascending=False), use_container_width=True, hide_index=True)

    st.caption("※ 모의투자 서버의 조회 데이터이며 실제 투자 판단의 근거로 사용하기 전에 데이터와 API 응답을 확인하세요.")

except requests.HTTPError as exc:
    st.error(f"키움 API HTTP 오류: {exc}")
except Exception as exc:
    st.error(f"데이터 조회에 실패했습니다: {exc}")
    st.caption("App Key/App Secret, 키움 API 사용신청 및 허용 IP 등록 상태를 확인해 주세요.")
