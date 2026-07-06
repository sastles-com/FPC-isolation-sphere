---
title: "ファームウェア: ESP32-S3で800個のLEDとIMU姿勢補正"
emoji: "🧠"
type: "tech"
topics: ["ESP32", "PlatformIO", "FastLED", "IMU", "組み込み"]
published: false
---

> **アウトライン（詳細）** — ソフト1本目。球の中で動くESP32ファーム。
> 元ネタ: `/Users/katano/work/sastle-isolation-sphere/core/` (src/, doc/) / README

## 1. ハードウェアと開発環境
- M5Atom S3R（ESP32-S3, 8MB Flash / 8MB PSRAM）、PlatformIO + C++
- なぜS3R: PSRAMで画像バッファ、デュアルコアで描画と通信を分離
- マネージャ構成: LED/IMU/Image/Network/Gesture/Sound/Config Manager

## 2. 800 LEDをどう駆動するか
- FastLED、5並列出力（5ストリップ×160、記事02のチェーン構成と一致）
- `core/data/led_layout.csv` = 記事02でエクスポートした `shared/led_positions.csv`
  - FaceID/strip/strip_num/x,y,z をファームが座標マッピングに使う（シリーズの伏線回収）
- 電流対策: 全白禁止 + 輝度上限（記事04の給電トポロジと連動）

## 3. デュアルコア設計
- Core0/Core1の役割分担（描画 vs 通信/デコード）
- 元ネタ: `core/doc/dual_core_design.md`
- フレーム供給が詰まらないためのバッファリング戦略

## 4. UDPで映像を受ける —— 画像プロトコル
- 制御はMQTT、映像はUDP（帯域最適化）の使い分け
- `ImageManager`: UDP受信→デコード→フレームバッファ
- 元ネタ: `core/doc/udp_image_protocol.md` / `image_manager_design.md`

## 5. IMU姿勢補正 —— 常に正立する地球儀
- BNO055でクォータニオン取得→映像を回転補正し、球を回しても上が上
- 球面座標(led_layout)とIMUクォータニオンを使った回転マッピング
- 元ネタ: `core/doc/imu_compensation.md`

## 6. ネットワークとジェスチャー
- WiFi STA、MQTT購読(制御/状態)、UDP受信(映像)
- GestureManager（IMUベースの操作）、SoundManager
- ConfigManager（config.jsonで設定外出し）

## 7. 球面マッピングの勘所
- 2D映像 → 球面800点へのサンプリング（FaceID/xyzの使い方）
- 記事02のCSVが「設計データ」から「実行時データ」になる接続点
