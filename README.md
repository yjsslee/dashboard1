# 두산에너빌리티 6개월 주가 차트

키움증권 REST API **모의투자 서버**의 `ka10081` 주식일봉차트조회요청을 이용하여 두산에너빌리티(034020)의 최근 6개월 일봉 차트를 Streamlit으로 표시합니다.

## 보안

App Key와 App Secret은 GitHub 저장소에 저장하지 않습니다.

Streamlit Cloud를 사용하는 경우 앱의 **Settings → Secrets**에 다음과 같이 등록하세요.

```toml
KIWOOM_APP_KEY = "여기에_모의투자_App_Key"
KIWOOM_APP_SECRET = "여기에_모의투자_App_Secret"
```

로컬에서 테스트할 때는 환경변수로도 설정할 수 있습니다. Secrets/환경변수가 없으면 앱의 사이드바에서 실행할 때 직접 입력할 수 있습니다.

## 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 사용 API

- 모의투자 서버: `https://mockapi.kiwoom.com`
- 접근토큰: `POST /oauth2/token`
- 일봉 차트: `POST /api/dostk/chart`
- API ID: `ka10081`
- 종목: 두산에너빌리티 `034020`
- 수정주가: 적용 (`upd_stkpc_tp=1`)

키움증권의 모의투자 App Key와 실전투자 App Key는 별도로 관리되므로 모의투자용 인증정보를 사용해야 합니다.
