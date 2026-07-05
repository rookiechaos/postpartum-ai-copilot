# Postpartum AI Copilot

**Version 2.0.0 — Server-Client Architecture with Task Queue**

**Architecture:** Server-client separation, queue worker pattern, JWT authentication

An intelligent AI companion for new mothers — empathetic support, smart tracking, and evidence-informed guidance through postpartum and newborn stages.

---

## English

### Overview

Postpartum AI Copilot is an AI assistant platform designed for new mothers in the postpartum period. Our mission is to provide warm, reliable, and safe AI companionship when support is needed most — reducing cognitive load and making the postpartum journey more manageable.

### Core Principles

- **Empathetic companionship** — A warm, supportive AI companion layer
- **Safety first** — Multi-layer validation and content safety rules
- **Personalization** — Responses tailored to user data and preferences
- **Efficient response** — Async task queue for concurrency and horizontal scaling
- **Multilingual** — English and Japanese (日本語)

### Product Disclaimer

This product is a **companion and support tool**, not a medical product or device. It does not provide medical or psychological diagnosis, treatment, or clinical assessment, and is not a substitute for professional medical or mental health care. For medical or emergency situations, contact a healthcare provider or local emergency services.

### Features

#### AI Postpartum Assistant
- Smart chat for newborn care, recovery, and emotional support
- Context-aware guidance (baby age, birth type, feeding method)
- Night mode for urgent, simplified support
- Daily emotional check-ins with gentle support

#### Safety & Validation
- Automatic validation of AI suggestions
- Hard-coded content safety rules (companion tool, not medical certification)
- RAG references from trusted sources for content safety
- Red-flag detection for situations requiring medical attention

#### Personalization
- Response styles: concise / detailed / balanced
- Tone preferences: warm / professional / casual
- Detail levels: minimal / moderate / comprehensive
- Learning from user behavior over time

#### Smart Tracking
- Multi-dimensional tracking: feeding, diapers, sleep, mood, pumping
- AI pattern recognition and anomaly detection
- AI-generated summaries and insights
- Reference patterns for reassurance (not a substitute for professional judgment)

### Tech Stack

| Layer | Technologies |
|-------|-------------|
| Backend | Python 3.9+, FastAPI, SQLAlchemy, JWT, custom task queue |
| Frontend | React 18, Vite, i18next |
| AI | OpenAI, Anthropic Claude, Google Gemini |
| Infrastructure | Docker, PostgreSQL (prod), SQLite (dev) |

### Quick Start

See [docs/deployment/SETUP.md](docs/deployment/SETUP.md) for detailed setup.

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
mkdir -p ../do-not-upload/local ../do-not-upload/data ../do-not-upload/logs
cp env.example ../do-not-upload/local/backend.env
# Edit do-not-upload/local/backend.env with API keys
uvicorn main:app --reload
```

**Worker (separate terminal, from repo root):**
```bash
cd backend && source venv/bin/activate   # if using venv
cd ..
python workers/worker.py
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Docker:**
```bash
docker-compose up -d
docker-compose logs -f api
docker-compose logs -f worker
```

See [docs/deployment/DEPLOYMENT.md](docs/deployment/DEPLOYMENT.md) for deployment details.

### AI Providers

Set `AI_PROVIDER` in `backend/.env` to one of: `openai`, `claude`, `gemini`.

### Documentation

- [Project Structure](docs/PROJECT_STRUCTURE.md)
- [Code Organization](docs/CODE_ORGANIZATION.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Backend docs](docs/backend/)
- [Project docs](docs/)

### Project Structure

```
Postpartum/
├── backend/           # FastAPI API, services, models
├── workers/           # Background AI / notification workers
├── frontend/          # React web app
├── tests/             # Unit, integration, and internal tests
├── locales/           # Backend locale strings (en/ja)
├── docs/              # Project documentation
└── docker-compose.yml
```

### Testing

```bash
# Unit tests
python tests/run_tests.py

# Internal API tests (no server required)
python tests/integration/test_internal_api.py

# Worker tests
python tests/integration/test_worker.py

# Stress tests
python tests/integration/stress_test.py --endpoint /health --concurrent 100 --requests 100

# Shell-based integration tests (requires running backend + frontend)
./test.sh
```

See [docs/testing/TESTING.md](docs/testing/TESTING.md) for more.

### Local-only files (`do-not-upload/`)

Secrets, databases, logs, and vector stores live in [`do-not-upload/`](do-not-upload/README.md). This folder is **gitignored** and must not be pushed to GitHub. See [docs/GITHUB.md](docs/GITHUB.md) for publishing steps.

### Publishing to GitHub

1. Create a new repository on GitHub (empty, no README)
2. From the project root:

```bash
git init
git add .
git status   # confirm no secrets under do-not-upload/local/
git commit -m "Initial commit: Postpartum AI Copilot"
git branch -M main
git remote add origin https://github.com/YOUR_USER/YOUR_REPO.git
git push -u origin main
```

