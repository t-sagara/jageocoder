---
# Feel free to add content and custom Front Matter to this file.
# To modify the layout, see https://jekyllrb.com/docs/themes/#overriding-theme-defaults

layout: home
---

<div>
  <video src="/jageocoder/assets/jageocoder_v201.mp4" height="400"
  controls autoplay muted loop style="border: 1px solid #000;" />
</div>

[English Document](/jageocoder/about/)

**jageocoder** は日本の住所を解析し、経緯度や郵便番号などを取得する
Python パッケージです。

- [Jageocoder ドキュメント](https://jageocoder.readthedocs.io/ja/latest/)
    - インストール手順や使い方、APIリファレンスなどの技術文書があります。
    - 過去のバージョンのドキュメントも確認できます。
- [デモンストレーション](https://jageocoder.info-proto.com/)
    - ジオコーディング機能を確認できるウェブアプリです。
    - 利用制限がありますが WebAPI も利用できます。
- [コード GitHub](https://github.com/t-sagara/jageocoder)
    - Python パッケージとして利用するためのコードをダウンロードできます。
    - 不具合報告もこちらにお願いします。
- [住所データベースファイル](https://www.info-proto.com/static/jageocoder/)
    - 住所データベースファイルの置き場です。
    - v1 用は[こちら](https://www.info-proto.com/static/jageocoder/latest/v1/)から、
      v2 用は[こちら](https://www.info-proto.com/static/jageocoder/latest/v2/)から
      ダウンロードしてください。
    - ファイル名は `<レベル>_<範囲>_<バージョン>.zip` というフォーマットです。
    - レベルが `gaiku_` ならば街区レベル（番・番地まで）、`jukyo_` ならば
      住居表示レベル（号・枝番まで）です。
    - 範囲が `all` ならば全国です。数字の場合は
      [都道府県コード](https://nlftp.mlit.go.jp/ksj/gml/codelist/PrefCd.html)
      です。
    - バージョンは `v14` ならば v1.4、 `v20` ならば v2.0 です。
      v14 のファイルは v1.3 でも利用できます。