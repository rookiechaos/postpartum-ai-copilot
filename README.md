# Postpartum AI Copilot · 産後のくらしサポート

日本の産後家庭と、小さな助産院・地域の支援拠点のための、記録と相談のアプリです。
AIに詳しくなくても、授乳を記録する、困りごとを整理する、相談先を探すところから始められます。

**現在は小規模な試行向けです。** AIの回答には誤りが含まれます。診断・治療・臨床的なリスク判定・救急対応は行いません。
日本で救急車が必要な場合は **119** に直接連絡してください。

## 二つの入口

| 入口 | 対象 | できること |
| --- | --- | --- |
| `/` | 初めての方 | 家庭用・機関用の選択、日本の相談先の確認 |
| `/family` | 産後家庭・家族 | 授乳・おむつ・赤ちゃんの睡眠・搾乳・自分の気分や回復の記録、場面から始めるAI相談、相談用の記録のプレビュー |
| `/organization` | 小さな助産院・地域支援機関 | 家庭向けリンクの案内、機関の公開連絡先・受付時間・地域の資料の編集 |

### ご家庭で使う

1. 家庭用の入口で、ご自身のアカウントを作成します。家族でパスワードを共有しないでください。
2. 最初の案内は2ステップです。赤ちゃんの呼び名・月齢などはすべて任意で、後から設定できます。
3. ホームの「記録する」「困りごとを相談する」「相談先を探す」から始めます。

記録の保存・読み込みだけでは、入力を外部AIへ送信しません。相談や分析などのAI機能は、外部サービスでの処理について確認してから送信します。
場面のボタンは質問の下書きを作るだけで、自動送信しません。日時と「今日」の集計は日本時間（JST）です。

相談用の記録は、直近7日間の赤ちゃんのケアをテキストでまとめます。**自分の気分・回復の記録と自由記述のメモは初期状態で除外**します。
必要な項目を選び、プレビューを編集してからダウンロードしてください。チャットやアカウント情報は含めず、機関へ自動送信しません。
ダウンロードして相手に渡したコピーをアプリから撤回することはできません。

### 小さな機関で使う

機関の画面で扱うのは、**この設置先の公開案内**です。家庭のチャット・気分・健康記録を一覧表示する機能や、自動で相談を受け付ける機能はありません。
案内リンクを利用しても、家庭の情報が機関に共有されることはありません。

- 運営者が実際のアカウントIDに編集権限を付与します。入口の選択、登録メールアドレス、新規登録だけでは権限を取得できません。
- 機関名、地域、業務用連絡先、受付時間、保存期間・削除依頼の案内を登録できます。
- 地域の資料やサービスは最大10件。HTTPSの情報元リンク、説明、受付時間、実際に確認した日を登録できます。
- 登録した案内は、未ログインの方にも公開されます。家庭の個人情報を記入しないでください。

**1回の設置につき1機関・1地域の案内**を想定しています。複数機関のデータを同じ管理画面で分離する仕組みは未実装です。

## 日本の相談先

相談先の基本情報はログインやAIの応答を必要としません。オフライン用ページにも全国向けの案内を掲載しています。
地域の案内の取得、記録の保存、AI相談にはネット接続が必要です。

- **119**：日本の救急・消防。救急対応が必要な場合、AIの返答を待たないでください。
- **#8000**：子ども医療電話相談。受付時間は都道府県により異なります。[厚生労働省の案内](https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/newpage_55223.html)
- **#7119**：受診や救急車について迷うときの相談。実施地域・対象年齢・時間を確認してください。[総務省消防庁の案内](https://www.fdma.go.jp/mission/enrichment/appropriate/appropriate007.html)

