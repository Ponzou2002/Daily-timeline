# Daily Timeline Development Guide

このドキュメントは、Daily TimelineをForkして改造する場合や、AIに開発を依頼する場合に、プロジェクト全体の構成を素早く把握するための簡易ガイドです。

利用方法は `README.md` を参照してください。

## Project Principle

Daily Timelineの基本理念は、**「今何をやっているかをはっきり自覚する」**ことです。

Activityは成果や生産性を評価するためではなく、その時間に実際に何をしていたかを連続して記録するためのものです。

- 新しいActivityを開始すると直前のActivityが終了する
- 原則としてStopボタンを置かず、休憩や睡眠もActivityとして扱う
- ScheduleやTODOは補助機能であり、アプリ全体を予定管理ツールへ寄せすぎない
- 入力の手間を増やしすぎない

機能追加時は、この方向性を大きく崩していないか確認してください。

## Stack

- Python / Flask
- SQLite
- Jinja2 templates
- Vanilla JavaScript
- CSS

フロントエンドのビルド工程はありません。

## Repository Structure

```text
Daily-timeline/
├─ app.py
├─ templates/
│  └─ index.html
├─ static/
│  ├─ style.css
│  ├─ dashboard.css
│  ├─ timeline.css
│  ├─ theme.css
│  ├─ navigation.css
│  ├─ timezone-window.css
│  ├─ schedule.css
│  ├─ timeline-date.css
│  ├─ timezone-window.js
│  └─ images/
│     └─ timezone/
├─ requirements.txt
├─ README.md
├─ DEVELOPMENT.md
├─ LICENSE
└─ daily_timeline.db    # 実行時に作成 / Git管理外
```

## Main Files

### `app.py`

Flaskアプリ本体です。

主に次を担当します。

- SQLiteの初期化と読み書き
- Activity / TODO / Schedule / Settingsのルート
- Time Zone変換
- Timelineへ表示するデータの計算
- Timelineの日付切り替え
- 編集用JSONの生成

バックエンドの挙動や保存データを変更する場合は、まずこのファイルを確認してください。

### `templates/index.html`

現在のメイン画面を構成するJinjaテンプレートです。

- Current Activity
- Next Action / Quick Start
- Today's TODO
- Timeline
- Schedule追加ダイアログ
- Activity Log
- Settings / Navigation

などの基本DOMを持ちます。

一部のフロントエンド処理もこのテンプレート内のJavaScriptにあります。

### `static/timezone-window.js`

現在もっとも多くのフロントエンド処理を担当しているファイルです。

- Time Zone時計の背景切り替え
- Activity / Scheduleの重なりレイアウト
- Timelineの日付ナビゲーション
- Activity / Schedule編集UI
- Schedule / TODOの削除ボタン追加

Timeline周辺を変更する場合は、`app.py` と合わせて確認してください。

将来的には責務ごとにJavaScriptを分割する余地があります。

### CSS

- `style.css` — 全体の基本スタイル
- `dashboard.css` — メイン画面・パネル配置
- `timeline.css` — Activity Timeline本体
- `theme.css` — Dark / Light、Texture、Accent Colorなどのテーマ変数
- `navigation.css` — メニューやナビゲーション周辺
- `timezone-window.css` — Time Zone時計の「窓」表示
- `schedule.css` — Schedule、Timeline共有レーン、編集UI、削除UI
- `timeline-date.css` — Timelineの日付切り替えUI

テーマ対応のUIを追加するときは、固定色を増やすより `theme.css` のセマンティック変数を優先してください。

## Database

SQLiteの `daily_timeline.db` を使用します。

主なテーブルは次の4つです。

```text
activities    実際のActivity記録
todos         Today's TODO
plans         手動Schedule
app_settings  Theme / Time Zoneなどの設定
```

`daily_timeline.db` は `.gitignore` の対象です。ForkやCloneごとに独立したDBが作成されます。

## Local Development

```bash
git clone <your fork URL>
cd Daily-timeline
python -m venv venv
```

仮想環境を有効化したあと、

```bash
python -m pip install -r requirements.txt
python -m flask --app app run --host 0.0.0.0 --port 8000
```

で起動できます。

通常の開発では `http://127.0.0.1:8000` を開いて確認します。

## Notes for AI-assisted Development

AIへ変更を依頼する場合は、少なくとも次を共有すると安全です。

- この `DEVELOPMENT.md`
- 変更対象に近いファイル
- 既存機能を残すこと
- Daily Timelineの基本理念

特にTimeline周辺はバックエンドとJavaScriptの両方で計算しています。片側だけを変更すると表示・編集データ・レーン配置がずれる可能性があります。

既存ファイルを大きく書き直すより、現在の挙動を確認して必要な範囲だけ変更する方針を推奨します。

また、次はリポジトリへコミットしないでください。

- `daily_timeline.db`
- APIキー
- OAuth Client Secret
- パスワードやトークン
- 個人環境固有の秘密情報
