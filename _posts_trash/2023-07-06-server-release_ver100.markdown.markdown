---
layout: post
title:  "Jageocoder-server 公開"
date:   2023-07-06 12:40:00 +0900
categories: Server
---

*jageocoder-server v1.0.0* をリリースしました。

Jageocoder はアプリケーションに組み込むことを想定し、
プログラマ向けのライブラリとして提供してきました。
そのため、プログラムを書かないと利用できないという制約があり、
一般の利用には適していないという問題があります。

そこでジオコーディングを手軽に利用できるように、
Docker で動作するウェブアプリケーションを開発しました。

詳細は [jageocoder-server](https://github.com/t-sagara/jageocoder-server) の GitHub リポジトリをご参照ください。

以下の機能をローカル環境で利用できます。
- 任意の住所文字列を解析する「住所解析機能」
- CSV ファイルの住所列を解析し、経緯度や自治体コードなどを付与する
  「CSV変換機能」
- JSON で通信して住所解析ができる「WebAPI サービス機能」
