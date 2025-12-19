# ----------------
# Importations
# ----------------
import pandas as pd
import streamlit as st
import tempfile
import os
import pathlib
import pandas as pd
from main import compress_file, decompress_file, tree_to_dot

# ------------------------
#   Streamlit App
# ------------------------
# Function to load CSS
def load_css(file_path):
    with open(file_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
# Load the external CSS
css_path = pathlib.Path("dsa-cep/style.css")
load_css(css_path)

st.set_page_config(page_title="File Compressor", layout="centered")
st.title("File Compression Studio 🗃")

current_dir = os.path.dirname(__file__)
image_path = os.path.join(current_dir, "my_image.png")  # split path parts

if os.path.exists(image_path):
    st.image(image_path, caption="My Image", use_column_width=True)
else:
    st.error(f"Image not found: {image_path}")



# ---------------------
#    Instructions
# ---------------------
st.subheader("1) Instructions")

st.markdown("""
*How to Use This File Compression Tool*  

1. Upload a file using the button below.  
2. .huff files → decompressed automatically.  
3. Other files → compressed automatically.  
4. Click *Process File to start.*  
5. Download your file after processing.
""")
st.divider()
# -------------------
# file Uploading
# -------------------
st.subheader("2) File Uploader")
uploaded_file = st.file_uploader("Upload a file", type=None)
if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name
    st.success(f"Uploaded file: {uploaded_file.name} ({os.path.getsize(tmp_path)} bytes)")

    action = st.radio("**Choose Action**", ["Compress", "Decompress"])

    if st.button("Process File"):
        st.divider()
        try:
            with st.spinner(f"{action}ing file..."):
                out_suffix = ".huff" if action == "Compress" else "_restored"
                out_path = tmp_path + out_suffix

                # ------------------
                #  File Compression
                # ------------------
                if action == "Compress":
                    root, stats = compress_file(tmp_path, out_path)

                    st.subheader("3) Compression Summary")
                    col1, col2, col3 = st.columns(3)

                    # If compress_file decided to skip (already compressed type or .huff), show note
                    if stats.get("skipped", False):
                        st.warning(stats.get("note", "Compression skipped."))
                        # still show basic sizes so user knows what happened
                        col1.metric("Original Size", f"{stats.get('original_bytes', 0)} bytes")
                        col2.metric("Compressed Size",
                                    f"{stats.get('compressed_bytes', stats.get('original_bytes', 0))} bytes")
                        col3.metric("Space Saved", "N/A")
                        # show timing if present
                       # st.markdown(f"**Note**: {stats.get('note')}")
                        st.markdown(
                            f"**Time (read)**: {stats.get('time_read', 0):.4f}s, **Total**: {stats.get('time_total', 0):.4f}s")
                    else:
                        # safe display for values that may be None (empty file case)
                        original = stats.get('original_bytes', 0)
                        compressed = stats.get('compressed_bytes', 0)
                        space_saved = stats.get('space_saved_percent')
                        ratio = stats.get('compression_ratio')

                        col1.metric("**Original Size**", f"{original} bytes")
                        col2.metric("**Compressed Size**", f"{compressed} bytes")

                        if space_saved is None:
                            col3.metric("Space Saved", "N/A")
                        else:
                            col3.metric("Space Saved", f"{space_saved:.2f}%")

                        # Compression ratio: use provided safe field if present
                        if ratio is None:
                            st.markdown("*Compression ratio: N/A (empty file)*")
                        else:
                            st.markdown(f"*Compression ratio: {ratio:.4f}*")

                        st.markdown(f"*Unique symbols: {stats.get('unique_symbols', 0)}*")
                        st.markdown(f"*Padding bits: {stats.get('pad_count')}*")

                        timings = {
                            "Read File": stats.get('time_read', 0),
                            "Build Tree": stats.get('time_tree_build', 0),
                            "Make Codes": stats.get('time_codes', 0),
                            "Encode & Pack": stats.get('time_pack', 0),
                            "Write File": stats.get('time_write', 0),
                            "Total": stats.get('time_total', 0),
                        }
                        df = pd.DataFrame(list(timings.items()),
                                          columns=["Step", "Time (s)"])
                        st.divider()
                        st.subheader("4) Processing Timings")
                        st.table(df)
                        st.divider()
                        st.subheader("5) Huffman Tree")
                        # Only show the tree if we actually have one
                        if root is not None:
                            try:
                                dot = tree_to_dot(root)
                                st.graphviz_chart(dot)
                            except Exception as e:
                                st.error(f"Could not render tree: {e}")
                        else:
                            st.info("No Huffman tree (empty file).")

                else:
                    try:
                        # ----------------------
                        # File Decompression
                        # ---------------------
                        stats = decompress_file(tmp_path, out_path)
                        st.subheader("3) Decompression Report")
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Compressed file size", f"{stats['compressed_size']} bytes")
                        col2.metric("Restored file size", f"{stats['restored_size']} bytes")
                        col3.metric("Padding bits", f"{stats['pad_count']}")
                        timings = {
                            "Read File": stats['time_read'],
                            "Remove Padding": stats['time_unpad'],
                            "Rebuild Tree": stats['time_tree'],
                            "Make Decode": stats['time_decode'],
                            "Rewrite file": stats['time_write'],
                            "Total": stats['time_total'],
                        }
                        df = pd.DataFrame(list(timings.items()),
                                          columns=["Step", "Time (s)"])
                        st.divider()
                        st.subheader("4) Processing Timings")
                        st.table(df)
                    except ValueError as e:
                        # "Not a .huff file (magic mismatch)"
                        st.error(f"Error: {str(e)}")
                    except Exception as e:
                        # 🔥 Any unexpected bug
                        st.error(f"Unexpected Error:{str(e)}")

            # If compress was skipped, comp function may not have created out_path file.
            if os.path.exists(out_path):
                with open(out_path, 'rb') as f:
                    # ------------------------
                    #   File Downloding
                    # ------------------------
                    st.divider()
                    st.subheader("Download Button")
                    st.info(f" Download your {action}ed file here.")
                    st.download_button(
                        label=f"{os.path.basename(out_path)}",
                        data=f.read(),
                        file_name=os.path.basename(out_path),
                        mime="application/octet-stream"
                    )
            else:
                # If output file doesn't exist, show clear message
                st.info("No output file was produced (compression may have been skipped). Check the message above.")

        finally:
            # cleanup
            try:
                os.remove(tmp_path)
            except Exception:
                pass
            try:
                if os.path.exists(out_path):
                    os.remove(out_path)
            except Exception:
                pass
