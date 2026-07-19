import numpy as np
import scipy.signal as signal
import soundfile as sf
from pydub import AudioSegment
import os

def apply_famicom_polyphonic_stable(input_path):
    print(f"解析中 (DSi直撮り質感再現・安定化型): {os.path.basename(input_path)}")
    try:
        audio = AudioSegment.from_file(input_path)
        audio = audio.set_channels(1)
        samplerate = audio.frame_rate
        samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
        
        data = samples / np.max(np.abs(samples))

        target_sr = 16000
        data_resampled = signal.resample(data, int(len(data) * target_sr / samplerate))
        
        frame_size = int(target_sr / 60) # 60Hz
        num_frames = len(data_resampled) // frame_size

        output = np.zeros_like(data_resampled)
        
        # ユーザー調整済みの黄金比をベースに設定！
        channels_info = [
            {"name": "Bass",    "vol": 0.02}, # ベース
            {"name": "Square1", "vol": 0.04}, # メロディ（主旋律）
            {"name": "Square2", "vol": 0.03}  # 伴奏・和音（副旋律）
        ]
        
        num_channels = len(channels_info)
        channel_phases = np.zeros(num_channels)
        is_channel_on = np.zeros(num_channels, dtype=bool)
        last_stable_freqs = np.zeros(num_channels) # 安定化した音程を記憶
        
        n_fft = 2048

        print("DSiの空気感を再現しつつ、音程のジャンプ（ガタつき）を抑制中...")

        def get_closest_famicom_freq(raw_freq):
            if raw_freq < 40 or raw_freq > 3000:
                return 0
            note = round(12 * np.log2(raw_freq / 440.0) + 69)
            return 440.0 * (2.0 ** ((note - 69) / 12.0))

        def get_precise_freq(fft_array, peak_idx, freqs):
            if 0 < peak_idx < len(fft_array) - 1:
                a, b, c = fft_array[peak_idx - 1], fft_array[peak_idx], fft_array[peak_idx + 1]
                denom = a - 2 * b + c
                if denom != 0:
                    p = 0.5 * (a - c) / denom
                    return (peak_idx + p) * (target_sr / n_fft)
            return freqs[peak_idx]

        for i in range(num_frames):
            start = i * frame_size
            end = start + frame_size
            frame = data_resampled[start:end]

            fft_data = np.abs(np.fft.rfft(frame * np.hanning(frame_size), n=n_fft))
            frequencies = np.fft.rfftfreq(n_fft, d=1.0/target_sr)

            frame_output = np.zeros(frame_size)
            detected_peaks = [ (0, 0) ] * 3 

            # --------------------------------------------------
            # 1. Bass抽出 (80〜280Hz)
            # --------------------------------------------------
            bass_mask = (frequencies >= 80) & (frequencies < 280)
            bass_fft = fft_data.copy()
            bass_fft[~bass_mask] = 0
            
            # 低音も前回の周波数を少し優遇して安定させる
            if last_stable_freqs[0] > 0:
                prev_f = last_stable_freqs[0]
                bias_mask = (frequencies >= prev_f * 0.9) & (frequencies <= prev_f * 1.1)
                bass_fft[bias_mask] *= 2.0

            bass_peak_idx = np.argmax(bass_fft)
            if bass_fft[bass_peak_idx] > 0:
                p_freq = get_precise_freq(bass_fft, bass_peak_idx, frequencies)
                p_amp = bass_fft[bass_peak_idx] / frame_size
                detected_peaks[0] = (p_freq, p_amp)

            # --------------------------------------------------
            # 2. メロディ＆伴奏抽出 (280〜1800Hz)
            # --------------------------------------------------
            treble_mask = (frequencies >= 280) & (frequencies < 1800)
            treble_fft = fft_data.copy()
            treble_fft[~treble_mask] = 0
            
            # 🔥【強化】前回の音の周辺を強力にえこひいき（3倍）してガタつきをブロック！
            for ch in [1, 2]:
                if last_stable_freqs[ch] > 0:
                    prev_f = last_stable_freqs[ch]
                    bias_mask = (frequencies >= prev_f * 0.92) & (frequencies <= prev_f * 1.08)
                    treble_fft[bias_mask] *= 3.0

            # ピーク（山の頂上）を検出
            peaks, _ = signal.find_peaks(treble_fft, distance=6) # 距離を少し広げて別々の音に固定
            
            if len(peaks) > 0:
                peaks = sorted(peaks, key=lambda x: treble_fft[x], reverse=True)
                
                # 1位の山（主旋律）
                p_freq_1 = get_precise_freq(treble_fft, peaks[0], frequencies)
                p_amp_1 = treble_fft[peaks[0]] / frame_size
                detected_peaks[1] = (p_freq_1, p_amp_1)
                
                # 2位の山（伴奏）
                if len(peaks) > 1:
                    p_freq_2 = get_precise_freq(treble_fft, peaks[1], frequencies)
                    p_amp_2 = treble_fft[peaks[1]] / frame_size
                    detected_peaks[2] = (p_freq_2, p_amp_2 * 1.2) 

            # --------------------------------------------------
            # 3. 音の生成処理（キレのあるカクカク波形 ＋ チャタリング防止）
            # --------------------------------------------------
            for ch in range(3):
                p_freq, p_amp = detected_peaks[ch]
                band = channels_info[ch]
                
                # 音量のバタつきを防ぐヒステリシス
                th_on = 0.0015
                th_off = 0.0007
                threshold = th_off if is_channel_on[ch] else th_on
                
                if p_amp > threshold and p_freq > 0:
                    is_channel_on[ch] = True
                    current_freq = get_closest_famicom_freq(p_freq)
                    
                    # 音程が検出できている間、前回の周波数として記憶
                    if current_freq > 0:
                        last_stable_freqs[ch] = current_freq
                    
                    raw_vol = np.clip(p_amp * band["vol"] * 25, 0, band["vol"])
                else:
                    is_channel_on[ch] = False
                    current_freq = 0
                    last_stable_freqs[ch] = 0
                    raw_vol = 0

                if raw_vol > 0 and current_freq > 0:
                    d_phase = 2 * np.pi * current_freq / target_sr
                    frame_phases = channel_phases[ch] + d_phase * np.arange(frame_size)
                    
                    # 完全な矩形波
                    wave = np.sign(np.sin(frame_phases))
                    channel_phases[ch] = (channel_phases[ch] + d_phase * frame_size) % (2 * np.pi)
                    
                    # 四角い4段階音量
                    norm_vol = raw_vol / band["vol"]
                    quantized_norm_vol = np.round(norm_vol * 3) / 3.0
                    final_vol = quantized_norm_vol * band["vol"]
                    
                    frame_output += wave * final_vol

            output[start:end] = frame_output

        final_output = np.clip(output, -1.0, 1.0)
        save_path = os.path.splitext(input_path)[0] + "_dsi_perfect_poly.wav"
        sf.write(save_path, final_output, target_sr)
        
        print(f"【DSi風・安定化ポリフォニック版】書き出し完了しました！\n{save_path}\n")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    filename = ".mp3" 
    music_dir = "/"
    input_file = os.path.join(music_dir, filename)
    
    if os.path.exists(input_file):
        apply_famicom_polyphonic_stable(input_file)
    else:
        print(f"ファイルが見つかりません: {input_file}")
