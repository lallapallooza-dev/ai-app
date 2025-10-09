import streamlit as st

st.title("📁 フォルダベースカテゴリー分け説明")

st.write("""
## フォルダベースカテゴリー分けの仕組み

このアプリでは、`src/streamlit/pages/` ディレクトリ内にカテゴリー別のフォルダを作成して、
アプリを整理しています。

### 現在のフォルダ構造

```
src/streamlit/pages/
├── SNS投稿系/
│   ├── X投稿作成.py
│   ├── X投稿.py
│   └── Threads投稿.py
├── YouTube系/
│   ├── YouTubeノウハウ要約.py
│   └── YouTube動画リスト作成.py
├── 投資・株価系/
│   ├── 株価取得.py
│   └── 決算投資判断.py
├── その他/
│   ├── WPテスト.py
│   └── 各種サンプルファイル
└── wp_test/
    └── WordPress関連ファイル
```

### メリット

1. **物理的な整理**: ファイルが実際のフォルダで分類される
2. **視覚的な分かりやすさ**: フォルダ名がそのままカテゴリー名になる
3. **拡張性**: 新しいカテゴリーの追加が簡単
4. **保守性**: ファイルの移動・整理が直感的

### 新しいカテゴリーの追加方法

1. `src/streamlit/pages/` に新しいフォルダを作成
2. フォルダ名を日本語で分かりやすく命名
3. 該当するアプリファイルをフォルダに移動
4. `main.py` の `CATEGORIES` 辞書に表示名を追加（必要に応じて）

### 例：新しいカテゴリー「データ分析系」を追加する場合

```bash
# 1. フォルダ作成
mkdir "src/streamlit/pages/データ分析系"

# 2. ファイル移動
mv "分析アプリ.py" "src/streamlit/pages/データ分析系/"

# 3. main.pyに表示名を追加（オプション）
CATEGORIES = {
    # ... 既存のカテゴリー ...
    "データ分析系": "📊 データ分析系"
}
```

### 注意点

- フォルダ名は日本語でも英語でも使用可能
- ファイル名の変更は避ける（既存のリンクが壊れる可能性）
- 新しいフォルダを作成したら、必ずアプリを再起動する
""")

# 現在のカテゴリー一覧を表示
st.subheader("📋 現在のカテゴリー一覧")

categories_info = {
    "📱 SNS投稿系": "X、ThreadsなどのSNS投稿関連アプリ",
    "📺 YouTube系": "YouTube動画の分析・要約関連アプリ", 
    "📈 投資・株価系": "株価取得・投資判断関連アプリ",
    "🔧 その他": "その他のユーティリティアプリ",
    "🌐 WordPress": "WordPress関連のテスト・管理アプリ"
}

for category, description in categories_info.items():
    with st.expander(category, expanded=False):
        st.write(description)
