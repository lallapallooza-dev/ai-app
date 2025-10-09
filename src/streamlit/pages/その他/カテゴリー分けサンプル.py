import streamlit as st

st.title("カテゴリー分けサンプル")

# サイドバーでカテゴリー選択
with st.sidebar:
    st.header("📁 カテゴリー選択")
    
    # カテゴリーを定義
    categories = {
        "SNS投稿系": ["X投稿作成", "X投稿", "Threads投稿"],
        "YouTube系": ["YouTubeノウハウ要約", "YouTube動画リスト作成"],
        "投資・株価系": ["株価取得", "決算投資判断"],
        "その他": ["WPテスト"]
    }
    
    # カテゴリー選択
    selected_category = st.selectbox(
        "カテゴリーを選択してください",
        list(categories.keys())
    )
    
    # 選択されたカテゴリーのアプリ一覧を表示
    st.subheader(f"📂 {selected_category}")
    for app in categories[selected_category]:
        if st.button(f"📱 {app}", key=f"btn_{app}"):
            st.info(f"{app}が選択されました")

# メインコンテンツ
st.write("選択されたカテゴリー:", selected_category)
st.write("利用可能なアプリ:", categories[selected_category])
