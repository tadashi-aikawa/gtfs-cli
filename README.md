gtfsjp-cli
==========

**⚠ 本プロジェクトはお試し版であり、開発中です**

[GTFS-JP]に準拠したデータを操作するCLIです。

[GTFS-JP]: https://www.gtfs.jp/developpers-guide/format-reference.html

## デモ

[インストールから実行までのデモ動画](https://dl.dropboxusercontent.com/s/zqtw0tzshfp1c9l/demo.mp4) をご覧下さい

## 動作環境

Python3.6以上

## インストール

```
$ pip install git+https://github.com/tadashi-aikawa/gtfsjp-cli.git
```

Pipenvの場合はeggの指定が必要です。

```
$ pipenv install git+https://github.com/tadashi-aikawa/gtfsjp-cli.git#egg=gtfsjp-cli
```

## 開発者向け

### 動作要件

* pipenv

### コマンド

#### 仮想環境作成とActivate

```
$ pipenv install -d
$ pipenv shell
```

### アーキテクチャ

[![](https://cacoo.com/diagrams/FaXrS1rZ5c7SUxiF-4B5CE.png)](https://cacoo.com/diagrams/FaXrS1rZ5c7SUxiF/4B5CE)
