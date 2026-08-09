# Daily Timeline

1日の行動を、途切れないタイムラインとして記録するためのシンプルなWebアプリです。

新しいActivityを開始すると、直前のActivityが自動的に終了します。手動予定も同じタイムライン上に表示できるため、「予定」と「実績」を並べて確認できます。

## Features

- 現在のActivityと経過時間を表示
- 新しいActivity開始時に直前のActivityを自動終了
- Quick Start
- Today's TODO
- 24時間のToday Timeline
- 手動Scheduleの追加
- Scheduleと実績Activityの重複を横並び表示
- Activity / Scheduleの名前・日時編集
- Schedule / TODOの削除
- Activity Log
- Dark / Lightテーマ
- Glass / Flat / Neumorphism
- Accent Color変更
- Time Zone設定

## Requirements

- Python 3
- Git

## Quick Start

### 1. Clone

```bash
git clone https://github.com/Ponzou2002/Daily-timeline.git
cd Daily-timeline
```

### 2. 仮想環境を作成

#### Windows

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

PowerShellの実行ポリシーでActivateできない場合は、Command Promptで以下を実行できます。

```cmd
venv\Scripts\activate.bat
```

#### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. 依存パッケージをインストール

```bash
python -m pip install -r requirements.txt
```

### 4. 起動

```bash
python -m flask --app app run --host 0.0.0.0 --port 8000
```

同じPCのブラウザから以下を開きます。

```text
http://127.0.0.1:8000
```

同じLAN内の別端末から使う場合は、起動しているPCのIPアドレスを使います。

```text
http://<PCのIPアドレス>:8000
```

## LinuxでGunicornを使う場合

`requirements.txt` はWindows以外ではGunicornもインストールします。

```bash
gunicorn --bind 0.0.0.0:8000 app:app
```

常時稼働させる場合は、systemdやリバースプロキシなどを別途設定してください。

## Data

Activity、TODO、Schedule、SettingsはSQLiteに保存されます。

```text
daily_timeline.db
```

DBファイルは初回起動時に自動作成されます。

`daily_timeline.db` はGitの管理対象外です。記録をバックアップしたい場合は、このファイルをコピーしてください。

## Update

最新版を取得する場合は、リポジトリ内で以下を実行します。

```bash
git pull
python -m pip install -r requirements.txt
```

その後、アプリを再起動してください。

## Notes

- 現在は個人利用・小規模利用を想定しています。
- 認証機能はありません。
- インターネットへ直接公開する用途は想定していません。
- 外部公開する場合は、HTTPS・認証・ファイアウォール・リバースプロキシ等を別途構成してください。
- Flask標準の開発サーバーは、信頼できるローカル環境やLAN内での利用を想定しています。

## License

This project is licensed under the PolyForm Noncommercial License 1.0.0.

Personal and other noncommercial use, modification, and redistribution are permitted under the license. Commercial use is not permitted under this license and requires separate permission from the author.

See the `LICENSE` file for details.
