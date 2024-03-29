---
layout: page
title: Server
permalink: /server/
---

## Jageocoder-server

[jageocoder-server](https://github.com/t-sagara/jageocoder-server) は
住所の検索・解析や、住所を含む CSV ファイルの
一括ジオコーディング機能（住所に対応する経緯度や市区町村コードなどの
列を追加する機能）を提供するウェブアプリケーションです。

まずは [デモンストレーション](https://jageocoder.info-proto.com/) で
何ができるのかお試しください。

Google Maps API 等のウェブサービスと比較すると、次のような特徴があります。

<u>メリット</u>

- 利用者側でサーバを立ち上げるので、情報漏洩などのセキュリティリスクを大幅に低減できます。
- 利用は無料で件数制限などもありません。
- サーバ構築時にはインターネット接続が必要ですが、一度構築すればオフライン環境でも利用できます（背景地図は利用できません）。

<u>デメリット</u>

- 物理的にサーバマシンを用意する必要があります。Windows PCでもOKです。
- 住所データファイルもサーバ上にインストールするため、住所データはデータファイルを差し替えないと更新されません。
- 住所データファイルはオープンデータから作成していますので、
  有償サービスに比べると精度や網羅している範囲が限定されています。
  また、データ提供元の利用条件には従ってください（成果物を公開する際の出典の明示など）。

# サーバ導入手順

例として、 Windows PC に Docker Desktop を利用して jageocoder-server を立ち上げる手順を説明します。

<div>
  <video src="/jageocoder/assets/jageocoder-server-windows-install.m4v" height="400" controls muted style="border: 1px solid #000;" />
</div>

<u>Docker Desktop のインストール</u>

- [Docker 公式ドキュメント](https://docs.docker.jp/docker-for-windows/install.html) に従い、 Windows 用の Docker Desktop をインストールしてください。

<u>jageocoder-server のダウンロードと配置</u>

- [ここから](https://github.com/t-sagara/jageocoder-server/archive/refs/heads/main.zip)最新のコードをダウンロードします。
- ファイルエクスプローラーなどでダウンロードした
  `jageocoder-server-main.zip` ファイルを展開します。
- [住所データファイル一覧](https://www.info-proto.com/static/jageocoder/latest) から適切なファイルをダウンロードします。
- ダウンロードした住所データファイルを、`jageocoder-server-main.zip` を展開したフォルダ内の `data` フォルダにコピーします。

<u>Docker Desktop で起動</u>

- PowerShell を開きます。
- `jageocoder-server-main.zip` を展開したフォルダに移動します。

        > cd c:\Users\xxxx\Downloads\jageocoder-server-main\jageocoder-server-main

- Docker イメージを作成します。

        > docker compose build

- Docker コンテナを起動します。

        > docker compose up -d

    初回起動時は、住所データファイルから辞書データをインストールするため、時間がかかります。
    `data\init.log` に途中結果が出力されるので、 `Starting server process...`
    と出力されるまでのんびりお待ちください。

        > Get-Content -Wait -Tail 10 -Path data\init.log

- ブラウザでアクセスします。

    ブラウザを起動して、 http://localhost:5000/ を開いてください。

- Docker コンテナを終了します。

    システムを停止する場合は Docker コンテナを停止します。
    
        > docker compose down

    インストールした辞書データは Docker Volume に保存されているので、
    二回目以降の実行時はコンテナを起動すればすぐに利用できます。

        > docker compose up -d

- 辞書を更新するには、 `data` フォルダに新しい辞書ファイルを置いてから、
    コンテナを再起動してください。自動的に辞書のインストールが始まります。

        > docker compose down
        > docker compose up -d
