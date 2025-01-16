import streamlit as st
import cv2
import mediapipe as mp
import matplotlib.pyplot as plt
import numpy as np
import tempfile
import os
from io import BytesIO
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

# CSS を使用して画像を中央ぞろえにする
st.markdown(
    """
    <style>
    .centered {
        display: flex;
        justify-content: center;
        align-items: center;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Streamlit UI設定
st.write("## 動画解析: 手首と肩の位置プロット")
st.sidebar.header("設定")

# ファイルアップロード
uploaded_file = st.file_uploader("動画ファイルをアップロードしてください", type=["mp4", "avi", "mov"])

if uploaded_file is not None:
    # アップロードされた動画をメモリに読み込む
    video_bytes = uploaded_file.read()

    # 一時的にメモリに保存した動画を処理
    input_video_path = '/tmp/input_video.mp4'
    with open(input_video_path, "wb") as f:
        f.write(video_bytes)

    st.sidebar.success("動画がアップロードされました。解析を開始します。")

    # MediaPipe Pose 初期化
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils

    # データ保存用
    frame_numbers = []
    right_shoulder_y = []
    left_shoulder_y = []

    # 動画読み込み
    cap = cv2.VideoCapture(input_video_path)
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # プロットのサイズを設定
    plot_width = 300
    plot_height = frame_height

    # 合成動画設定
    combined_width = frame_width + plot_width
    combined_height = max(frame_height, plot_height)

    # メモリ内での出力動画の作成
    memory_output = BytesIO()

    # VideoWriterを使って出力動画を作成
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # MP4形式で書き込み
    out = cv2.VideoWriter(memory_output, fourcc, fps, (combined_width, combined_height))

    # 進捗バーを表示
    progress_bar = st.progress(0)
    st.info("動画を解析中です。しばらくお待ちください...")

    # Pose インスタンス作成
    with mp_pose.Pose(static_image_mode=False, model_complexity=1, enable_segmentation=False) as pose:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_number = int(cap.get(cv2.CAP_PROP_POS_FRAMES))

            # フレームをRGBに変換して処理
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(image_rgb)

            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark
                right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
                left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]

                # データ保存
                frame_numbers.append(frame_number)
                right_shoulder_y.append(right_shoulder.y)
                left_shoulder_y.append(left_shoulder.y)

                # 骨格を描画
                mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

            # グラフ作成
            fig, ax = plt.subplots(figsize=(3, plot_height / 100), dpi=100)
            ax.plot(frame_numbers, [1 - y for y in right_shoulder_y], label="Right Shoulder Y", color="blue")
            ax.plot(frame_numbers, [1 - y for y in left_shoulder_y], label="Left Shoulder Y", color="green")
            ax.legend()
            ax.set_xlim(0, max(total_frames, frame_number + 10))
            ax.set_ylim(0, 1)
            ax.set_xlabel("Frame Number")
            ax.set_ylabel("Normalized Y Coordinate")
            plt.tight_layout()

            # FigureCanvasでグラフを画像として保存
            canvas = FigureCanvas(fig)
            canvas.draw()
            plot_image = np.frombuffer(canvas.buffer_rgba(), dtype=np.uint8)
            plot_image = plot_image.reshape(canvas.get_width_height()[::-1] + (4,))
            plot_image = cv2.cvtColor(plot_image, cv2.COLOR_RGBA2BGR)
            plt.close(fig)

            # グラフ画像とフレームを横に連結
            plot_image_resized = cv2.resize(plot_image, (plot_width, plot_height))
            combined_frame = np.hstack((frame, plot_image_resized))

            # 合成フレームを保存
            out.write(combined_frame)

            # 進捗バー更新
            progress = int((frame_number / total_frames) * 100)
            progress_bar.progress(progress)

        cap.release()
        out.release()

    # 解析完了メッセージ
    progress_bar.empty()
    st.success("解析が完了しました！")

    # メモリ内での動画を表示
    memory_output.seek(0)  # ポインタを先頭に戻す
    st.video(memory_output)

    # 一時ファイルをクリーンアップ
    os.remove(input_video_path)
    st.info("一時ファイルをクリーンアップしました。")
