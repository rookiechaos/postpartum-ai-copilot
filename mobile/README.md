# Postpartum AI Copilot - Mobile App (React Native)

原生移动应用 - iOS 和 Android

## 技术栈

- **React Native**: 0.73.0
- **React Navigation**: 导航
- **Zustand**: 状态管理
- **Axios**: API 调用

## 项目结构

```
mobile/
├── src/
│   ├── screens/          # 屏幕组件
│   │   ├── HomeScreen.js
│   │   ├── ChatScreen.js
│   │   ├── TrackingScreen.js
│   │   ├── CommunityScreen.js
│   │   └── ProfileScreen.js
│   ├── components/       # 可复用组件
│   ├── navigation/       # 导航配置
│   ├── services/         # API 服务
│   ├── store/            # 状态管理
│   ├── utils/            # 工具函数
│   └── constants/        # 常量配置
├── android/              # Android 原生代码
├── ios/                  # iOS 原生代码
├── package.json
└── app.json
```

## 快速开始

### 安装依赖

```bash
cd mobile
npm install
```

### iOS 运行

```bash
cd ios
pod install
cd ..
npx react-native run-ios
```

### Android 运行

```bash
npx react-native run-android
```

## 功能

- ✅ AI 聊天
- ✅ 追踪功能
- ✅ 社区功能
- ✅ 推送通知
- ✅ 离线支持

## 开发状态

🚧 **开发中** - 基础框架已创建，功能正在实现中
