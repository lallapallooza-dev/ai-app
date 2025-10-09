import streamlit as st
import subprocess
import sys
import os

st.title("カテゴリー分け実装版")

# カテゴリーとファイルのマッピング
app_categories = {
    "SNS投稿系": {
        "X投稿作成": "X投稿作成.py",
        "X投稿": "X投稿.py", 
        "Threads投稿": "Threads投稿.py"
    },
    "YouTube系": {
        "YouTubeノウハウ要約": "YouTubeノウハウ要約.py",
        "YouTube動画リスト作成": "YouTube動画リスト作成.py"
    },
    "投資・株価系": {
        "株価取得": "株価取得.py",
        "決算投資判断": "決算投資判断.py"
    },
    "その他": {
        "WPテスト": "WPテスト.py"
    }
}

# サイドバーでカテゴリー分け
with st.sidebar:
    st.header("📁 アプリカテゴリー")
    
    # 各カテゴリーをエクスパンダーで表示
    for category_name, apps in app_categories.items():
        with st.expander(f"📂 {category_name}", expanded=(category_name == "SNS投稿系")):
            for app_name, file_name in apps.items():
                if st.button(f"📱 {app_name}", key=f"btn_{file_name}"):
                    # ファイルの存在確認
                    file_path = os.path.join(os.path.dirname(__file__), file_name)
                    if os.path.exists(file_path):
                        st.success(f"{app_name}を起動します...")
                        # 実際の実装では、ここでページ遷移やアプリ起動の処理を行う
                        st.info(f"ファイルパス: {file_path}")
                    else:
                        st.error(f"ファイルが見つかりません: {file_path}")

# メインコンテンツ
st.write("### 利用可能なアプリ一覧")

# カテゴリー別にアプリ一覧を表示
for category_name, apps in app_categories.items():
    st.subheader(f"📂 {category_name}")
    cols = st.columns(2)
    for i, (app_name, file_name) in enumerate(apps.items()):
        with cols[i % 2]:
            st.write(f"• {app_name}")

st.write("---")
st.write("サイドバーからアプリを選択してください。")
