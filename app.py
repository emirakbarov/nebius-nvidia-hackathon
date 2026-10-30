import streamlit as st
import yt_dlp
from pipeline import check_transcript, check_video, check_link
from pathlib import Path

#for tomorrow: https://www.instagram.com/reels/DYcARZXt8ly/

st.title("ShortCheck - Check Short-form Videos for Misinformation")
st.caption("ShortCheck checks the factual claims in a video against web sources. "
           "It is not a judgement of the video's overall message.")

mode = st.radio("How do you want to upload a video?",
                ["Upload a file", "Paste a link", "Paste a transcript"],
                horizontal=True)

if mode == "Upload a file":
    uploaded = st.file_uploader("Upload a reel", type=["mp4"])
elif mode == "Paste a link":
    uploaded = st.text_input("Paste a link")
else:
    uploaded = st.text_area("Paste a transcript")

if st.button("Submit"):
    if not uploaded:
        st.warning("Please provide a video, link or transcript first.")
    else:
        try:
            with st.spinner("Checking... this can take a minute."):
                if mode == "Upload a file":
                    with open("upload.mp4", "wb") as f:
                        f.write(uploaded.getbuffer())
                    try:
                        st.session_state["verdicts"] = check_video("upload.mp4")
                    finally:
                        Path("upload.mp4").unlink(missing_ok = True)
                elif mode == "Paste a link":
                    st.session_state["verdicts"] = check_link(uploaded)
                else:
                    st.session_state["verdicts"] = check_transcript(uploaded)
        except yt_dlp.utils.DownloadError:
            st.error("Couldn't download this link. The platform may be blocking it. "
                     "Please download the video and upload the file instead.")

VERDICT_BOXES = {
    "True": st.success,
    "False": st.error,
    "Exaggerated": st.warning,
    "Can't determine": st.info,
}

if "verdicts" in st.session_state:
    verdicts = st.session_state["verdicts"]

    if not verdicts:
        st.info("No checkable factual claims were found in this video.")

    for v in verdicts:
        st.divider()
        st.subheader(v.get("claim", ""))

        label = v.get("verdict", "Error")
        show_box = VERDICT_BOXES.get(label, st.info)
        show_box(f"**{label}**")

        st.write(v.get("explanation", ""))

        sources = v.get("source_details", [])
        if sources:
            with st.expander("Sources"):
                for i, s in zip(v.get("sources", []), sources):
                    st.markdown(f"[{i}] [{s.get('title', 'Untitled')}]({s.get('url', '')})")