---
title: "制御サーバーとWebUI: 映像配信と操作系"
emoji: "🎛️"
type: "tech"
topics: ["FastAPI", "React", "MQTT", "WebSocket", "Python"]
published: false
---

> **アウトライン（詳細）** — ソフト2本目。球の外から操る制御基盤。
> 元ネタ: `/Users/katano/work/sastle-isolation-sphere/server/` (app/, frontend/, joystick/, video/) / docs/

## 1. サーバーの役割と構成
- Ubuntu MiniPC / Raspberry Pi 4+ で動作
- FastAPI(REST/WebSocket) + React WebUI(Vite) + MQTT Broker + StateManager
- 通信の住み分け: 制御/状態=MQTT、映像=UDP、UI同期=WebSocket

## 2. 状態管理（StateManager）
- 球の状態（再生中・輝度・姿勢など）を一元管理
- MQTTで ESP32 ⇄ サーバー ⇄ WebUI を同期
- 元ネタ: `server/app/services/`

## 3. 映像配信デーモン（video/）
- 2D映像/プレイリストを生成し、UDPでESP32へストリーミング
- ※実装予定の領域は「予定」と明記（正直に）
- プレイリスト設計: `docs/playlist_system_design.md`

## 4. WebUI（React）
- スマホ/タブレット/PC対応、スワイプでタブナビゲーション
- モバイル最適化（URLバー自動非表示、viewport）
- **IMUクォータニオンによる3D球体可視化**（記事05のIMUと接続）
- 元ネタ: `server/frontend/src/`（components/contexts/pages）

## 5. 物理ジョイスティック対応（joystick/）
- USBジョイスティックデーモン: device_manager → mapper → MQTT
- WebUIと物理操作の二系統入力をStateManagerで統合

## 6. セットアップと運用
- ESP32専用APの構築（setup_network.sh）、systemd常駐（setup_services.sh）
- 元ネタ: `server/scripts/` / `migration_guide_ubuntu.md`

## 7. システムを一周して見せる
- WebUIで操作 → MQTT → サーバー → UDP映像 → ESP32 → 800 LED → IMUで姿勢補正
- 記事00の全体像図をここで「動く形」として回収（シリーズの締め）