地域の産後ケアや保健相談は、自治体・提供機関の最新の案内を登録してください。[こども家庭庁の母子保健情報](https://www.cfa.go.jp/policies/boshihoken)
情報の確認日は、医療専門家による監修や、AI回答の正しさを保証するものではありません。

## データの取り扱い

| データ | 取り扱い |
| --- | --- |
| 個人のプロフィール・ケアの記録 | 認証された本人のアカウントに保存。機関用の編集権限でも他人の記録にはアクセスできません |
| AIへの入力と関連するコンテキスト | 運営者が設定した外部AIプロバイダーに送信されます |
| 機関の連絡先・地域の資料 | 公開情報。ログインなしで取得できます |
| 相談用にダウンロードしたファイル | 利用者が共有先と保管方法を判断します |

**ローカルに設置しても、外部AIへの送信は発生します。完全オフラインのAIアプリではありません。**
運営者は実際の保存期間、AI事業者のデータ処理条件、問い合わせ先、削除依頼への対応方法を説明してください。
保存期間の案内を入力するだけでは自動削除は実行されません。アプリ内の完全なアカウント削除・パスワード再設定・機関内の複数担当者管理は未実装です。
生成AIと個人情報については、[個人情報保護委員会の注意喚起](https://www.ppc.go.jp/news/careful_information/230602_AI_utilize_alert/)も参照してください。

## English overview

Postpartum AI Copilot supports small Japanese pilots through two entrances:

- **Families:** simple care records, guided questions, Japanese support contacts and a reviewed text export for care conversations.
- **Small organizations:** a separately authorized workspace for public contact details and local resources. Staff access does not grant access to families’ private records.

The interface supports Japanese and English. Support contacts target **Japan in either language**.
AI responses are labeled as generated content; rule checks and heuristic scores are not presented as medical certification or clinical confidence.
This is a care companion for everyday support, not a diagnosis, treatment or emergency-response service.

## Run locally · 運営者向けセットアップ

Families do not need API keys or model settings. The operator configures the server once.
You need Python, Node.js/npm, and a configured AI provider for AI features. Dependencies are listed in
[`backend/requirements.txt`](backend/requirements.txt) and [`frontend/package.json`](frontend/package.json).

### 1. Backend

Run from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
cp -n do-not-upload/local/backend.env.example do-not-upload/local/backend.env
python -c 'import secrets; print(secrets.token_hex(32))'
```

Edit the ignored `do-not-upload/local/backend.env`: replace `JWT_SECRET_KEY` with a new random secret and configure your chosen provider's API key.
Do not reuse the example values. Set `AI_PROVIDER` to `openai`, `claude` or `gemini`; use the corresponding API-key field.
Then start the API:

```bash
python -m uvicorn main:app --app-dir backend --reload
```

The default local API address is `http://localhost:8000`. Data, logs and vector stores live under the ignored `do-not-upload/` directory.

### 2. Worker

In a second terminal, from the repository root with the same virtual environment:

```bash
source .venv/bin/activate
python workers/worker.py
```

The default `ASYNC_MODE=true` uses this worker for chat and tracking analysis. Use the same database and provider configuration for the API and worker.

### 3. Frontend

In another terminal, from the repository root:

```bash
cd frontend
npm install
cp -n .env.example .env.local
npm run dev
```

Open `http://localhost:3000`, then choose `/family` or `/organization`.
For deployment, set `VITE_API_BASE_URL` to the browser-accessible API URL and rebuild the frontend.
`VITE_ASYNC_MODE` must match the backend's `ASYNC_MODE`.

### 4. Grant organization access

1. Create and sign in to the intended staff account at `/organization`.
2. Confirm who controls that account. The access-required screen shows its server-generated account ID.
3. Put the actual ID in `INSTITUTION_USER_IDS` in the ignored backend environment file; separate multiple IDs with commas.
4. Restart the API. The staff member can now edit the deployment's public directory.

`INSTITUTION_USER_IDS` is separate from `ADMIN_USER_IDS`. It does not grant system administrator privileges or access to other users' records.
Remove an ID and restart the API to revoke directory editing access. All configured editors manage the same public directory.

### Docker / hosted deployment

```bash
docker compose --env-file do-not-upload/local/backend.env up -d --build
```

Compose starts the API, worker and PostgreSQL; it does **not** serve the frontend. Build and host the frontend separately:

```bash
cd frontend
npm run build
```

Configure your web server to serve `index.html` for `/family` and `/organization`, use HTTPS, and set the API's `CORS_ORIGINS` to the actual frontend origin.
For real pilots, configure non-example database credentials, back up the database and test restoration. AI spending limits and account recovery remain operator responsibilities.
See [setup](docs/deployment/SETUP.md), [deployment](docs/deployment/DEPLOYMENT.md) and the [Japan pilot guide](docs/product/JAPAN_PILOT.md).

## Architecture and APIs

React/Vite/i18next → FastAPI → SQLAlchemy (SQLite locally, PostgreSQL with Compose).
Background workers process AI tasks through OpenAI, Claude or Gemini.

| Endpoint | Access | Purpose |
| --- | --- | --- |
| `GET /api/pilot` | Public | Public contact details and local resources; no family data |
| `GET /api/pilot/organization` | Institution allowlist | Load directory for editing |
| `POST /api/pilot/organization` | Institution allowlist | Validate and save public information |
| Existing tracking / context / chat APIs | Authenticated owner | Personal data and AI requests |

The `pilot_profiles` table is added on startup through the existing table-initialization mechanism. Existing account and tracking tables are unchanged.

## Verification

```bash
python -W ignore tests/regression/japan_pilot_checks.py
node --test tests/regression/japan_pilot.test.cjs
python -W ignore tests/regression/security_checks.py
python -W ignore tests/regression/followup_checks.py
python -W ignore tests/regression/review_235a4c9_checks.py
node --test tests/regression/frontend_security.test.cjs tests/regression/frontend_tasks.test.cjs tests/regression/frontend_review.test.cjs
node --test tests/regression/review_3961c93.test.cjs
python -m unittest discover -s tests/privacy -v
./check-privacy.sh
```

The offline regression scripts use controlled authentication/provider fixtures; they do not validate live AI providers or clinical accuracy.
The JSX harness executes transpiled component handlers with controlled React hooks. If TypeScript is already installed elsewhere, set `REVIEW_TYPESCRIPT_PATH` to its module path.
Production build, browser and full integration checks require their corresponding installed dependencies. See the [pilot guide](docs/product/JAPAN_PILOT.md) for validation scope and manual acceptance steps.

## Documentation and license

- [Japan pilot guide](docs/product/JAPAN_PILOT.md): scope, access, privacy and acceptance scenarios.
- [Architecture](docs/ARCHITECTURE.md) · [Project structure](docs/PROJECT_STRUCTURE.md) · [Testing](docs/testing/TESTING.md).
- [Security review fixes](docs/security/SECURITY_FIXES_2026-10-10.md) · [Local-only files](do-not-upload/README.md).
- Run `./check-privacy.sh` before publishing. Secrets, live contact information and real family data belong in ignored runtime files, not Git.
- [Apache License 2.0](LICENSE) · [Contributing](CONTRIBUTING.md).
