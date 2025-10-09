import streamlit as st

st.title("エクスパンダーカテゴリー分け")

# サイドバーでカテゴリー分け
with st.sidebar:
    st.header("📁 アプリカテゴリー")
    
    # SNS投稿系
    with st.expander("📱 SNS投稿系", expanded=True):
        if st.button("X投稿作成", key="x_create"):
            st.info("X投稿作成アプリに移動します")
        if st.button("X投稿", key="x_post"):
            st.info("X投稿アプリに移動します")
        if st.button("Threads投稿", key="threads"):
            st.info("Threads投稿アプリに移動します")
    
    # YouTube系
    with st.expander("📺 YouTube系", expanded=False):
        if st.button("YouTubeノウハウ要約", key="yt_summary"):
            st.info("YouTubeノウハウ要約アプリに移動します")
        if st.button("YouTube動画リスト作成", key="yt_list"):
            st.info("YouTube動画リスト作成アプリに移動します")
    
    # 投資・株価系
    with st.expander("📈 投資・株価系", expanded=False):
        if st.button("株価取得", key="stock_price"):
            st.info("株価取得アプリに移動します")
        if st.button("決算投資判断", key="investment"):
            st.info("決算投資判断アプリに移動します")
    
    # その他
    with st.expander("🔧 その他", expanded=False):
        if st.button("WPテスト", key="wp_test"):
            st.info("WPテストアプリに移動します")

# メインコンテンツ
st.write("サイドバーのカテゴリーからアプリを選択してください")
