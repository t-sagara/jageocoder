---
layout: page
title: Server
permalink: /server/
---

# 住所ジオコーディングサーバ jageocoder-server

[jageocoder-server](https://github.com/t-sagara/jageocoder-server) は
住所の検索・解析や、住所を含む CSV ファイルの
一括ジオコーディング機能（住所に対応する経緯度や市区町村コードなどの
列を追加する機能）を提供するウェブアプリケーションです。

まずは [デモンストレーション](https://jageocoder.info-proto.com/) で
何ができるのかお試しください。

Google Maps API 等のウェブサービスと比較すると、次のような特徴があります。

<u>メリット</u>

- 利用者側でサーバを立ち上げるので、情報漏洩などのセキュリティリスクを
  大幅に低減できます。
- 利用は無料で件数制限などもありません。
- サーバ構築時にはインターネット接続が必要ですが、一度構築すれば
  オフライン環境でも利用できます（背景地図は利用できません）。

<u>デメリット</u>

- 物理的にサーバマシンを用意する必要があります。Windows PCでもOKです。
- 住所データファイルもサーバ上にインストールするため、住所データは
  データファイルを差し替えないと更新されません。
- 住所データファイルはオープンデータから作成していますので、
  提供元の利用条件には従ってください（成果物を公開する際の出典の明示など）。

# サーバ導入手順

例として、 Windows PC に Docker Desktop を利用して
jageocoder-server を立ち上げる手順を説明します。

<u>Docker Desktop のインストール</u>

- [Docker 公式ドキュメント](https://docs.docker.jp/docker-for-windows/install.html) に従い、 Windows 用の Docker Desktop をインストールしてください。

<u>jageocoder-server のダウンロードと配置</u>

- [ここから](https://github.com/t-sagara/jageocoder-server/archive/refs/heads/main.zip)最新のコードをダウンロードします。
- ファイルエクスプローラーなどでダウンロードした
  `jageocoder-server-main.zip` ファイルを展開します。
- [住所データファイル一覧](https://www.info-proto.com/static/jageocoder/latest/v2/) から適切なファイルをダウンロードします。
東京都の住所しか扱わないならば `jukyo_13_v20.zip`、複数の都道府県の
住所を扱うならば `jukyo_all_v20.zip` のように選択してください。
- ダウンロードした住所データファイルを、`jageocoder-server-main.zip`
を展開したフォルダ内の `data` フォルダにコピーします。

<u>Docker Desktop で起動</u>

- PowerShell を開きます。
- `jageocoder-server-main.zip` を展開したフォルダに移動します。

        > cd c:\Users\xxxx\Downloads\jageocoder-server-main\jageocoder-server-main

- Docker イメージを作成します。

        > docker compose build

- Docker コンテナを起動します。

        > docker compose up -d

    初回起動時は、住所データファイルを展開してインデックスを
    構築するため、時間がかかります。`data\init.log` に
    途中結果が出力されるので、 `All done.` と出力されるまで
    のんびりお待ちください。

        > Get-Content -Wait -Tail 10 -Path data\init.log

- ブラウザでアクセスします。

    ブラウザを起動して、 http://localhost:5000/ を開いてください。

- Docker コンテナを終了します。

    システムを停止する場合は Docker コンテナを停止します。
    
        > docker compose down