Full checklist: [docs/GITHUB.md](docs/GITHUB.md)

Before pushing, run `./check-privacy.sh` to scan tracked files for paths, secrets, and accidental staging.

### Safety & Ethics

- Not a medical diagnosis tool — provides general information only
- Always recommends consulting healthcare professionals for medical concerns
- AI responses include safety boundaries and red-flag warnings
- Emotional check-ins may escalate to human resources when needed

### License

[Apache License 2.0](LICENSE) — see [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

---

## 日本語 / Japanese

### 概要

Postpartum AI Copilot（産後AIコパイロット）は、産後の新しいお母さんのために設計されたAIアシスタントプラットフォームです。最もサポートが必要な時期に、温かく信頼でき安全なAI伴走を提供し、認知負荷を減らして産後の旅をより穏やかにすることを目指しています。

### 核心理念

- **共感的な伴走** — 温かく支援的なAIコンパニオン層
- **安全第一** — 多層検証とコンテンツ安全ルール
- **パーソナライズ** — ユーザーデータと好みに合わせた応答
- **効率的な応答** — 非同期タスクキューによる高い並行処理と水平スケール
- **多言語対応** — 英語と日本語

### 製品免責事項

本製品は**伴走・サポートツール**であり、医療製品・医療機器ではありません。医学的または心理学的な診断、治療、臨床評価を提供せず、専門的な医療またはメンタルヘルスケアの代替にはなりません。医療上または緊急の場合は、医療提供者または地域の緊急サービスに連絡してください。

### 主な機能

#### AI産後アシスタント
- 新生児ケア、回復、感情サポートのためのスマートチャット
- コンテキスト対応（赤ちゃんの月齢、出産方法、授乳方法）
- ナイトモード — 緊急時の簡潔なサポート
- 毎日の感情チェックイン

#### 安全と検証
- AI提案の自動検証
- ハードコードされたコンテンツ安全ルール
- 信頼できる情報源からのRAG参照
- 医療的な対応が必要な状況の危険信号検出

#### パーソナライズ
- 応答スタイル：簡潔 / 詳細 / バランス
- トーン：温かい / プロフェッショナル / カジュアル
- 詳細度：最小 / 中程度 / 包括的

#### スマート記録
- 授乳、おむつ、睡眠、気分、搾乳の多軸トラッキング
- AIパターン認識と異常検出
- AI生成のサマリーとインサイト

### 技術スタック

| レイヤー | 技術 |
|---------|------|
| バックエンド | Python 3.9+, FastAPI, SQLAlchemy, JWT, カスタムタスクキュー |
| フロントエンド | React 18, Vite, i18next |
| AI | OpenAI, Anthropic Claude, Google Gemini |
| インフラ | Docker, PostgreSQL（本番）, SQLite（開発） |

### クイックスタート

詳細は [docs/deployment/SETUP.md](docs/deployment/SETUP.md) を参照してください。

**バックエンド:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
mkdir -p ../do-not-upload/local ../do-not-upload/data ../do-not-upload/logs
cp env.example ../do-not-upload/local/backend.env
# do-not-upload/local/backend.env にAPIキーを記入
uvicorn main:app --reload
```

**ワーカー（別ターミナル、リポジトリルートから）:**
```bash
python workers/worker.py
```

**フロントエンド:**
```bash
cd frontend
npm install
npm run dev
```

**Docker:**
```bash
docker-compose up -d
```

### AIプロバイダー

`do-not-upload/local/backend.env` の `AI_PROVIDER` を `openai`、`claude`、`gemini` のいずれかに設定します。

### ローカル専用ファイル（`do-not-upload/`）

秘密情報・DB・ログは [`do-not-upload/`](../do-not-upload/README.md) に保存し、GitHubにはアップロードしません。公開手順は [docs/GITHUB.md](docs/GITHUB.md) を参照。

### ドキュメント

- [プロジェクト構造](docs/PROJECT_STRUCTURE.md)
- [アーキテクチャ](docs/ARCHITECTURE.md)
- [バックエンドドキュメント](docs/backend/)
- [プロジェクトドキュメント](docs/)

### テスト

```bash
# ユニットテスト
python tests/run_tests.py

# 内部 API テスト（サーバー不要）
python tests/integration/test_internal_api.py

# ワーカーテスト
python tests/integration/test_worker.py

# 統合テスト（バックエンド + フロントエンド起動が必要）
./test.sh
```

詳細は [docs/testing/TESTING.md](docs/testing/TESTING.md) を参照。

### 安全と倫理

- 医療診断ツールではありません — 一般的な情報のみ提供
- 医療上の懸念については常に医療専門家への相談を推奨
- AI応答には安全境界と危険信号警告を含む
- 必要に応じて人的リソースへのエスカレーション

### ライセンス

[Apache License 2.0](LICENSE) — 貢献方法は [CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。
