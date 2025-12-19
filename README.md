# File Compression Studio 🗃

A **lossless file compression tool** built as a key academic project in the third semester of my Computer Systems Engineering program. This project showcases the practical application of **Data Structures and Algorithms (DSA)** to real-world file compression and decompression.

---

## Features

- **Lossless Compression & Decompression:** Safely reduces file size without losing data.
- **Huffman Coding:** Generates optimal prefix codes based on character frequency.
- **Min-Heap (Priority Queue):** Efficiently builds the Huffman tree.
- **Binary Tree Implementation:** Represents the Huffman tree for encoding and decoding.
- **Bit-Level I/O Operations:** Reads and writes data at the bit level for maximum compression.
- **Interactive Streamlit Web App:** Seamless user interface for both compression and decompression.
- **Compression Report:** Displays original size, compressed size, space saved, and processing timings.

---

## Getting Started

### Prerequisites

- Python 3.10+  
- Streamlit  

Install dependencies with:

```bash
pip install -r requirements.txt
```
Running the App

1. Clone the repository:

git clone <your-repo-link>
cd file-compression-utility

2. Run the Streamlit app:
```bash
streamlit run app.py
```
3. Upload a file:

.huff files → automatically decompressed

Other files → automatically compressed

4. Click Process File and download your result.

---

Project Details

Core Objective: Design a lossless compression tool to reduce file size efficiently.

Key Algorithms & Data Structures:

Huffman Coding (Greedy algorithm)

Min-Heap / Priority Queue

Binary Trees

Bit-Level File Handling

Achievements:

Compression ratios of 40–60% depending on file entropy.

Hands-on experience with DSA concepts in a real-world context.

Interactive Streamlit interface with clear metrics and download options.


---

Live Demo

Access the app live: https://file-compreappr-tool.streamlit.app/

---

Tech Stack

Language: Python 3

Framework: Streamlit

Algorithms: Huffman Coding, Min-Heap, Binary Trees

Visualization: Streamlit metrics and reports


---

License

MIT License © 2025
